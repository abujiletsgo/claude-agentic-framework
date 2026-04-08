"""
Unit tests for circuit breaker implementation.

Tests cover:
- Circuit breaker state machine logic
- State transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
- Failure counting and threshold detection
- Cooldown and recovery testing
- Exclusion list handling
- Configuration integration
- Error handling
"""

import shutil
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from circuit_breaker import CircuitBreaker, CircuitBreakerDecision, CircuitBreakerResult
from hook_state_manager import HookStateManager
from config_loader import GuardrailsConfig, CircuitBreakerConfig, LoggingConfig
from state_schema import CircuitState, HookState


@pytest.fixture
def temp_state_file():
    """Create a temporary state file."""
    temp_dir = Path(tempfile.mkdtemp())
    temp_path = temp_dir / "state.json"
    yield temp_path
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def temp_log_file():
    """Create a temporary log file."""
    temp_dir = Path(tempfile.mkdtemp())
    temp_path = temp_dir / "test.log"
    yield temp_path
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def config(temp_state_file, temp_log_file):
    """Create test configuration."""
    config = GuardrailsConfig(
        circuit_breaker=CircuitBreakerConfig(
            enabled=True,
            failure_threshold=3,
            cooldown_seconds=5,  # Short cooldown for testing
            success_threshold=2,
            exclude=[]
        ),
        logging=LoggingConfig(
            file=str(temp_log_file),
            level="DEBUG",
            format="%(asctime)s | %(levelname)s | %(hook_cmd)s | %(message)s"
        ),
        state_file=str(temp_state_file)
    )
    config.expand_paths()
    return config


@pytest.fixture
def state_manager(config):
    """Create state manager with test configuration."""
    return HookStateManager(config.get_state_file_path())


@pytest.fixture
def breaker(state_manager, config):
    """Create circuit breaker with test configuration."""
    return CircuitBreaker(state_manager, config)


class TestCircuitBreakerInitialization:
    """Tests for circuit breaker initialization."""

    def test_initialization(self, breaker):
        """Test circuit breaker initializes correctly."""
        assert breaker.state_manager is not None
        assert breaker.config is not None
        assert breaker.logger is not None

    def test_logger_creation(self, breaker, temp_log_file):
        """Test logger is created with correct configuration."""
        assert breaker.logger.name == "circuit_breaker"
        assert breaker.logger.level == 10  # DEBUG level


class TestShouldExecute:
    """Tests for should_execute decision logic."""

    def test_closed_circuit_executes(self, breaker):
        """Test that closed circuit allows execution."""
        result = breaker.should_execute("test_hook")

        assert result.should_execute is True
        assert result.decision == CircuitBreakerDecision.EXECUTE
        assert result.state == CircuitState.CLOSED

    def test_excluded_hook_always_executes(self, breaker):
        """Test that excluded hooks always execute."""
        breaker.config.circuit_breaker.exclude = ["damage-control"]

        result = breaker.should_execute("damage-control/safety-check.py")

        assert result.should_execute is True
        assert result.decision == CircuitBreakerDecision.EXECUTE

    def test_open_circuit_skips_before_cooldown(self, breaker):
        """Test that open circuit skips execution before cooldown."""
        hook_cmd = "test_hook"

        # Trigger failures to open circuit
        for _ in range(3):
            breaker.record_failure(hook_cmd, "test error")

        result = breaker.should_execute(hook_cmd)

        assert result.should_execute is False
        assert result.decision == CircuitBreakerDecision.SKIP
        assert result.state == CircuitState.OPEN

    def test_open_circuit_transitions_after_cooldown(self, breaker):
        """Test that open circuit transitions to half-open after cooldown."""
        hook_cmd = "test_hook"

        # Open circuit
        for _ in range(3):
            breaker.record_failure(hook_cmd, "test error")

        # Wait for cooldown
        time.sleep(6)  # cooldown_seconds is 5

        result = breaker.should_execute(hook_cmd)

        assert result.should_execute is True
        assert result.decision == CircuitBreakerDecision.EXECUTE_TEST
        assert result.state == CircuitState.HALF_OPEN

    def test_half_open_circuit_executes_test(self, breaker):
        """Test that half-open circuit allows test execution."""
        hook_cmd = "test_hook"

        # Open circuit
        for _ in range(3):
            breaker.record_failure(hook_cmd, "test error")

        # Wait for cooldown and trigger transition
        time.sleep(6)
        breaker.should_execute(hook_cmd)

        # Now in half-open state
        result = breaker.should_execute(hook_cmd)

        assert result.should_execute is True
        assert result.decision == CircuitBreakerDecision.EXECUTE_TEST
        assert result.state == CircuitState.HALF_OPEN


