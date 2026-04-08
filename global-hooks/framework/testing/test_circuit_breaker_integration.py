# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest", "pyyaml", "pydantic>=2.0.0"]
# ///
"""
Circuit Breaker Integration Tests
==================================

Tests for the circuit breaker system integrated with hooks:
  - Hook wrapped with circuit breaker
  - Failure tracking across hooks
  - Circuit opening after threshold
  - Cooldown and recovery
  - Integration with review system
  - Integration with knowledge pipeline

Run:
  uv run pytest test_circuit_breaker_integration.py -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure framework modules are importable
TESTING_DIR = Path(__file__).parent
FRAMEWORK_DIR = TESTING_DIR.parent
GUARDRAILS_DIR = FRAMEWORK_DIR / "guardrails"
sys.path.insert(0, str(GUARDRAILS_DIR))
sys.path.insert(0, str(TESTING_DIR))

from test_utils import TempDirFixture

from state_schema import CircuitState, HookState, HookStateData, GlobalStats, get_current_timestamp
from hook_state_manager import HookStateManager
from config_loader import GuardrailsConfig, CircuitBreakerConfig, LoggingConfig
from circuit_breaker import CircuitBreaker, CircuitBreakerDecision, CircuitBreakerResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_config(
    failure_threshold: int = 3,
    cooldown_seconds: int = 300,
    success_threshold: int = 2,
    exclude: list[str] | None = None,
    enabled: bool = True,
) -> GuardrailsConfig:
    """Create a GuardrailsConfig with test-appropriate settings."""
    return GuardrailsConfig(
        circuit_breaker=CircuitBreakerConfig(
            enabled=enabled,
            failure_threshold=failure_threshold,
            cooldown_seconds=cooldown_seconds,
            success_threshold=success_threshold,
            exclude=exclude or [],
        ),
        logging=LoggingConfig(
            file="/tmp/test_circuit_breaker.log",
            level="DEBUG",
        ),
        state_file="/tmp/test_hook_state.json",
    )


def make_state_manager(tmp_dir: Path) -> HookStateManager:
    """Create a HookStateManager with a temp state file."""
    state_file = tmp_dir / "hook_state.json"
    return HookStateManager(state_file)


# ===========================================================================
# State Schema Tests
# ===========================================================================


class TestStateSchema:
    """Tests for state_schema.py data structures."""

    def test_circuit_state_enum_values(self):
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"

    def test_hook_state_defaults(self):
        state = HookState()
        assert state.state == "closed"
        assert state.failure_count == 0
        assert state.consecutive_failures == 0
        assert state.consecutive_successes == 0
        assert state.first_failure is None
        assert state.last_error is None

    def test_hook_state_to_dict(self):
        state = HookState(state="open", failure_count=5)
        d = state.to_dict()
        assert d["state"] == "open"
        assert d["failure_count"] == 5

    def test_hook_state_from_dict(self):
        d = {"state": "half_open", "failure_count": 3, "consecutive_failures": 2}
        state = HookState.from_dict(d)
        assert state.state == "half_open"
        assert state.failure_count == 3

    def test_hook_state_from_dict_extra_keys(self):
        """Extra keys in dict should be ignored."""
        d = {"state": "closed", "unknown_field": "value"}
        state = HookState.from_dict(d)
        assert state.state == "closed"

    def test_global_stats_defaults(self):
        stats = GlobalStats()
        assert stats.total_executions == 0
        assert stats.total_failures == 0
        assert stats.hooks_disabled == 0

    def test_hook_state_data_round_trip(self):
        """Test serialization round-trip."""
        original = HookStateData(
            hooks={
                "cmd1": HookState(state="open", failure_count=5),
                "cmd2": HookState(state="closed"),
            },
            global_stats=GlobalStats(total_executions=100, total_failures=10),
        )
        d = original.to_dict()
        restored = HookStateData.from_dict(d)
        assert restored.hooks["cmd1"].state == "open"
        assert restored.hooks["cmd1"].failure_count == 5
        assert restored.hooks["cmd2"].state == "closed"
        assert restored.global_stats.total_executions == 100

    def test_get_current_timestamp_format(self):
        ts = get_current_timestamp()
        # Should be parseable ISO format
        dt = datetime.fromisoformat(ts)
        assert dt.tzinfo is not None


# ===========================================================================
# Hook State Manager Tests
# ===========================================================================


class TestHookStateManager:
    """Tests for hook_state_manager.py"""

    def test_initial_state_empty(self):
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            hooks = mgr.get_all_hooks()
            assert hooks == {}

    def test_get_hook_state_new_hook(self):
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            state = mgr.get_hook_state("uv run test.py")
            assert state.state == CircuitState.CLOSED.value
            assert state.failure_count == 0

    def test_record_success(self):
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            hook_state, changed = mgr.record_success("uv run test.py")
            assert hook_state.consecutive_successes == 1
            assert hook_state.consecutive_failures == 0
            assert changed is False

    def test_record_failure(self):
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            hook_state, changed = mgr.record_failure("uv run test.py", "error msg", failure_threshold=3)
            assert hook_state.consecutive_failures == 1
            assert hook_state.failure_count == 1
            assert hook_state.last_error == "error msg"
            assert changed is False  # Not at threshold yet

    def test_circuit_opens_at_threshold(self):
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            cmd = "uv run failing-hook.py"
            # Record 3 failures (threshold=3)
            for i in range(2):
                mgr.record_failure(cmd, f"error {i}", failure_threshold=3)
            hook_state, changed = mgr.record_failure(cmd, "error final", failure_threshold=3)
            assert changed is True
            assert hook_state.state == CircuitState.OPEN.value
            assert hook_state.consecutive_failures == 3
            assert hook_state.disabled_at is not None
            assert hook_state.retry_after is not None

    def test_success_resets_consecutive_failures(self):
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            cmd = "uv run test.py"
            mgr.record_failure(cmd, "err1", failure_threshold=5)
            mgr.record_failure(cmd, "err2", failure_threshold=5)
            mgr.record_success(cmd)
            state = mgr.get_hook_state(cmd)
            assert state.consecutive_failures == 0
            assert state.consecutive_successes == 1

    def test_transition_to_half_open(self):
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            cmd = "uv run test.py"
            # Open circuit
            for _ in range(3):
                mgr.record_failure(cmd, "err", failure_threshold=3)
            state = mgr.get_hook_state(cmd)
            assert state.state == CircuitState.OPEN.value
            # Transition to half-open
            result = mgr.transition_to_half_open(cmd)
            assert result is True
            state = mgr.get_hook_state(cmd)
            assert state.state == CircuitState.HALF_OPEN.value
            assert state.consecutive_successes == 0
            assert state.consecutive_failures == 0

    def test_transition_to_half_open_not_open(self):
        """Transition should fail if circuit is not OPEN."""
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            result = mgr.transition_to_half_open("uv run test.py")
            assert result is False

    def test_half_open_to_closed_after_successes(self):
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            cmd = "uv run test.py"
            # Open circuit
            for _ in range(3):
                mgr.record_failure(cmd, "err", failure_threshold=3)
            # Transition to half-open
            mgr.transition_to_half_open(cmd)
            # Record enough successes to close
            mgr.record_success(cmd)
            hook_state, changed = mgr.record_success(cmd)
            assert changed is True
            assert hook_state.state == CircuitState.CLOSED.value
            assert hook_state.failure_count == 0

    def test_half_open_failure_reopens_circuit(self):
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            cmd = "uv run test.py"
            # Open circuit
            for _ in range(3):
                mgr.record_failure(cmd, "err", failure_threshold=3)
            # Transition to half-open
            mgr.transition_to_half_open(cmd)
            # Failure in half-open reopens
            hook_state, _ = mgr.record_failure(cmd, "still failing", failure_threshold=3)
            assert hook_state.state == CircuitState.OPEN.value

    def test_reset_hook(self):
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            cmd = "uv run test.py"
            mgr.record_failure(cmd, "err", failure_threshold=3)
            result = mgr.reset_hook(cmd)
            assert result is True
            state = mgr.get_hook_state(cmd)
            assert state.state == CircuitState.CLOSED.value
            assert state.failure_count == 0

    def test_reset_nonexistent_hook(self):
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            result = mgr.reset_hook("nonexistent")
            assert result is False

    def test_reset_all(self):
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            mgr.record_failure("cmd1", "err", failure_threshold=3)
            mgr.record_failure("cmd2", "err", failure_threshold=3)
            count = mgr.reset_all()
            assert count == 2
            assert mgr.get_all_hooks() == {}

    def test_global_stats_tracking(self):
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            mgr.record_success("cmd1")
            mgr.record_failure("cmd2", "err", failure_threshold=3)
            stats = mgr.get_global_stats()
            assert stats.total_executions == 2
            assert stats.total_failures == 1

    def test_get_disabled_hooks(self):
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            # Open circuit for one hook
            for _ in range(3):
                mgr.record_failure("bad-hook", "err", failure_threshold=3)
            mgr.record_success("good-hook")
            disabled = mgr.get_disabled_hooks()
            assert len(disabled) == 1
            assert disabled[0][0] == "bad-hook"

    def test_health_report(self):
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            for _ in range(3):
                mgr.record_failure("bad-hook", "err", failure_threshold=3)
            mgr.record_success("good-hook")
            report = mgr.get_health_report()
            assert report["total_hooks"] == 2
            assert report["active_hooks"] == 1
            assert report["disabled_hooks"] == 1
            assert len(report["disabled_hook_details"]) == 1
            assert report["disabled_hook_details"][0]["command"] == "bad-hook"


# ===========================================================================
# Circuit Breaker Logic Tests
# ===========================================================================


class TestCircuitBreakerLogic:
    """Tests for circuit_breaker.py CircuitBreaker class."""

    def test_closed_circuit_allows_execution(self):
        with TempDirFixture() as tmp:
            config = make_config()
            config.expand_paths()
            mgr = make_state_manager(tmp.path)
            breaker = CircuitBreaker(mgr, config)
            result = breaker.should_execute("uv run hook.py")
            assert result.should_execute is True
            assert result.decision == CircuitBreakerDecision.EXECUTE
            assert result.state == CircuitState.CLOSED

    def test_open_circuit_skips_execution(self):
        with TempDirFixture() as tmp:
            config = make_config(failure_threshold=2, cooldown_seconds=3600)
            config.expand_paths()
            mgr = make_state_manager(tmp.path)
            breaker = CircuitBreaker(mgr, config)
            cmd = "uv run hook.py"
            # Trigger circuit opening
            for _ in range(2):
                mgr.record_failure(cmd, "err", failure_threshold=2)
            result = breaker.should_execute(cmd)
            assert result.should_execute is False
            assert result.decision == CircuitBreakerDecision.SKIP
            assert result.state == CircuitState.OPEN

    def test_excluded_hook_always_executes(self):
        with TempDirFixture() as tmp:
            config = make_config(exclude=["critical-hook"])
            config.expand_paths()
            mgr = make_state_manager(tmp.path)
            breaker = CircuitBreaker(mgr, config)
            cmd = "uv run critical-hook.py"
            # Even after failures, excluded hooks execute
            for _ in range(10):
                mgr.record_failure(cmd, "err", failure_threshold=3)
            result = breaker.should_execute(cmd)
            assert result.should_execute is True
            assert result.decision == CircuitBreakerDecision.EXECUTE

    def test_cooldown_elapsed_transitions_to_half_open(self):
        with TempDirFixture() as tmp:
            config = make_config(failure_threshold=2, cooldown_seconds=0)  # 0 for instant cooldown
            config.expand_paths()
            mgr = make_state_manager(tmp.path)
            breaker = CircuitBreaker(mgr, config)
            cmd = "uv run hook.py"
            # Open circuit
            for _ in range(2):
                mgr.record_failure(cmd, "err", failure_threshold=2)
            # With cooldown=0, should immediately transition
            result = breaker.should_execute(cmd)
            assert result.should_execute is True
            assert result.decision == CircuitBreakerDecision.EXECUTE_TEST
            assert result.state == CircuitState.HALF_OPEN

    def test_half_open_allows_test_execution(self):
        with TempDirFixture() as tmp:
            config = make_config(failure_threshold=2, cooldown_seconds=0)
            config.expand_paths()
            mgr = make_state_manager(tmp.path)
            breaker = CircuitBreaker(mgr, config)
            cmd = "uv run hook.py"
            # Open circuit, then transition to half-open
            for _ in range(2):
                mgr.record_failure(cmd, "err", failure_threshold=2)
            mgr.transition_to_half_open(cmd)
            result = breaker.should_execute(cmd)
            assert result.should_execute is True
            assert result.decision == CircuitBreakerDecision.EXECUTE_TEST
            assert result.is_testing is True

    def test_record_success_after_half_open(self):
        with TempDirFixture() as tmp:
            config = make_config(failure_threshold=2, cooldown_seconds=0)
            config.expand_paths()
            mgr = make_state_manager(tmp.path)
            breaker = CircuitBreaker(mgr, config)
            cmd = "uv run hook.py"
            # Open circuit
            for _ in range(2):
                mgr.record_failure(cmd, "err", failure_threshold=2)
            mgr.transition_to_half_open(cmd)
            # Record successes to close
            breaker.record_success(cmd)
            breaker.record_success(cmd)
            state = mgr.get_hook_state(cmd)
            assert state.state == CircuitState.CLOSED.value

    def test_record_failure_reopens_from_half_open(self):
        with TempDirFixture() as tmp:
            config = make_config(failure_threshold=2, cooldown_seconds=0)
            config.expand_paths()
            mgr = make_state_manager(tmp.path)
            breaker = CircuitBreaker(mgr, config)
            cmd = "uv run hook.py"
            # Open circuit
            for _ in range(2):
                mgr.record_failure(cmd, "err", failure_threshold=2)
            mgr.transition_to_half_open(cmd)
            # Failure reopens
            breaker.record_failure(cmd, "still broken")
            state = mgr.get_hook_state(cmd)
            assert state.state == CircuitState.OPEN.value


# ===========================================================================
# Multi-Hook Tracking Tests
# ===========================================================================


class TestMultiHookTracking:
    """Tests for tracking failures across multiple hooks independently."""

    def test_independent_failure_tracking(self):
        """Each hook tracks failures independently."""
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            mgr.record_failure("hook-A", "err", failure_threshold=3)
            mgr.record_failure("hook-A", "err", failure_threshold=3)
            mgr.record_failure("hook-B", "err", failure_threshold=3)

            state_a = mgr.get_hook_state("hook-A")
            state_b = mgr.get_hook_state("hook-B")
            assert state_a.consecutive_failures == 2
            assert state_b.consecutive_failures == 1

    def test_one_hook_open_others_closed(self):
        """Opening one circuit does not affect others."""
        with TempDirFixture() as tmp:
            config = make_config(failure_threshold=2)
            config.expand_paths()
            mgr = make_state_manager(tmp.path)
            breaker = CircuitBreaker(mgr, config)

            # Open hook-A
            for _ in range(2):
                mgr.record_failure("hook-A", "err", failure_threshold=2)

            result_a = breaker.should_execute("hook-A")
            result_b = breaker.should_execute("hook-B")

            assert result_a.should_execute is False  # Open
            assert result_b.should_execute is True   # Still closed

    def test_global_stats_across_hooks(self):
        """Global stats aggregate across all hooks."""
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            mgr.record_success("hook-A")
            mgr.record_success("hook-B")
            mgr.record_failure("hook-C", "err", failure_threshold=3)

            stats = mgr.get_global_stats()
            assert stats.total_executions == 3
            assert stats.total_failures == 1

    def test_disabled_hooks_count_accurate(self):
        """Disabled hooks count updates correctly."""
        with TempDirFixture() as tmp:
            mgr = make_state_manager(tmp.path)
            # Open two circuits
            for cmd in ["hook-A", "hook-B"]:
                for _ in range(3):
                    mgr.record_failure(cmd, "err", failure_threshold=3)

            stats = mgr.get_global_stats()
            assert stats.hooks_disabled == 2

            # Reset one
            mgr.reset_hook("hook-A")
            stats = mgr.get_global_stats()
            assert stats.hooks_disabled == 1


# ===========================================================================
# Circuit Breaker Wrapper Integration Tests
# ===========================================================================


class TestCircuitBreakerWrapper:
    """Tests for circuit_breaker_wrapper.py integration."""

    def test_parse_args_with_separator(self):
        from circuit_breaker_wrapper import parse_args
        with patch("sys.argv", ["wrapper.py", "--", "uv", "run", "hook.py"]):
            cmd = parse_args()
            assert cmd == ["uv", "run", "hook.py"]

    def test_parse_args_no_separator(self):
        from circuit_breaker_wrapper import parse_args
        with patch("sys.argv", ["wrapper.py", "uv", "run", "hook.py"]):
            cmd = parse_args()
            assert cmd is None

    def test_parse_args_empty(self):
        from circuit_breaker_wrapper import parse_args
        with patch("sys.argv", ["wrapper.py"]):
            cmd = parse_args()
            assert cmd is None

    def test_parse_args_separator_but_no_command(self):
        from circuit_breaker_wrapper import parse_args
        with patch("sys.argv", ["wrapper.py", "--"]):
            cmd = parse_args()
            assert cmd is None

    def test_execute_command_success(self):
        from circuit_breaker_wrapper import execute_command
        exit_code, stdout, stderr = execute_command(["echo", "hello"])
        assert exit_code == 0
        assert "hello" in stdout

    def test_execute_command_failure(self):
        from circuit_breaker_wrapper import execute_command
        exit_code, stdout, stderr = execute_command(["false"])
        assert exit_code != 0

    def test_execute_command_not_found(self):
        from circuit_breaker_wrapper import execute_command
        exit_code, stdout, stderr = execute_command(["nonexistent_command_xyz"])
        assert exit_code == 1
        assert "not found" in stderr.lower() or "Command not found" in stderr

    def test_output_claude_json(self):
        from circuit_breaker_wrapper import output_claude_json
        import io
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            output_claude_json("continue", "test message", success=True)
            output = json.loads(mock_out.getvalue())
            assert output["result"] == "continue"
            assert output["message"] == "test message"
            assert output["success"] is True


# ===========================================================================
# Recovery and Lifecycle Tests
# ===========================================================================


class TestCircuitBreakerLifecycle:
    """Tests for the complete circuit breaker lifecycle."""

    def test_full_lifecycle_closed_to_open_to_closed(self):
        """Test complete lifecycle: closed -> open -> half_open -> closed."""
        with TempDirFixture() as tmp:
            config = make_config(failure_threshold=3, cooldown_seconds=0, success_threshold=2)
            config.expand_paths()
            mgr = make_state_manager(tmp.path)
            breaker = CircuitBreaker(mgr, config)
            cmd = "uv run lifecycle-hook.py"

            # Phase 1: Normal operation (CLOSED)
            result = breaker.should_execute(cmd)
            assert result.state == CircuitState.CLOSED
            breaker.record_success(cmd)

            # Phase 2: Accumulate failures
            breaker.record_failure(cmd, "error 1")
            breaker.record_failure(cmd, "error 2")
            breaker.record_failure(cmd, "error 3")  # Opens circuit

            # Phase 3: Circuit is OPEN
            result = breaker.should_execute(cmd)
            # With cooldown=0, immediately transitions to HALF_OPEN
            assert result.state == CircuitState.HALF_OPEN
            assert result.decision == CircuitBreakerDecision.EXECUTE_TEST

            # Phase 4: Recovery test succeeds
            breaker.record_success(cmd)
            breaker.record_success(cmd)  # Enough to close

            # Phase 5: Circuit is CLOSED again
            result = breaker.should_execute(cmd)
            assert result.state == CircuitState.CLOSED
            assert result.decision == CircuitBreakerDecision.EXECUTE

    def test_repeated_open_close_cycles(self):
        """Circuit can open and close multiple times."""
        with TempDirFixture() as tmp:
            config = make_config(failure_threshold=2, cooldown_seconds=0, success_threshold=2)
            config.expand_paths()
            mgr = make_state_manager(tmp.path)
            breaker = CircuitBreaker(mgr, config)
            cmd = "uv run flaky-hook.py"

            for cycle in range(3):
                # Open circuit
                breaker.record_failure(cmd, f"cycle {cycle} err 1")
                breaker.record_failure(cmd, f"cycle {cycle} err 2")

                # Should be open (transitions to half-open with cooldown=0)
                result = breaker.should_execute(cmd)
                assert result.should_execute is True  # half-open test

                # Recover
                breaker.record_success(cmd)
                breaker.record_success(cmd)

                # Should be closed
                state = mgr.get_hook_state(cmd)
                assert state.state == CircuitState.CLOSED.value

    def test_intermittent_failures_dont_open_circuit(self):
        """Non-consecutive failures should not open the circuit."""
        with TempDirFixture() as tmp:
            config = make_config(failure_threshold=3)
            config.expand_paths()
            mgr = make_state_manager(tmp.path)
            breaker = CircuitBreaker(mgr, config)
            cmd = "uv run intermittent.py"

            # Failure, success, failure, success, failure
            breaker.record_failure(cmd, "err1")
            breaker.record_success(cmd)
            breaker.record_failure(cmd, "err2")
            breaker.record_success(cmd)
            breaker.record_failure(cmd, "err3")

            # Consecutive failures never reached 3
            state = mgr.get_hook_state(cmd)
            assert state.state == CircuitState.CLOSED.value
            assert state.consecutive_failures == 1  # Only the last one


# ===========================================================================
# Config Loader Tests
# ===========================================================================


class TestConfigLoader:
    """Tests for config_loader.py"""

    def test_default_config_values(self):
        config = GuardrailsConfig()
        assert config.circuit_breaker.enabled is True
        assert config.circuit_breaker.failure_threshold == 3
        assert config.circuit_breaker.cooldown_seconds == 300
        assert config.circuit_breaker.success_threshold == 2
        assert config.circuit_breaker.exclude == []
        assert config.logging.level == "INFO"

    def test_config_from_yaml(self):
        from config_loader import ConfigLoader
        with TempDirFixture() as tmp:
            import yaml
            config_file = tmp.path / "guardrails.yaml"
            config_file.write_text(yaml.dump({
                "circuit_breaker": {
                    "failure_threshold": 5,
                    "cooldown_seconds": 60,
                    "exclude": ["critical-hook"],
                },
                "logging": {"level": "DEBUG"},
            }))
            loader = ConfigLoader(config_file)
            config = loader.load()
            assert config.circuit_breaker.failure_threshold == 5
            assert config.circuit_breaker.cooldown_seconds == 60
            assert "critical-hook" in config.circuit_breaker.exclude
            assert config.logging.level == "DEBUG"

    def test_config_from_env(self):
        from config_loader import ConfigLoader
        with TempDirFixture() as tmp:
            config_file = tmp.path / "nonexistent.yaml"
            env_vars = {
                "GUARDRAILS_CIRCUIT_BREAKER_FAILURE_THRESHOLD": "7",
                "GUARDRAILS_LOGGING_LEVEL": "WARNING",
            }
            with patch.dict(os.environ, env_vars, clear=False):
                loader = ConfigLoader(config_file)
                config = loader.load()
                assert config.circuit_breaker.failure_threshold == 7
                assert config.logging.level == "WARNING"

    def test_invalid_log_level_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            LoggingConfig(level="INVALID")

    def test_failure_threshold_bounds(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CircuitBreakerConfig(failure_threshold=0)
        with pytest.raises(ValidationError):
            CircuitBreakerConfig(failure_threshold=101)

    def test_path_expansion(self):
        config = GuardrailsConfig(
            state_file="~/test_state.json",
            logging=LoggingConfig(file="~/test.log"),
        )
        config.expand_paths()
        assert "~" not in config.state_file
        assert "~" not in config.logging.file

    def test_deep_merge(self):
        from config_loader import ConfigLoader
        base = {"a": {"b": 1, "c": 2}, "d": 3}
        override = {"a": {"b": 10, "e": 5}, "f": 6}
        result = ConfigLoader._deep_merge(base, override)
        assert result["a"]["b"] == 10  # Overridden
        assert result["a"]["c"] == 2   # Preserved
        assert result["a"]["e"] == 5   # Added
        assert result["d"] == 3        # Preserved
        assert result["f"] == 6        # Added

    def test_env_value_parsing(self):
        from config_loader import ConfigLoader
        assert ConfigLoader._parse_env_value("true") is True
        assert ConfigLoader._parse_env_value("false") is False
        assert ConfigLoader._parse_env_value("42") == 42
        assert ConfigLoader._parse_env_value("-1") == -1
        assert ConfigLoader._parse_env_value("hello") == "hello"


# ===========================================================================
# Performance Tests
# ===========================================================================


class TestCircuitBreakerPerformance:
    """Tests for circuit breaker performance requirements."""

    def test_should_execute_under_10ms(self):
        """Circuit breaker decision should be fast."""
        with TempDirFixture() as tmp:
            config = make_config()
            config.expand_paths()
            mgr = make_state_manager(tmp.path)
            breaker = CircuitBreaker(mgr, config)

            start = time.monotonic()
            for _ in range(100):
                breaker.should_execute("uv run hook.py")
            elapsed = time.monotonic() - start

            avg_ms = (elapsed / 100) * 1000
            assert avg_ms < 10, f"Average decision time {avg_ms:.1f}ms exceeds 10ms"

    def test_record_success_under_10ms(self):
        """Recording success should be fast."""
        with TempDirFixture() as tmp:
            config = make_config()
            config.expand_paths()
            mgr = make_state_manager(tmp.path)
            breaker = CircuitBreaker(mgr, config)

            start = time.monotonic()
            for i in range(100):
                breaker.record_success(f"hook-{i}")
            elapsed = time.monotonic() - start

            avg_ms = (elapsed / 100) * 1000
            assert avg_ms < 10, f"Average record time {avg_ms:.1f}ms exceeds 10ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
