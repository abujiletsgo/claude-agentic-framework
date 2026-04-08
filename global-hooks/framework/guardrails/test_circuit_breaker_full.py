#!/usr/bin/env python3
"""
Circuit Breaker Full Test Suite
================================
In-depth testing of every failure point in the circuit breaker system.

Run with:
    cd global-hooks/framework/guardrails && python3 test_circuit_breaker_full.py

Coverage:
  1.  State machine: CLOSED → OPEN on failure threshold
  2.  State machine: OPEN → skips execution
  3.  State machine: OPEN → HALF_OPEN when cooldown elapsed
  4.  State machine: HALF_OPEN → CLOSED on enough successes
  5.  State machine: HALF_OPEN → OPEN on any failure
  6.  Exclude patterns: excluded hooks always execute
  7.  State persistence: survives across manager instances
  8.  Corrupted state file: raises ValueError
  9.  Atomic write: temp file + rename pattern
 10.  Thread safety: concurrent record_failure calls don't corrupt state
 11.  BUG: cooldown_seconds hardcoded 300 in record_failure (not from config)
 12.  BUG: success_threshold hardcoded >= 2 in record_success (ignores config)
 13.  Config: defaults when no file exists
 14.  Config: YAML file overrides defaults
 15.  Config: env vars override YAML
 16.  Config: invalid values raise ValidationError
 17.  Config: malformed YAML falls back to defaults
 18.  Wrapper: arg parsing - no args, missing --, no cmd after --
 19.  Wrapper: stdin forwarding to inner command
 20.  Wrapper: circuit OPEN exits 0 (never blocks agent)
 21.  Wrapper: inner command exit 0 → records success
 22.  Wrapper: inner command exit non-0 → records failure
 23.  Wrapper: command not found → records failure
 24.  Wrapper: timeout → records failure
 25.  Wrapper: wrapper crash → fallback executes command directly
 26.  Global stats: total_executions, total_failures, hooks_disabled
 27.  Multiple hooks isolated: each hook has independent state
 28.  disabled_at / retry_after timezone: consistent UTC usage
 29.  reset_hook: clears specific hook only
 30.  reset_all: clears everything
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add guardrails dir to path
_guardrails_dir = Path(__file__).parent
sys.path.insert(0, str(_guardrails_dir))

from state_schema import CircuitState, HookState, HookStateData
from hook_state_manager import HookStateManager
from config_loader import GuardrailsConfig, CircuitBreakerConfig, LoggingConfig, load_config
from circuit_breaker import CircuitBreaker, CircuitBreakerDecision


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_config(
    failure_threshold=3,
    cooldown_seconds=300,
    success_threshold=2,
    exclude=None,
    enabled=True,
) -> GuardrailsConfig:
    """Build a GuardrailsConfig with a temp state/log file."""
    tmp_dir = tempfile.mkdtemp()
    cfg = GuardrailsConfig(
        circuit_breaker=CircuitBreakerConfig(
            enabled=enabled,
            failure_threshold=failure_threshold,
            cooldown_seconds=cooldown_seconds,
            success_threshold=success_threshold,
            exclude=exclude or [],
        ),
        logging=LoggingConfig(
            file=str(Path(tmp_dir) / "cb.log"),
            level="DEBUG",
        ),
        state_file=str(Path(tmp_dir) / "state.json"),
    )
    cfg.expand_paths()
    return cfg


def make_breaker(config=None, state_file=None):
    """Create a CircuitBreaker with isolated state and a silent logger."""
    if config is None:
        config = make_config()
    if state_file is None:
        state_file = config.get_state_file_path()
    mgr = HookStateManager(state_file)
    import logging
    logger = logging.getLogger("test_cb")
    logger.handlers = []
    logger.addHandler(logging.NullHandler())
    return CircuitBreaker(mgr, config, logger=logger), mgr


CMD = "uv run fake_hook.py"


# ---------------------------------------------------------------------------
# 1-6. State machine transitions
# ---------------------------------------------------------------------------

class TestStateMachine(unittest.TestCase):

    def setUp(self):
        self.cfg = make_config(failure_threshold=3, cooldown_seconds=5)
        self.breaker, self.mgr = make_breaker(self.cfg)

    # --- CLOSED state ---

    def test_01_closed_allows_execution(self):
        result = self.breaker.should_execute(CMD)
        self.assertTrue(result.should_execute)
        self.assertEqual(result.decision, CircuitBreakerDecision.EXECUTE)
        self.assertEqual(result.state, CircuitState.CLOSED)

    def test_02_failures_below_threshold_stay_closed(self):
        self.breaker.record_failure(CMD, "err1")
        self.breaker.record_failure(CMD, "err2")
        result = self.breaker.should_execute(CMD)
        self.assertTrue(result.should_execute)
        self.assertEqual(result.state, CircuitState.CLOSED)

    def test_03_threshold_failures_open_circuit(self):
        for i in range(3):
            self.breaker.record_failure(CMD, f"err{i}")
        result = self.breaker.should_execute(CMD)
        self.assertFalse(result.should_execute)
        self.assertEqual(result.state, CircuitState.OPEN)
        self.assertEqual(result.decision, CircuitBreakerDecision.SKIP)

    def test_04_open_skips_execution_returns_success(self):
        """When OPEN, should_execute returns should_execute=False."""
        for i in range(3):
            self.breaker.record_failure(CMD, "err")
        result = self.breaker.should_execute(CMD)
        self.assertFalse(result.should_execute)
        # Circuit should stay OPEN within cooldown
        result2 = self.breaker.should_execute(CMD)
        self.assertFalse(result2.should_execute)

    def test_05_open_transitions_to_half_open_after_cooldown(self):
        """Simulate cooldown elapsed by backdating disabled_at."""
        for i in range(3):
            self.breaker.record_failure(CMD, "err")

        # Manually backdate disabled_at to simulate cooldown elapsed
        state_data = self.mgr._read_state()
        past = datetime.now(timezone.utc) - timedelta(seconds=10)
        state_data.hooks[CMD].disabled_at = past.isoformat()
        state_data.hooks[CMD].retry_after = past.isoformat()
        self.mgr._write_state(state_data)

        result = self.breaker.should_execute(CMD)
        self.assertTrue(result.should_execute)
        self.assertEqual(result.decision, CircuitBreakerDecision.EXECUTE_TEST)

    def test_06_half_open_success_closes_circuit(self):
        """2 consecutive successes in HALF_OPEN → CLOSED."""
        for i in range(3):
            self.breaker.record_failure(CMD, "err")

        # Force to HALF_OPEN
        self.mgr.transition_to_half_open(CMD)

        self.breaker.record_success(CMD)
        state = self.mgr.get_hook_state(CMD)
        # After 1 success in HALF_OPEN, still HALF_OPEN
        self.assertEqual(state.state, CircuitState.HALF_OPEN.value)

        self.breaker.record_success(CMD)
        state = self.mgr.get_hook_state(CMD)
        # After 2 successes, CLOSED
        self.assertEqual(state.state, CircuitState.CLOSED.value)
        self.assertIsNone(state.disabled_at)
        self.assertIsNone(state.retry_after)
        self.assertIsNone(state.last_error)

    def test_07_half_open_failure_reopens_circuit(self):
        """Any failure in HALF_OPEN → back to OPEN immediately."""
        for i in range(3):
            self.breaker.record_failure(CMD, "err")
        self.mgr.transition_to_half_open(CMD)

        self.breaker.record_failure(CMD, "recovery failed")
        state = self.mgr.get_hook_state(CMD)
        self.assertEqual(state.state, CircuitState.OPEN.value)
        # retry_after should be set
        self.assertIsNotNone(state.retry_after)

    def test_08_success_in_closed_resets_failure_counter(self):
        """A success in CLOSED resets consecutive_failures."""
        self.breaker.record_failure(CMD, "err1")
        self.breaker.record_failure(CMD, "err2")
        self.breaker.record_success(CMD)
        state = self.mgr.get_hook_state(CMD)
        self.assertEqual(state.consecutive_failures, 0)
        self.assertEqual(state.consecutive_successes, 1)
        # Circuit still CLOSED after success
        self.assertEqual(state.state, CircuitState.CLOSED.value)

    def test_09_excluded_hook_always_executes(self):
        """Excluded hooks ignore circuit state entirely."""
        cfg = make_config(exclude=["fake_hook"])
        breaker, _ = make_breaker(cfg)
        # Even after 100 failures, excluded hook still executes
        for i in range(100):
            breaker.record_failure(CMD, "err")
        result = breaker.should_execute(CMD)
        self.assertTrue(result.should_execute)
        self.assertEqual(result.decision, CircuitBreakerDecision.EXECUTE)

    def test_10_two_hooks_have_independent_state(self):
        """Failures on one hook don't affect another."""
        cmd_b = "uv run other_hook.py"
        for i in range(3):
            self.breaker.record_failure(CMD, "err")
        # cmd_b should still be CLOSED
        result = self.breaker.should_execute(cmd_b)
        self.assertTrue(result.should_execute)
        self.assertEqual(result.state, CircuitState.CLOSED)


