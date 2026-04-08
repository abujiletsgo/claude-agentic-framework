"""
Unit tests for hook state manager.

Tests cover:
- State initialization and persistence
- Success/failure recording
- Circuit breaker state transitions
- Reset operations
- Concurrent access safety
- Error handling and recovery
"""

import json
import os
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Import from parent directory
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from state_schema import HookState, HookStateData, GlobalStats, CircuitState
from hook_state_manager import HookStateManager


@pytest.fixture
def temp_state_file():
    """
    Create a temporary state file path (file does NOT exist yet).

    IMPORTANT: This creates a path to a non-existing file in a temp directory.
    The HookStateManager will properly initialize it on first use.
    """
    import shutil
    temp_dir = Path(tempfile.mkdtemp())
    state_file = temp_dir / "state.json"

    yield state_file

    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def state_manager(temp_state_file):
    """Create a state manager with temporary state file."""
    return HookStateManager(temp_state_file)


class TestStateInitialization:
    """Test state file initialization and basic operations."""

    def test_creates_state_file(self, temp_state_file):
        """Test that state file is created on initialization."""
        # File should not exist yet (fixture creates path only)
        assert not temp_state_file.exists()

        # Initialize manager
        HookStateManager(temp_state_file)

        # File should now exist
        assert temp_state_file.exists()

    def test_creates_parent_directory(self):
        """Test that parent directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "subdir" / "state.json"
            assert not state_file.parent.exists()

            HookStateManager(state_file)

            assert state_file.parent.exists()
            assert state_file.exists()

    def test_empty_state_structure(self, temp_state_file):
        """Test that empty state has correct structure."""
        manager = HookStateManager(temp_state_file)

        with open(temp_state_file) as f:
            data = json.load(f)

        assert "hooks" in data
        assert "global_stats" in data
        assert isinstance(data["hooks"], dict)
        assert len(data["hooks"]) == 0


class TestGetHookState:
    """Test retrieving hook state."""

    def test_get_nonexistent_hook(self, state_manager):
        """Test getting state for hook that doesn't exist returns default."""
        state = state_manager.get_hook_state("test_hook")

        assert state.state == CircuitState.CLOSED.value
        assert state.failure_count == 0
        assert state.consecutive_failures == 0
        assert state.consecutive_successes == 0

    def test_get_existing_hook(self, state_manager):
        """Test getting state for hook that exists."""
        # Record a failure first
        state_manager.record_failure("test_hook", "error message")

        # Get state
        state = state_manager.get_hook_state("test_hook")

        assert state.failure_count == 1
        assert state.consecutive_failures == 1
        assert state.last_error == "error message"


class TestRecordSuccess:
    """Test recording successful hook executions."""

    def test_record_first_success(self, state_manager):
        """Test recording first success for a hook."""
        state, changed = state_manager.record_success("test_hook")

        assert state.consecutive_successes == 1
        assert state.consecutive_failures == 0
        assert state.last_success is not None
        assert not changed

    def test_success_resets_failure_streak(self, state_manager):
        """Test that success resets consecutive failure count."""
        # Record failures
        state_manager.record_failure("test_hook", "error1")
        state_manager.record_failure("test_hook", "error2")

        # Record success
        state, _ = state_manager.record_success("test_hook")

        assert state.consecutive_successes == 1
        assert state.consecutive_failures == 0
        assert state.failure_count == 2  # Total failures not reset

    def test_success_increments_global_executions(self, state_manager):
        """Test that success increments global execution counter."""
        initial_stats = state_manager.get_global_stats()
        initial_count = initial_stats.total_executions

        state_manager.record_success("test_hook")

        final_stats = state_manager.get_global_stats()
        assert final_stats.total_executions == initial_count + 1

    def test_half_open_to_closed_transition(self, state_manager):
        """Test circuit transitions from HALF_OPEN to CLOSED after successes."""
        # Set up hook in OPEN state
        for i in range(3):
            state_manager.record_failure("test_hook", f"error{i}")

        # Transition to HALF_OPEN
        state_manager.transition_to_half_open("test_hook")

        # First success shouldn't close circuit
        state, changed = state_manager.record_success("test_hook")
        assert state.state == CircuitState.HALF_OPEN.value
        assert not changed

        # Second success should close circuit
        state, changed = state_manager.record_success("test_hook")
        assert state.state == CircuitState.CLOSED.value
        assert changed
        assert state.failure_count == 0


