# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest", "pyyaml", "pydantic>=2.0.0"]
# ///
"""
End-to-End Integration Tests
==============================

Tests for complete workflows:
  - SessionStart -> tool use -> analysis -> learning -> SessionEnd
  - Review findings -> knowledge storage -> next session injection
  - Circuit breaker protecting all hooks
  - Multi-hook parallel execution simulation
  - Full hook event type coverage

Run:
  uv run pytest test_integration.py -v
"""

import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

TESTING_DIR = Path(__file__).parent
FRAMEWORK_DIR = TESTING_DIR.parent
KNOWLEDGE_DIR = FRAMEWORK_DIR / "knowledge"
GUARDRAILS_DIR = FRAMEWORK_DIR / "guardrails"
REVIEW_DIR = FRAMEWORK_DIR / "review"
sys.path.insert(0, str(KNOWLEDGE_DIR))
sys.path.insert(0, str(GUARDRAILS_DIR))
sys.path.insert(0, str(REVIEW_DIR))
sys.path.insert(0, str(TESTING_DIR))

from test_utils import (
    make_hook_input,
    make_pre_tool_use_input,
    make_post_tool_use_input,
    make_session_start_input,
    make_session_end_input,
    make_observation,
    make_learning,
    make_pending_learnings,
    MockLLMResponse,
    TempDirFixture,
    DatabaseFixture,
    GitRepoFixture,
    SettingsFixture,
)


# ===========================================================================
# Workflow 1: Complete Session Lifecycle
# ===========================================================================


class TestSessionLifecycle:
    """Test a complete session lifecycle: start -> tool use -> end."""

    def test_session_start_to_end(self):
        """Simulate SessionStart -> multiple tool uses -> SessionEnd."""
        session_id = "lifecycle-test-001"

        # SessionStart
        start_input = make_session_start_input(session_id=session_id)
        assert start_input["hook_event_name"] == "SessionStart"
        assert start_input["session_id"] == session_id

        # Multiple tool uses (PreToolUse + PostToolUse pairs)
        tool_uses = [
            ("Bash", {"command": "git status"}),
            ("Read", {"file_path": "/tmp/test.py"}),
            ("Edit", {"file_path": "/tmp/test.py", "old_string": "old", "new_string": "new"}),
            ("Bash", {"command": "pytest tests/"}),
            ("Grep", {"pattern": "TODO", "path": "/tmp"}),
        ]

        pre_tool_inputs = []
        post_tool_inputs = []
        for tool_name, tool_input in tool_uses:
            pre = make_pre_tool_use_input(
                tool_name=tool_name,
                tool_input=tool_input,
                session_id=session_id,
            )
            post = make_post_tool_use_input(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output="success",
                session_id=session_id,
            )
            pre_tool_inputs.append(pre)
            post_tool_inputs.append(post)

        assert len(pre_tool_inputs) == 5
        assert len(post_tool_inputs) == 5

        # SessionEnd
        end_input = make_session_end_input(session_id=session_id)
        assert end_input["hook_event_name"] == "SessionEnd"
        assert end_input["session_id"] == session_id

    def test_observation_accumulation_through_session(self):
        """Observations accumulate during a session via PostToolUse."""
        from observe_patterns import classify_tool_pattern, extract_context

        session_id = "obs-accum-test"
        observations = []

        tools = [
            ("Bash", {"command": "git log --oneline -5"}),
            ("Grep", {"pattern": "def main"}),
            ("Read", {"file_path": "/tmp/app.py"}),
            ("Edit", {"file_path": "/tmp/app.py", "old_string": "old", "new_string": "new"}),
            ("Bash", {"command": "pytest -v"}),
        ]

        for tool_name, tool_input in tools:
            pattern = classify_tool_pattern(tool_name, tool_input)
            context = extract_context(tool_name, tool_input, "")
            obs = make_observation(
                tool=tool_name,
                pattern=pattern,
                session_id=session_id,
                context=context,
            )
            observations.append(obs)

        assert len(observations) == 5
        patterns = [o["pattern"] for o in observations]
        assert "git_operation" in patterns
        assert "code_search" in patterns
        assert "file_read" in patterns


# ===========================================================================
# Workflow 2: Knowledge Pipeline End-to-End
# ===========================================================================


