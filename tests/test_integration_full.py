#!/usr/bin/env python3
"""\nFull Integration Test Suite\n============================\nSimulates a complete session lifecycle exercising all subsystems:\n\n  Session start → Caddy classify → Damage control → Tool execution\n  → Context bundle logging → Error analysis → Circuit breaker\n  → Context manager (pre-compress) → Pre-compact preservation\n  → Knowledge pipeline → Session cleanup\n\nAlso tests cross-subsystem interactions and complex workflows.\n"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# Roots
REPO_ROOT = Path(__file__).parent.parent
HOOKS = REPO_ROOT / "global-hooks"
FRAMEWORK = HOOKS / "framework"
DAMAGE_CONTROL = HOOKS / "damage-control"
AUTOMATION = FRAMEWORK / "automation"
CONTEXT = FRAMEWORK / "context"
CADDY = FRAMEWORK / "caddy"
GUARDRAILS = FRAMEWORK / "guardrails"
KNOWLEDGE = FRAMEWORK / "knowledge"
SESSION = FRAMEWORK / "session"

sys.path.insert(0, str(DAMAGE_CONTROL))
sys.path.insert(0, str(AUTOMATION))
sys.path.insert(0, str(CONTEXT))
sys.path.insert(0, str(CADDY))
sys.path.insert(0, str(GUARDRAILS))
sys.path.insert(0, str(KNOWLEDGE))
sys.path.insert(0, str(SESSION))

# Damage control is enforced by the RUST binary — that is what PreToolUse runs.
# These tests used to import a Python `unified-damage-control.py` that was never
# wired into any settings file, so they asserted against an implementation with no
# effect on a live session while the one that actually guards every command went
# untested. Drive the binary the way the hook does: JSON on stdin, exit 2 = block.
import pytest

CAF_HOOKS_BIN = REPO_ROOT / "target" / "release" / "caf-hooks"

requires_caf_hooks = pytest.mark.skipif(
    not CAF_HOOKS_BIN.is_file(),
    reason="caf-hooks release binary not built (run: cargo build --release)",
)


def _damage_control(tool_name: str, tool_input: dict) -> tuple[bool, str]:
    """Run the wired Rust damage-control. Returns (blocked, message)."""
    proc = subprocess.run(
        [str(CAF_HOOKS_BIN), "damage-control"],
        input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
        capture_output=True,
        text=True,
        env={**os.environ, "CAF_HOOKS_DIR": str(DAMAGE_CONTROL)},
        timeout=15,
    )
    return proc.returncode == 2, (proc.stdout + proc.stderr).strip()


def _make_tracker_mock(daily=0.0, weekly=0.0, monthly=0.0):
    """Build cost tracker mock using get_summary(period) API."""
    tracker = MagicMock()
    tracker.get_summary.side_effect = lambda period: {
        "today": {"total_cost": daily},
        "week":  {"total_cost": weekly},
        "month": {"total_cost": monthly},
    }[period]
    return tracker


# ══════════════════════════════════════════════════════════════════
# WORKFLOW 1: Destructive command blocked before damage
# ══════════════════════════════════════════════════════════════════

@requires_caf_hooks
class TestDamageControlWorkflow:
    """The wired Rust damage-control intercepts dangerous commands before they run."""

    def test_recursive_delete_blocked_before_execution(self):
        blocked, msg = _damage_control("Bash", {"command": "rm" + " -rf /important/data"})
        assert blocked, f"recursive delete must be blocked before reaching the shell; got: {msg}"

    def test_force_push_blocked(self):
        # Regression: this pattern uses a lookahead the `regex` crate cannot compile,
        # so it was silently skipped and force-push went unenforced (see F11).
        blocked, msg = _damage_control("Bash", {"command": "git push --force origin main"})
        assert blocked, f"force-push must be blocked; got: {msg}"

    def test_force_with_lease_allowed(self):
        blocked, _ = _damage_control("Bash", {"command": "git push --force-with-lease origin main"})
        assert not blocked, "--force-with-lease is the safe form and must pass"

    def test_safe_command_passes_through(self):
        blocked, _ = _damage_control("Bash", {"command": "pytest tests/ -v"})
        assert not blocked

    def test_zero_access_path_blocked(self):
        blocked, msg = _damage_control(
            "Edit", {"file_path": str(Path.home() / ".claude" / "settings.json")})
        assert blocked, f"settings.json is a zero-access path; got: {msg}"

    def test_every_pattern_compiles(self):
        """A pattern that fails to compile is silently unenforced — the exact bug
        that left force-push open. The binary must warn on any that do not."""
        _, msg = _damage_control("Bash", {"command": "echo hello"})
        assert "WARN" not in msg, f"some patterns failed to compile: {msg}"


# ══════════════════════════════════════════════════════════════════
# WORKFLOW 2: Test failure triggers error analysis
# ══════════════════════════════════════════════════════════════════

class TestErrorAnalysisWorkflow:
    """Failed test → error analyzer fires → suggests /error-analyzer."""

    def test_pytest_failure_triggers_analysis(self):
        import auto_error_analyzer as ae
        assert ae.is_test_command("pytest tests/")

    def test_analysis_includes_error_context(self):
        import auto_error_analyzer as ae
        stderr = "FAILED tests/test_auth.py::test_login - AssertionError: expected 200 got 401"
        stdout = "collected 5 items\n4 passed, 1 failed"
        ctx = ae.extract_error_context(stderr, stdout, 1)
        assert "AssertionError" in ctx or "FAILED" in ctx

    def test_circuit_breaker_protects_error_analyzer(self):
        """Circuit breaker should wrap the hook call."""
        from circuit_breaker import CircuitBreaker, CircuitBreakerDecision
        from hook_state_manager import HookStateManager

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            mgr = HookStateManager(state_file)

            config = MagicMock()
            config.circuit_breaker.failure_threshold = 3
            config.circuit_breaker.cooldown_seconds = 60
            config.circuit_breaker.success_threshold = 2
            config.circuit_breaker.exclude = []
            config.logging.level = "WARNING"
            config.get_log_file_path.return_value = Path(tmpdir) / "cb.log"
            config.logging.format = "%(asctime)s %(message)s"

            cb = CircuitBreaker(mgr, config)
            hook_name = "auto_error_analyzer"

            # First 2 failures — circuit stays CLOSED
            for _ in range(2):
                mgr.record_failure(hook_name, "test error",
                                   failure_threshold=3, cooldown_seconds=60)

            result = cb.should_execute(hook_name)
            assert result.decision == CircuitBreakerDecision.EXECUTE

            # Third failure opens circuit
            mgr.record_failure(hook_name, "test error",
                               failure_threshold=3, cooldown_seconds=60)
            result = cb.should_execute(hook_name)
            assert result.decision == CircuitBreakerDecision.SKIP



# ══════════════════════════════════════════════════════════════════
# WORKFLOWS 3-5 REMOVED (native-parity audit, 2026-07-12)
#
# These exercised auto_context_manager, auto_delegate and
# session_lock_manager, all retired: native auto-compaction supersedes
# the context manager, auto_delegate duplicated analyze_request's
# classification, and session_lock_manager early-exited unless an opt-in
# flag file existed while paying a process cold-start on every tool call.
# ══════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════
# WORKFLOW 6: Knowledge pipeline — extract → store → inject
# ══════════════════════════════════════════════════════════════════

class TestKnowledgePipeline:
    """Knowledge flows: extract at PostToolUse → store at Stop → inject at SessionStart."""

    def test_extract_learnings_hook_exits_cleanly(self):
        hook = str(KNOWLEDGE / "extract_learnings.py")
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "/src/auth.py"},
            "tool_response": "Successfully edited file.",
        }
        r = subprocess.run(["python3", hook], input=json.dumps(payload),
                           capture_output=True, text=True)
        assert r.returncode == 0

    def test_store_learnings_hook_exits_cleanly(self):
        hook = str(KNOWLEDGE / "store_learnings.py")
        payload = {"session_id": "integration-test-knowledge"}
        r = subprocess.run(["python3", hook], input=json.dumps(payload),
                           capture_output=True, text=True)
        assert r.returncode == 0

    def test_inject_relevant_hook_exits_cleanly(self):
        hook = str(KNOWLEDGE / "inject_relevant.py")
        payload = {"session_id": "integration-test-knowledge"}
        r = subprocess.run(["python3", hook], input=json.dumps(payload),
                           capture_output=True, text=True)
        assert r.returncode == 0


# ══════════════════════════════════════════════════════════════════
# WORKFLOW 7: Dependency audit state machine
# ══════════════════════════════════════════════════════════════════

class TestDependencyAuditStateMachine:
    """State machine: tool_use_count increments → audit triggers at thresholds."""

    def test_counter_increments_across_calls(self):
        import auto_dependency_audit as ada

        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"

            with patch.object(ada, "get_state_path", return_value=state_path):
                state = ada.load_state("sess1")
                assert state["tool_use_count"] == 0

                state["tool_use_count"] += 1
                ada.save_state(state)

                state2 = ada.load_state("sess1")
                assert state2["tool_use_count"] == 1

    def test_audit_not_triggered_below_thresholds(self):
        import auto_dependency_audit as ada
        state = {"tool_use_count": 5, "last_audit_timestamp": datetime.now().isoformat(), "session_id": "x"}
        triggered, reason = ada.should_trigger_audit(state)
        assert not triggered

    def test_audit_triggered_at_50_tool_uses(self):
        import auto_dependency_audit as ada
        state = {
            "tool_use_count": 50,
            "last_audit_timestamp": datetime.now().isoformat(),
            "session_id": "x",
        }
        triggered, reason = ada.should_trigger_audit(state)
        assert triggered


# ══════════════════════════════════════════════════════════════════
# WORKFLOW 8: Budget warning cascade
# ══════════════════════════════════════════════════════════════════

class TestBudgetWarningCascade:
    """Cost crosses 75% → warning; 90% → critical; 0% → silent."""

    def test_no_warning_under_75_pct(self):
        import auto_cost_warnings as acw
        config = acw.load_budget_config()
        tracker = _make_tracker_mock(daily=7.0, weekly=30.0, monthly=100.0)
        warnings = acw.check_budget_thresholds(tracker, config, "s1")
        assert warnings == []

    def test_warning_at_76_pct(self):
        import auto_cost_warnings as acw
        config = acw.load_budget_config()
        tracker = _make_tracker_mock(daily=7.6)
        warnings = acw.check_budget_thresholds(tracker, config, "s1")
        assert len(warnings) > 0

    def test_critical_at_91_pct(self):
        import auto_cost_warnings as acw
        config = acw.load_budget_config()
        tracker = _make_tracker_mock(daily=9.1)
        warnings = acw.check_budget_thresholds(tracker, config, "s1")
        assert any("CRITICAL" in w for w in warnings)


# ══════════════════════════════════════════════════════════════════
# WORKFLOW 9: Context bundle logs complete session history
# ══════════════════════════════════════════════════════════════════

class TestContextBundleSessionHistory:
    """Bundle accumulates all file operations throughout a session."""

    def _load_cbl(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "context_bundle_logger",
            FRAMEWORK / "context-bundle-logger.py",
        )
        cbl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cbl)
        return cbl

    def test_session_accumulates_reads_and_writes(self):
        cbl = self._load_cbl()
        bundle = {
            "session_id": "test", "created_at": "2026-02-17", "last_updated": "2026-02-17",
            "operations": [], "files_read": [], "files_modified": [],
            "summary": {"read_count": 0, "edit_count": 0, "write_count": 0, "total_operations": 0},
        }
        files = [
            ("Read", "/src/auth.py"),
            ("Read", "/src/models.py"),
            ("Edit", "/src/auth.py"),
            ("Write", "/src/new_feature.py"),
            ("Read", "/tests/test_auth.py"),
        ]
        for tool, fp in files:
            inp = {"file_path": fp}
            if tool == "Edit":
                inp.update({"old_string": "x", "new_string": "y"})
            cbl.log_operation(bundle, tool, inp, "2026-02-17")

        assert bundle["summary"]["read_count"] == 3
        assert bundle["summary"]["edit_count"] == 1
        assert bundle["summary"]["write_count"] == 1
        assert bundle["summary"]["total_operations"] == 5
        assert len(bundle["files_read"]) == 3
        assert len(bundle["files_modified"]) == 2  # Edit + Write

    def test_read_deduplication_in_bundle(self):
        cbl = self._load_cbl()
        bundle = {
            "session_id": "test", "created_at": "t", "last_updated": "t",
            "operations": [], "files_read": [], "files_modified": [],
            "summary": {"read_count": 0, "edit_count": 0, "write_count": 0, "total_operations": 0},
        }
        for _ in range(5):
            cbl.log_operation(bundle, "Read", {"file_path": "/src/auth.py"}, "t")
        assert bundle["files_read"].count("/src/auth.py") == 1
        assert bundle["summary"]["read_count"] == 5