class TestRecordFailure:
    """Test recording failed hook executions."""

    def test_record_first_failure(self, state_manager):
        """Test recording first failure for a hook."""
        state, changed = state_manager.record_failure("test_hook", "error message")

        assert state.failure_count == 1
        assert state.consecutive_failures == 1
        assert state.consecutive_successes == 0
        assert state.last_error == "error message"
        assert state.first_failure is not None
        assert state.last_failure is not None
        assert not changed  # Circuit still closed after 1 failure

    def test_failure_resets_success_streak(self, state_manager):
        """Test that failure resets consecutive success count."""
        # Record successes
        state_manager.record_success("test_hook")
        state_manager.record_success("test_hook")

        # Record failure
        state, _ = state_manager.record_failure("test_hook", "error")

        assert state.consecutive_failures == 1
        assert state.consecutive_successes == 0

    def test_failure_increments_global_stats(self, state_manager):
        """Test that failure increments global counters."""
        initial_stats = state_manager.get_global_stats()
        initial_executions = initial_stats.total_executions
        initial_failures = initial_stats.total_failures

        state_manager.record_failure("test_hook", "error")

        final_stats = state_manager.get_global_stats()
        assert final_stats.total_executions == initial_executions + 1
        assert final_stats.total_failures == initial_failures + 1

    def test_circuit_opens_after_threshold(self, state_manager):
        """Test circuit opens after reaching failure threshold."""
        # First 2 failures shouldn't open circuit
        for i in range(2):
            state, changed = state_manager.record_failure("test_hook", f"error{i}")
            assert state.state == CircuitState.CLOSED.value
            assert not changed

        # Third failure should open circuit
        state, changed = state_manager.record_failure("test_hook", "error3", failure_threshold=3)
        assert state.state == CircuitState.OPEN.value
        assert changed
        assert state.disabled_at is not None
        assert state.retry_after is not None

    def test_custom_failure_threshold(self, state_manager):
        """Test using custom failure threshold."""
        # Open circuit with threshold of 2
        state_manager.record_failure("test_hook", "error1", failure_threshold=2)
        state, changed = state_manager.record_failure("test_hook", "error2", failure_threshold=2)

        assert state.state == CircuitState.OPEN.value
        assert changed

    def test_disabled_hooks_counter(self, state_manager):
        """Test that disabled hooks counter is updated."""
        # Open circuit for first hook
        for i in range(3):
            state_manager.record_failure("hook1", f"error{i}")

        stats = state_manager.get_global_stats()
        assert stats.hooks_disabled == 1

        # Open circuit for second hook
        for i in range(3):
            state_manager.record_failure("hook2", f"error{i}")

        stats = state_manager.get_global_stats()
        assert stats.hooks_disabled == 2


class TestCircuitTransitions:
    """Test circuit breaker state transitions."""

    def test_transition_to_half_open(self, state_manager):
        """Test transitioning from OPEN to HALF_OPEN."""
        # Open circuit
        for i in range(3):
            state_manager.record_failure("test_hook", f"error{i}")

        # Transition to half-open
        result = state_manager.transition_to_half_open("test_hook")
        assert result is True

        state = state_manager.get_hook_state("test_hook")
        assert state.state == CircuitState.HALF_OPEN.value
        assert state.consecutive_successes == 0
        assert state.consecutive_failures == 0

    def test_transition_already_closed(self, state_manager):
        """Test transition returns False if already in CLOSED state."""
        result = state_manager.transition_to_half_open("test_hook")
        assert result is False

    def test_transition_nonexistent_hook(self, state_manager):
        """Test transition returns False for nonexistent hook."""
        result = state_manager.transition_to_half_open("nonexistent")
        assert result is False

    def test_half_open_failure_reopens_circuit(self, state_manager):
        """Test that failure in HALF_OPEN state reopens circuit."""
        # Open circuit
        for i in range(3):
            state_manager.record_failure("test_hook", f"error{i}")

        # Transition to half-open
        state_manager.transition_to_half_open("test_hook")

        # Record another failure
        state, changed = state_manager.record_failure("test_hook", "error_again")

        # Circuit transitions back to OPEN; HALF_OPEN → OPEN is a real state change
        assert state.state == CircuitState.OPEN.value
        assert changed  # HALF_OPEN → OPEN transition is logged as state_changed