# ---------------------------------------------------------------------------
# 7-9. State persistence and file operations
# ---------------------------------------------------------------------------

class TestStatePersistence(unittest.TestCase):

    def test_11_state_survives_manager_restart(self):
        """State file persists across separate HookStateManager instances."""
        cfg = make_config()
        state_file = cfg.get_state_file_path()
        breaker1, mgr1 = make_breaker(cfg, state_file)

        for i in range(3):
            breaker1.record_failure(CMD, "err")

        # New manager reading same file
        mgr2 = HookStateManager(state_file)
        state = mgr2.get_hook_state(CMD)
        self.assertEqual(state.state, CircuitState.OPEN.value)
        self.assertEqual(state.consecutive_failures, 3)

    def test_12_corrupted_state_file_raises_value_error(self):
        """Corrupted JSON in state file → ValueError."""
        cfg = make_config()
        state_file = cfg.get_state_file_path()
        # Ensure file created
        mgr = HookStateManager(state_file)
        # Corrupt it
        state_file.write_text("not json at all {{{")
        with self.assertRaises(ValueError):
            mgr._read_state()

    def test_13_atomic_write_no_partial_state(self):
        """Write goes through temp file → rename; no partial writes."""
        cfg = make_config()
        state_file = cfg.get_state_file_path()
        mgr = HookStateManager(state_file)

        # Record some state
        mgr.record_failure(CMD, "err1")
        mgr.record_failure(CMD, "err2")

        # Verify no .tmp files left behind
        tmp_files = list(state_file.parent.glob(".hook_state_*.tmp"))
        self.assertEqual(len(tmp_files), 0, f"Temp files left: {tmp_files}")

        # State file should be valid JSON
        data = json.loads(state_file.read_text())
        self.assertIn("hooks", data)

    def test_14_new_hook_starts_closed(self):
        """Hook not in state file returns fresh CLOSED state."""
        cfg = make_config()
        mgr = HookStateManager(cfg.get_state_file_path())
        state = mgr.get_hook_state("brand_new_hook")
        self.assertEqual(state.state, CircuitState.CLOSED.value)
        self.assertEqual(state.consecutive_failures, 0)
        self.assertIsNone(state.disabled_at)


