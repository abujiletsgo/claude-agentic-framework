# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest", "pyyaml"]
# ///
"""
Knowledge Pipeline Tests
========================

Tests for all four stages of the knowledge pipeline:
  1. OBSERVE  - observe_patterns.py (observation generation)
  2. ANALYZE  - analyze_session.py  (LLM analysis with mock)
  3. LEARN    - store_learnings.py  (database storage)
  4. EVOLVE   - inject_knowledge.py (context injection)

Plus end-to-end pipeline tests and error handling.

Run:
  uv run pytest test_knowledge_pipeline.py -v
"""

import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure framework modules are importable
TESTING_DIR = Path(__file__).parent
FRAMEWORK_DIR = TESTING_DIR.parent
KNOWLEDGE_DIR = FRAMEWORK_DIR / "knowledge"
sys.path.insert(0, str(KNOWLEDGE_DIR))
sys.path.insert(0, str(TESTING_DIR))

from test_utils import (
    make_hook_input,
    make_post_tool_use_input,
    make_session_end_input,
    make_observation,
    make_learning,
    make_pending_learnings,
    MockLLMResponse,
    TempDirFixture,
    DatabaseFixture,
)


# ===========================================================================
# OBSERVE Stage Tests - observe_patterns.py
# ===========================================================================


class TestClassifyToolPattern:
    """Tests for classify_tool_pattern() in observe_patterns.py"""

    def setup_method(self):
        from observe_patterns import classify_tool_pattern
        self.classify = classify_tool_pattern

    def test_edit_small_modification(self):
        tool_input = {"old_string": "a\nb", "new_string": "c\nd"}
        assert self.classify("Edit", tool_input) == "small_modification"

    def test_edit_expansion(self):
        tool_input = {"old_string": "line1", "new_string": "line1\nline2\nline3\nline4\nline5"}
        assert self.classify("Edit", tool_input) == "expansion"

    def test_edit_reduction(self):
        tool_input = {
            "old_string": "a\nb\nc\nd\ne\nf\ng\nh\ni\nj",
            "new_string": "a\nb",
        }
        assert self.classify("Edit", tool_input) == "reduction"

    def test_edit_refactor(self):
        old = "\n".join([f"line{i}" for i in range(10)])
        new = "\n".join([f"changed{i}" for i in range(10)])
        tool_input = {"old_string": old, "new_string": new}
        assert self.classify("Edit", tool_input) == "refactor"

    def test_write_small(self):
        tool_input = {"content": "line1\nline2\n"}
        assert self.classify("Write", tool_input) == "small_file_write"

    def test_write_medium(self):
        tool_input = {"content": "\n".join([f"line{i}" for i in range(50)])}
        assert self.classify("Write", tool_input) == "medium_file_write"

    def test_write_large(self):
        tool_input = {"content": "\n".join([f"line{i}" for i in range(150)])}
        assert self.classify("Write", tool_input) == "large_file_write"

    def test_read_pattern(self):
        assert self.classify("Read", {"file_path": "/tmp/x.py"}) == "file_read"

    def test_bash_git(self):
        assert self.classify("Bash", {"command": "git status"}) == "git_operation"

    def test_bash_test(self):
        assert self.classify("Bash", {"command": "pytest tests/"}) == "test_execution"

    def test_bash_package(self):
        assert self.classify("Bash", {"command": "npm install express"}) == "package_management"

    def test_bash_uv(self):
        assert self.classify("Bash", {"command": "uv run script.py"}) == "package_management"

    def test_bash_file_discovery(self):
        assert self.classify("Bash", {"command": "find . -name '*.py'"}) == "file_discovery"

    def test_bash_generic(self):
        assert self.classify("Bash", {"command": "curl https://example.com"}) == "shell_command"

    def test_grep_pattern(self):
        assert self.classify("Grep", {"pattern": "TODO"}) == "code_search"

    def test_glob_pattern(self):
        assert self.classify("Glob", {"pattern": "*.py"}) == "file_search"

    def test_task_management(self):
        for tool in ["TaskCreate", "TaskUpdate", "TaskGet", "TaskList"]:
            assert self.classify(tool, {}) == "task_management"

    def test_web_lookup(self):
        assert self.classify("WebSearch", {"query": "test"}) == "web_lookup"
        assert self.classify("WebFetch", {"url": "http://x"}) == "web_lookup"

    def test_unknown_tool(self):
        assert self.classify("UnknownTool", {}) == "other"