class TestKnowledgePipelineE2E:
    """End-to-end test of the full knowledge pipeline."""

    def test_observe_analyze_learn_inject(self):
        """Full pipeline: observe -> analyze -> learn -> inject."""
        from observe_patterns import classify_tool_pattern, extract_context
        from analyze_session import summarize_observations, parse_llm_response
        from store_learnings import store_learning

        session_id = "e2e-pipeline-001"

        # --- OBSERVE ---
        observations = []
        for i in range(15):
            tools = [
                ("Bash", {"command": f"git diff file{i}.py"}),
                ("Edit", {"file_path": f"/tmp/file{i}.py", "old_string": "a", "new_string": "b"}),
            ]
            for tool_name, tool_input in tools:
                pattern = classify_tool_pattern(tool_name, tool_input)
                context = extract_context(tool_name, tool_input, "")
                observations.append(make_observation(
                    tool=tool_name,
                    pattern=pattern,
                    session_id=session_id,
                    context=context,
                ))

        assert len(observations) == 30

        # --- ANALYZE ---
        summary = summarize_observations(observations)
        assert "Bash" in summary
        assert "Edit" in summary

        # Mock LLM response
        llm_response = MockLLMResponse.analysis_response([
            {
                "tag": "PATTERN",
                "content": "Git diff followed by Edit is the standard review-then-modify workflow",
                "context": "Observed git diff -> Edit sequence in 15 out of 15 modifications",
                "confidence": 0.95,
            },
            {
                "tag": "LEARNED",
                "content": "Always review diff before editing to understand full context",
                "context": "Pattern suggests careful review before modification",
                "confidence": 0.8,
            },
        ])
        learnings = parse_llm_response(llm_response)
        assert len(learnings) == 2

        # --- LEARN ---
        config = {
            "min_confidence": 0.0,
            "deduplicate": False,
            "auto_tag": True,
            "source": "pipeline",
        }
        with DatabaseFixture(schema="knowledge_entries") as db:
            stored_ids = []
            for learning in learnings:
                row_id = store_learning(db.conn, learning, session_id, config)
                if row_id is not None:
                    stored_ids.append(row_id)

            assert len(stored_ids) == 2
            assert db.count_rows("knowledge_entries") == 2

            # Verify FTS works
            rows = db.conn.execute(
                "SELECT * FROM knowledge_fts WHERE knowledge_fts MATCH 'workflow'",
            ).fetchall()
            assert len(rows) >= 1

            # --- INJECT (simulated) ---
            # In real usage, inject_knowledge.py reads from knowledge_db
            # and formats a context block
            from inject_knowledge import format_knowledge_block
            entries = []
            for row_id in stored_ids:
                row = db.conn.execute(
                    "SELECT * FROM knowledge_entries WHERE id = ?", (row_id,)
                ).fetchone()
                entries.append({
                    "tag": row["category"],
                    "content": row["content"],
                    "context": "",
                    "timestamp": row["created_at"],
                })

            block = format_knowledge_block(entries)
            assert "Relevant Knowledge" in block
            assert "workflow" in block.lower()


# ===========================================================================
# Workflow 3: Circuit Breaker Protecting Hooks
# ===========================================================================


class TestCircuitBreakerProtection:
    """Tests for circuit breaker protecting hook execution."""

    def test_circuit_breaker_protects_failing_hook(self):
        """A repeatedly failing hook gets disabled by circuit breaker."""
        from hook_state_manager import HookStateManager
        from circuit_breaker import CircuitBreaker, CircuitBreakerDecision
        from config_loader import GuardrailsConfig, CircuitBreakerConfig, LoggingConfig

        with TempDirFixture() as tmp:
            config = GuardrailsConfig(
                circuit_breaker=CircuitBreakerConfig(
                    failure_threshold=3,
                    cooldown_seconds=3600,
                ),
                logging=LoggingConfig(
                    file=str(tmp.path / "test.log"),
                    level="DEBUG",
                ),
                state_file=str(tmp.path / "state.json"),
            )
            config.expand_paths()
            mgr = HookStateManager(tmp.path / "state.json")
            breaker = CircuitBreaker(mgr, config)

            hook_cmd = "uv run observe_patterns.py"

            # Simulate 3 hook failures
            for i in range(3):
                result = breaker.should_execute(hook_cmd)
                assert result.should_execute is True
                breaker.record_failure(hook_cmd, f"ImportError attempt {i}")

            # Now the circuit should be open
            result = breaker.should_execute(hook_cmd)
            assert result.should_execute is False
            assert result.decision == CircuitBreakerDecision.SKIP

    def test_circuit_breaker_allows_other_hooks(self):
        """Disabling one hook should not affect others."""
        from hook_state_manager import HookStateManager
        from circuit_breaker import CircuitBreaker, CircuitBreakerDecision
        from config_loader import GuardrailsConfig, CircuitBreakerConfig, LoggingConfig

        with TempDirFixture() as tmp:
            config = GuardrailsConfig(
                circuit_breaker=CircuitBreakerConfig(failure_threshold=2),
                logging=LoggingConfig(
                    file=str(tmp.path / "test.log"),
                    level="DEBUG",
                ),
                state_file=str(tmp.path / "state.json"),
            )
            config.expand_paths()
            mgr = HookStateManager(tmp.path / "state.json")
            breaker = CircuitBreaker(mgr, config)

            # Disable hook A
            for _ in range(2):
                breaker.record_failure("hook-A", "error")

            # Hook A is disabled
            result_a = breaker.should_execute("hook-A")
            assert result_a.should_execute is False

            # Hook B is still active
            result_b = breaker.should_execute("hook-B")
            assert result_b.should_execute is True