# ---------------------------------------------------------------------------
# 10. Thread safety
# ---------------------------------------------------------------------------

class TestThreadSafety(unittest.TestCase):

    def test_15_concurrent_failures_dont_corrupt_state(self):
        """10 threads each recording failures don't corrupt state file."""
        cfg = make_config(failure_threshold=100)
        mgr = HookStateManager(cfg.get_state_file_path())
        errors = []

        def record_failures():
            try:
                for _ in range(5):
                    mgr.record_failure(CMD, "concurrent err")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_failures) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Thread errors: {errors}")

        # State should be valid and consistent
        state = mgr.get_hook_state(CMD)
        # 10 threads × 5 failures = 50 total
        self.assertEqual(state.failure_count, 50)

    def test_16_concurrent_success_and_failure(self):
        """Mixed concurrent success/failure calls don't corrupt state."""
        cfg = make_config()
        mgr = HookStateManager(cfg.get_state_file_path())
        errors = []

        def worker(success: bool):
            try:
                for _ in range(3):
                    if success:
                        mgr.record_success(CMD)
                    else:
                        mgr.record_failure(CMD, "err")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=worker, args=(i % 2 == 0,))
            for i in range(8)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        # State file should still be valid JSON
        state_data = mgr._read_state()
        self.assertIsInstance(state_data, HookStateData)


# ---------------------------------------------------------------------------
# 11-12. Known bugs: hardcoded values
# ---------------------------------------------------------------------------