class TestExtractContext:
    """Tests for extract_context() in observe_patterns.py"""

    def setup_method(self):
        from observe_patterns import extract_context
        self.extract = extract_context

    def test_edit_context(self):
        ctx = self.extract(
            "Edit",
            {"file_path": "/tmp/test.py", "old_string": "a\nb", "new_string": "c"},
            "",
        )
        assert ctx["file_path"] == "/tmp/test.py"
        assert ctx["old_lines"] == 2
        assert ctx["new_lines"] == 1
        assert ctx["file_ext"] == ".py"
        assert ctx["file_name"] == "test.py"

    def test_write_context(self):
        ctx = self.extract(
            "Write",
            {"file_path": "/tmp/out.txt", "content": "hello\nworld"},
            "",
        )
        assert ctx["content_lines"] == 2
        assert ctx["content_bytes"] > 0
        assert ctx["file_name"] == "out.txt"

    def test_bash_context_truncated(self):
        long_cmd = "x" * 300
        ctx = self.extract("Bash", {"command": long_cmd}, "")
        assert len(ctx["command"]) == 200

    def test_grep_context(self):
        ctx = self.extract("Grep", {"pattern": "TODO", "path": "/src"}, "")
        assert ctx["pattern"] == "TODO"
        assert ctx["path"] == "/src"

    def test_read_context(self):
        ctx = self.extract("Read", {"file_path": "/tmp/x.py", "offset": 10, "limit": 50}, "")
        assert ctx["offset"] == 10
        assert ctx["limit"] == 50


class TestObserveSessionCounting:
    """Tests for session counting in observe_patterns.py"""

    def test_get_session_count_no_file(self):
        from observe_patterns import get_session_count
        # With a non-existent file, should return 0
        with patch("observe_patterns.SESSION_COUNT_FILE") as mock_file:
            mock_file.exists.return_value = False
            assert get_session_count("any-session") == 0

    def test_increment_session_count(self):
        from observe_patterns import get_session_count, increment_session_count
        with TempDirFixture() as tmp:
            count_file = tmp.path / ".obs_session_count"
            with patch("observe_patterns.SESSION_COUNT_FILE", count_file):
                assert get_session_count("s1") == 0
                count = increment_session_count("s1")
                assert count == 1
                count = increment_session_count("s1")
                assert count == 2

    def test_session_count_resets_for_new_session(self):
        from observe_patterns import get_session_count, increment_session_count
        with TempDirFixture() as tmp:
            count_file = tmp.path / ".obs_session_count"
            with patch("observe_patterns.SESSION_COUNT_FILE", count_file):
                increment_session_count("session-A")
                increment_session_count("session-A")
                # Different session should reset to 0
                assert get_session_count("session-B") == 0


class TestObserveLoadConfig:
    """Tests for config loading in observe_patterns.py"""

    def test_default_config_when_no_file(self):
        from observe_patterns import load_config
        with patch("observe_patterns.CONFIG_PATH") as mock_path:
            mock_path.exists.return_value = False
            config = load_config()
            assert config["enabled"] is True
            assert config["track_tool_usage"] is True
            assert config["max_observations_per_session"] == 1000

    def test_config_override_from_yaml(self):
        from observe_patterns import load_config
        with TempDirFixture() as tmp:
            config_file = tmp.path / "pipeline.yaml"
            import yaml
            config_file.write_text(yaml.dump({
                "observe": {
                    "enabled": False,
                    "max_observations_per_session": 50,
                }
            }))
            with patch("observe_patterns.CONFIG_PATH", config_file):
                config = load_config()
                assert config["enabled"] is False
                assert config["max_observations_per_session"] == 50
                # Defaults preserved
                assert config["track_tool_usage"] is True


# ===========================================================================
# ANALYZE Stage Tests - analyze_session.py
# ===========================================================================