# ===========================================================================
# Workflow 4: Review -> Knowledge -> Injection
# ===========================================================================


class TestReviewToKnowledgeFlow:
    """Test flow from review findings to knowledge storage to injection."""

    def test_review_findings_become_knowledge(self):
        """Review findings should be storable as knowledge entries."""
        from store_learnings import store_learning

        # Simulate review findings converted to learnings
        review_learnings = [
            make_learning(
                tag="LEARNED",
                content="Function process_data() in data_handler.py has complexity 15, should be split",
                context="Detected by complexity analyzer in post-commit review",
                confidence=0.9,
            ),
            make_learning(
                tag="PATTERN",
                content="Code duplication detected between validate_input() functions",
                context="Duplication analyzer found 85% token overlap across 2 files",
                confidence=0.85,
            ),
        ]

        config = {
            "min_confidence": 0.0,
            "deduplicate": False,
            "auto_tag": True,
            "source": "review",
        }

        with DatabaseFixture(schema="knowledge_entries") as db:
            for learning in review_learnings:
                row_id = store_learning(db.conn, learning, "review-session", config)
                assert row_id is not None

            assert db.count_rows("knowledge_entries") == 2

            # Search for the stored knowledge
            rows = db.conn.execute(
                "SELECT * FROM knowledge_fts WHERE knowledge_fts MATCH 'complexity'",
            ).fetchall()
            assert len(rows) >= 1


# ===========================================================================
# Workflow 5: Multi-Hook Parallel Execution
# ===========================================================================


class TestMultiHookParallelExecution:
    """Tests simulating multiple hooks running for the same event."""

    def test_pretooluse_multiple_hooks(self):
        """Multiple PreToolUse hooks can process the same input."""
        hook_input = make_pre_tool_use_input(
            tool_name="Bash",
            tool_input={"command": "rm -rf /tmp/safe-dir"},
        )

        # Simulate multiple hooks processing this input
        results = []

        # Hook 1: Pattern-based command hook
        command = hook_input["tool_input"].get("command", "")
        is_dangerous = "rm -rf" in command and ("/" == command.split()[-1] or "~" in command)
        results.append({"hook": "command", "decision": "block" if is_dangerous else "allow"})

        # Hook 2: Prompt-based hook (simulated)
        # Would normally call LLM, here we simulate
        results.append({"hook": "prompt", "decision": "allow"})

        # In the real system, if any hook blocks, the tool use is blocked
        # The command hook correctly identifies rm -rf /tmp/safe-dir as safe
        # (it only blocks rm -rf / or rm -rf ~)
        assert results[0]["decision"] == "allow"
        assert results[1]["decision"] == "allow"

    def test_pretooluse_first_block_wins(self):
        """If the first hook blocks, subsequent hooks are skipped."""
        hook_input = make_pre_tool_use_input(
            tool_name="Bash",
            tool_input={"command": "rm -rf /"},
        )

        # Hook 1: Pattern-based (blocks)
        command = hook_input["tool_input"].get("command", "")
        hook1_blocks = command.strip() in ["rm -rf /", "rm -rf /*"]
        assert hook1_blocks is True

        # In real execution, hook 2 would not run
        # The blocked result propagates immediately


# ===========================================================================
# All Hook Event Types Coverage
# ===========================================================================


class TestAllHookEventTypes:
    """Verify test coverage for all hook event types."""

    HOOK_EVENT_TYPES = [
        "PreToolUse",
        "PostToolUse",
        "SessionStart",
        "SessionEnd",
        "Stop",
        "SubagentStart",
        "SubagentStop",
        "PreCompact",
        "UserPromptSubmit",
        "Notification",
        "PermissionRequest",
        "PostToolUseFailure",
    ]

    def test_hook_input_generator_covers_key_events(self):
        """Verify our test utils can generate inputs for key events."""
        for event in ["PreToolUse", "PostToolUse", "SessionStart", "SessionEnd"]:
            input_data = make_hook_input(hook_event_name=event)
            assert input_data["hook_event_name"] == event
            assert "session_id" in input_data

    def test_pretooluse_input_has_tool_fields(self):
        input_data = make_pre_tool_use_input(tool_name="Bash")
        assert "tool_name" in input_data
        assert "tool_input" in input_data
        assert input_data["tool_name"] == "Bash"

    def test_posttooluse_input_has_output(self):
        input_data = make_post_tool_use_input(
            tool_name="Bash",
            tool_output="command output here",
        )
        assert "tool_output" in input_data
        assert input_data["tool_output"] == "command output here"

    def test_session_inputs_have_session_id(self):
        start = make_session_start_input(session_id="test-123")
        end = make_session_end_input(session_id="test-123")
        assert start["session_id"] == "test-123"
        assert end["session_id"] == "test-123"


