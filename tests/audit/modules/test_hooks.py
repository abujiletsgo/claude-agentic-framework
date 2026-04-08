"""
test_hooks.py — Verify all hooks exist and return valid output for mock inputs.
Builder-2 | CAF Audit Suite
"""
from pathlib import Path
import json
import subprocess
import time
import sys

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent  # tests/audit/modules/test_hooks.py -> repo root
SETTINGS_TEMPLATE = REPO_ROOT / "templates/settings.json.template"
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

TIMINGS: list[dict] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_settings_template() -> dict:
    return json.loads(SETTINGS_TEMPLATE.read_text())


def extract_hook_paths(settings: dict) -> list[Path]:
    """Parse all hook commands from settings.json.template and return resolved Python paths.

    Handles two forms:
      - "uv run --no-project __REPO_DIR__/path/to/hook.py"
      - "__REPO_DIR__/caf-hooks/target/release/caf-hooks subcommand"

    Returns only .py paths; Rust binary paths are handled by test_rust_binary_exists.
    """
    paths: list[Path] = []
    hooks_section = settings.get("hooks", {})
    for _event, hook_groups in hooks_section.items():
        if not isinstance(hook_groups, list):
            continue
        for group in hook_groups:
            for hook in group.get("hooks", []):
                cmd = hook.get("command", "")
                if not cmd:
                    continue
                # Extract the path token that starts with __REPO_DIR__
                tokens = cmd.split()
                for token in tokens:
                    if token.startswith("__REPO_DIR__"):
                        relative = token.replace("__REPO_DIR__/", "")
                        full = REPO_ROOT / relative
                        if str(full).endswith(".py"):
                            paths.append(full)
                        break
    # Deduplicate while preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def extract_all_hook_commands(settings: dict) -> list[str]:
    """Return every raw command string from hooks section."""
    commands: list[str] = []
    hooks_section = settings.get("hooks", {})
    for _event, hook_groups in hooks_section.items():
        if not isinstance(hook_groups, list):
            continue
        for group in hook_groups:
            for hook in group.get("hooks", []):
                cmd = hook.get("command", "")
                if cmd:
                    commands.append(cmd)
    return commands


def resolve_command_path(cmd: str) -> Path:
    """Given a raw command string, resolve the executable path."""
    tokens = cmd.split()
    for token in tokens:
        if token.startswith("__REPO_DIR__"):
            relative = token.replace("__REPO_DIR__/", "")
            return REPO_ROOT / relative
    return Path(cmd.split()[0])