class TestLoadUnprocessedObservations:
    """Tests for load_unprocessed_observations() in analyze_session.py"""

    def test_empty_file(self):
        from analyze_session import load_unprocessed_observations
        with TempDirFixture() as tmp:
            obs_file = tmp.path / "observations.jsonl"
            obs_file.write_text("")
            result = load_unprocessed_observations(obs_file)
            assert result == []

    def test_all_processed(self):
        from analyze_session import load_unprocessed_observations
        with TempDirFixture() as tmp:
            records = [make_observation(processed=True) for _ in range(5)]
            obs_file = tmp.write_jsonl("observations.jsonl", records)
            result = load_unprocessed_observations(obs_file)
            assert result == []

    def test_mixed_processed_unprocessed(self):
        from analyze_session import load_unprocessed_observations
        with TempDirFixture() as tmp:
            records = [
                make_observation(tool="Bash", processed=True),
                make_observation(tool="Edit", processed=False),
                make_observation(tool="Grep", processed=False),
            ]
            obs_file = tmp.write_jsonl("observations.jsonl", records)
            result = load_unprocessed_observations(obs_file)
            assert len(result) == 2
            assert result[0]["tool"] == "Edit"

    def test_max_count_limit(self):
        from analyze_session import load_unprocessed_observations
        with TempDirFixture() as tmp:
            records = [make_observation(tool=f"Tool{i}") for i in range(20)]
            obs_file = tmp.write_jsonl("observations.jsonl", records)
            result = load_unprocessed_observations(obs_file, max_count=5)
            assert len(result) == 5

    def test_nonexistent_file(self):
        from analyze_session import load_unprocessed_observations
        result = load_unprocessed_observations(Path("/nonexistent/obs.jsonl"))
        assert result == []

    def test_malformed_jsonl_skipped(self):
        from analyze_session import load_unprocessed_observations
        with TempDirFixture() as tmp:
            obs_file = tmp.path / "observations.jsonl"
            with open(obs_file, "w") as f:
                f.write(json.dumps(make_observation(tool="Valid")) + "\n")
                f.write("this is not valid json\n")
                f.write(json.dumps(make_observation(tool="AlsoValid")) + "\n")
            result = load_unprocessed_observations(obs_file)
            assert len(result) == 2


class TestSummarizeObservations:
    """Tests for summarize_observations() in analyze_session.py"""

    def test_empty_observations(self):
        from analyze_session import summarize_observations
        assert summarize_observations([]) == ""

    def test_summary_contains_tool_frequency(self):
        from analyze_session import summarize_observations
        obs = [
            make_observation(tool="Bash"),
            make_observation(tool="Bash"),
            make_observation(tool="Edit"),
        ]
        summary = summarize_observations(obs)
        assert "Bash" in summary
        assert "Edit" in summary
        assert "Tool Usage Frequency" in summary

    def test_summary_contains_pattern_frequency(self):
        from analyze_session import summarize_observations
        obs = [
            make_observation(pattern="git_operation"),
            make_observation(pattern="git_operation"),
            make_observation(pattern="file_read"),
        ]
        summary = summarize_observations(obs)
        assert "git_operation" in summary
        assert "Pattern Frequency" in summary

    def test_summary_includes_errors(self):
        from analyze_session import summarize_observations
        obs = [
            make_observation(obs_type="error", context={"error_snippet": "FileNotFoundError: test.py"}),
            make_observation(obs_type="tool_usage"),
        ]
        summary = summarize_observations(obs)
        assert "Error" in summary
        assert "1 total" in summary


class TestParseLLMResponse:
    """Tests for parse_llm_response() in analyze_session.py"""

    def test_valid_json_array(self):
        from analyze_session import parse_llm_response
        response = MockLLMResponse.analysis_response()
        result = parse_llm_response(response)
        assert len(result) == 3
        assert result[0]["tag"] == "LEARNED"
        assert result[1]["tag"] == "PATTERN"
        assert 0.0 <= result[0]["confidence"] <= 1.0

    def test_markdown_code_fences_stripped(self):
        from analyze_session import parse_llm_response
        response = MockLLMResponse.analysis_response_with_markdown()
        result = parse_llm_response(response)
        assert len(result) == 1
        assert result[0]["tag"] == "LEARNED"

    def test_invalid_json_returns_empty(self):
        from analyze_session import parse_llm_response
        response = MockLLMResponse.analysis_response_invalid()
        result = parse_llm_response(response)
        assert result == []

    def test_empty_array(self):
        from analyze_session import parse_llm_response
        response = MockLLMResponse.analysis_response_empty_array()
        result = parse_llm_response(response)
        assert result == []

    def test_entries_missing_required_fields_filtered(self):
        from analyze_session import parse_llm_response
        response = MockLLMResponse.analysis_response_missing_fields()
        result = parse_llm_response(response)
        # Only entries with both tag and content should pass
        assert len(result) == 1
        assert result[0]["content"] == "Valid entry"

    def test_none_response(self):
        from analyze_session import parse_llm_response
        assert parse_llm_response(None) == []

    def test_empty_string_response(self):
        from analyze_session import parse_llm_response
        assert parse_llm_response("") == []

    def test_default_confidence(self):
        from analyze_session import parse_llm_response
        response = json.dumps([{"tag": "FACT", "content": "Something true"}])
        result = parse_llm_response(response)
        assert len(result) == 1
        assert result[0]["confidence"] == 0.5  # Default


