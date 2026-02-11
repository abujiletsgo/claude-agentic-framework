"""
Hook state manager with thread-safe persistence.

This module provides CRUD operations for hook failure tracking state,
with atomic file operations and thread-safe access via file locking.
"""

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from contextlib import contextmanager

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    # Windows doesn't have fcntl
    HAS_FCNTL = False
    try:
        import portalocker
        HAS_PORTALOCKER = True
    except ImportError:
        HAS_PORTALOCKER = False

from state_schema import (
    HookState,
    HookStateData,
    GlobalStats,
    CircuitState,
    get_current_timestamp,
)


class HookStateManager:
    """
    Thread-safe manager for hook failure tracking state.

    Provides atomic read/write operations with file locking to ensure
    consistency across concurrent access.
    """

    def __init__(self, state_file: Optional[Path] = None):
        """
        Initialize state manager.

        Args:
            state_file: Path to state file. Defaults to ~/.claude/hook_state.json
        """
        if state_file is None:
            state_file = Path.home() / ".claude" / "hook_state.json"
        else:
            state_file = Path(state_file)

        self.state_file = state_file
        self._method_lock = threading.RLock()  # Reentrant lock for method-level synchronization
        self._ensure_state_file_exists()

    def _ensure_state_file_exists(self) -> None:
        """Ensure state file and parent directory exist."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            # Create empty state file
            empty_state = HookStateData()
            self._write_state(empty_state)

    @contextmanager
    def _lock_file(self, file_handle, exclusive: bool = False):
        """
        Context manager for file locking.

        Args:
            file_handle: Open file handle to lock
            exclusive: If True, acquire exclusive (write) lock. Otherwise shared (read) lock.

        Yields:
            The file handle (for convenience)
        """
        if HAS_FCNTL:
            # Unix-like systems
            lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            fcntl.flock(file_handle.fileno(), lock_type)
            try:
                yield file_handle
            finally:
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
        elif HAS_PORTALOCKER:
            # Windows with portalocker
            lock_flags = portalocker.LOCK_EX if exclusive else portalocker.LOCK_SH
            portalocker.lock(file_handle, lock_flags)
            try:
                yield file_handle
            finally:
                portalocker.unlock(file_handle)
        else:
            # No locking available (fallback)
            yield file_handle

    def _read_state(self) -> HookStateData:
        """
        Read state from file with shared lock.

        Returns:
            Current state data

        Raises:
            ValueError: If state file is corrupted
        """
        with open(self.state_file, 'r') as f:
            with self._lock_file(f, exclusive=False):
                try:
                    data = json.load(f)
                    return HookStateData.from_dict(data)
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    raise ValueError(f"Corrupted state file: {e}") from e

    def _write_state(self, state: HookStateData) -> None:
        """
        Write state to file atomically with exclusive lock.

        Uses atomic write pattern: write to temp file, then rename.
        This ensures the state file is never left in a partially written state.

        Args:
            state: State data to write
        """
        # Create temp file in same directory for atomic rename
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.state_file.parent,
            prefix=".hook_state_",
            suffix=".tmp"
        )

        try:
            with os.fdopen(temp_fd, 'w') as f:
                with self._lock_file(f, exclusive=True):
                    json.dump(state.to_dict(), f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())

            # Atomic rename
            os.replace(temp_path, self.state_file)
        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def get_hook_state(self, hook_cmd: str) -> HookState:
        """
        Get state for a specific hook command.

        Args:
            hook_cmd: The hook command string

        Returns:
            Hook state (creates new state if doesn't exist)
        """
        state = self._read_state()
        if hook_cmd not in state.hooks:
            return HookState()
        return state.hooks[hook_cmd]

    def record_success(self, hook_cmd: str) -> Tuple[HookState, bool]:
        """
        Record a successful hook execution.

        Updates consecutive success/failure counters and may transition
        circuit breaker state from HALF_OPEN to CLOSED.

        Args:
            hook_cmd: The hook command string

        Returns:
            Tuple of (updated hook state, state_changed flag)
            state_changed is True if circuit breaker transitioned to CLOSED
        """
        with self._method_lock:
            state = self._read_state()

            if hook_cmd not in state.hooks:
                state.hooks[hook_cmd] = HookState()

            hook_state = state.hooks[hook_cmd]
            hook_state.consecutive_successes += 1
            hook_state.consecutive_failures = 0
            hook_state.last_success = get_current_timestamp()

            state_changed = False
            if hook_state.state == CircuitState.HALF_OPEN.value:
                # Check if we should close the circuit
                # This would be configurable, but default to 2 successes
                if hook_state.consecutive_successes >= 2:
                    hook_state.state = CircuitState.CLOSED.value
                    hook_state.failure_count = 0
                    hook_state.first_failure = None
                    hook_state.disabled_at = None
                    hook_state.retry_after = None
                    hook_state.last_error = None
                    state_changed = True

            # Update global stats
            state.global_stats.total_executions += 1
            state.global_stats.last_updated = get_current_timestamp()
            state.global_stats.hooks_disabled = sum(
                1 for h in state.hooks.values() if h.state == CircuitState.OPEN.value
            )

            self._write_state(state)
            return hook_state, state_changed

    def record_failure(
        self,
        hook_cmd: str,
        error: str,
        failure_threshold: int = 3
    ) -> Tuple[HookState, bool]:
        """
        Record a failed hook execution.

        Updates failure counters and may open circuit breaker if threshold exceeded.

        Args:
            hook_cmd: The hook command string
            error: Error message from the failure
            failure_threshold: Number of consecutive failures before opening circuit

        Returns:
            Tuple of (updated hook state, state_changed flag)
            state_changed is True if circuit breaker transitioned to OPEN
        """
        with self._method_lock:
            state = self._read_state()

            if hook_cmd not in state.hooks:
                state.hooks[hook_cmd] = HookState()

            hook_state = state.hooks[hook_cmd]
            hook_state.consecutive_failures += 1
            hook_state.consecutive_successes = 0
            hook_state.failure_count += 1
            hook_state.last_failure = get_current_timestamp()
            hook_state.last_error = error

            if hook_state.first_failure is None:
                hook_state.first_failure = hook_state.last_failure

            state_changed = False
            # Special case: any failure in HALF_OPEN immediately reopens circuit
            # Note: state_changed = False because circuit was already open before HALF_OPEN
            if hook_state.state == CircuitState.HALF_OPEN.value:
                hook_state.state = CircuitState.OPEN.value
                hook_state.disabled_at = get_current_timestamp()
                # Calculate retry_after (5 minutes from now by default)
                from datetime import datetime, timedelta, timezone
                retry_time = datetime.now(timezone.utc) + timedelta(seconds=300)
                hook_state.retry_after = retry_time.isoformat()
                state_changed = False  # Circuit was already open, just tested recovery and failed
            elif hook_state.consecutive_failures >= failure_threshold:
                if hook_state.state != CircuitState.OPEN.value:
                    hook_state.state = CircuitState.OPEN.value
                    hook_state.disabled_at = get_current_timestamp()
                    # Calculate retry_after (5 minutes from now by default)
                    from datetime import datetime, timedelta, timezone
                    retry_time = datetime.now(timezone.utc) + timedelta(seconds=300)
                    hook_state.retry_after = retry_time.isoformat()
                    state_changed = True

            # Update global stats
            state.global_stats.total_executions += 1
            state.global_stats.total_failures += 1
            state.global_stats.last_updated = get_current_timestamp()
            state.global_stats.hooks_disabled = sum(
                1 for h in state.hooks.values() if h.state == CircuitState.OPEN.value
            )

            self._write_state(state)
            return hook_state, state_changed

    def transition_to_half_open(self, hook_cmd: str) -> bool:
        """
        Transition circuit from OPEN to HALF_OPEN for testing recovery.

        Args:
            hook_cmd: The hook command string

        Returns:
            True if transition occurred, False if already not in OPEN state
        """
        state = self._read_state()

        if hook_cmd not in state.hooks:
            return False

        hook_state = state.hooks[hook_cmd]
        if hook_state.state != CircuitState.OPEN.value:
            return False

        hook_state.state = CircuitState.HALF_OPEN.value
        hook_state.consecutive_successes = 0
        hook_state.consecutive_failures = 0

        state.global_stats.last_updated = get_current_timestamp()
        state.global_stats.hooks_disabled = sum(
            1 for h in state.hooks.values() if h.state == CircuitState.OPEN.value
        )

        self._write_state(state)
        return True

    def reset_hook(self, hook_cmd: str) -> bool:
        """
        Reset all state for a specific hook.

        Args:
            hook_cmd: The hook command string

        Returns:
            True if hook existed and was reset, False if didn't exist
        """
        state = self._read_state()

        if hook_cmd not in state.hooks:
            return False

        del state.hooks[hook_cmd]

        state.global_stats.last_updated = get_current_timestamp()
        state.global_stats.hooks_disabled = sum(
            1 for h in state.hooks.values() if h.state == CircuitState.OPEN.value
        )

        self._write_state(state)
        return True

    def reset_all(self) -> int:
        """
        Reset all hook states.

        Returns:
            Number of hooks that were reset
        """
        state = self._read_state()
        hook_count = len(state.hooks)

        # Create fresh state
        state.hooks = {}
        state.global_stats = GlobalStats()

        self._write_state(state)
        return hook_count

    def get_all_hooks(self) -> Dict[str, HookState]:
        """
        Get state for all hooks.

        Returns:
            Dictionary mapping hook commands to their states
        """
        state = self._read_state()
        return state.hooks.copy()

    def get_global_stats(self) -> GlobalStats:
        """
        Get global statistics.

        Returns:
            Global statistics object
        """
        state = self._read_state()
        return state.global_stats

    def get_disabled_hooks(self) -> List[Tuple[str, HookState]]:
        """
        Get all hooks currently in OPEN state.

        Returns:
            List of (hook_cmd, hook_state) tuples for disabled hooks
        """
        state = self._read_state()
        return [
            (cmd, hook_state)
            for cmd, hook_state in state.hooks.items()
            if hook_state.state == CircuitState.OPEN.value
        ]

    def get_health_report(self) -> Dict:
        """
        Generate comprehensive health report.

        Returns:
            Dictionary with health status information
        """
        state = self._read_state()
        total_hooks = len(state.hooks)
        disabled_hooks = [
            (cmd, hook_state)
            for cmd, hook_state in state.hooks.items()
            if hook_state.state == CircuitState.OPEN.value
        ]

        return {
            "total_hooks": total_hooks,
            "active_hooks": total_hooks - len(disabled_hooks),
            "disabled_hooks": len(disabled_hooks),
            "disabled_hook_details": [
                {
                    "command": cmd,
                    "state": hook_state.state,
                    "failure_count": hook_state.failure_count,
                    "consecutive_failures": hook_state.consecutive_failures,
                    "last_error": hook_state.last_error,
                    "disabled_at": hook_state.disabled_at,
                    "retry_after": hook_state.retry_after,
                }
                for cmd, hook_state in disabled_hooks
            ],
            "global_stats": state.global_stats.to_dict(),
        }
