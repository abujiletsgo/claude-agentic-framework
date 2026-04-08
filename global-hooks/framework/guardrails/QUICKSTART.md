# Hook State Manager - Quick Start Guide

Get up and running with the hook failure tracking state manager in 5 minutes.

## Installation

```bash
cd /Users/tomkwon/Documents/claude-agentic-framework/global-hooks/framework/guardrails

# Install dependencies
pip install -r requirements.txt
```

## Basic Usage

### 1. Initialize State Manager

```python
from hook_state_manager import HookStateManager

# Use default state file (~/.claude/hook_state.json)
manager = HookStateManager()

# Or specify custom location
from pathlib import Path
manager = HookStateManager(Path("/custom/path/state.json"))
```

### 2. Track Hook Execution

```python
hook_cmd = "uv run validators/validate_file.py"

# Record successful execution
state, state_changed = manager.record_success(hook_cmd)
print(f"Consecutive successes: {state.consecutive_successes}")

# Record failed execution
state, state_changed = manager.record_failure(
    hook_cmd,
    error="File not found",
    failure_threshold=3  # Open circuit after 3 failures
)

if state_changed:
    print(f"Circuit opened! Retry after: {state.retry_after}")
```

### 3. Check Circuit State

```python
from state_schema import CircuitState

state = manager.get_hook_state(hook_cmd)

if state.state == CircuitState.OPEN.value:
    print(f"Hook is disabled until {state.retry_after}")
elif state.state == CircuitState.HALF_OPEN.value:
    print("Hook is being tested for recovery")
else:
    print("Hook is active")
```

### 4. Monitor Health

```python
# Get health report
report = manager.get_health_report()
print(f"Total hooks: {report['total_hooks']}")
print(f"Active: {report['active_hooks']}")
print(f"Disabled: {report['disabled_hooks']}")

# List disabled hooks
for hook_detail in report['disabled_hook_details']:
    print(f"  {hook_detail['command']}")
    print(f"    Failures: {hook_detail['failure_count']}")
    print(f"    Last error: {hook_detail['last_error']}")

# Or use convenience method
disabled = manager.get_disabled_hooks()
for cmd, state in disabled:
    print(f"{cmd}: {state.consecutive_failures} failures")
```

### 5. Reset State

```python
# Reset single hook
manager.reset_hook(hook_cmd)

# Reset all hooks
count = manager.reset_all()
print(f"Reset {count} hooks")
```

## Running the Example

```bash
# Run the basic usage example
python examples/basic_usage.py
```

This demonstrates:
- Recording successes and failures
- Circuit breaker state transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
- Health reporting
- Reset operations

## Running Tests

```bash
# Install test dependencies (if not already installed)
pip install -r requirements.txt

# Run all tests
pytest tests/test_state_manager.py -v

# Run with coverage
./run_tests.sh --cov

# Run specific test class
pytest tests/test_state_manager.py::TestCircuitTransitions -v
```

## State File Format

The state is persisted to `~/.claude/hook_state.json`:

```json
{
  "hooks": {
    "uv run validators/validate.py": {
      "state": "closed",
      "failure_count": 0,
      "consecutive_failures": 0,
      "consecutive_successes": 5,
      "first_failure": null,
      "last_failure": null,
      "last_success": "2026-02-10T23:45:00+00:00",
      "last_error": null,
      "disabled_at": null,
      "retry_after": null
    }
  },
  "global_stats": {
    "total_executions": 150,
    "total_failures": 3,
    "hooks_disabled": 0,
    "last_updated": "2026-02-10T23:45:00+00:00"
  }
}
```

## Circuit Breaker Flow

```
1. Hook executes successfully
   → record_success()
   → Increment consecutive_successes
   → Reset consecutive_failures

2. Hook fails (1st time)
   → record_failure()
   → failure_count = 1
   → consecutive_failures = 1
   → State: CLOSED (still active)

3. Hook fails (2nd time)
   → record_failure()
   → failure_count = 2
   → consecutive_failures = 2
   → State: CLOSED (still active)

4. Hook fails (3rd time)
   → record_failure()
   → failure_count = 3
   → consecutive_failures = 3
   → State: OPEN (disabled!)
   → retry_after = now + 300 seconds

5. After cooldown period
   → transition_to_half_open()
   → State: HALF_OPEN (testing recovery)
   → Reset consecutive counters

6. Hook succeeds (1st time in HALF_OPEN)
   → record_success()
   → consecutive_successes = 1
   → State: HALF_OPEN (still testing)

7. Hook succeeds (2nd time in HALF_OPEN)
   → record_success()
   → consecutive_successes = 2
   → State: CLOSED (recovered!)
   → Clear failure counts
```

## Common Patterns

### Pattern 1: Circuit Breaker Wrapper