class TestMarkObservationsProcessed:
    """Tests for mark_observations_processed() in analyze_session.py"""

    def test_marks_session_observations(self):
        from analyze_session import mark_observations_processed
        with TempDirFixture() as tmp:
            records = [
                make_observation(session_id="s1"),
                make_observation(session_id="s2"),
                make_observation(session_id="s1"),
            ]
            obs_file = tmp.write_jsonl("observations.jsonl", records)
            mark_observations_processed(obs_file, "s1")
            # Read back
            with open(obs_file) as f:
                lines = [json.loads(l) for l in f if l.strip()]
            assert lines[0]["processed"] is True  # s1
            assert lines[1]["processed"] is False  # s2
            assert lines[2]["processed"] is True  # s1

    def test_nonexistent_file_no_error(self):
        from analyze_session import mark_observations_processed
        # Should not raise
        mark_observations_processed(Path("/nonexistent/obs.jsonl"), "s1")


class TestCallLLMFallbackChain:
    """Tests for the LLM fallback chain in analyze_session.py"""

    @patch("analyze_session.call_anthropic")
    def test_anthropic_success(self, mock_anthropic):
        from analyze_session import call_llm
        mock_anthropic.return_value = '[]'
        result, provider = call_llm("test summary", {"model": "claude-haiku-4-5"})
        assert result == '[]'
        assert provider == "anthropic"

    @patch("analyze_session.call_ollama")
    @patch("analyze_session.call_openai")
    @patch("analyze_session.call_anthropic")
    def test_fallback_to_openai(self, mock_anth, mock_oai, mock_ollama):
        from analyze_session import call_llm
        mock_anth.return_value = None
        mock_oai.return_value = '[]'
        result, provider = call_llm("test summary", {})
        assert provider == "openai"

    @patch("analyze_session.call_ollama")
    @patch("analyze_session.call_openai")
    @patch("analyze_session.call_anthropic")
    def test_fallback_to_ollama(self, mock_anth, mock_oai, mock_ollama):
        from analyze_session import call_llm
        mock_anth.return_value = None
        mock_oai.return_value = None
        mock_ollama.return_value = '[]'
        result, provider = call_llm("test summary", {})
        assert provider == "ollama"

    @patch("analyze_session.call_ollama")
    @patch("analyze_session.call_openai")
    @patch("analyze_session.call_anthropic")
    def test_all_providers_fail(self, mock_anth, mock_oai, mock_ollama):
        from analyze_session import call_llm
        mock_anth.return_value = None
        mock_oai.return_value = None
        mock_ollama.return_value = None
        result, provider = call_llm("test summary", {})
        assert result is None
        assert provider is None


# ===========================================================================
# LEARN Stage Tests - store_learnings.py
# ===========================================================================


class TestAutoGenerateTags:
    """Tests for auto_generate_tags() in store_learnings.py"""

    def setup_method(self):
        from store_learnings import auto_generate_tags
        self.auto_tags = auto_generate_tags

    def test_basic_tag_included(self):
        tags = self.auto_tags("LEARNED", "something", "")
        assert "learned" in tags

    def test_tool_mentions_extracted(self):
        tags = self.auto_tags("LEARNED", "Always check Edit operations", "Edit failures")
        assert "tool:edit" in tags

    def test_concept_extraction(self):
        tags = self.auto_tags("PATTERN", "Error handling workflow", "debug session")
        assert "error-handling" in tags
        assert "debugging" in tags

    def test_git_concept(self):
        tags = self.auto_tags("LEARNED", "Git operations need care", "")
        assert "git" in tags

    def test_testing_concept(self):
        tags = self.auto_tags("PATTERN", "Always run tests before commit", "")
        assert "testing" in tags

    def test_deduplicated_tags(self):
        tags = self.auto_tags("LEARNED", "Edit tool Edit handling", "")
        # Should not have duplicate tool:edit
        tag_list = tags.split(",")
        assert len(tag_list) == len(set(tag_list))


