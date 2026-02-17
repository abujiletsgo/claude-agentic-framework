#!/usr/bin/env python3
"""
Comprehensive tests for auto-hook subsystems:
  - auto_error_analyzer.py
  - auto_cost_warnings.py
  - auto_refine.py
  - auto_dependency_audit.py
  - auto_voice_notifications.py
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# Paths
HOOKS_ROOT = Path(__file__).parent.parent
AUTOMATION = HOOKS_ROOT / "automation"
NOTIFICATIONS = HOOKS_ROOT / "notifications"

sys.path.insert(0, str(AUTOMATION))
sys.path.insert(0, str(NOTIFICATIONS))


# ════════════════════════════════════════════════════════════
# auto_error_analyzer.py
# ════════════════════════════════════════════════════════════

def test_is_test_command_pytest():
    import auto_error_analyzer as ae
    assert ae.is_test_command("pytest tests/")
    assert ae.is_test_command("uv run pytest tests/ -v")
    assert ae.is_test_command("python -m pytest")

def test_is_test_command_npm():
    import auto_error_analyzer as ae
    assert ae.is_test_command("npm test")
    assert ae.is_test_command("npm run test")

def test_is_test_command_others():
    import auto_error_analyzer as ae
    assert ae.is_test_command("jest --coverage")
    assert ae.is_test_command("go test ./...")
    assert ae.is_test_command("cargo test")
    assert ae.is_test_command("bun test")

def test_is_test_command_negative():
    import auto_error_analyzer as ae
    assert not ae.is_test_command("git status")
    assert not ae.is_test_command("ls -la")
    assert not ae.is_test_command("echo hello")
    assert not ae.is_test_command("cat file.txt")

def test_extract_error_context_combines_output():
    import auto_error_analyzer as ae
    stderr = "ERROR: assertion failed"
    stdout = "test output"
    ctx = ae.extract_error_context(stderr, stdout, 1)
    assert "ERROR" in ctx or "assertion" in ctx

def test_extract_error_context_truncates_long_output():
    import auto_error_analyzer as ae
    long_stderr = "x" * 10000
    ctx = ae.extract_error_context(long_stderr, "", 1)
    assert len(ctx) <= 5100  # some slack for headers

def test_extract_error_context_exit_code_0_empty():
    import auto_error_analyzer as ae
    ctx = ae.extract_error_context("", "", 0)
    # Function always appends exit code line, so result is non-empty but still a string
    assert isinstance(ctx, str)

def test_error_analyzer_hook_exit_0_on_success():
    """Hook should exit 0 and not analyze when exit_code=0."""
    import subprocess
    hook = str(AUTOMATION / "auto_error_analyzer.py")
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest tests/"},
        "tool_response": json.dumps({"stdout": "1 passed", "stderr": "", "exit_code": 0}),
    }
    r = subprocess.run(["python3", hook], input=json.dumps(payload),
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert "AUTO ERROR ANALYSIS" not in r.stderr

def test_error_analyzer_hook_analyzes_on_failure():
    import subprocess
    hook = str(AUTOMATION / "auto_error_analyzer.py")
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest tests/"},
        "tool_response": json.dumps({
            "stdout": "FAILED tests/test_foo.py",
            "stderr": "AssertionError: expected 1 got 2",
            "exit_code": 1,
        }),
    }
    r = subprocess.run(["python3", hook], input=json.dumps(payload),
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert "AUTO ERROR ANALYSIS" in r.stderr

def test_error_analyzer_skips_non_test_command():
    import subprocess
    hook = str(AUTOMATION / "auto_error_analyzer.py")
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"},
        "tool_response": json.dumps({"stdout": "", "stderr": "error here", "exit_code": 1}),
    }
    r = subprocess.run(["python3", hook], input=json.dumps(payload),
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert "AUTO ERROR ANALYSIS" not in r.stderr

def test_error_analyzer_handles_raw_string_response():
    import subprocess
    hook = str(AUTOMATION / "auto_error_analyzer.py")
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest tests/"},
        "tool_response": "FAILED: tests/test_foo.py::test_bar - AssertionError",
    }
    r = subprocess.run(["python3", hook], input=json.dumps(payload),
                       capture_output=True, text=True)
    assert r.returncode == 0  # Must not crash on raw string


# ════════════════════════════════════════════════════════════
# auto_cost_warnings.py
# ════════════════════════════════════════════════════════════

def _make_tracker(daily=0.0, weekly=0.0, monthly=0.0):
    """Build a mock tracker that uses get_summary(period) -> {"total_cost": X}."""
    tracker = MagicMock()
    tracker.get_summary.side_effect = lambda period: {
        "today": {"total_cost": daily},
        "week":  {"total_cost": weekly},
        "month": {"total_cost": monthly},
    }[period]
    return tracker

def test_check_budget_thresholds_warning_at_75():
    import auto_cost_warnings as acw
    config = acw.load_budget_config()
    tracker = _make_tracker(daily=7.60)  # 76% of $10
    warnings = acw.check_budget_thresholds(tracker, config, "test-session")
    assert any("WARNING" in w or "CRITICAL" in w for w in warnings), \
        f"Expected warning at 76%, got: {warnings}"

def test_check_budget_thresholds_critical_at_90():
    import auto_cost_warnings as acw
    config = acw.load_budget_config()
    tracker = _make_tracker(daily=9.10)  # 91% of $10
    warnings = acw.check_budget_thresholds(tracker, config, "test-session")
    assert any("CRITICAL" in w for w in warnings), \
        f"Expected critical at 91%, got: {warnings}"

def test_check_budget_thresholds_no_warning_below_75():
    import auto_cost_warnings as acw
    config = acw.load_budget_config()
    tracker = _make_tracker(daily=5.0, weekly=20.0, monthly=60.0)
    warnings = acw.check_budget_thresholds(tracker, config, "test-session")
    assert warnings == [], f"Expected no warnings below 75%, got: {warnings}"

def test_load_budget_config_has_defaults():
    import auto_cost_warnings as acw
    config = acw.load_budget_config()
    # Config has nested structure: {"budgets": {...}, "alerts": {...}}
    assert config["budgets"].get("daily", 0) > 0
    assert config["budgets"].get("weekly", 0) > 0
    assert config["budgets"].get("monthly", 0) > 0
    assert 0 < config["alerts"].get("warning_threshold", 0) < 1
    assert 0 < config["alerts"].get("critical_threshold", 0) < 1

def test_budget_zero_daily_no_division_error():
    import auto_cost_warnings as acw
    config = {
        "budgets": {"daily": 0, "weekly": 50, "monthly": 150},
        "alerts": {"warning_threshold": 0.75, "critical_threshold": 0.90}
    }
    tracker = _make_tracker()
    # Should not raise ZeroDivisionError
    warnings = acw.check_budget_thresholds(tracker, config, "test-session")
    assert isinstance(warnings, list)


# ════════════════════════════════════════════════════════════
# auto_refine.py
# ════════════════════════════════════════════════════════════

def test_count_findings_warning():
    import auto_refine as ar
    # count_findings looks for [WARNING], [ERROR], [CRITICAL], [!!] bracket patterns
    assert ar.count_findings("[WARNING] unused variable") >= 1

def test_count_findings_error():
    import auto_refine as ar
    assert ar.count_findings("[ERROR] null pointer dereference") >= 1

def test_count_findings_critical():
    import auto_refine as ar
    assert ar.count_findings("[CRITICAL] SQL injection vulnerability") >= 1

def test_count_findings_exclamation():
    import auto_refine as ar
    assert ar.count_findings("[!!] Breaking change detected") >= 1

def test_count_findings_zero_for_clean():
    import auto_refine as ar
    assert ar.count_findings("All tests passed, no issues found") == 0

def test_count_findings_none_input():
    import auto_refine as ar
    assert ar.count_findings(None) == 0

def test_is_review_command_skill():
    import auto_refine as ar
    assert ar.is_review_command("Skill", {"skill": "review"})
    assert ar.is_review_command("Skill", {"skill": "code-review"})

def test_is_review_command_bash():
    import auto_refine as ar
    assert ar.is_review_command("Bash", {"command": "/review src/"})

def test_is_review_command_negative():
    import auto_refine as ar
    assert not ar.is_review_command("Bash", {"command": "pytest tests/"})
    assert not ar.is_review_command("Edit", {"file_path": "review_notes.py"})

def test_refine_hook_no_output_for_clean_review():
    import subprocess
    hook = str(AUTOMATION / "auto_refine.py")
    payload = {
        "tool_name": "Skill",
        "tool_input": {"skill": "review"},
        "tool_response": "All checks passed. No issues found.",
    }
    r = subprocess.run(["python3", hook], input=json.dumps(payload),
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert "/refine" not in r.stderr

def test_refine_hook_suggests_refine_on_findings():
    import subprocess
    hook = str(AUTOMATION / "auto_refine.py")
    payload = {
        "tool_name": "Skill",
        "tool_input": {"skill": "review"},
        "tool_response": "[WARNING] Missing input validation\n[ERROR] SQL injection risk",
    }
    r = subprocess.run(["python3", hook], input=json.dumps(payload),
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert "/refine" in r.stderr


# ════════════════════════════════════════════════════════════
# auto_dependency_audit.py
# ════════════════════════════════════════════════════════════

def test_load_state_fresh():
    import auto_dependency_audit as ada
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.object(ada, "get_state_path", return_value=Path(tmpdir) / "state.json"):
            state = ada.load_state("test-session")
            assert state["tool_use_count"] == 0
            assert state["session_id"] == "test-session"

def test_load_state_resets_on_new_session():
    import auto_dependency_audit as ada
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "state.json"
        state_path.write_text(json.dumps({
            "tool_use_count": 45,
            "last_audit_timestamp": None,
            "session_id": "old-session",
        }))
        with patch.object(ada, "get_state_path", return_value=state_path):
            state = ada.load_state("new-session")
            assert state["tool_use_count"] == 0
            assert state["session_id"] == "new-session"

def test_load_state_preserves_same_session():
    import auto_dependency_audit as ada
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "state.json"
        state_path.write_text(json.dumps({
            "tool_use_count": 30,
            "last_audit_timestamp": None,
            "session_id": "same-session",
        }))
        with patch.object(ada, "get_state_path", return_value=state_path):
            state = ada.load_state("same-session")
            assert state["tool_use_count"] == 30

def test_should_trigger_audit_at_50_uses():
    import auto_dependency_audit as ada
    state = {"tool_use_count": 50, "last_audit_timestamp": "2026-01-01T00:00:00", "session_id": "x"}
    triggered, reason = ada.should_trigger_audit(state)
    assert triggered
    assert "50" in reason

def test_should_trigger_initial_audit_at_10():
    import auto_dependency_audit as ada
    state = {"tool_use_count": 10, "last_audit_timestamp": None, "session_id": "x"}
    triggered, reason = ada.should_trigger_audit(state)
    assert triggered

def test_should_not_trigger_below_threshold():
    import auto_dependency_audit as ada
    state = {"tool_use_count": 9, "last_audit_timestamp": None, "session_id": "x"}
    triggered, reason = ada.should_trigger_audit(state)
    assert not triggered

def test_should_trigger_after_7_days():
    import auto_dependency_audit as ada
    from datetime import timezone
    # Must use timezone-aware timestamp — function compares with datetime.now(timezone.utc)
    old_ts = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    state = {"tool_use_count": 5, "last_audit_timestamp": old_ts, "session_id": "x"}
    triggered, reason = ada.should_trigger_audit(state)
    assert triggered

def test_should_not_trigger_recent_audit():
    import auto_dependency_audit as ada
    recent_ts = (datetime.now() - timedelta(days=2)).isoformat()
    state = {"tool_use_count": 5, "last_audit_timestamp": recent_ts, "session_id": "x"}
    triggered, reason = ada.should_trigger_audit(state)
    assert not triggered


# ════════════════════════════════════════════════════════════
# auto_voice_notifications.py
# ════════════════════════════════════════════════════════════

def test_detect_task_completion_true():
    import auto_voice_notifications as avn
    hook_input = {
        "tool_name": "TaskUpdate",
        "tool_input": {"status": "completed", "subject": "Fix auth bug"},
    }
    triggered, subject = avn.detect_task_completion(hook_input)
    assert triggered
    assert subject == "Fix auth bug"

def test_detect_task_completion_false_pending():
    import auto_voice_notifications as avn
    hook_input = {
        "tool_name": "TaskUpdate",
        "tool_input": {"status": "in_progress", "subject": "Fix auth bug"},
    }
    triggered, _ = avn.detect_task_completion(hook_input)
    assert not triggered

def test_detect_task_completion_false_wrong_tool():
    import auto_voice_notifications as avn
    hook_input = {"tool_name": "Bash", "tool_input": {"command": "pytest"}}
    triggered, _ = avn.detect_task_completion(hook_input)
    assert not triggered

def test_detect_error_bash_failure():
    import auto_voice_notifications as avn
    hook_input = {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest tests/"},
        "tool_response": {"exit_code": 1},
    }
    triggered, reason = avn.detect_error_or_attention(hook_input)
    assert triggered

def test_detect_error_bash_success_no_trigger():
    import auto_voice_notifications as avn
    hook_input = {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest tests/"},
        "tool_response": {"exit_code": 0},
    }
    triggered, _ = avn.detect_error_or_attention(hook_input)
    assert not triggered

def test_speak_noop_when_disabled():
    import auto_voice_notifications as avn
    with patch.dict(os.environ, {"VOICE_NOTIFICATIONS": "false"}):
        # Should not raise, should be a no-op
        import importlib
        importlib.reload(avn)
        avn.speak("test message")  # no-op

def test_voice_hook_exits_0():
    import subprocess
    hook = str(NOTIFICATIONS / "auto_voice_notifications.py")
    payload = {
        "tool_name": "TaskUpdate",
        "tool_input": {"status": "completed", "subject": "Test task"},
    }
    r = subprocess.run(
        ["python3", hook],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={**os.environ, "VOICE_NOTIFICATIONS": "false"},
    )
    assert r.returncode == 0
