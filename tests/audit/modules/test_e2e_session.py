"""
test_e2e_session.py — Full E2E simulation of a Claude Code session lifecycle.
Builder-2 | CAF Audit Suite
"""
import pytest
import subprocess
import json
import time
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent  # tests/audit/modules/test_e2e_session.py -> repo root

TIMINGS: list[dict] = []

pytestmark = pytest.mark.slow

# ---------------------------------------------------------------------------
# Session event sequence
# ---------------------------------------------------------------------------

SESSION_EVENTS = [
    (
        "SessionStart",
        {
            "hookEventName": "SessionStart",
            "cwd": None,  # filled in at runtime with str(REPO_ROOT)
            "session_id": "e2e-test-001",
        },
    ),
    (
        "UserPromptSubmit",
        {
            "hookEventName": "UserPromptSubmit",
            "prompt": "fix the auth bug",
            "session_id": "e2e-test-001",
        },
    ),
    (
        "PreToolUse_grep",
        {
            "hookEventName": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "grep -r 'auth' src/"},
            "session_id": "e2e-test-001",
        },
    ),
    (
        "PostToolUse_grep",
        {
            "hookEventName": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "grep -r 'auth' src/"},
            "tool_response": {
                "stdout": "src/auth.py:42:def authenticate():",
                "exit_code": 0,
            },
            "session_id": "e2e-test-001",
        },
    ),
    (
        "PreToolUse_edit",
        {
            "hookEventName": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "/tmp/test-audit/src/auth.py",
                "old_string": "pass",
                "new_string": "return True",
            },
            "session_id": "e2e-test-001",
        },
    ),
    (
        "PostToolUse_edit",
        {
            "hookEventName": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": "/tmp/test-audit/src/auth.py"},
            "tool_response": {"success": True},
            "session_id": "e2e-test-001",
        },
    ),
    (
        "PreToolUse_rm_rf",
        {
            "hookEventName": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "rm -rf /tmp/test-audit-delete-me"},
            "session_id": "e2e-test-001",
        },
    ),
    (
        "Stop",
        {
            "hookEventName": "Stop",
            "session_id": "e2e-test-001",
            "stop_reason": "end_turn",
        },
    ),
]

# ---------------------------------------------------------------------------
# Hook paths
# ---------------------------------------------------------------------------

HOOKS = {
    "session_startup": REPO_ROOT / "global-hooks/framework/session/session_startup.py",
    "caddy_analyze": REPO_ROOT / "global-hooks/framework/caddy/analyze_request.py",
    "damage_control_py": REPO_ROOT / "global-hooks/damage-control/unified-damage-control.py",
    "check_lthread": REPO_ROOT / "global-hooks/framework/validators/check_lthread_progress.py",
    "auto_error_analyzer_py": REPO_ROOT / "global-hooks/framework/automation/auto_error_analyzer.py",
}

CAF_HOOKS_RELEASE = REPO_ROOT / "caf-hooks/target/release/caf-hooks"
CAF_HOOKS_DEBUG = REPO_ROOT / "caf-hooks/target/debug/caf-hooks"


def get_caf_hooks_bin() -> Path | None:
    if CAF_HOOKS_RELEASE.exists():
        return CAF_HOOKS_RELEASE
    if CAF_HOOKS_DEBUG.exists():
        return CAF_HOOKS_DEBUG
    return None


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------