class TestResetOperations:
    """Test reset operations."""

    def test_reset_hook(self, state_manager):
        """Test resetting a single hook."""
        # Create state
        state_manager.record_failure("test_hook", "error")

        # Reset
        result = state_manager.reset_hook("test_hook")
        assert result is True

        # Should return default state now
        state = state_manager.get_hook_state("test_hook")
        assert state.failure_count == 0
        assert state.state == CircuitState.CLOSED.value

    def test_reset_nonexistent_hook(self, state_manager):
        """Test resetting nonexistent hook returns False."""
        result = state_manager.reset_hook("nonexistent")
        assert result is False

    def test_reset_all(self, state_manager):
        """Test resetting all hooks."""
        # Create multiple hooks
        state_manager.record_failure("hook1", "error1")
        state_manager.record_failure("hook2", "error2")
        state_manager.record_failure("hook3", "error3")

        # Reset all
        count = state_manager.reset_all()
        assert count == 3

        # All hooks should be gone
        all_hooks = state_manager.get_all_hooks()
        assert len(all_hooks) == 0

        # Global stats should be reset
        stats = state_manager.get_global_stats()
        assert stats.total_executions == 0
        assert stats.total_failures == 0
        assert stats.hooks_disabled == 0


class TestQueryOperations:
    """Test query and reporting operations."""

    def test_get_all_hooks(self, state_manager):
        """Test getting all hooks."""
        # Create multiple hooks
        state_manager.record_failure("hook1", "error1")
        state_manager.record_success("hook2")
        state_manager.record_failure("hook3", "error3")

        all_hooks = state_manager.get_all_hooks()
        assert len(all_hooks) == 3
        assert "hook1" in all_hooks
        assert "hook2" in all_hooks
        assert "hook3" in all_hooks

    def test_get_disabled_hooks(self, state_manager):
        """Test getting only disabled hooks."""
        # Create some hooks, open circuit for some
        state_manager.record_success("hook1")

        for i in range(3):
            state_manager.record_failure("hook2", f"error{i}")

        for i in range(3):
            state_manager.record_failure("hook3", f"error{i}")

        disabled = state_manager.get_disabled_hooks()
        assert len(disabled) == 2

        disabled_cmds = [cmd for cmd, _ in disabled]
        assert "hook2" in disabled_cmds
        assert "hook3" in disabled_cmds
        assert "hook1" not in disabled_cmds

    def test_get_health_report(self, state_manager):
        """Test generating health report."""
        # Create various hook states
        state_manager.record_success("active_hook")

        for i in range(3):
            state_manager.record_failure("disabled_hook", f"error{i}")

        report = state_manager.get_health_report()

        assert report["total_hooks"] == 2
        assert report["active_hooks"] == 1
        assert report["disabled_hooks"] == 1
        assert len(report["disabled_hook_details"]) == 1

        disabled_detail = report["disabled_hook_details"][0]
        assert disabled_detail["command"] == "disabled_hook"
        assert disabled_detail["state"] == CircuitState.OPEN.value
        assert disabled_detail["failure_count"] == 3


class TestPersistence:
    """Test state persistence across restarts."""

    def test_state_persists_across_instances(self, temp_state_file):
        """Test that state persists when manager is recreated."""
        # Create first manager and record state
        manager1 = HookStateManager(temp_state_file)
        manager1.record_failure("test_hook", "error")
        manager1.record_success("test_hook")

        # Create second manager with same file
        manager2 = HookStateManager(temp_state_file)
        state = manager2.get_hook_state("test_hook")

        assert state.failure_count == 1
        assert state.consecutive_successes == 1

    def test_atomic_writes(self, temp_state_file):
        """Test that writes are atomic (file is never corrupted)."""
        manager = HookStateManager(temp_state_file)

        # Perform many writes
        for i in range(100):
            if i % 2 == 0:
                manager.record_success(f"hook{i % 10}")
            else:
                manager.record_failure(f"hook{i % 10}", f"error{i}")

        # File should be valid JSON
        with open(temp_state_file) as f:
            data = json.load(f)

        assert "hooks" in data
        assert "global_stats" in data