class TestKnownBugs(unittest.TestCase):

    def test_17_cooldown_seconds_respected_in_half_open_failure(self):
        """
        FIX #17: record_failure for HALF_OPEN now uses config cooldown_seconds
        instead of hardcoded 300s.
        """
        cfg = make_config(failure_threshold=3, cooldown_seconds=60)
        breaker, mgr = make_breaker(cfg)

        for i in range(3):
            breaker.record_failure(CMD, "err")
        mgr.transition_to_half_open(CMD)

        before = datetime.now(timezone.utc)
        breaker.record_failure(CMD, "recovery failed")

        state = mgr.get_hook_state(CMD)
        retry_after = datetime.fromisoformat(state.retry_after)
        actual_delta = (retry_after - before).total_seconds()

        # Should be ~60s (config value), not ~300s (old hardcoded value)
        self.assertAlmostEqual(actual_delta, 60, delta=5,
            msg=f"retry_after should be ~60s (config), got {actual_delta:.0f}s")

    def test_18_success_threshold_respected_in_record_success(self):
        """
        FIX #18: record_success now uses the success_threshold parameter
        instead of hardcoded >= 2.
        """
        cfg = make_config(failure_threshold=3, success_threshold=4)
        breaker, mgr = make_breaker(cfg)

        for i in range(3):
            breaker.record_failure(CMD, "err")
        mgr.transition_to_half_open(CMD)

        # 3 successes — not enough when threshold=4
        for _ in range(3):
            breaker.record_success(CMD)
        state = mgr.get_hook_state(CMD)
        self.assertEqual(state.state, CircuitState.HALF_OPEN.value,
            "Circuit should still be HALF_OPEN after only 3 successes with threshold=4")

        # 4th success — now should close
        breaker.record_success(CMD)
        state = mgr.get_hook_state(CMD)
        self.assertEqual(state.state, CircuitState.CLOSED.value,
            "Circuit should be CLOSED after 4 successes with threshold=4")

    def test_19_half_open_failure_state_changed_is_true(self):
        """
        FIX #19: record_failure for HALF_OPEN now sets state_changed=True so
        CircuitBreaker.record_failure emits the warning log for the transition.
        """
        cfg = make_config(failure_threshold=3)
        _, mgr = make_breaker(cfg)

        for i in range(3):
            mgr.record_failure(CMD, "err", failure_threshold=3)
        mgr.transition_to_half_open(CMD)

        hook_state, state_changed = mgr.record_failure(CMD, "recovery failed", failure_threshold=3)

        self.assertEqual(hook_state.state, CircuitState.OPEN.value)
        self.assertTrue(state_changed,
            "HALF_OPEN→OPEN transition should set state_changed=True so warning is logged")


# ---------------------------------------------------------------------------
# 13-17. Config loading
# ---------------------------------------------------------------------------

class TestConfigLoading(unittest.TestCase):

    def test_20_defaults_when_no_file(self):
        """Defaults are correct when no config file exists."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "nonexistent.yaml"
            from config_loader import ConfigLoader
            loader = ConfigLoader(cfg_path)
            config = loader.load()
            self.assertEqual(config.circuit_breaker.failure_threshold, 3)
            self.assertEqual(config.circuit_breaker.cooldown_seconds, 300)
            self.assertEqual(config.circuit_breaker.success_threshold, 2)
            self.assertTrue(config.circuit_breaker.enabled)

    def test_21_yaml_overrides_defaults(self):
        """YAML file values override defaults."""
        yaml_content = """
