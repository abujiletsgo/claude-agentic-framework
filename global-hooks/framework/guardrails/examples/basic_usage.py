#!/usr/bin/env python3
"""
Basic usage example for HookStateManager.

This script demonstrates the core functionality of the hook state manager,
including recording successes/failures and monitoring circuit breaker state.
"""

import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from hook_state_manager import HookStateManager
from state_schema import CircuitState


def main():
    """Demonstrate basic state manager operations."""

    # Use temporary state file for demo
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        state_file = Path(f.name)

    print(f"Using temporary state file: {state_file}\n")

    try:
        # Initialize manager
        manager = HookStateManager(state_file)
        print("=" * 60)
        print("Hook State Manager - Basic Usage Demo")
        print("=" * 60)

        # Demo 1: Record successes
        print("\n1. Recording successful executions:")
        print("-" * 40)
        hook_cmd = "uv run validators/validate_file.py"

        for i in range(3):
            state, changed = manager.record_success(hook_cmd)
            print(f"  Success #{i+1}: consecutive_successes={state.consecutive_successes}")

        # Demo 2: Record failures and watch circuit open
        print("\n2. Recording failures (circuit breaker demo):")
        print("-" * 40)
        failing_hook = "uv run validators/missing_file.py"

        for i in range(4):
            state, changed = manager.record_failure(
                failing_hook,
                f"Error: File not found (attempt {i+1})",
                failure_threshold=3
            )
            print(f"  Failure #{i+1}:")
            print(f"    State: {state.state}")
            print(f"    Consecutive failures: {state.consecutive_failures}")
            if changed:
                print(f"    ⚠️  Circuit OPENED - hook disabled!")
                print(f"    Retry after: {state.retry_after}")

        # Demo 3: Check disabled hooks
        print("\n3. Getting disabled hooks:")
        print("-" * 40)
        disabled = manager.get_disabled_hooks()
        print(f"  Found {len(disabled)} disabled hook(s):")
        for cmd, state in disabled:
            print(f"    - {cmd}")
            print(f"      Failures: {state.failure_count}")
            print(f"      Last error: {state.last_error}")

        # Demo 4: Health report
        print("\n4. Health report:")
        print("-" * 40)
        report = manager.get_health_report()
        print(f"  Total hooks: {report['total_hooks']}")
        print(f"  Active: {report['active_hooks']}")
        print(f"  Disabled: {report['disabled_hooks']}")
        print(f"  Total executions: {report['global_stats']['total_executions']}")
        print(f"  Total failures: {report['global_stats']['total_failures']}")

        # Demo 5: Transition to HALF_OPEN
        print("\n5. Testing recovery (HALF_OPEN state):")
        print("-" * 40)
        result = manager.transition_to_half_open(failing_hook)
        if result:
            state = manager.get_hook_state(failing_hook)
            print(f"  Transitioned to {state.state}")
            print(f"  Now testing recovery...")

            # First success
            state, changed = manager.record_success(failing_hook)
            print(f"  After 1st success: state={state.state}, changed={changed}")

            # Second success (should close circuit)
            state, changed = manager.record_success(failing_hook)
            print(f"  After 2nd success: state={state.state}, changed={changed}")
            if changed:
                print(f"  ✅ Circuit CLOSED - hook re-enabled!")

        # Demo 6: Reset operations
        print("\n6. Reset operations:")
        print("-" * 40)

        # Reset single hook
        reset_result = manager.reset_hook(hook_cmd)
        print(f"  Reset '{hook_cmd}': {reset_result}")

        # Show remaining hooks
        remaining = manager.get_all_hooks()
        print(f"  Remaining hooks: {len(remaining)}")

        # Reset all
        count = manager.reset_all()
        print(f"  Reset all hooks: {count} hook(s) cleared")

        # Final state
        final_hooks = manager.get_all_hooks()
        print(f"  Final hook count: {len(final_hooks)}")

        print("\n" + "=" * 60)
        print("Demo completed successfully!")
        print("=" * 60)

    finally:
        # Cleanup temp file
        try:
            state_file.unlink()
            print(f"\nCleaned up temporary file: {state_file}")
        except Exception as e:
            print(f"\nWarning: Could not delete temp file: {e}")


if __name__ == "__main__":
    main()