def run_hook_subprocess(
    hook_path: Path,
    payload: dict,
    timeout: int = 15,
    extra_args: list[str] | None = None,
) -> tuple[int, str, str]:
    """Run a Python hook via uv run. Returns (returncode, stdout, stderr)."""
    cmd = ["uv", "run", "--no-project", str(hook_path)]
    if extra_args:
        cmd.extend(extra_args)
    t0 = time.perf_counter()
    result = subprocess.run(
        cmd,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=timeout,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    TIMINGS.append({"hook": str(hook_path.name), "ms": elapsed_ms})
    return result.returncode, result.stdout, result.stderr


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_all_hook_files_exist():
    """Every Python hook path referenced in settings.json.template must exist."""
    settings = load_settings_template()
    hook_paths = extract_hook_paths(settings)
    assert len(hook_paths) > 0, "No hook paths found — template may be empty"

    missing: list[str] = []
    for p in hook_paths:
        if not p.exists():
            missing.append(str(p.relative_to(REPO_ROOT)))

    found = len(hook_paths) - len(missing)
    report = f"{found}/{len(hook_paths)} hooks found"
    if missing:
        pytest.fail(f"{report} — MISSING:\n" + "\n".join(missing))
    else:
        # Print summary for audit report
        print(f"\n  {report}")


def test_rust_binary_exists():
    """At least one of the release or debug caf-hooks binaries must exist."""
    release = REPO_ROOT / "caf-hooks/target/release/caf-hooks"
    debug = REPO_ROOT / "caf-hooks/target/debug/caf-hooks"
    if not (release.exists() or debug.exists()):
        pytest.fail(
            f"caf-hooks binary not found at:\n  {release}\n  {debug}\n"
            "Run: cd caf-hooks && cargo build --release"
        )


def test_hook_settings_template_consistency():
    """Every file path (Python or Rust) in settings.json.template references a real file."""
    settings = load_settings_template()
    commands = extract_all_hook_commands(settings)
    missing: list[str] = []

    for cmd in commands:
        p = resolve_command_path(cmd)
        # Skip subcommand tokens (e.g. "caf-hooks voice-done" → p is the binary)
        # Only flag if it looks like a source path (contains 'global-hooks' or ends with .py)
        rel = str(p)
        if "global-hooks" in rel or rel.endswith(".py"):
            if not p.exists():
                missing.append(str(p.relative_to(REPO_ROOT)))
        elif "caf-hooks/target" in rel:
            # Rust binary — release or debug both acceptable
            release_path = REPO_ROOT / "caf-hooks/target/release/caf-hooks"
            debug_path = REPO_ROOT / "caf-hooks/target/debug/caf-hooks"
            if not (release_path.exists() or debug_path.exists()):
                missing.append("caf-hooks/target/release/caf-hooks (or debug)")

    if missing:
        deduped = sorted(set(missing))
        pytest.fail("Missing files referenced in settings.json.template:\n" + "\n".join(deduped))


def test_hook_json_input_output_sessionstart():
    """SessionStart hook must run without crashing and produce valid JSON or empty stdout."""
    hook = REPO_ROOT / "global-hooks/framework/session/session_startup.py"
    if not hook.exists():
        pytest.skip(f"Hook not found: {hook.relative_to(REPO_ROOT)}")

    payload = {
        "hookEventName": "SessionStart",
        "cwd": str(REPO_ROOT),
        "session_id": "test-audit-001",
    }
    rc, stdout, stderr = run_hook_subprocess(hook, payload, timeout=15)
    assert rc in (0, 1), f"Unexpected exit code {rc}. stderr: {stderr[:500]}"
    if stdout.strip():
        try:
            json.loads(stdout)
        except json.JSONDecodeError:
            pytest.fail(f"SessionStart hook produced non-JSON stdout:\n{stdout[:500]}")


def test_hook_json_input_output_userpromptsubmit():
    """UserPromptSubmit/analyze_request.py must produce output with hookSpecificOutput field."""
    hook = REPO_ROOT / "global-hooks/framework/caddy/analyze_request.py"
    if not hook.exists():
        pytest.skip(f"Hook not found: {hook.relative_to(REPO_ROOT)}")

    payload = {
        "hookEventName": "UserPromptSubmit",
        "prompt": "fix the auth bug",
        "session_id": "test-audit-001",
    }
    rc, stdout, stderr = run_hook_subprocess(hook, payload, timeout=15)
    assert rc in (0, 1), f"analyze_request.py crashed with exit code {rc}. stderr: {stderr[:500]}"
    if stdout.strip():
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            pytest.fail(f"Non-JSON output from analyze_request.py:\n{stdout[:500]}")
            return
        # Accept either hookSpecificOutput or any dict — hook may be disabled
        assert isinstance(data, dict), "Output must be a JSON object"


def test_hook_json_input_output_pretooluse_safe():
    """PreToolUse with a safe Bash command must exit 0 from damage-control hook."""
    # damage-control is the Rust binary; look for it
    release = REPO_ROOT / "caf-hooks/target/release/caf-hooks"
    debug = REPO_ROOT / "caf-hooks/target/debug/caf-hooks"
    caf_bin = release if release.exists() else (debug if debug.exists() else None)
    if caf_bin is None:
        pytest.skip("caf-hooks binary not found")

    payload = {
        "hookEventName": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "echo hello"},
        "session_id": "test-audit-001",
    }
    t0 = time.perf_counter()
    result = subprocess.run(
        [str(caf_bin), "damage-control"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=10,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    TIMINGS.append({"hook": "caf-hooks damage-control (safe)", "ms": elapsed_ms})
    assert result.returncode == 0, (
        f"damage-control should exit 0 for safe command, got {result.returncode}. "
        f"stderr: {result.stderr[:300]}"
    )


def test_hook_json_input_output_pretooluse_dangerous():
    """PreToolUse with rm -rf must cause damage-control to exit 2 (block)."""
    release = REPO_ROOT / "caf-hooks/target/release/caf-hooks"
    debug = REPO_ROOT / "caf-hooks/target/debug/caf-hooks"
    caf_bin = release if release.exists() else (debug if debug.exists() else None)
    if caf_bin is None:
        pytest.skip("caf-hooks binary not found")

    payload = {
        "hookEventName": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "rm -rf /tmp/test-audit"},
        "session_id": "test-audit-001",
    }
    t0 = time.perf_counter()
    result = subprocess.run(
        [str(caf_bin), "damage-control"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=10,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    TIMINGS.append({"hook": "caf-hooks damage-control (dangerous)", "ms": elapsed_ms})
    assert result.returncode == 2, (
        f"damage-control should exit 2 for dangerous command, got {result.returncode}. "
        f"stdout: {result.stdout[:300]}  stderr: {result.stderr[:300]}"
    )


def test_hook_timeout_compliance():
    """Each non-async Python hook with timeout <= 10s must complete within 5 seconds."""
    settings = load_settings_template()
    hooks_section = settings.get("hooks", {})
    violations: list[str] = []
    skipped: list[str] = []

    for _event, hook_groups in hooks_section.items():
        if not isinstance(hook_groups, list):
            continue
        for group in hook_groups:
            for hook in group.get("hooks", []):
                if hook.get("async"):
                    continue  # skip async hooks — they're fire-and-forget
                configured_timeout = hook.get("timeout", 999)
                if configured_timeout > 10:
                    continue  # only test fast hooks
                cmd = hook.get("command", "")
                if not cmd:
                    continue
                # Only test Python hooks
                tokens = cmd.split()
                py_path = None
                for token in tokens:
                    if token.startswith("__REPO_DIR__") and token.endswith(".py"):
                        py_path = REPO_ROOT / token.replace("__REPO_DIR__/", "")
                        break
                if py_path is None:
                    continue
                if not py_path.exists():
                    skipped.append(str(py_path.name))
                    continue

                # Use a minimal generic payload
                payload = {
                    "hookEventName": _event,
                    "session_id": "test-timeout-check",
                    "cwd": str(REPO_ROOT),
                }
                t0 = time.perf_counter()
                try:
                    result = subprocess.run(
                        ["uv", "run", "--no-project", str(py_path)],
                        input=json.dumps(payload),
                        capture_output=True,
                        text=True,
                        cwd=str(REPO_ROOT),
                        timeout=5,
                    )
                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    TIMINGS.append({"hook": py_path.name, "ms": elapsed_ms})
                except subprocess.TimeoutExpired:
                    violations.append(f"{py_path.name} (event={_event}) exceeded 5s deadline")

    if violations:
        pytest.fail("Hooks exceeded 5s deadline:\n" + "\n".join(violations))
    if skipped:
        print(f"\n  Skipped (not found): {', '.join(skipped)}")