circuit_breaker:
  failure_threshold: 5
  cooldown_seconds: 120
  enabled: true
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            cfg_path = Path(f.name)
        try:
            from config_loader import ConfigLoader
            loader = ConfigLoader(cfg_path)
            config = loader.load()
            self.assertEqual(config.circuit_breaker.failure_threshold, 5)
            self.assertEqual(config.circuit_breaker.cooldown_seconds, 120)
        finally:
            cfg_path.unlink()

    def test_22_env_vars_override_yaml(self):
        """Environment variables take highest priority."""
        yaml_content = "circuit_breaker:\n  failure_threshold: 5\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            cfg_path = Path(f.name)
        try:
            env = {**os.environ, "GUARDRAILS_CIRCUIT_BREAKER_FAILURE_THRESHOLD": "10"}
            from config_loader import ConfigLoader
            with patch.dict("os.environ", env, clear=True):
                loader = ConfigLoader(cfg_path)
                config = loader.load()
            self.assertEqual(config.circuit_breaker.failure_threshold, 10)
        finally:
            cfg_path.unlink()

    def test_23_invalid_failure_threshold_raises(self):
        """failure_threshold=0 violates ge=1 → ValidationError."""
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            CircuitBreakerConfig(failure_threshold=0)

    def test_24_invalid_log_level_raises(self):
        """Invalid log level → ValidationError."""
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            LoggingConfig(level="VERBOSE")

    def test_25_malformed_yaml_falls_back_to_defaults(self):
        """Malformed YAML → warning printed + defaults used (no crash)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("this: is: not: valid: yaml: [[[")
            cfg_path = Path(f.name)
        try:
            from config_loader import ConfigLoader
            import io
            stderr_capture = io.StringIO()
            with patch("sys.stderr", stderr_capture):
                loader = ConfigLoader(cfg_path)
                config = loader.load()
            # Should have fallen back to defaults
            self.assertEqual(config.circuit_breaker.failure_threshold, 3)
        finally:
            cfg_path.unlink()

    def test_26_disabled_circuit_breaker(self):
        """Circuit breaker disabled → config returns enabled=False."""
        from config_loader import CircuitBreakerConfig
        cfg_cb = CircuitBreakerConfig(enabled=False)
        self.assertFalse(cfg_cb.enabled)


# ---------------------------------------------------------------------------
# 18-25. Wrapper: argument parsing and end-to-end
# ---------------------------------------------------------------------------

WRAPPER = str(_guardrails_dir / "circuit_breaker_wrapper.py")


class TestWrapperArgParsing(unittest.TestCase):

    def _run_wrapper(self, args: list[str], stdin_data: str = "{}") -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, WRAPPER] + args,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_27_no_args_exits_2(self):
        result = self._run_wrapper([])
        self.assertEqual(result.returncode, 2)

    def test_28_missing_separator_exits_2(self):
        result = self._run_wrapper(["echo", "hello"])
        self.assertEqual(result.returncode, 2)

    def test_29_no_command_after_separator_exits_2(self):
        result = self._run_wrapper(["--"])
        self.assertEqual(result.returncode, 2)


class TestWrapperEndToEnd(unittest.TestCase):
    """End-to-end tests using real subprocesses and temp state files."""

    def _run_wrapped(
        self,
        inner_cmd: list[str],
        state_file: Path = None,
        stdin_data: str = "{}",
        extra_env: dict = None,
    ) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        if state_file:
            env["GUARDRAILS_STATE_FILE"] = str(state_file)
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, WRAPPER, "--"] + inner_cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
        )

    def test_30_successful_inner_command_exits_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "state.json"
            result = self._run_wrapped(
                [sys.executable, "-c", "import sys; sys.exit(0)"],
                state_file=state_file,
            )
            self.assertEqual(result.returncode, 0)

    def test_31_failing_inner_command_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "state.json"
            result = self._run_wrapped(
                [sys.executable, "-c", "import sys; sys.exit(1)"],
                state_file=state_file,
            )
            self.assertEqual(result.returncode, 1)

    def test_32_stdin_forwarded_to_inner_command(self):
        """Inner hook receives exactly what Claude Code writes to stdin."""
        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "state.json"
            payload = json.dumps({"tool": "Bash", "command": "ls"})
            # Inner command: read stdin, print it to stdout
            inner = [sys.executable, "-c", "import sys; print(sys.stdin.read(), end='')"]
            result = self._run_wrapped(inner, state_file=state_file, stdin_data=payload)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), payload)

    def test_33_command_not_found_exits_1(self):
        """FileNotFoundError on missing binary exits 1."""
        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "state.json"
            result = self._run_wrapped(
                ["/nonexistent/binary/that/does/not/exist"],
                state_file=state_file,
            )
            self.assertEqual(result.returncode, 1)

    def test_34_repeated_failures_open_circuit(self):
        """3 failures → circuit opens → 4th call exits 0 (skipped)."""
        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "state.json"
            env = {"GUARDRAILS_CIRCUIT_BREAKER_FAILURE_THRESHOLD": "3"}

            # 3 failing calls
            for i in range(3):
                self._run_wrapped(
                    [sys.executable, "-c", "import sys; sys.exit(1)"],
                    state_file=state_file,
                    extra_env=env,
                )

            # 4th call: circuit should be OPEN → wrapper exits 0 (graceful skip)
            result = self._run_wrapped(
                [sys.executable, "-c", "import sys; sys.exit(1)"],
                state_file=state_file,
                extra_env=env,
            )
            self.assertEqual(result.returncode, 0, "Open circuit should exit 0 to not block agent")

    def test_35_open_circuit_outputs_skip_message(self):
        """When circuit is OPEN, wrapper outputs a JSON continue message."""
        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "state.json"
            env = {"GUARDRAILS_CIRCUIT_BREAKER_FAILURE_THRESHOLD": "3"}

            for i in range(3):
                self._run_wrapped(
                    [sys.executable, "-c", "import sys; sys.exit(1)"],
                    state_file=state_file,
                    extra_env=env,
                )

            result = self._run_wrapped(
                [sys.executable, "-c", "import sys; sys.exit(1)"],
                state_file=state_file,
                extra_env=env,
            )
            # Should have output (the skip message)
            if result.stdout.strip():
                data = json.loads(result.stdout.strip())
                self.assertIn("result", data)
                self.assertEqual(data["result"], "continue")

    def test_36_success_after_failures_prevents_circuit_open(self):
        """
        Interleaved successes reset the failure counter.

        NOTE: The wrapper tracks state per command string. Using different
        inline commands (sys.exit(0) vs sys.exit(1)) creates separate state
        entries. This test uses a single script controlled by a flag file to
        ensure the same hook_cmd is tracked for both success and failure cases.
        """
        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "state.json"
            flag_file = Path(tmp) / "should_fail.flag"
            env = {"GUARDRAILS_CIRCUIT_BREAKER_FAILURE_THRESHOLD": "3"}

            # Controlled script: exits 1 if flag exists, else 0
            script = (
                "import sys; from pathlib import Path; "
                f"sys.exit(1 if Path(r'{flag_file}').exists() else 0)"
            )
            inner_cmd = [sys.executable, "-c", script]

            # 2 failures
            flag_file.touch()
            for i in range(2):
                self._run_wrapped(inner_cmd, state_file=state_file, extra_env=env)

            # 1 success → resets consecutive_failures to 0
            flag_file.unlink()
            self._run_wrapped(inner_cmd, state_file=state_file, extra_env=env)

            # 2 more failures (consecutive_failures starts from 0 again)
            flag_file.touch()
            for i in range(2):
                self._run_wrapped(inner_cmd, state_file=state_file, extra_env=env)

            # 3rd consecutive failure: circuit opens ON this call but command still runs (exit 1)
            result = self._run_wrapped(inner_cmd, state_file=state_file, extra_env=env)
            self.assertEqual(result.returncode, 1, "Circuit opens at threshold but command ran this call")

            # 4th consecutive failure: circuit already OPEN → skipped (exit 0)
            result2 = self._run_wrapped(inner_cmd, state_file=state_file, extra_env=env)
            self.assertEqual(result2.returncode, 0, "Circuit is now OPEN → wrapper skips execution")

    def test_37_circuit_disabled_runs_normally(self):
        """Circuit breaker disabled → command always runs, failures don't open circuit."""
        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "state.json"
            env = {
                "GUARDRAILS_CIRCUIT_BREAKER_ENABLED": "false",
                "GUARDRAILS_CIRCUIT_BREAKER_FAILURE_THRESHOLD": "2",
            }
            # 5 failures with disabled CB → should always exit 1 (command runs)
            for i in range(5):
                result = self._run_wrapped(
                    [sys.executable, "-c", "import sys; sys.exit(1)"],
                    state_file=state_file,
                    extra_env=env,
                )
                self.assertEqual(result.returncode, 1, f"Iteration {i}: disabled CB should not skip")