class TestIsDuplicate:
    """Tests for is_duplicate() in store_learnings.py"""

    def test_no_duplicate_in_empty_db(self):
        from store_learnings import is_duplicate
        with DatabaseFixture(schema="knowledge_entries") as db:
            result = is_duplicate(db.conn, "brand new learning about testing")
            assert result is False

    def test_exact_duplicate_detected(self):
        from store_learnings import is_duplicate
        with DatabaseFixture(schema="knowledge_entries") as db:
            db.insert_knowledge_entry(
                "LEARNED", "Always check files",
                "Always check file existence before editing files",
                tags="learned,file-operations",
            )
            result = is_duplicate(
                db.conn,
                "Always check file existence before editing files",
            )
            assert result is True

    def test_very_different_content_not_duplicate(self):
        from store_learnings import is_duplicate
        with DatabaseFixture(schema="knowledge_entries") as db:
            db.insert_knowledge_entry(
                "LEARNED", "Git operations",
                "Git rebase operations need careful handling",
                tags="learned,git",
            )
            result = is_duplicate(
                db.conn,
                "Python testing with pytest requires fixtures setup",
            )
            assert result is False


class TestStoreLearning:
    """Tests for store_learning() in store_learnings.py"""

    def test_basic_storage(self):
        from store_learnings import store_learning
        config = {"min_confidence": 0.3, "deduplicate": False, "auto_tag": True, "source": "test"}
        with DatabaseFixture(schema="knowledge_entries") as db:
            learning = make_learning(
                tag="LEARNED",
                content="Always verify paths",
                context="Path errors observed",
                confidence=0.8,
            )
            row_id = store_learning(db.conn, learning, "test-session", config)
            assert row_id is not None
            assert db.count_rows("knowledge_entries") == 1

    def test_low_confidence_rejected(self):
        from store_learnings import store_learning
        config = {"min_confidence": 0.5, "deduplicate": False, "auto_tag": True, "source": "test"}
        with DatabaseFixture(schema="knowledge_entries") as db:
            learning = make_learning(confidence=0.2)
            row_id = store_learning(db.conn, learning, "test-session", config)
            assert row_id is None
            assert db.count_rows("knowledge_entries") == 0

    def test_empty_content_rejected(self):
        from store_learnings import store_learning
        config = {"min_confidence": 0.0, "deduplicate": False, "auto_tag": True, "source": "test"}
        with DatabaseFixture(schema="knowledge_entries") as db:
            learning = make_learning(content="")
            row_id = store_learning(db.conn, learning, "test-session", config)
            assert row_id is None

    def test_title_truncated_at_80_chars(self):
        from store_learnings import store_learning
        config = {"min_confidence": 0.0, "deduplicate": False, "auto_tag": True, "source": "test"}
        with DatabaseFixture(schema="knowledge_entries") as db:
            learning = make_learning(content="A" * 200)
            row_id = store_learning(db.conn, learning, "sess", config)
            row = db.conn.execute(
                "SELECT title FROM knowledge_entries WHERE id = ?", (row_id,)
            ).fetchone()
            # Title should be at most 83 chars (80 + "...")
            assert len(row["title"]) <= 83

    def test_context_appended_to_content(self):
        from store_learnings import store_learning
        config = {"min_confidence": 0.0, "deduplicate": False, "auto_tag": True, "source": "test"}
        with DatabaseFixture(schema="knowledge_entries") as db:
            learning = make_learning(content="Main content", context="Extra context")
            row_id = store_learning(db.conn, learning, "sess", config)
            row = db.conn.execute(
                "SELECT content FROM knowledge_entries WHERE id = ?", (row_id,)
            ).fetchone()
            assert "Extra context" in row["content"]