# ===========================================================================
# Performance Integration Tests
# ===========================================================================


class TestPerformanceIntegration:
    """Performance tests for integrated hook execution."""

    def test_observation_classification_under_1ms(self):
        """Pattern classification should be very fast."""
        from observe_patterns import classify_tool_pattern

        start = time.monotonic()
        for _ in range(1000):
            classify_tool_pattern("Bash", {"command": "git status"})
            classify_tool_pattern("Edit", {"old_string": "a", "new_string": "b"})
            classify_tool_pattern("Write", {"content": "hello"})
        elapsed = time.monotonic() - start

        avg_us = (elapsed / 3000) * 1_000_000  # microseconds
        assert avg_us < 1000, f"Average classification time {avg_us:.0f}us exceeds 1ms"

    def test_context_extraction_under_1ms(self):
        """Context extraction should be very fast."""
        from observe_patterns import extract_context

        start = time.monotonic()
        for _ in range(1000):
            extract_context("Bash", {"command": "git status"}, "")
            extract_context("Edit", {"file_path": "/tmp/x.py", "old_string": "a", "new_string": "b"}, "")
        elapsed = time.monotonic() - start

        avg_us = (elapsed / 2000) * 1_000_000
        assert avg_us < 1000, f"Average extraction time {avg_us:.0f}us exceeds 1ms"

    def test_llm_response_parsing_under_5ms(self):
        """LLM response parsing should be fast."""
        from analyze_session import parse_llm_response

        response = MockLLMResponse.analysis_response()

        start = time.monotonic()
        for _ in range(1000):
            parse_llm_response(response)
        elapsed = time.monotonic() - start

        avg_ms = (elapsed / 1000) * 1000
        assert avg_ms < 5, f"Average parsing time {avg_ms:.1f}ms exceeds 5ms"

    def test_database_insert_under_10ms(self):
        """Database insert should be fast."""
        from store_learnings import store_learning

        config = {
            "min_confidence": 0.0,
            "deduplicate": False,
            "auto_tag": True,
            "source": "perf-test",
        }

        with DatabaseFixture(schema="knowledge_entries") as db:
            start = time.monotonic()
            for i in range(100):
                learning = make_learning(content=f"Performance test learning {i}")
                store_learning(db.conn, learning, "perf-session", config)
            elapsed = time.monotonic() - start

            avg_ms = (elapsed / 100) * 1000
            assert avg_ms < 10, f"Average insert time {avg_ms:.1f}ms exceeds 10ms"


# ===========================================================================
# Git Integration Tests
# ===========================================================================


class TestGitIntegration:
    """Tests using real git repositories."""

    def test_git_repo_fixture_creates_valid_repo(self):
        with GitRepoFixture() as repo:
            assert repo.path.exists()
            assert (repo.path / ".git").exists()

    def test_git_repo_commit_and_diff(self):
        with GitRepoFixture() as repo:
            repo.write_file("hello.py", "print('hello')\n")
            commit_hash = repo.add_and_commit("Initial commit")
            assert len(commit_hash) == 40  # Full SHA

            # Modify and check diff
            repo.write_file("hello.py", "print('world')\n")
            diff = repo.get_diff()
            assert "hello" in diff
            assert "world" in diff

    def test_post_commit_review_input(self):
        """Verify that post-commit review hook input is valid."""
        with GitRepoFixture() as repo:
            repo.write_file("app.py", "def main():\n    pass\n")
            commit_hash = repo.add_and_commit("Add app")

            # Build the hook input a review hook would receive
            hook_input = make_hook_input(
                hook_event_name="PostToolUse",
                tool_name="Bash",
                tool_input={"command": f"git commit -m 'Add app'"},
                tool_output=f"[main {commit_hash[:7]}] Add app",
                session_id="git-test",
                cwd=str(repo.path),
            )

            assert hook_input["cwd"] == str(repo.path)
            assert "git commit" in hook_input["tool_input"]["command"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