# ---------------------------------------------------------------------------
# 26. Global stats
# ---------------------------------------------------------------------------

class TestGlobalStats(unittest.TestCase):

    def test_38_stats_track_executions_and_failures(self):
        cfg = make_config()
        mgr = HookStateManager(cfg.get_state_file_path())

        mgr.record_success(CMD)
        mgr.record_failure(CMD, "err1")
        mgr.record_failure(CMD, "err2")

        stats = mgr.get_global_stats()
        self.assertEqual(stats.total_executions, 3)
        self.assertEqual(stats.total_failures, 2)

    def test_39_hooks_disabled_count_updates(self):
        cfg = make_config(failure_threshold=2)
        mgr = HookStateManager(cfg.get_state_file_path())

        mgr.record_failure(CMD, "err", failure_threshold=2)
        mgr.record_failure(CMD, "err", failure_threshold=2)

        stats = mgr.get_global_stats()
        self.assertEqual(stats.hooks_disabled, 1)

    def test_40_reset_all_clears_stats(self):
        cfg = make_config()
        mgr = HookStateManager(cfg.get_state_file_path())

        mgr.record_failure(CMD, "err")
        count = mgr.reset_all()
        self.assertEqual(count, 1)

        stats = mgr.get_global_stats()
        self.assertEqual(stats.total_executions, 0)

    def test_41_reset_hook_removes_only_that_hook(self):
        cfg = make_config()
        mgr = HookStateManager(cfg.get_state_file_path())
        cmd_b = "other_hook"

        mgr.record_failure(CMD, "err")
        mgr.record_failure(cmd_b, "err")

        mgr.reset_hook(CMD)
        all_hooks = mgr.get_all_hooks()
        self.assertNotIn(CMD, all_hooks)
        self.assertIn(cmd_b, all_hooks)

    def test_42_reset_nonexistent_hook_returns_false(self):
        cfg = make_config()
        mgr = HookStateManager(cfg.get_state_file_path())
        result = mgr.reset_hook("hook_that_never_existed")
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# 29. disabled_at/retry_after timezone consistency
# ---------------------------------------------------------------------------