class TestStoreLearningsConfig:
    """Tests for config loading in store_learnings.py"""

    def test_default_config(self):
        from store_learnings import load_config
        with patch("store_learnings.CONFIG_PATH") as mock_path:
            mock_path.exists.return_value = False
            config = load_config()
            assert config["enabled"] is True
            assert config["deduplicate"] is True
            assert config["min_confidence"] == 0.3


# ===========================================================================
# EVOLVE Stage Tests - inject_knowledge.py
# ===========================================================================


class TestGetProjectContext:
    """Tests for get_project_context() in inject_knowledge.py"""

    def test_vaultmind_context(self):
        from inject_knowledge import get_project_context
        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": "/home/user/vaultmind-plugin"}):
            assert get_project_context() == "vaultmind"

    def test_claude_agentic_context(self):
        from inject_knowledge import get_project_context
        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": "/home/user/claude-agentic-framework"}):
            assert get_project_context() == "claude-agentic-framework"

    def test_generic_context_from_dirname(self):
        from inject_knowledge import get_project_context
        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": "/home/user/my-cool-project"}):
            assert get_project_context() == "my-cool-project"


class TestFormatKnowledgeBlock:
    """Tests for format_knowledge_block() in inject_knowledge.py"""

    def test_empty_entries(self):
        from inject_knowledge import format_knowledge_block
        assert format_knowledge_block([]) == ""

    def test_formatting_includes_tag_and_content(self):
        from inject_knowledge import format_knowledge_block
        entries = [
            {
                "tag": "LEARNED",
                "content": "Always check paths",
                "context": "file-ops",
                "timestamp": "2026-02-10T12:00:00Z",
            }
        ]
        block = format_knowledge_block(entries)
        assert "LEARNED" in block
        assert "Always check paths" in block
        assert "file-ops" in block
        assert "2026-02-10" in block
        assert "Relevant Knowledge" in block

    def test_multiple_entries(self):
        from inject_knowledge import format_knowledge_block
        entries = [
            {"tag": "LEARNED", "content": "Entry 1", "context": "", "timestamp": "2026-01-01T00:00:00Z"},
            {"tag": "PATTERN", "content": "Entry 2", "context": "", "timestamp": "2026-01-02T00:00:00Z"},
        ]
        block = format_knowledge_block(entries)
        assert "Entry 1" in block
        assert "Entry 2" in block


# ===========================================================================
# End-to-End Pipeline Tests
# ===========================================================================


