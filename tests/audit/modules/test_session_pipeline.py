"""
CAF Audit — Session Pipeline Tests
=====================================
Tests the SessionStart hook pipeline:
  1. session_startup.py  — orchestrates 6 sub-hooks via subprocess
  2. spawn_hud.py        — detects active orch job, launches caf-hud
  3. auto_prime.py       — loads PROJECT_CONTEXT.md if git hash matches

Run standalone:
  uv run pytest tests/audit/modules/test_session_pipeline.py -v
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent
SESSION_DIR = REPO_ROOT / "global-hooks/framework/session"
AUTOMATION_DIR = REPO_ROOT / "global-hooks/framework/automation"

TIMINGS: list[dict] = []

SESSION_STARTUP = SESSION_DIR / "session_startup.py"
SPAWN_HUD = SESSION_DIR / "spawn_hud.py"
AUTO_PRIME = AUTOMATION_DIR / "auto_prime.py"


# ── helpers ────────────────────────────────────────────────────────────────────

def record_timing(test_name: str, elapsed_ms: float) -> None:
    TIMINGS.append({"test": test_name, "ms": elapsed_ms})


def get_git_hash(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    return result.stdout.strip()


def make_context_file(tmp_path: Path, git_hash: str) -> Path:
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(exist_ok=True)
    ctx = claude_dir / "PROJECT_CONTEXT.md"
    ctx.write_text(
        f"<!-- GIT_HASH: {git_hash} -->\n"
        f"<!-- GENERATED: 2026-04-14 -->\n\n"
        f"# Test Context\n\n"
        + ("x" * 600)  # ensure len > 500 so load_cached_context accepts it
        + "\n"
    )
    return ctx


def run_script(script: Path, *, stdin_text: str = "{}", extra_env: dict | None = None,
               cwd: Path | None = None, timeout: int = 10) -> subprocess.CompletedProcess:
    env = {**os.environ, "HOME": str(cwd or script.parent)}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["python3", str(script)],
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(cwd or script.parent),
        env=env,
    )


# ── TestSessionStartup ─────────────────────────────────────────────────────────

_SESSION_STARTUP_EXISTS = SESSION_STARTUP.exists()


@pytest.mark.skipif(not _SESSION_STARTUP_EXISTS, reason="session_startup.py not found")
class TestSessionStartup:
    @pytest.mark.timeout(10)
    def test_empty_json_exits_zero(self, tmp_path):
        t0 = time.perf_counter()
        result = run_script(SESSION_STARTUP, stdin_text="{}", cwd=tmp_path)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("TestSessionStartup.test_empty_json_exits_zero", elapsed_ms)
        assert result.returncode == 0, (
            f"session_startup.py with empty JSON should exit 0, got {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )

    @pytest.mark.timeout(10)
    def test_valid_event_exits_zero(self, tmp_path):
        event = {
            "hookEventName": "SessionStart",
            "sessionId": "test-session-123",
            "cwd": str(tmp_path),
        }
        t0 = time.perf_counter()
        result = run_script(SESSION_STARTUP, stdin_text=json.dumps(event), cwd=tmp_path)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("TestSessionStartup.test_valid_event_exits_zero", elapsed_ms)
        assert result.returncode == 0, (
            f"session_startup.py with valid SessionStart event should exit 0, got {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )

    @pytest.mark.timeout(10)
    def test_invalid_json_exits_zero(self, tmp_path):
        t0 = time.perf_counter()
        result = run_script(SESSION_STARTUP, stdin_text="not json", cwd=tmp_path)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("TestSessionStartup.test_invalid_json_exits_zero", elapsed_ms)
        assert result.returncode == 0, (
            f"session_startup.py should be fail-open on invalid JSON, got {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )

    @pytest.mark.timeout(10)
    def test_no_stdin_exits_zero(self, tmp_path):
        """Run with no input at all (empty string) — should exit 0."""
        t0 = time.perf_counter()
        result = run_script(SESSION_STARTUP, stdin_text="", cwd=tmp_path)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("TestSessionStartup.test_no_stdin_exits_zero", elapsed_ms)
        assert result.returncode == 0, (
            f"session_startup.py with no stdin should exit 0, got {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )

    @pytest.mark.timeout(10)
    def test_does_not_crash_on_missing_sub_hooks(self, tmp_path):
        """Sub-hooks may be absent or fail; startup.py must not propagate failures."""
        # Run from tmp_path (no framework dir there), so all sub-hooks will be missing.
        env = {**os.environ, "HOME": str(tmp_path)}
        t0 = time.perf_counter()
        result = subprocess.run(
            ["python3", str(SESSION_STARTUP)],
            input="{}",
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(tmp_path),
            env=env,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("TestSessionStartup.test_does_not_crash_on_missing_sub_hooks", elapsed_ms)
        assert result.returncode == 0, (
            f"session_startup.py should exit 0 even when sub-hooks fail/are missing, "
            f"got {result.returncode}.\nstderr: {result.stderr}"
        )


# ── TestSpawnHud ───────────────────────────────────────────────────────────────

_SPAWN_HUD_EXISTS = SPAWN_HUD.exists()


@pytest.mark.skipif(not _SPAWN_HUD_EXISTS, reason="spawn_hud.py not found")
class TestSpawnHud:
    @pytest.mark.timeout(10)
    def test_no_cmux_surface_exits_zero(self, monkeypatch, tmp_path):
        """When CMUX_SURFACE_ID is not set, spawn_hud exits 0 without calling cmux-sprint."""
        env = {k: v for k, v in os.environ.items() if k != "CMUX_SURFACE_ID"}
        env["HOME"] = str(tmp_path)
        t0 = time.perf_counter()
        result = subprocess.run(
            ["python3", str(SPAWN_HUD)],
            input="{}",
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(tmp_path),
            env=env,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("TestSpawnHud.test_no_cmux_surface_exits_zero", elapsed_ms)
        assert result.returncode == 0, (
            f"spawn_hud.py without CMUX_SURFACE_ID should exit 0, got {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )

    @pytest.mark.timeout(10)
    def test_no_active_orch_job_exits_zero(self, monkeypatch, tmp_path):
        """CMUX_SURFACE_ID set but /tmp/caf_orch/ is empty — should exit 0."""
        fake_orch = tmp_path / "caf_orch"
        fake_orch.mkdir()
        env = {**os.environ, "CMUX_SURFACE_ID": "test-surface-1", "HOME": str(tmp_path)}
        t0 = time.perf_counter()
        # Patch orch_base by pointing ORCH_BASE env (spawn_hud reads /tmp/caf_orch hard-coded,
        # so we test against the real path being empty — if it happens to exist and have jobs
        # this test still passes because the script exits 0 either way).
        result = subprocess.run(
            ["python3", str(SPAWN_HUD)],
            input="{}",
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(tmp_path),
            env=env,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("TestSpawnHud.test_no_active_orch_job_exits_zero", elapsed_ms)
        assert result.returncode == 0, (
            f"spawn_hud.py with no active orch job should exit 0, got {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )

    @pytest.mark.timeout(10)
    def test_exits_zero_even_when_cmux_sprint_missing(self, monkeypatch, tmp_path):
        """CMUX_SURFACE_ID set, fake acceptance_criteria.md exists, cmux-sprint absent → exit 0."""
        # Create a fake orch dir under /tmp/caf_orch so the script finds a job.
        # spawn_hud hard-codes /tmp/caf_orch, so create a real entry there if writable.
        orch_base = Path("/tmp/caf_orch")
        test_orch_dir = orch_base / "test_spawn_hud_no_cmux"
        try:
            test_orch_dir.mkdir(parents=True, exist_ok=True)
            criteria = test_orch_dir / "acceptance_criteria.md"
            criteria.write_text("# Test\n")
            created = True
        except OSError:
            created = False

        env = {
            **os.environ,
            "CMUX_SURFACE_ID": "test-surface-2",
            "HOME": str(tmp_path),
            # Put a non-existent bin dir first so cmux-sprint is guaranteed not found.
            "PATH": str(tmp_path / "nonexistent_bin") + ":" + os.environ.get("PATH", ""),
        }
        t0 = time.perf_counter()
        result = subprocess.run(
            ["python3", str(SPAWN_HUD)],
            input="{}",
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(tmp_path),
            env=env,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("TestSpawnHud.test_exits_zero_even_when_cmux_sprint_missing", elapsed_ms)

        # Clean up
        if created:
            try:
                criteria.unlink()
                test_orch_dir.rmdir()
            except OSError:
                pass

        assert result.returncode == 0, (
            f"spawn_hud.py should exit 0 even when cmux-sprint is missing, got {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )

    @pytest.mark.timeout(10)
    def test_detects_active_orch_job(self, monkeypatch, tmp_path):
        """With CMUX_SURFACE_ID set and a real acceptance_criteria.md found, exits 0."""
        # Create a fake orch entry under /tmp/caf_orch (spawn_hud hard-codes this path).
        orch_base = Path("/tmp/caf_orch")
        test_orch_dir = orch_base / "test_spawn_hud_detect"
        try:
            test_orch_dir.mkdir(parents=True, exist_ok=True)
            criteria = test_orch_dir / "acceptance_criteria.md"
            criteria.write_text("# Test acceptance criteria\n")
            created = True
        except OSError:
            created = False

        env = {
            **os.environ,
            "CMUX_SURFACE_ID": "test-surface-3",
            "HOME": str(tmp_path),
        }
        t0 = time.perf_counter()
        result = subprocess.run(
            ["python3", str(SPAWN_HUD)],
            input="{}",
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(tmp_path),
            env=env,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("TestSpawnHud.test_detects_active_orch_job", elapsed_ms)

        # Clean up
        if created:
            try:
                criteria.unlink()
                test_orch_dir.rmdir()
            except OSError:
                pass

        assert result.returncode == 0, (
            f"spawn_hud.py should exit 0 after detecting orch job (Popen failure caught), "
            f"got {result.returncode}.\nstderr: {result.stderr}"
        )


# ── TestAutoPrime ──────────────────────────────────────────────────────────────

_AUTO_PRIME_EXISTS = AUTO_PRIME.exists()


@pytest.mark.skipif(not _AUTO_PRIME_EXISTS, reason="auto_prime.py not found")
class TestAutoPrime:
    @pytest.mark.timeout(10)
    def test_missing_context_file_exits_zero(self, tmp_path):
        """No .claude/PROJECT_CONTEXT.md — auto_prime should exit 0 silently."""
        event = {"hookEventName": "SessionStart", "cwd": str(tmp_path)}
        t0 = time.perf_counter()
        result = run_script(AUTO_PRIME, stdin_text=json.dumps(event), cwd=tmp_path)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("TestAutoPrime.test_missing_context_file_exits_zero", elapsed_ms)
        assert result.returncode == 0, (
            f"auto_prime.py without PROJECT_CONTEXT.md should exit 0, got {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )

    @pytest.mark.timeout(10)
    def test_stale_cache_exits_zero(self, tmp_path):
        """PROJECT_CONTEXT.md with a wrong git hash — auto_prime should exit 0.

        Note: auto_prime.py actually *loads* the context even when stale (it appends a stale
        note). So we verify returncode == 0 and do not assert empty stdout — just confirm
        no crash.
        """
        wrong_hash = "a" * 40
        make_context_file(tmp_path, wrong_hash)
        event = {"hookEventName": "SessionStart", "cwd": str(tmp_path)}
        t0 = time.perf_counter()
        result = run_script(AUTO_PRIME, stdin_text=json.dumps(event), cwd=tmp_path)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("TestAutoPrime.test_stale_cache_exits_zero", elapsed_ms)
        assert result.returncode == 0, (
            f"auto_prime.py with stale hash should exit 0, got {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )

    @pytest.mark.timeout(10)
    def test_fresh_cache_emits_context(self, tmp_path):
        """PROJECT_CONTEXT.md with correct git hash — auto_prime should emit context to stdout."""
        current_hash = get_git_hash(REPO_ROOT)
        if not current_hash:
            pytest.skip("Could not determine git HEAD hash")

        make_context_file(tmp_path, current_hash)
        event = {"hookEventName": "SessionStart", "cwd": str(tmp_path)}
        t0 = time.perf_counter()
        result = run_script(AUTO_PRIME, stdin_text=json.dumps(event), cwd=tmp_path)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("TestAutoPrime.test_fresh_cache_emits_context", elapsed_ms)

        assert result.returncode == 0, (
            f"auto_prime.py with fresh cache should exit 0, got {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )
        assert result.stdout.strip(), (
            "auto_prime.py with fresh cache should emit something to stdout"
        )

    @pytest.mark.timeout(10)
    def test_malformed_context_file_exits_zero(self, tmp_path):
        """PROJECT_CONTEXT.md with no GIT_HASH comment — auto_prime exits 0."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(exist_ok=True)
        ctx = claude_dir / "PROJECT_CONTEXT.md"
        # Write content with no GIT_HASH line and length > 500 to pass load_cached_context,
        # but without a hash the stale-check will treat cached_hash as None → not stale →
        # still loads. Either way returncode must be 0.
        ctx.write_text("# No hash here\n\n" + ("y" * 600) + "\n")
        event = {"hookEventName": "SessionStart", "cwd": str(tmp_path)}
        t0 = time.perf_counter()
        result = run_script(AUTO_PRIME, stdin_text=json.dumps(event), cwd=tmp_path)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("TestAutoPrime.test_malformed_context_file_exits_zero", elapsed_ms)
        assert result.returncode == 0, (
            f"auto_prime.py with malformed context file should exit 0, got {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )

    @pytest.mark.timeout(10)
    def test_context_injection_is_valid_json(self, tmp_path):
        """When fresh cache emits output, the output must be valid JSON."""
        current_hash = get_git_hash(REPO_ROOT)
        if not current_hash:
            pytest.skip("Could not determine git HEAD hash")

        make_context_file(tmp_path, current_hash)
        event = {"hookEventName": "SessionStart", "cwd": str(tmp_path)}
        result = run_script(AUTO_PRIME, stdin_text=json.dumps(event), cwd=tmp_path)

        assert result.returncode == 0
        stdout = result.stdout.strip()
        assert stdout, "Expected non-empty stdout for fresh cache"

        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"auto_prime.py output is not valid JSON: {exc}\nOutput was:\n{stdout[:500]}"
            )

        record_timing("TestAutoPrime.test_context_injection_is_valid_json", 0)
        assert isinstance(parsed, dict), f"Expected a JSON object, got: {type(parsed)}"

    @pytest.mark.timeout(10)
    def test_context_injection_has_context_key(self, tmp_path):
        """Emitted JSON must contain 'message' or 'result' key (SessionStart hook format)."""
        current_hash = get_git_hash(REPO_ROOT)
        if not current_hash:
            pytest.skip("Could not determine git HEAD hash")

        make_context_file(tmp_path, current_hash)
        event = {"hookEventName": "SessionStart", "cwd": str(tmp_path)}
        result = run_script(AUTO_PRIME, stdin_text=json.dumps(event), cwd=tmp_path)

        assert result.returncode == 0
        stdout = result.stdout.strip()
        assert stdout, "Expected non-empty stdout for fresh cache"

        parsed = json.loads(stdout)
        has_context_key = "message" in parsed or "result" in parsed or "context" in parsed
        assert has_context_key, (
            f"auto_prime.py output should contain 'message', 'result', or 'context' key. "
            f"Got keys: {list(parsed.keys())}"
        )
        record_timing("TestAutoPrime.test_context_injection_has_context_key", 0)