class TestRecordSuccess:
    """Tests for recording successful executions."""

    def test_record_success_increments_counter(self, breaker):
        """Test that recording success increments counter."""
        hook_cmd = "test_hook"

        breaker.record_success(hook_cmd)
        state = breaker.state_manager.get_hook_state(hook_cmd)

        assert state.consecutive_successes == 1
        assert state.consecutive_failures == 0

    def test_record_success_closes_circuit_from_half_open(self, breaker):
        """Test that successes close circuit from half-open."""
        hook_cmd = "test_hook"

        # Open circuit
        for _ in range(3):
            breaker.record_failure(hook_cmd, "test error")

        # Transition to half-open
        time.sleep(6)
        breaker.should_execute(hook_cmd)

        # Record successes to close circuit
        breaker.record_success(hook_cmd)
        breaker.record_success(hook_cmd)  # threshold is 2

        state = breaker.state_manager.get_hook_state(hook_cmd)
        assert state.state == CircuitState.CLOSED.value
        assert state.consecutive_successes >= 2

    def test_record_success_resets_failure_counter(self, breaker):
        """Test that success resets consecutive failure counter."""
        hook_cmd = "test_hook"

        # Record some failures
        breaker.record_failure(hook_cmd, "error 1")
        breaker.record_failure(hook_cmd, "error 2")

        # Record success
        breaker.record_success(hook_cmd)

        state = breaker.state_manager.get_hook_state(hook_cmd)
        assert state.consecutive_failures == 0
        assert state.consecutive_successes == 1


class TestRecordFailure:
    """Tests for recording failed executions."""

    def test_record_failure_increments_counter(self, breaker):
        """Test that recording failure increments counter."""
        hook_cmd = "test_hook"

        breaker.record_failure(hook_cmd, "test error")
        state = breaker.state_manager.get_hook_state(hook_cmd)

        assert state.consecutive_failures == 1
        assert state.failure_count == 1
        assert state.last_error == "test error"

    def test_record_failure_opens_circuit_at_threshold(self, breaker):
        """Test that circuit opens after threshold failures."""
        hook_cmd = "test_hook"

        # Record failures up to threshold (3)
        breaker.record_failure(hook_cmd, "error 1")
        breaker.record_failure(hook_cmd, "error 2")
        breaker.record_failure(hook_cmd, "error 3")

        state = breaker.state_manager.get_hook_state(hook_cmd)
        assert state.state == CircuitState.OPEN.value
        assert state.consecutive_failures == 3
        assert state.disabled_at is not None

    def test_record_failure_resets_success_counter(self, breaker):
        """Test that failure resets consecutive success counter."""
        hook_cmd = "test_hook"

        # Record some successes
        breaker.record_success(hook_cmd)
        breaker.record_success(hook_cmd)

        # Record failure
        breaker.record_failure(hook_cmd, "test error")

        state = breaker.state_manager.get_hook_state(hook_cmd)
        assert state.consecutive_successes == 0
        assert state.consecutive_failures == 1

    def test_record_failure_reopens_from_half_open(self, breaker):
        """Test that failure in half-open state reopens circuit."""
        hook_cmd = "test_hook"

        # Open circuit
        for _ in range(3):
            breaker.record_failure(hook_cmd, "test error")

        # Transition to half-open
        time.sleep(6)
        breaker.should_execute(hook_cmd)

        # Record failure (should reopen)
        breaker.record_failure(hook_cmd, "test error")

        state = breaker.state_manager.get_hook_state(hook_cmd)
        assert state.state == CircuitState.OPEN.value