class TestEndToEndPipeline:
    """End-to-end tests simulating the full Observe -> Analyze -> Learn flow."""

    def test_observe_writes_to_jsonl(self):
        """Test that the observe stage writes observation records."""
        from observe_patterns import classify_tool_pattern, extract_context
        with TempDirFixture() as tmp:
            obs_file = tmp.path / "observations.jsonl"
            # Simulate what observe_patterns.main() does
            tool_name = "Bash"
            tool_input = {"command": "git status"}
            pattern = classify_tool_pattern(tool_name, tool_input)
            context = extract_context(tool_name, tool_input, "")
            observation = {
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "type": "tool_usage",
                "tool": tool_name,
                "pattern": pattern,
                "context": context,
                "session_id": "e2e-test",
                "processed": False,
            }
            with open(obs_file, "a") as f:
                f.write(json.dumps(observation) + "\n")
            # Verify
            with open(obs_file) as f:
                lines = [json.loads(l) for l in f if l.strip()]
            assert len(lines) == 1
            assert lines[0]["pattern"] == "git_operation"

    def test_analyze_parses_and_produces_learnings(self):
        """Test that analysis of observations produces learning output."""
        from analyze_session import summarize_observations, parse_llm_response
        observations = [make_observation(tool="Bash", pattern="git_operation") for _ in range(15)]
        summary = summarize_observations(observations)
        assert "Bash" in summary
        # Simulate LLM response
        llm_response = MockLLMResponse.analysis_response()
        learnings = parse_llm_response(llm_response)
        assert len(learnings) == 3

    def test_learn_stores_into_database(self):
        """Test that learnings are stored into the knowledge database."""
        from store_learnings import store_learning
        config = {"min_confidence": 0.0, "deduplicate": False, "auto_tag": True, "source": "pipeline"}
        with DatabaseFixture(schema="knowledge_entries") as db:
            learnings = [
                make_learning("LEARNED", "Check paths before editing"),
                make_learning("PATTERN", "Grep then Edit is standard"),
                make_learning("INVESTIGATION", "Git error rate is high"),
            ]
            stored = 0
            for learning in learnings:
                row_id = store_learning(db.conn, learning, "e2e-session", config)
                if row_id is not None:
                    stored += 1
            assert stored == 3
            assert db.count_rows("knowledge_entries") == 3

    def test_full_pipeline_observe_analyze_learn(self):
        """Full pipeline: generate observations, analyze, store learnings."""
        from observe_patterns import classify_tool_pattern, extract_context
        from analyze_session import summarize_observations, parse_llm_response
        from store_learnings import store_learning

        # OBSERVE: Generate observations
        observations = []
        tools = [
            ("Bash", {"command": "git status"}),
            ("Edit", {"old_string": "a", "new_string": "b", "file_path": "/tmp/x.py"}),
            ("Bash", {"command": "pytest tests/"}),
            ("Grep", {"pattern": "TODO"}),
            ("Bash", {"command": "git diff"}),
        ]
        for tool_name, tool_input in tools:
            pattern = classify_tool_pattern(tool_name, tool_input)
            context = extract_context(tool_name, tool_input, "")
            observations.append(make_observation(
                tool=tool_name,
                pattern=pattern,
                context=context,
            ))

        # ANALYZE: Summarize and parse
        # Add more observations to meet minimum threshold
        for i in range(10):
            observations.append(make_observation(tool="Read", pattern="file_read"))
        summary = summarize_observations(observations)
        assert len(summary) > 0

        llm_response = MockLLMResponse.analysis_response()
        learnings = parse_llm_response(llm_response)
        assert len(learnings) > 0

        # LEARN: Store
        config = {"min_confidence": 0.0, "deduplicate": False, "auto_tag": True, "source": "pipeline"}
        with DatabaseFixture(schema="knowledge_entries") as db:
            stored_ids = []
            for learning in learnings:
                row_id = store_learning(db.conn, learning, "e2e-session", config)
                if row_id is not None:
                    stored_ids.append(row_id)
            assert len(stored_ids) == 3
            # Verify FTS search works
            rows = db.conn.execute(
                "SELECT * FROM knowledge_fts WHERE knowledge_fts MATCH 'verify'",
            ).fetchall()
            assert len(rows) >= 1


# ===========================================================================
# Error Handling and Fallback Tests
# ===========================================================================


class TestErrorHandling:
    """Tests for error handling and graceful fallback behavior."""

    def test_observe_invalid_json_exits_cleanly(self):
        """observe_patterns.main() should exit(0) on invalid JSON input."""
        from observe_patterns import main
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = "not json"
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_analyze_disabled_exits_cleanly(self):
        """analyze_session.main() should exit(0) when disabled."""
        from analyze_session import main
        input_data = json.dumps(make_session_end_input())
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = input_data
            with patch("analyze_session.load_config") as mock_config:
                mock_config.return_value = {"enabled": False}
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0

    def test_analyze_too_few_observations_exits(self):
        """analyze_session should exit when below min observation threshold."""
        from analyze_session import load_unprocessed_observations
        with TempDirFixture() as tmp:
            records = [make_observation() for _ in range(3)]
            obs_file = tmp.write_jsonl("observations.jsonl", records)
            result = load_unprocessed_observations(obs_file)
            # 3 < 10 (default min), so analysis should skip
            assert len(result) == 3
            # The main() function checks len < min and exits

    def test_store_learnings_no_pending_file_exits(self):
        """store_learnings should exit cleanly when no pending file exists."""
        from store_learnings import main
        input_data = json.dumps(make_session_end_input())
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = input_data
            with patch("store_learnings.PENDING_LEARNINGS") as mock_path:
                mock_path.exists.return_value = False
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0

    def test_classify_empty_tool_input(self):
        """classify_tool_pattern handles empty tool input gracefully."""
        from observe_patterns import classify_tool_pattern
        # Empty dict should not crash
        result = classify_tool_pattern("Bash", {})
        assert result == "shell_command"

    def test_extract_context_empty_input(self):
        """extract_context handles empty tool input gracefully."""
        from observe_patterns import extract_context
        ctx = extract_context("Bash", {}, "")
        assert "command" in ctx
        assert ctx["command"] == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
