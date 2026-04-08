#!/usr/bin/env python3
"""
Circuit breaker example demonstrating complete usage.

This example shows:
1. Basic circuit breaker setup
2. Recording successes and failures
3. Circuit opening after threshold
4. Cooldown and recovery testing
5. Circuit closing after successful recovery
"""

import tempfile
import time
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from circuit_breaker import CircuitBreaker, CircuitBreakerDecision
from hook_state_manager import HookStateManager
from config_loader import GuardrailsConfig, CircuitBreakerConfig, LoggingConfig


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_result(result):
    """Print circuit breaker result."""
    print(f"Decision: {result.decision.value}")
    print(f"State: {result.state.value}")
    print(f"Should Execute: {result.should_execute}")
    print(f"Message: {result.message}")


def main():
    """Run circuit breaker demonstration."""
    print("=" * 60)
    print("  Circuit Breaker Example")
    print("=" * 60)

    # Create temporary state and log files
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        state_file = Path(f.name)

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        log_file = Path(f.name)

    try:
        # Configure circuit breaker
        config = GuardrailsConfig(
            circuit_breaker=CircuitBreakerConfig(
                enabled=True,
                failure_threshold=3,
                cooldown_seconds=5,
                success_threshold=2,
                exclude=[]
            ),
            logging=LoggingConfig(
                file=str(log_file),
                level="INFO",
                format="%(asctime)s | %(levelname)s | %(hook_cmd)s | %(message)s"
            ),
            state_file=str(state_file)
        )
        config.expand_paths()

        # Create circuit breaker
        state_manager = HookStateManager(config.get_state_file_path())
        breaker = CircuitBreaker(state_manager, config)

        hook_cmd = "example_hook"

        # Example 1: Normal operation (CLOSED state)
        print_section("1. Normal Operation (CLOSED)")
        result = breaker.should_execute(hook_cmd)
        print_result(result)
        assert result.should_execute is True
        print("✓ Hook executes normally")

        # Example 2: Record successful execution
        print_section("2. Recording Successes")
        breaker.record_success(hook_cmd)
        breaker.record_success(hook_cmd)
        state = state_manager.get_hook_state(hook_cmd)
        print(f"Consecutive successes: {state.consecutive_successes}")
        print("✓ Successes tracked correctly")

        # Example 3: Record failures
        print_section("3. Recording Failures")
        print("Recording 3 failures to trigger circuit opening...")
        for i in range(3):
            breaker.record_failure(hook_cmd, f"Error {i+1}")
            state = state_manager.get_hook_state(hook_cmd)
            print(f"  Failure {i+1}: consecutive_failures = {state.consecutive_failures}")

        state = state_manager.get_hook_state(hook_cmd)
        print(f"\nCircuit state: {state.state}")
        print("✓ Circuit opened after threshold")

        # Example 4: Circuit open (skip execution)
        print_section("4. Circuit Open (Skip Execution)")
        result = breaker.should_execute(hook_cmd)
        print_result(result)
        assert result.should_execute is False
        print("✓ Execution skipped (graceful degradation)")

        # Example 5: Cooldown period
        print_section("5. Cooldown Period")
        print(f"Waiting {config.circuit_breaker.cooldown_seconds} seconds for cooldown...")
        time.sleep(config.circuit_breaker.cooldown_seconds + 1)
        print("✓ Cooldown period elapsed")

        # Example 6: Recovery test (HALF_OPEN)
        print_section("6. Recovery Test (HALF_OPEN)")
        result = breaker.should_execute(hook_cmd)
        print_result(result)
        assert result.should_execute is True
        assert result.state.value == "half_open"
        print("✓ Circuit transitioned to HALF_OPEN for testing")

        # Example 7: Successful recovery
        print_section("7. Successful Recovery")
        print("Recording successes to close circuit...")
        breaker.record_success(hook_cmd)
        state = state_manager.get_hook_state(hook_cmd)
        print(f"  Success 1: consecutive_successes = {state.consecutive_successes}")

        breaker.record_success(hook_cmd)
        state = state_manager.get_hook_state(hook_cmd)
        print(f"  Success 2: consecutive_successes = {state.consecutive_successes}")
        print(f"\nCircuit state: {state.state}")
        print("✓ Circuit closed after successful recovery")

        # Example 8: Back to normal
        print_section("8. Back to Normal Operation")
        result = breaker.should_execute(hook_cmd)
        print_result(result)
        assert result.should_execute is True
        assert result.state.value == "closed"
        print("✓ Circuit back to normal operation")

        # Example 9: Exclusion list
        print_section("9. Hook Exclusion")
        config.circuit_breaker.exclude = ["critical"]
        breaker_with_exclusion = CircuitBreaker(state_manager, config)

        critical_hook = "critical_safety_check"
        print(f"Hook: {critical_hook}")

        # Record many failures
        for i in range(10):
            breaker_with_exclusion.record_failure(critical_hook, f"Error {i+1}")

        result = breaker_with_exclusion.should_execute(critical_hook)
        print_result(result)
        assert result.should_execute is True
        print("✓ Critical hook always executes (excluded from circuit breaker)")

        # Example 10: Health report
        print_section("10. Health Report")
        report = state_manager.get_health_report()
        print(f"Total hooks: {report['total_hooks']}")
        print(f"Active hooks: {report['active_hooks']}")
        print(f"Disabled hooks: {report['disabled_hooks']}")
        print(f"\nGlobal stats:")
        stats = report['global_stats']
        print(f"  Total executions: {stats['total_executions']}")
        print(f"  Total failures: {stats['total_failures']}")
        print("✓ Health reporting works correctly")

        print_section("Summary")
        print("✓ All circuit breaker features demonstrated successfully")
        print("\nKey Features:")
        print("  - Automatic failure detection")
        print("  - Circuit opening after threshold")
        print("  - Graceful degradation (skip execution)")
        print("  - Cooldown period before recovery")
        print("  - Recovery testing in half-open state")
        print("  - Automatic circuit closing after success")
        print("  - Hook exclusion support")
        print("  - Comprehensive state tracking")

        # Show log file location
        print(f"\nLog file: {log_file}")
        print("Check the log file for detailed circuit breaker activity.")

    finally:
        # Cleanup
        if state_file.exists():
            state_file.unlink()
        if log_file.exists():
            print(f"\nLog file contents:")
            print("-" * 60)
            print(log_file.read_text())
            log_file.unlink()


if __name__ == "__main__":
    main()