class TestStateTransitions:
    """Tests for circuit breaker state transitions."""

    def test_closed_to_open_transition(self, breaker):
        """Test CLOSED -> OPEN transition."""
        hook_cmd = "test_hook"

        # Start in CLOSED
        result = breaker.should_execute(hook_cmd)
        assert result.state == CircuitState.CLOSED

        # Record failures to trigger OPEN
        for i in range(3):
            breaker.record_failure(hook_cmd, f"error {i}")

        state = breaker.state_manager.get_hook_state(hook_cmd)
        assert state.state == CircuitState.OPEN.value

    def test_open_to_half_open_transition(self, breaker):
        """Test OPEN -> HALF_OPEN transition."""
        hook_cmd = "test_hook"

        # Open circuit
        for _ in range(3):
            breaker.record_failure(hook_cmd, "test error")

        # Verify OPEN
        result = breaker.should_execute(hook_cmd)
        assert result.state == CircuitState.OPEN

        # Wait for cooldown
        time.sleep(6)

        # Should transition to HALF_OPEN
        result = breaker.should_execute(hook_cmd)
        assert result.state == CircuitState.HALF_OPEN

    def test_half_open_to_closed_transition(self, breaker):
        """Test HALF_OPEN -> CLOSED transition."""
        hook_cmd = "test_hook"

        # Open circuit
        for _ in range(3):
            breaker.record_failure(hook_cmd, "test error")

        # Transition to HALF_OPEN
        time.sleep(6)
        breaker.should_execute(hook_cmd)

        # Record successes to close
        breaker.record_success(hook_cmd)
        breaker.record_success(hook_cmd)

        state = breaker.state_manager.get_hook_state(hook_cmd)
        assert state.state == CircuitState.CLOSED.value

    def test_half_open_to_open_transition(self, breaker):
        """Test HALF_OPEN -> OPEN transition on failure."""
        hook_cmd = "test_hook"

        # Open circuit
        for _ in range(3):
            breaker.record_failure(hook_cmd, "test error")

        # Transition to HALF_OPEN
        time.sleep(6)
        breaker.should_execute(hook_cmd)

        # Record failure (should reopen)
        breaker.record_failure(hook_cmd, "test error")

        state = breaker.state_manager.get_hook_state(hook_cmd)
        assert state.state == CircuitState.OPEN.value

    def test_complete_recovery_cycle(self, breaker):
        """Test complete recovery cycle: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
        hook_cmd = "test_hook"

        # Start in CLOSED
        result = breaker.should_execute(hook_cmd)
        assert result.state == CircuitState.CLOSED

        # Fail to OPEN
        for _ in range(3):
            breaker.record_failure(hook_cmd, "test error")
        assert breaker.state_manager.get_hook_state(hook_cmd).state == CircuitState.OPEN.value

        # Wait for cooldown -> HALF_OPEN
        time.sleep(6)
        result = breaker.should_execute(hook_cmd)
        assert result.state == CircuitState.HALF_OPEN

        # Succeed to CLOSED
        breaker.record_success(hook_cmd)
        breaker.record_success(hook_cmd)
        assert breaker.state_manager.get_hook_state(hook_cmd).state == CircuitState.CLOSED.value


class TestExclusionLogic:
    """Tests for hook exclusion logic."""

    def test_excluded_hook_never_opens_circuit(self, breaker):
        """Test that excluded hooks never open circuit."""
        breaker.config.circuit_breaker.exclude = ["critical-hook"]
        hook_cmd = "critical-hook/validator.py"

        # Record many failures
        for _ in range(10):
            breaker.record_failure(hook_cmd, "test error")

        # Should still execute
        result = breaker.should_execute(hook_cmd)
        assert result.should_execute is True

    def test_exclusion_pattern_matching(self, breaker):
        """Test that exclusion patterns match correctly."""
        breaker.config.circuit_breaker.exclude = ["damage-control", "safety"]

        # Should match
        assert breaker._is_excluded("damage-control/check.py")
        assert breaker._is_excluded("hooks/safety/validator.py")

        # Should not match
        assert not breaker._is_excluded("hooks/validator.py")
        assert not breaker._is_excluded("test.py")

    def test_multiple_exclusion_patterns(self, breaker):
        """Test multiple exclusion patterns."""
        breaker.config.circuit_breaker.exclude = ["pattern1", "pattern2", "pattern3"]

        assert breaker._is_excluded("path/pattern1/file.py")
        assert breaker._is_excluded("path/pattern2/file.py")
        assert breaker._is_excluded("path/pattern3/file.py")
        assert not breaker._is_excluded("path/pattern4/file.py")


class TestCooldownLogic:
    """Tests for cooldown period logic."""

    def test_cooldown_not_elapsed_before_period(self, breaker):
        """Test that cooldown is not elapsed before period."""
        hook_cmd = "test_hook"

        # Open circuit
        for _ in range(3):
            breaker.record_failure(hook_cmd, "test error")

        # Immediately check (cooldown not elapsed)
        state = breaker.state_manager.get_hook_state(hook_cmd)
        assert not breaker._is_cooldown_elapsed(state)

    def test_cooldown_elapsed_after_period(self, breaker):
        """Test that cooldown is elapsed after period."""
        hook_cmd = "test_hook"

        # Open circuit
        for _ in range(3):
            breaker.record_failure(hook_cmd, "test error")

        # Wait for cooldown
        time.sleep(6)

        state = breaker.state_manager.get_hook_state(hook_cmd)
        assert breaker._is_cooldown_elapsed(state)

    def test_cooldown_calculation_with_different_periods(self, breaker):
        """Test cooldown with different configured periods."""
        hook_cmd = "test_hook"

        # Open circuit
        for _ in range(3):
            breaker.record_failure(hook_cmd, "test error")

        # Change cooldown to 10 seconds
        breaker.config.circuit_breaker.cooldown_seconds = 10

        # After 6 seconds, should not be elapsed
        time.sleep(6)
        state = breaker.state_manager.get_hook_state(hook_cmd)
        assert not breaker._is_cooldown_elapsed(state)


class TestConfigurationIntegration:
    """Tests for configuration integration."""

    def test_failure_threshold_from_config(self, breaker):
        """Test that failure threshold comes from config."""
        hook_cmd = "test_hook"

        # Config has threshold of 3
        assert breaker.config.circuit_breaker.failure_threshold == 3

        # Should open after 3 failures
        breaker.record_failure(hook_cmd, "error 1")
        breaker.record_failure(hook_cmd, "error 2")
        breaker.record_failure(hook_cmd, "error 3")

        state = breaker.state_manager.get_hook_state(hook_cmd)
        assert state.state == CircuitState.OPEN.value

    def test_success_threshold_from_config(self, breaker):
        """Test that success threshold comes from config."""
        hook_cmd = "test_hook"

        # Open and transition to half-open
        for _ in range(3):
            breaker.record_failure(hook_cmd, "test error")
        time.sleep(6)
        breaker.should_execute(hook_cmd)

        # Config has success threshold of 2
        assert breaker.config.circuit_breaker.success_threshold == 2

        # One success should not close circuit
        breaker.record_success(hook_cmd)
        state = breaker.state_manager.get_hook_state(hook_cmd)
        assert state.state == CircuitState.HALF_OPEN.value

        # Second success should close circuit
        breaker.record_success(hook_cmd)
        state = breaker.state_manager.get_hook_state(hook_cmd)
        assert state.state == CircuitState.CLOSED.value

    def test_cooldown_from_config(self, breaker):
        """Test that cooldown period comes from config."""
        assert breaker.config.circuit_breaker.cooldown_seconds == 5

    def test_disabled_circuit_breaker(self, breaker):
        """Test behavior when circuit breaker is disabled."""
        breaker.config.circuit_breaker.enabled = False
        hook_cmd = "test_hook"

        # Note: This would need to be tested at wrapper level
        # Circuit breaker itself doesn't check enabled flag
        # The wrapper checks and skips breaker if disabled


class TestErrorHandling:
    """Tests for error handling."""

    def test_handles_missing_state_gracefully(self, breaker):
        """Test that missing state is handled gracefully."""
        hook_cmd = "new_hook"

        # Should create new state and execute
        result = breaker.should_execute(hook_cmd)
        assert result.should_execute is True
        assert result.state == CircuitState.CLOSED

    def test_handles_invalid_timestamp(self, breaker):
        """Test handling of invalid timestamps."""
        hook_cmd = "test_hook"

        # Open circuit
        for _ in range(3):
            breaker.record_failure(hook_cmd, "test error")

        # Get state and corrupt timestamp
        state = breaker.state_manager.get_hook_state(hook_cmd)
        state.disabled_at = None

        # Should handle gracefully
        result = breaker._is_cooldown_elapsed(state)
        assert result is False


class TestLogging:
    """Tests for logging functionality."""

    def test_logs_circuit_opening(self, breaker, temp_log_file):
        """Test that circuit opening is logged."""
        hook_cmd = "test_hook"

        # Trigger circuit opening
        for _ in range(3):
            breaker.record_failure(hook_cmd, "test error")

        # Check log file
        log_content = temp_log_file.read_text()
        assert "Circuit opened" in log_content

    def test_logs_circuit_closing(self, breaker, temp_log_file):
        """Test that circuit closing is logged."""
        hook_cmd = "test_hook"

        # Open and close circuit
        for _ in range(3):
            breaker.record_failure(hook_cmd, "test error")
        time.sleep(6)
        breaker.should_execute(hook_cmd)
        breaker.record_success(hook_cmd)
        breaker.record_success(hook_cmd)

        # Check log file
        log_content = temp_log_file.read_text()
        assert "Circuit closed" in log_content

    def test_logs_half_open_transition(self, breaker, temp_log_file):
        """Test that half-open transition is logged."""
        hook_cmd = "test_hook"

        # Open circuit and transition
        for _ in range(3):
            breaker.record_failure(hook_cmd, "test error")
        time.sleep(6)
        breaker.should_execute(hook_cmd)

        # Check log file
        log_content = temp_log_file.read_text()
        assert "HALF_OPEN" in log_content


class TestMultipleHooks:
    """Tests for managing multiple hooks independently."""

    def test_hooks_have_independent_state(self, breaker):
        """Test that different hooks have independent circuit breakers."""
        hook1 = "hook_1"
        hook2 = "hook_2"

        # Fail hook1
        for _ in range(3):
            breaker.record_failure(hook1, "error")

        # hook1 should be open
        result1 = breaker.should_execute(hook1)
        assert result1.state == CircuitState.OPEN

        # hook2 should still be closed
        result2 = breaker.should_execute(hook2)
        assert result2.state == CircuitState.CLOSED

    def test_multiple_hooks_can_open_independently(self, breaker):
        """Test that multiple hooks can open independently."""
        hooks = ["hook_1", "hook_2", "hook_3"]

        # Open all hooks
        for hook in hooks:
            for _ in range(3):
                breaker.record_failure(hook, "error")

        # All should be open
        for hook in hooks:
            result = breaker.should_execute(hook)
            assert result.state == CircuitState.OPEN

    def test_one_hook_recovery_doesnt_affect_others(self, breaker):
        """Test that one hook's recovery doesn't affect others."""
        hook1 = "hook_1"
        hook2 = "hook_2"

        # Open both
        for hook in [hook1, hook2]:
            for _ in range(3):
                breaker.record_failure(hook, "error")

        # Recover hook1
        time.sleep(6)
        breaker.should_execute(hook1)
        breaker.record_success(hook1)
        breaker.record_success(hook1)

        # hook1 should be closed
        state1 = breaker.state_manager.get_hook_state(hook1)
        assert state1.state == CircuitState.CLOSED.value

        # hook2 should still be open
        state2 = breaker.state_manager.get_hook_state(hook2)
        assert state2.state == CircuitState.OPEN.value