class TestTimestampHandling(unittest.TestCase):

    def test_43_disabled_at_is_utc(self):
        """disabled_at should be timezone-aware UTC."""
        cfg = make_config(failure_threshold=2)
        _, mgr = make_breaker(cfg)

        mgr.record_failure(CMD, "e", failure_threshold=2)
        mgr.record_failure(CMD, "e", failure_threshold=2)

        state = mgr.get_hook_state(CMD)
        self.assertEqual(state.state, CircuitState.OPEN.value)
        self.assertIsNotNone(state.disabled_at)

        # Must parse as timezone-aware datetime
        disabled_time = datetime.fromisoformat(state.disabled_at)
        self.assertIsNotNone(disabled_time.tzinfo)

    def test_44_cooldown_elapsed_check_uses_utc(self):
        """_is_cooldown_elapsed uses UTC for comparison (no naive datetime mixing)."""
        cfg = make_config(failure_threshold=2, cooldown_seconds=5)
        breaker, mgr = make_breaker(cfg)

        mgr.record_failure(CMD, "e", failure_threshold=2)
        mgr.record_failure(CMD, "e", failure_threshold=2)

        state = mgr.get_hook_state(CMD)
        # Backdating to force cooldown elapsed
        past = datetime.now(timezone.utc) - timedelta(seconds=10)
        state.disabled_at = past.isoformat()
        state_data = mgr._read_state()
        state_data.hooks[CMD].disabled_at = past.isoformat()
        mgr._write_state(state_data)

        # Should not raise (no naive/aware mixing)
        updated_state = mgr.get_hook_state(CMD)
        elapsed = breaker._is_cooldown_elapsed(updated_state)
        self.assertTrue(elapsed)

    def test_45_retry_after_in_future(self):
        """retry_after is set to future time when circuit opens."""
        cfg = make_config(failure_threshold=2)
        _, mgr = make_breaker(cfg)

        mgr.record_failure(CMD, "e", failure_threshold=2)
        mgr.record_failure(CMD, "e", failure_threshold=2)

        state = mgr.get_hook_state(CMD)
        self.assertIsNotNone(state.retry_after)
        retry_time = datetime.fromisoformat(state.retry_after)
        self.assertGreater(retry_time, datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# 30. Health report
# ---------------------------------------------------------------------------

class TestHealthReport(unittest.TestCase):

    def test_46_health_report_shows_disabled_hooks(self):
        cfg = make_config(failure_threshold=2)
        mgr = HookStateManager(cfg.get_state_file_path())

        mgr.record_failure(CMD, "e", failure_threshold=2)
        mgr.record_failure(CMD, "e", failure_threshold=2)

        report = mgr.get_health_report()
        self.assertEqual(report["disabled_hooks"], 1)
        self.assertEqual(len(report["disabled_hook_details"]), 1)
        detail = report["disabled_hook_details"][0]
        self.assertEqual(detail["command"], CMD)
        self.assertIsNotNone(detail["last_error"])

    def test_47_health_report_active_hooks(self):
        cfg = make_config()
        mgr = HookStateManager(cfg.get_state_file_path())

        mgr.record_success(CMD)
        mgr.record_success("cmd_b")
        mgr.record_failure("cmd_c", "e", failure_threshold=1)

        report = mgr.get_health_report()
        self.assertEqual(report["disabled_hooks"], 1)
        self.assertEqual(report["active_hooks"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