class TestConcurrentAccess:
    """Test thread safety of concurrent operations."""

    def test_concurrent_reads(self, state_manager):
        """Test that concurrent reads don't interfere with each other."""
        state_manager.record_failure("test_hook", "error")

        results = []

        def read_state():
            state = state_manager.get_hook_state("test_hook")
            results.append(state.failure_count)

        threads = [threading.Thread(target=read_state) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All reads should see same value
        assert all(count == 1 for count in results)

    def test_concurrent_writes(self, state_manager):
        """Test that concurrent writes are properly serialized."""
        def record_failure():
            state_manager.record_failure("test_hook", "error", failure_threshold=100)

        threads = [threading.Thread(target=record_failure) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have exactly 10 failures recorded
        state = state_manager.get_hook_state("test_hook")
        assert state.failure_count == 10

    def test_concurrent_mixed_operations(self, state_manager):
        """Test concurrent mix of reads and writes."""
        def worker(worker_id):
            for i in range(5):
                if worker_id % 2 == 0:
                    state_manager.record_success(f"hook{worker_id}")
                else:
                    state_manager.record_failure(f"hook{worker_id}", "error", failure_threshold=100)
                state_manager.get_hook_state(f"hook{worker_id}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Check that state is consistent
        all_hooks = state_manager.get_all_hooks()
        total_failures = sum(h.failure_count for h in all_hooks.values())
        total_executions = state_manager.get_global_stats().total_executions

        # Should have recorded all operations
        assert total_executions == 50  # 10 workers * 5 operations
        # 5 odd workers with 5 failures each = 25 failures
        assert total_failures == 25


class TestErrorHandling:
    """Test error handling and recovery."""

    def test_corrupted_state_file(self, temp_state_file):
        """Test handling of corrupted state file."""
        # Write invalid JSON
        with open(temp_state_file, 'w') as f:
            f.write("not valid json{")

        manager = HookStateManager(temp_state_file)

        # Should raise ValueError on read
        with pytest.raises(ValueError, match="Corrupted state file"):
            manager.get_hook_state("test_hook")

    def test_empty_state_file(self, temp_state_file):
        """Test handling of empty state file."""
        # Write empty file
        with open(temp_state_file, 'w') as f:
            f.write("")

        manager = HookStateManager(temp_state_file)

        with pytest.raises(ValueError):
            manager.get_hook_state("test_hook")

    def test_recovery_after_corruption(self, temp_state_file):
        """Test that state can be recovered by resetting."""
        manager = HookStateManager(temp_state_file)

        # Corrupt the file
        with open(temp_state_file, 'w') as f:
            f.write("corrupted")

        # Should be able to reset and recover
        # We need to reinitialize to get fresh state
        with pytest.raises(ValueError):
            manager.get_hook_state("test_hook")

        # Manual recovery by writing empty state
        empty_state = HookStateData()
        with open(temp_state_file, 'w') as f:
            json.dump(empty_state.to_dict(), f)

        # Now should work
        state = manager.get_hook_state("test_hook")
        assert state.state == CircuitState.CLOSED.value


class TestTimestamps:
    """Test timestamp handling."""

    def test_timestamp_format(self, state_manager):
        """Test that timestamps are in ISO 8601 format."""
        state, _ = state_manager.record_failure("test_hook", "error")

        # Should be parseable as ISO 8601
        assert state.last_failure is not None
        dt = datetime.fromisoformat(state.last_failure)
        assert dt.tzinfo is not None  # Should have timezone

    def test_retry_after_calculation(self, state_manager):
        """Test that retry_after is set correctly."""
        # Open circuit
        for i in range(3):
            state_manager.record_failure("test_hook", f"error{i}")

        state = state_manager.get_hook_state("test_hook")

        # Parse timestamps
        disabled_at = datetime.fromisoformat(state.disabled_at)
        retry_after = datetime.fromisoformat(state.retry_after)

        # Should be approximately 5 minutes apart
        diff = (retry_after - disabled_at).total_seconds()
        assert 299 <= diff <= 301  # Allow for small timing variations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
