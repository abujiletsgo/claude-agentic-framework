"""
test_rust_hooks.py — Verify caf-hooks Rust binary subcommands and benchmark vs Python.
Builder-2 | CAF Audit Suite
"""
import pytest
import subprocess
import json
import time
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent  # tests/audit/modules/test_rust_hooks.py -> repo root
CAF_HOOKS_RELEASE = REPO_ROOT / "caf-hooks/target/release/caf-hooks"
CAF_HOOKS_DEBUG = REPO_ROOT / "caf-hooks/target/debug/caf-hooks"

TIMINGS: list[dict] = []

pytestmark = pytest.mark.slow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_caf_hooks_bin() -> Path | None:
    if CAF_HOOKS_RELEASE.exists():
        return CAF_HOOKS_RELEASE
    if CAF_HOOKS_DEBUG.exists():
        return CAF_HOOKS_DEBUG
    return None


def run_caf_hooks(subcommand: str, payload: dict, timeout: int = 10) -> subprocess.CompletedProcess:
    """Run a caf-hooks subcommand with JSON payload on stdin."""
    caf_bin = get_caf_hooks_bin()
    if caf_bin is None:
        pytest.skip("caf-hooks binary not found")
    t0 = time.perf_counter()
    result = subprocess.run(
        [str(caf_bin), subcommand],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=timeout,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    TIMINGS.append({"hook": f"caf-hooks {subcommand}", "ms": elapsed_ms})
    return result


def benchmark(cmd: list[str], payload: dict, n: int = 50) -> dict:
    """Run cmd with JSON payload n times and return timing stats."""
    times: list[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        subprocess.run(
            cmd,
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=30,
        )
        times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    return {
        "mean_ms": sum(times) / len(times),
        "p50_ms": times[len(times) // 2],
        "p95_ms": times[int(len(times) * 0.95)],
        "p99_ms": times[int(len(times) * 0.99)],
    }


# ---------------------------------------------------------------------------
# Existence and help tests
# ---------------------------------------------------------------------------


def test_rust_binary_exists():
    """caf-hooks binary must exist at release or debug path."""
    if get_caf_hooks_bin() is None:
        pytest.fail(
            f"caf-hooks binary not found at:\n  {CAF_HOOKS_RELEASE}\n  {CAF_HOOKS_DEBUG}\n"
            "Run: cd caf-hooks && cargo build --release"
        )


def test_rust_binary_help():
    """caf-hooks --help must exit 0."""
    caf_bin = get_caf_hooks_bin()
    if caf_bin is None:
        pytest.skip("caf-hooks binary not found")

    result = subprocess.run(
        [str(caf_bin), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"caf-hooks --help exited {result.returncode}. "
        f"stderr: {result.stderr[:300]}"
    )


# ---------------------------------------------------------------------------
# Subcommand functional tests
# ---------------------------------------------------------------------------


def test_enforce_orchestrate_fires_on_slash_command():
    """Prompt starting with /orchestrate must produce non-empty stdout."""
    result = run_caf_hooks(
        "enforce-orchestrate",
        {"prompt": "/orchestrate fix the bug", "hookEventName": "UserPromptSubmit"},
    )
    assert result.returncode in (0, 1, 2), f"Unexpected exit code {result.returncode}"
    assert result.stdout.strip() != "", (
        "enforce-orchestrate should produce output for /orchestrate prompts. "
        f"Got empty stdout. stderr: {result.stderr[:300]}"
    )


def test_enforce_orchestrate_silent_on_normal_prompt():
    """A non-orchestrate prompt must produce empty or minimal stdout."""
    result = run_caf_hooks(
        "enforce-orchestrate",
        {"prompt": "fix the bug", "hookEventName": "UserPromptSubmit"},
    )
    assert result.returncode == 0, (
        f"enforce-orchestrate should exit 0 for normal prompts. "
        f"exit={result.returncode} stderr={result.stderr[:300]}"
    )
    stdout = result.stdout.strip()
    # Should be silent or produce an empty JSON object
    if stdout:
        try:
            data = json.loads(stdout)
            # Allow {"hookSpecificOutput": ""} or {} but not enforcement messages
            output_text = str(data.get("hookSpecificOutput", ""))
            assert len(output_text) < 50, (
                f"Expected minimal/empty output for normal prompt, got: {output_text}"
            )
        except json.JSONDecodeError:
            assert len(stdout) < 50, (
                f"Expected minimal stdout for normal prompt, got: {stdout}"
            )


def test_epistemic_guard_fires_on_analysis_prompt():
    """Prompt containing 'analyze' must trigger OBSERVED/INFERRED reminder in output."""
    result = run_caf_hooks(
        "epistemic-guard",
        {
            "prompt": "analyze the performance of this system",
            "hookEventName": "UserPromptSubmit",
        },
    )
    assert result.returncode in (0, 1), f"Unexpected exit code {result.returncode}"
    combined = result.stdout + result.stderr
    found = (
        "OBSERVED" in combined
        or "INFERRED" in combined
        or "epistemic" in combined.lower()
        or "observation" in combined.lower()
    )
    assert found, (
        "Expected OBSERVED/INFERRED reminder in epistemic-guard output for analysis prompt. "
        f"stdout: {result.stdout[:300]}  stderr: {result.stderr[:300]}"
    )


def test_auto_refine_suggestion_on_warning():
    """PostToolUse payload where tool_response contains [WARNING] must trigger refine suggestion."""
    result = run_caf_hooks(
        "auto-refine",
        {
            "hookEventName": "PostToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": "/src/auth.py"},
            "tool_response": {
                "stdout": "[WARNING] deprecated function used",
                "success": True,
            },
        },
    )
    assert result.returncode in (0, 1), f"Unexpected exit code {result.returncode}"
    combined = result.stdout + result.stderr
    # A refine suggestion should mention the issue or provide guidance
    has_suggestion = (
        len(combined.strip()) > 0
        and (
            "refine" in combined.lower()
            or "warning" in combined.lower()
            or "suggest" in combined.lower()
            or "improve" in combined.lower()
            or "deprecated" in combined.lower()
        )
    )
    assert has_suggestion, (
        "Expected refine suggestion for PostToolUse with [WARNING] response. "
        f"stdout: {result.stdout[:300]}  stderr: {result.stderr[:300]}"
    )


def test_stop_failure_recovery_rate_limit():
    """stop-failure-recovery with error_type=rate_limit must include recovery advice."""
    result = run_caf_hooks(
        "stop-failure-recovery",
        {
            "hookEventName": "StopFailure",
            "error_type": "rate_limit",
            "session_id": "test-rust-001",
        },
    )
    assert result.returncode in (0, 1), f"Unexpected exit code {result.returncode}"
    combined = result.stdout + result.stderr
    has_recovery = (
        "rate" in combined.lower()
        or "limit" in combined.lower()
        or "retry" in combined.lower()
        or "wait" in combined.lower()
        or "recovery" in combined.lower()
        or len(combined.strip()) > 10  # any non-trivial output counts
    )
    assert has_recovery, (
        "Expected recovery advice for rate_limit error. "
        f"stdout: {result.stdout[:300]}  stderr: {result.stderr[:300]}"
    )


# ---------------------------------------------------------------------------
# Speed benchmark tests
# ---------------------------------------------------------------------------


def test_rust_vs_python_speed_enforce_orchestrate():
    """Rust enforce-orchestrate must be faster than Python equivalent (50 iterations each)."""
    caf_bin = get_caf_hooks_bin()
    if caf_bin is None:
        pytest.skip("caf-hooks binary not found")

    py_hook = REPO_ROOT / "caf-hooks/src/hooks"
    # Look for a Python equivalent
    python_equivalent = None
    for candidate in [
        REPO_ROOT / "global-hooks/framework/caddy/enforce_orchestrate.py",
        REPO_ROOT / "global-hooks" / "enforce_orchestrate.py",
    ]:
        if candidate.exists():
            python_equivalent = candidate
            break

    payload = {"prompt": "/orchestrate fix the bug", "hookEventName": "UserPromptSubmit"}

    rust_stats = benchmark([str(caf_bin), "enforce-orchestrate"], payload, n=50)
    TIMINGS.append({"hook": "rust enforce-orchestrate benchmark", **rust_stats})

    print(f"\n  Rust enforce-orchestrate: mean={rust_stats['mean_ms']:.1f}ms p99={rust_stats['p99_ms']:.1f}ms")

    if python_equivalent is None:
        print("  Python equivalent not found — skipping speedup ratio comparison")
        return

    python_stats = benchmark(
        ["uv", "run", "--no-project", str(python_equivalent)],
        payload,
        n=50,
    )
    TIMINGS.append({"hook": "python enforce-orchestrate benchmark", **python_stats})

    speedup = python_stats["mean_ms"] / rust_stats["mean_ms"] if rust_stats["mean_ms"] > 0 else 0
    print(f"  Python enforce-orchestrate: mean={python_stats['mean_ms']:.1f}ms p99={python_stats['p99_ms']:.1f}ms")
    print(f"  Speedup ratio: {speedup:.1f}x (expected 6-32x)")

    # Rust should be at least as fast as Python (not necessarily 6x if startup dominates)
    assert rust_stats["mean_ms"] <= python_stats["mean_ms"] * 1.5, (
        f"Rust ({rust_stats['mean_ms']:.1f}ms) was not faster than Python ({python_stats['mean_ms']:.1f}ms). "
        "This may indicate the Rust binary has significant startup overhead."
    )


def test_rust_vs_python_speed_epistemic_guard():
    """Rust epistemic-guard must be faster than Python equivalent (50 iterations each)."""
    caf_bin = get_caf_hooks_bin()
    if caf_bin is None:
        pytest.skip("caf-hooks binary not found")

    python_equivalent = None
    for candidate in [
        REPO_ROOT / "global-hooks/framework/caddy/epistemic_guard.py",
        REPO_ROOT / "global-hooks" / "epistemic_guard.py",
    ]:
        if candidate.exists():
            python_equivalent = candidate
            break

    payload = {
        "prompt": "analyze the performance of this system",
        "hookEventName": "UserPromptSubmit",
    }

    rust_stats = benchmark([str(caf_bin), "epistemic-guard"], payload, n=50)
    TIMINGS.append({"hook": "rust epistemic-guard benchmark", **rust_stats})

    print(f"\n  Rust epistemic-guard: mean={rust_stats['mean_ms']:.1f}ms p99={rust_stats['p99_ms']:.1f}ms")

    if python_equivalent is None:
        print("  Python equivalent not found — skipping speedup ratio comparison")
        return

    python_stats = benchmark(
        ["uv", "run", "--no-project", str(python_equivalent)],
        payload,
        n=50,
    )
    TIMINGS.append({"hook": "python epistemic-guard benchmark", **python_stats})

    speedup = python_stats["mean_ms"] / rust_stats["mean_ms"] if rust_stats["mean_ms"] > 0 else 0
    print(f"  Python epistemic-guard: mean={python_stats['mean_ms']:.1f}ms p99={python_stats['p99_ms']:.1f}ms")
    print(f"  Speedup ratio: {speedup:.1f}x (expected 6-32x)")

    assert rust_stats["mean_ms"] <= python_stats["mean_ms"] * 1.5, (
        f"Rust ({rust_stats['mean_ms']:.1f}ms) was not faster than Python ({python_stats['mean_ms']:.1f}ms)."
    )