```python
def execute_with_circuit_breaker(hook_cmd, failure_threshold=3):
    """Execute hook with circuit breaker protection."""
    manager = HookStateManager()
    state = manager.get_hook_state(hook_cmd)

    # Check if circuit is open
    if state.state == CircuitState.OPEN.value:
        # Check if cooldown elapsed (5 minutes default)
        from datetime import datetime, timezone
        retry_after = datetime.fromisoformat(state.retry_after)
        now = datetime.now(timezone.utc)

        if now >= retry_after:
            # Transition to testing mode
            manager.transition_to_half_open(hook_cmd)
        else:
            # Still in cooldown
            print(f"Hook disabled, retry after {state.retry_after}")
            return {"result": "skip", "reason": "circuit_open"}

    # Execute the hook
    try:
        result = subprocess.run(hook_cmd, shell=True, capture_output=True)
        if result.returncode == 0:
            manager.record_success(hook_cmd)
            return {"result": "success"}
        else:
            error = result.stderr.decode()
            manager.record_failure(hook_cmd, error, failure_threshold)
            return {"result": "failure", "error": error}
    except Exception as e:
        manager.record_failure(hook_cmd, str(e), failure_threshold)
        return {"result": "error", "error": str(e)}
```

### Pattern 2: Health Dashboard

```python
def display_health_dashboard():
    """Display circuit breaker health status."""
    manager = HookStateManager()
    report = manager.get_health_report()

    print("=" * 60)
    print("Circuit Breaker Health Dashboard")
    print("=" * 60)
    print(f"Total Hooks: {report['total_hooks']}")
    print(f"Active: {report['active_hooks']}")
    print(f"Disabled: {report['disabled_hooks']}")
    print()

    if report['disabled_hooks'] > 0:
        print("DISABLED HOOKS:")
        for hook in report['disabled_hook_details']:
            print(f"  [{hook['state'].upper()}] {hook['command']}")
            print(f"    Failures: {hook['consecutive_failures']} consecutive, "
                  f"{hook['failure_count']} total")
            print(f"    Last Error: {hook['last_error']}")
            print(f"    Disabled Since: {hook['disabled_at']}")
            print(f"    Retry After: {hook['retry_after']}")
            print()

    stats = report['global_stats']
    print(f"Global Stats:")
    print(f"  Total Executions: {stats['total_executions']}")
    print(f"  Total Failures: {stats['total_failures']}")
    print(f"  Last Updated: {stats['last_updated']}")
```

### Pattern 3: Recovery Management

```python
def manage_recovery(hook_cmd):
    """Manage hook recovery process."""
    manager = HookStateManager()
    state = manager.get_hook_state(hook_cmd)

    if state.state == CircuitState.OPEN.value:
        print(f"Hook is disabled (opened at {state.disabled_at})")
        print(f"Can retry after: {state.retry_after}")

        # Manual override (use with caution)
        response = input("Force enable? (yes/no): ")
        if response.lower() == "yes":
            manager.reset_hook(hook_cmd)
            print("Hook re-enabled!")
    elif state.state == CircuitState.HALF_OPEN.value:
        print("Hook is being tested for recovery")
        print(f"Consecutive successes so far: {state.consecutive_successes}")
    else:
        print("Hook is active")
        if state.failure_count > 0:
            print(f"Previous failures: {state.failure_count}")
```

## Configuration Integration

The state manager works with the existing config loader:

```python
from config_loader import load_config
from hook_state_manager import HookStateManager
from pathlib import Path

# Load configuration
config = load_config()

# Use configured state file path
state_file = config.get_state_file_path()
manager = HookStateManager(state_file)

# Use configured thresholds
failure_threshold = config.circuit_breaker.failure_threshold
success_threshold = config.circuit_breaker.success_threshold

# Record failure with configured threshold
manager.record_failure(hook_cmd, error, failure_threshold=failure_threshold)
```

## Next Steps

1. **Read the full documentation**: See [README.md](README.md) for complete API reference
2. **Review the architecture**: See [ANTI_LOOP_GUARDRAILS.md](../ANTI_LOOP_GUARDRAILS.md)
3. **Explore examples**: Check [examples/basic_usage.py](examples/basic_usage.py)
4. **Run tests**: Execute test suite to verify installation
5. **Integrate with circuit breaker**: Ready for Phase 2 integration

## Troubleshooting

### State file not created

```python
# Check if directory exists
from pathlib import Path
state_dir = Path.home() / ".claude"
state_dir.mkdir(parents=True, exist_ok=True)

# Initialize manager (will create file)
manager = HookStateManager()
```

### Permission errors

```bash
# Check permissions
ls -la ~/.claude/

# Fix permissions
chmod 755 ~/.claude
chmod 644 ~/.claude/hook_state.json
```

### Corrupted state file

```python
# Reset to clean state
manager = HookStateManager()
manager.reset_all()
```

### Import errors

```bash
# Ensure all dependencies installed
pip install -r requirements.txt

# Verify installation
python -c "from hook_state_manager import HookStateManager; print('OK')"
```

## Support

- **Documentation**: [README.md](README.md)
- **Architecture**: [ANTI_LOOP_GUARDRAILS.md](../ANTI_LOOP_GUARDRAILS.md)
- **Configuration**: [CONFIG.md](CONFIG.md)
- **Tests**: `pytest tests/test_state_manager.py -v`
- **Examples**: `python examples/basic_usage.py`
