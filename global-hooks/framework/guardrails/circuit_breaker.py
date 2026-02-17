#!/usr/bin/env python3
"""
Circuit breaker logic for hook execution.

This module provides the core circuit breaker state machine logic for preventing
infinite loops caused by repeatedly failing hooks.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

try:
    from .state_schema import CircuitState, HookState
    from .hook_state_manager import HookStateManager
    from .config_loader import GuardrailsConfig
except ImportError:
    from state_schema import CircuitState, HookState
    from hook_state_manager import HookStateManager
    from config_loader import GuardrailsConfig


class CircuitBreakerDecision(str, Enum):
    """Decision from circuit breaker about whether to execute hook."""
    EXECUTE = "execute"           # Execute the hook normally
    SKIP = "skip"                 # Skip execution (circuit open, cooldown not elapsed)
    EXECUTE_TEST = "execute_test" # Execute for recovery test (half-open state)


@dataclass
class CircuitBreakerResult:
    """Result from circuit breaker logic."""
    decision: CircuitBreakerDecision
    state: CircuitState
    message: str
    should_execute: bool

    @property
    def is_testing(self) -> bool:
        """Check if this is a recovery test execution."""
        return self.decision == CircuitBreakerDecision.EXECUTE_TEST


class CircuitBreaker:
    """
    Circuit breaker for hook execution.

    Implements the circuit breaker pattern to prevent infinite loops:
    - CLOSED: Normal operation, hook executes
    - OPEN: Hook disabled after failures, returns success immediately
    - HALF_OPEN: Testing recovery after cooldown

    State transitions:
        CLOSED --[failures >= threshold]--> OPEN
        OPEN --[cooldown elapsed]--> HALF_OPEN
        HALF_OPEN --[success]--> CLOSED
        HALF_OPEN --[failure]--> OPEN
    """

    def __init__(
        self,
        state_manager: HookStateManager,
        config: GuardrailsConfig,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize circuit breaker.

        Args:
            state_manager: State manager for persistence
            config: Configuration object
            logger: Logger instance (creates default if None)
        """
        self.state_manager = state_manager
        self.config = config
        self.logger = logger or self._create_default_logger()

    def _create_default_logger(self) -> logging.Logger:
        """Create default logger with configuration from config."""
        logger = logging.getLogger("circuit_breaker")
        logger.setLevel(getattr(logging, self.config.logging.level))

        # Create log directory if it doesn't exist
        log_path = self.config.get_log_file_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # File handler
        handler = logging.FileHandler(log_path)
        handler.setLevel(getattr(logging, self.config.logging.level))

        # Format with hook_cmd context (will be added per-log via extra)
        formatter = logging.Formatter(self.config.logging.format)
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger

    def should_execute(self, hook_cmd: str) -> CircuitBreakerResult:
        """
        Determine if hook should execute based on circuit breaker state.

        Args:
            hook_cmd: The hook command string

        Returns:
            CircuitBreakerResult with decision and metadata
        """
        # Check if hook is excluded from circuit breaker
        if self._is_excluded(hook_cmd):
            self.logger.info(
                "Hook excluded from circuit breaker, executing normally",
                extra={"hook_cmd": hook_cmd}
            )
            return CircuitBreakerResult(
                decision=CircuitBreakerDecision.EXECUTE,
                state=CircuitState.CLOSED,
                message="Hook excluded from circuit breaker",
                should_execute=True
            )

        # Get current state
        state = self.state_manager.get_hook_state(hook_cmd)
        current_state = CircuitState(state.state)

        # CLOSED state: execute normally
        if current_state == CircuitState.CLOSED:
            self.logger.debug(
                "Circuit closed, executing normally",
                extra={"hook_cmd": hook_cmd}
            )
            return CircuitBreakerResult(
                decision=CircuitBreakerDecision.EXECUTE,
                state=current_state,
                message="Circuit closed, executing normally",
                should_execute=True
            )

        # OPEN state: check if cooldown elapsed
        if current_state == CircuitState.OPEN:
            if self._is_cooldown_elapsed(state):
                # Transition to half-open for recovery test
                self.state_manager.transition_to_half_open(hook_cmd)
                self.logger.info(
                    "Cooldown elapsed, transitioning to HALF_OPEN for recovery test",
                    extra={"hook_cmd": hook_cmd}
                )
                return CircuitBreakerResult(
                    decision=CircuitBreakerDecision.EXECUTE_TEST,
                    state=CircuitState.HALF_OPEN,
                    message="Testing recovery after cooldown",
                    should_execute=True
                )
            else:
                # Cooldown not elapsed, skip execution
                retry_after = self._format_retry_after(state)
                msg = f"Circuit open, hook disabled until {retry_after}"
                self.logger.debug(msg, extra={"hook_cmd": hook_cmd})
                return CircuitBreakerResult(
                    decision=CircuitBreakerDecision.SKIP,
                    state=current_state,
                    message=msg,
                    should_execute=False
                )

        # HALF_OPEN state: allow execution for testing
        if current_state == CircuitState.HALF_OPEN:
            self.logger.info(
                "Circuit half-open, testing recovery",
                extra={"hook_cmd": hook_cmd}
            )
            return CircuitBreakerResult(
                decision=CircuitBreakerDecision.EXECUTE_TEST,
                state=current_state,
                message="Testing recovery",
                should_execute=True
            )

        # Should never reach here
        self.logger.error(
            f"Unknown circuit state: {current_state}",
            extra={"hook_cmd": hook_cmd}
        )
        return CircuitBreakerResult(
            decision=CircuitBreakerDecision.EXECUTE,
            state=CircuitState.CLOSED,
            message="Unknown state, defaulting to execute",
            should_execute=True
        )

    def record_success(self, hook_cmd: str) -> None:
        """
        Record successful hook execution.

        Updates state and may close circuit if in HALF_OPEN state.

        Args:
            hook_cmd: The hook command string
        """
        hook_state, state_changed = self.state_manager.record_success(
            hook_cmd,
            success_threshold=self.config.circuit_breaker.success_threshold,
        )

        if state_changed:
            self.logger.info(
                f"Circuit closed after {hook_state.consecutive_successes} successes",
                extra={"hook_cmd": hook_cmd}
            )
        else:
            self.logger.debug(
                f"Success recorded (consecutive: {hook_state.consecutive_successes})",
                extra={"hook_cmd": hook_cmd}
            )

    def record_failure(self, hook_cmd: str, error: str) -> None:
        """
        Record failed hook execution.

        Updates state and may open circuit if threshold exceeded.

        Args:
            hook_cmd: The hook command string
            error: Error message from the failure
        """
        threshold = self.config.circuit_breaker.failure_threshold
        hook_state, state_changed = self.state_manager.record_failure(
            hook_cmd,
            error,
            failure_threshold=threshold,
            cooldown_seconds=self.config.circuit_breaker.cooldown_seconds,
        )

        if state_changed:
            self.logger.warning(
                f"Circuit opened after {hook_state.consecutive_failures} failures. "
                f"Hook disabled for {self.config.circuit_breaker.cooldown_seconds}s. "
                f"Last error: {error}",
                extra={"hook_cmd": hook_cmd}
            )
        else:
            self.logger.debug(
                f"Failure recorded (consecutive: {hook_state.consecutive_failures}/{threshold}). "
                f"Error: {error}",
                extra={"hook_cmd": hook_cmd}
            )

    def _is_excluded(self, hook_cmd: str) -> bool:
        """
        Check if hook is excluded from circuit breaker.

        Args:
            hook_cmd: The hook command string

        Returns:
            True if hook should be excluded
        """
        exclude_patterns = self.config.circuit_breaker.exclude
        for pattern in exclude_patterns:
            if pattern in hook_cmd:
                return True
        return False

    def _is_cooldown_elapsed(self, state: HookState) -> bool:
        """
        Check if cooldown period has elapsed.

        Args:
            state: Current hook state

        Returns:
            True if cooldown period has elapsed
        """
        if state.disabled_at is None:
            return False

        disabled_time = datetime.fromisoformat(state.disabled_at)
        cooldown_seconds = self.config.circuit_breaker.cooldown_seconds
        elapsed = datetime.now(timezone.utc) - disabled_time

        return elapsed.total_seconds() >= cooldown_seconds

    def _format_retry_after(self, state: HookState) -> str:
        """
        Format retry_after timestamp for display.

        Args:
            state: Current hook state

        Returns:
            Formatted timestamp string
        """
        if state.retry_after:
            retry_time = datetime.fromisoformat(state.retry_after)
            return retry_time.strftime("%Y-%m-%d %H:%M:%S UTC")
        return "unknown"