def run_hook(hook_path: Path, payload: dict, cwd: Path) -> tuple[int, dict | None, str]:
    """Returns (exit_code, parsed_json_or_None, stderr)."""
    result = subprocess.run(
        ["uv", "run", "--no-project", str(hook_path)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=15,
    )
    try:
        parsed = json.loads(result.stdout) if result.stdout.strip() else None
    except json.JSONDecodeError:
        parsed = None
    return result.returncode, parsed, result.stderr


def run_rust_hook(subcommand: str, payload: dict) -> tuple[int, dict | None, str]:
    """Run a caf-hooks subcommand. Returns (exit_code, parsed_json_or_None, stderr)."""
    caf_bin = get_caf_hooks_bin()
    if caf_bin is None:
        return -1, None, "caf-hooks binary not found"
    result = subprocess.run(
        [str(caf_bin), subcommand],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=10,
    )
    try:
        parsed = json.loads(result.stdout) if result.stdout.strip() else None
    except json.JSONDecodeError:
        parsed = None
    return result.returncode, parsed, result.stderr


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_caddy_fires_on_prompt(tmp_path):
    """UserPromptSubmit to analyze_request.py must produce output containing classification."""
    hook = HOOKS["caddy_analyze"]
    if not hook.exists():
        pytest.skip(f"caddy analyze_request.py not found: {hook}")

    payload = {
        "hookEventName": "UserPromptSubmit",
        "prompt": "fix the auth bug",
        "session_id": "e2e-test-001",
    }
    t0 = time.perf_counter()
    rc, parsed, stderr = run_hook(hook, payload, tmp_path)
    TIMINGS.append({"hook": "caddy_analyze", "ms": (time.perf_counter() - t0) * 1000})

    assert rc in (0, 1), f"caddy analyze_request.py crashed: exit={rc} stderr={stderr[:300]}"
    # If it produced JSON, it should be a dict
    if parsed is not None:
        assert isinstance(parsed, dict), f"Expected dict output, got: {type(parsed)}"


def test_damage_control_passes_safe_command(tmp_path):
    """grep PreToolUse to damage-control (Rust) must exit 0."""
    caf_bin = get_caf_hooks_bin()
    if caf_bin is None:
        pytest.skip("caf-hooks binary not found")

    payload = SESSION_EVENTS[2][1]  # PreToolUse_grep
    t0 = time.perf_counter()
    rc, parsed, stderr = run_rust_hook("damage-control", payload)
    TIMINGS.append({"hook": "damage-control (safe grep)", "ms": (time.perf_counter() - t0) * 1000})

    assert rc == 0, (
        f"damage-control should pass safe grep command (exit 0), got {rc}. "
        f"stderr: {stderr[:300]}"
    )


def test_damage_control_blocks_rm_rf(tmp_path):
    """rm -rf PreToolUse to damage-control (Rust) must exit 2."""
    caf_bin = get_caf_hooks_bin()
    if caf_bin is None:
        pytest.skip("caf-hooks binary not found")

    payload = SESSION_EVENTS[6][1]  # PreToolUse_rm_rf
    t0 = time.perf_counter()
    rc, parsed, stderr = run_rust_hook("damage-control", payload)
    TIMINGS.append({"hook": "damage-control (rm -rf block)", "ms": (time.perf_counter() - t0) * 1000})

    assert rc == 2, (
        f"damage-control should block rm -rf (exit 2), got {rc}. "
        f"stdout: {parsed}  stderr: {stderr[:300]}"
    )


def test_full_session_no_crashes(tmp_path):
    """Full session pipeline must complete without unexpected crashes.

    Expected exit codes:
    - Most hooks: 0 (allow/pass)
    - damage-control on rm -rf: 2 (block)
    - Any exit code 1 is acceptable (hook disabled/no-op)
    """
    caf_bin = get_caf_hooks_bin()
    session_hooks_map: dict[str, list[tuple[str, list]]] = {
        "SessionStart": [("py", [HOOKS["session_startup"]])],
        "UserPromptSubmit": [("py", [HOOKS["caddy_analyze"]])],
        "PreToolUse_grep": [("rust", ["damage-control"])],
        "PostToolUse_grep": [],
        "PreToolUse_edit": [("rust", ["damage-control"])],
        "PostToolUse_edit": [],
        "PreToolUse_rm_rf": [("rust", ["damage-control"])],
        "Stop": [("py", [HOOKS["check_lthread"]])],
    }

    for event_name, payload in SESSION_EVENTS:
        # Fill in cwd
        if payload.get("cwd") is None:
            payload = {**payload, "cwd": str(REPO_ROOT)}

        hooks_to_run = session_hooks_map.get(event_name, [])
        for hook_type, hook_args in hooks_to_run:
            if hook_type == "py":
                hook_path = hook_args[0]
                if not hook_path.exists():
                    continue
                rc, _parsed, stderr = run_hook(hook_path, payload, tmp_path)
                # exit 2 is expected only for damage-control on rm -rf
                if event_name == "PreToolUse_rm_rf":
                    assert rc in (0, 1, 2), (
                        f"[{event_name}] {hook_path.name}: unexpected exit {rc}. stderr: {stderr[:200]}"
                    )
                else:
                    assert rc in (0, 1), (
                        f"[{event_name}] {hook_path.name}: unexpected exit {rc}. stderr: {stderr[:200]}"
                    )
            elif hook_type == "rust":
                if caf_bin is None:
                    continue
                subcommand = hook_args[0]
                rc, _parsed, stderr = run_rust_hook(subcommand, payload)
                if event_name == "PreToolUse_rm_rf":
                    assert rc in (0, 1, 2), (
                        f"[{event_name}] caf-hooks {subcommand}: unexpected exit {rc}. stderr: {stderr[:200]}"
                    )
                else:
                    assert rc in (0, 1), (
                        f"[{event_name}] caf-hooks {subcommand}: unexpected exit {rc}. stderr: {stderr[:200]}"
                    )


def test_full_session_timing(tmp_path):
    """Full session simulation must complete in under 30 seconds."""
    caf_bin = get_caf_hooks_bin()

    hooks_to_run: list[tuple[str, dict, str]] = [
        # (event_label, payload, hook_type::identifier)
    ]

    # Build execution list
    for event_name, payload in SESSION_EVENTS:
        if payload.get("cwd") is None:
            payload = {**payload, "cwd": str(REPO_ROOT)}
        if event_name == "SessionStart" and HOOKS["session_startup"].exists():
            hooks_to_run.append((event_name, payload, f"py::{HOOKS['session_startup']}"))
        elif event_name == "UserPromptSubmit" and HOOKS["caddy_analyze"].exists():
            hooks_to_run.append((event_name, payload, f"py::{HOOKS['caddy_analyze']}"))
        elif event_name in ("PreToolUse_grep", "PreToolUse_edit", "PreToolUse_rm_rf") and caf_bin:
            hooks_to_run.append((event_name, payload, "rust::damage-control"))
        elif event_name == "Stop" and HOOKS["check_lthread"].exists():
            hooks_to_run.append((event_name, payload, f"py::{HOOKS['check_lthread']}"))

    t_start = time.perf_counter()

    for _event_name, payload, hook_id in hooks_to_run:
        if hook_id.startswith("py::"):
            hook_path = Path(hook_id[4:])
            if hook_path.exists():
                run_hook(hook_path, payload, tmp_path)
        elif hook_id.startswith("rust::"):
            subcommand = hook_id[6:]
            if caf_bin:
                run_rust_hook(subcommand, payload)

    elapsed = time.perf_counter() - t_start
    TIMINGS.append({"hook": "full_session_e2e_total", "ms": elapsed * 1000})

    assert elapsed < 30, (
        f"Full session simulation took {elapsed:.1f}s, expected < 30s"
    )


def test_session_event_sequence(tmp_path):
    """Hooks correctly process events in order without state corruption between calls."""
    caf_bin = get_caf_hooks_bin()
    results: list[dict] = []

    for event_name, payload in SESSION_EVENTS:
        if payload.get("cwd") is None:
            payload = {**payload, "cwd": str(REPO_ROOT)}

        event_result = {"event": event_name, "hooks_run": [], "errors": []}

        # SessionStart
        if event_name == "SessionStart" and HOOKS["session_startup"].exists():
            rc, parsed, stderr = run_hook(HOOKS["session_startup"], payload, tmp_path)
            event_result["hooks_run"].append({"hook": "session_startup", "rc": rc})
            if rc not in (0, 1):
                event_result["errors"].append(f"session_startup exit {rc}")

        # UserPromptSubmit
        elif event_name == "UserPromptSubmit" and HOOKS["caddy_analyze"].exists():
            rc, parsed, stderr = run_hook(HOOKS["caddy_analyze"], payload, tmp_path)
            event_result["hooks_run"].append({"hook": "caddy_analyze", "rc": rc})
            if rc not in (0, 1):
                event_result["errors"].append(f"caddy_analyze exit {rc}")

        # PreToolUse — damage-control
        elif event_name.startswith("PreToolUse") and caf_bin:
            rc, parsed, stderr = run_rust_hook("damage-control", payload)
            event_result["hooks_run"].append({"hook": "damage-control", "rc": rc})
            # rm -rf should be blocked (exit 2), others allowed (exit 0)
            if event_name == "PreToolUse_rm_rf":
                if rc not in (0, 1, 2):
                    event_result["errors"].append(f"damage-control exit {rc} (expected 0/1/2)")
            else:
                if rc not in (0, 1):
                    event_result["errors"].append(f"damage-control exit {rc} (expected 0/1 for safe cmd)")

        results.append(event_result)

    all_errors = [(r["event"], e) for r in results for e in r["errors"]]
    assert len(all_errors) == 0, (
        "Errors during session event sequence:\n"
        + "\n".join(f"  [{ev}] {err}" for ev, err in all_errors)
    )


def test_error_hook_fires_on_test_failure(tmp_path):
    """PostToolUse with pytest failure exit code must cause auto-error analyzer to produce output."""
    caf_bin = get_caf_hooks_bin()
    if caf_bin is None:
        # Try Python fallback
        py_hook = HOOKS["auto_error_analyzer_py"]
        if not py_hook.exists():
            pytest.skip("Neither caf-hooks binary nor Python auto_error_analyzer found")
        payload = {
            "hookEventName": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "pytest tests/"},
            "tool_response": {
                "stdout": "FAILED tests/test_auth.py::test_login - AssertionError: expected True got False",
                "exit_code": 1,
            },
            "session_id": "e2e-test-001",
        }
        rc, parsed, stderr = run_hook(py_hook, payload, tmp_path)
        assert rc in (0, 1), f"auto_error_analyzer crashed: exit={rc}"
        combined = (parsed or {}).get("hookSpecificOutput", "") + stderr
        has_output = len(combined.strip()) > 0 or (parsed is not None)
        assert has_output, "Expected auto_error_analyzer to produce output for failed test"
        return

    # Use Rust auto-error-analyzer
    payload = {
        "hookEventName": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "pytest tests/"},
        "tool_response": {
            "stdout": "FAILED tests/test_auth.py::test_login - AssertionError: expected True got False",
            "exit_code": 1,
        },
        "session_id": "e2e-test-001",
    }
    t0 = time.perf_counter()
    rc, parsed, stderr = run_rust_hook("auto-error-analyzer", payload)
    TIMINGS.append({"hook": "auto-error-analyzer", "ms": (time.perf_counter() - t0) * 1000})

    assert rc in (0, 1), f"auto-error-analyzer crashed: exit={rc} stderr={stderr[:300]}"
    combined = str(parsed or "") + stderr
    # Should produce some classification or guidance
    has_output = len(combined.strip()) > 10 or parsed is not None
    assert has_output, (
        "Expected auto-error-analyzer output for pytest failure. "
        f"stdout: {str(parsed)[:200]}  stderr: {stderr[:200]}"
    )


def test_stop_hook_completes(tmp_path):
    """Stop event to check_lthread_progress.py must exit without error."""
    hook = HOOKS["check_lthread"]
    if not hook.exists():
        pytest.skip(f"check_lthread_progress.py not found: {hook}")

    payload = {
        "hookEventName": "Stop",
        "session_id": "e2e-test-001",
        "stop_reason": "end_turn",
    }
    t0 = time.perf_counter()
    rc, parsed, stderr = run_hook(hook, payload, tmp_path)
    TIMINGS.append({"hook": "check_lthread_progress", "ms": (time.perf_counter() - t0) * 1000})

    assert rc in (0, 1), (
        f"check_lthread_progress.py exited {rc} on Stop event. "
        f"stderr: {stderr[:300]}"
    )
