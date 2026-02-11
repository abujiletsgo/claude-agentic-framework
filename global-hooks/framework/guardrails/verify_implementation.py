#!/usr/bin/env python3
"""
Implementation verification script.

This script performs basic validation of the state manager implementation
without requiring pytest. It can be run as a quick smoke test.

Usage:
    python verify_implementation.py
"""

import sys
import tempfile
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from hook_state_manager import HookStateManager
    from state_schema import HookState, CircuitState, get_current_timestamp
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the guardrails directory")
    sys.exit(1)


def test_basic_operations():
    """Test basic state operations."""
    print("Testing basic operations...")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        state_file = Path(f.name)

    try:
        manager = HookStateManager(state_file)

        # Test 1: Record success
        state, changed = manager.record_success("test_hook")
        assert state.consecutive_successes == 1, "Success count should be 1"
        assert not changed, "State should not change on first success"
        print("  ✓ Record success")

        # Test 2: Record failure
        state, changed = manager.record_failure("test_hook2", "error message")
        assert state.failure_count == 1, "Failure count should be 1"
        assert state.last_error == "error message", "Error message should be stored"
        print("  ✓ Record failure")

        # Test 3: Circuit opens after threshold
        for i in range(3):
            state, changed = manager.record_failure("test_hook3", f"error{i}")

        assert state.state == CircuitState.OPEN.value, "Circuit should be open"
        assert state.disabled_at is not None, "Disabled timestamp should be set"
        print("  ✓ Circuit opens after threshold")

        # Test 4: Get all hooks
        all_hooks = manager.get_all_hooks()
        assert len(all_hooks) == 3, "Should have 3 hooks"
        print("  ✓ Get all hooks")

        # Test 5: Get disabled hooks
        disabled = manager.get_disabled_hooks()
        assert len(disabled) == 1, "Should have 1 disabled hook"
        print("  ✓ Get disabled hooks")

        # Test 6: Health report
        report = manager.get_health_report()
        assert report['total_hooks'] == 3, "Should report 3 total hooks"
        assert report['disabled_hooks'] == 1, "Should report 1 disabled hook"
        print("  ✓ Health report")

        # Test 7: Reset hook
        result = manager.reset_hook("test_hook")
        assert result, "Reset should return True"
        remaining = manager.get_all_hooks()
        assert len(remaining) == 2, "Should have 2 hooks after reset"
        print("  ✓ Reset hook")

        # Test 8: Reset all
        count = manager.reset_all()
        assert count == 2, "Should reset 2 hooks"
        final = manager.get_all_hooks()
        assert len(final) == 0, "Should have 0 hooks after reset all"
        print("  ✓ Reset all")

        return True

    except AssertionError as e:
        print(f"  ❌ Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    finally:
        try:
            state_file.unlink()
        except Exception:
            pass


def test_circuit_transitions():
    """Test circuit breaker state transitions."""
    print("Testing circuit transitions...")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        state_file = Path(f.name)

    try:
        manager = HookStateManager(state_file)

        # Open circuit
        for i in range(3):
            manager.record_failure("test_hook", f"error{i}")

        state = manager.get_hook_state("test_hook")
        assert state.state == CircuitState.OPEN.value, "Should be OPEN"
        print("  ✓ CLOSED → OPEN transition")

        # Transition to half-open
        result = manager.transition_to_half_open("test_hook")
        assert result, "Transition should succeed"
        state = manager.get_hook_state("test_hook")
        assert state.state == CircuitState.HALF_OPEN.value, "Should be HALF_OPEN"
        print("  ✓ OPEN → HALF_OPEN transition")

        # Close circuit with successes
        manager.record_success("test_hook")
        state, changed = manager.record_success("test_hook")
        assert state.state == CircuitState.CLOSED.value, "Should be CLOSED"
        assert changed, "State should have changed"
        print("  ✓ HALF_OPEN → CLOSED transition")

        return True

    except AssertionError as e:
        print(f"  ❌ Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    finally:
        try:
            state_file.unlink()
        except Exception:
            pass


def test_persistence():
    """Test state persistence across instances."""
    print("Testing persistence...")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        state_file = Path(f.name)

    try:
        # Create first instance and record state
        manager1 = HookStateManager(state_file)
        manager1.record_failure("test_hook", "error1")
        manager1.record_success("test_hook")

        # Create second instance and verify state persists
        manager2 = HookStateManager(state_file)
        state = manager2.get_hook_state("test_hook")

        assert state.failure_count == 1, "Failure count should persist"
        assert state.consecutive_successes == 1, "Success count should persist"
        print("  ✓ State persists across instances")

        return True

    except AssertionError as e:
        print(f"  ❌ Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    finally:
        try:
            state_file.unlink()
        except Exception:
            pass


def test_timestamps():
    """Test timestamp handling."""
    print("Testing timestamps...")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        state_file = Path(f.name)

    try:
        manager = HookStateManager(state_file)

        # Record failure and check timestamp format
        state, _ = manager.record_failure("test_hook", "error")
        assert state.last_failure is not None, "Timestamp should be set"

        # Verify ISO 8601 format
        from datetime import datetime
        dt = datetime.fromisoformat(state.last_failure)
        assert dt.tzinfo is not None, "Timestamp should have timezone"
        print("  ✓ Timestamps are ISO 8601 with timezone")

        return True

    except AssertionError as e:
        print(f"  ❌ Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    finally:
        try:
            state_file.unlink()
        except Exception:
            pass


def test_file_creation():
    """Test automatic file and directory creation."""
    print("Testing file creation...")

    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = Path(tmpdir) / "subdir" / "state.json"

        try:
            # Directory doesn't exist yet
            assert not state_file.parent.exists()

            # Initialize manager (should create directory and file)
            manager = HookStateManager(state_file)

            assert state_file.parent.exists(), "Directory should be created"
            assert state_file.exists(), "State file should be created"
            print("  ✓ Automatic directory and file creation")

            return True

        except AssertionError as e:
            print(f"  ❌ Assertion failed: {e}")
            return False
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Hook State Manager - Implementation Verification")
    print("=" * 60)
    print()

    tests = [
        ("Basic Operations", test_basic_operations),
        ("Circuit Transitions", test_circuit_transitions),
        ("Persistence", test_persistence),
        ("Timestamps", test_timestamps),
        ("File Creation", test_file_creation),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n[{name}]")
        result = test_func()
        results.append((name, result))

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print()
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All verification tests passed!")
        print("Implementation is working correctly.")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        print("Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
