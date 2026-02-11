# Hook State Manager - Guardrails System

Thread-safe state management for hook failure tracking and circuit breaker implementation.

## Overview

This module provides persistent state tracking for hook executions, enabling circuit breaker patterns to prevent infinite loops caused by repeatedly failing hooks.

## Components

### 1. State Schema (`state_schema.py`)

Defines the data structures for tracking hook state:

- **CircuitState**: Enum for circuit breaker states (CLOSED, OPEN, HALF_OPEN)
- **HookState**: Per-hook state tracking (failures, successes, timestamps, errors)
- **GlobalStats**: Aggregate statistics across all hooks
- **HookStateData**: Complete state file structure

### 2. State Manager (`hook_state_manager.py`)

Provides thread-safe CRUD operations:

- `get_hook_state(hook_cmd)`: Get current state for a hook
- `record_success(hook_cmd)`: Record successful execution
- `record_failure(hook_cmd, error)`: Record failed execution
- `transition_to_half_open(hook_cmd)`: Transition from OPEN to HALF_OPEN
- `reset_hook(hook_cmd)`: Clear state for a specific hook
- `reset_all()`: Clear all state
- `get_all_hooks()`: Get all hook states
- `get_disabled_hooks()`: Get hooks in OPEN state
- `get_health_report()`: Generate comprehensive health report

### 3. Test Suite (`tests/test_state_manager.py`)

Comprehensive unit tests covering:

- State initialization and persistence
- Success/failure recording
- Circuit breaker state transitions
- Reset operations
- Query operations
- Concurrent access safety
- Error handling and recovery
- Timestamp handling

## Features

### Thread Safety

All operations are thread-safe using file locking:

- **Unix/Linux/macOS**: Uses `fcntl` for file locking
- **Windows**: Falls back to `portalocker` library
- **Fallback**: Graceful degradation if neither available

### Atomic Writes

State updates use atomic write pattern:

1. Write to temporary file
2. Flush and sync to disk
3. Atomic rename to actual state file

This ensures the state file is never left in a corrupted state.

### Persistence

State is persisted to `~/.claude/hook_state.json` (configurable) in human-readable JSON format.

## State File Format

```json
{
  "hooks": {
    "hook_command_string": {
      "state": "closed|open|half_open",
      "failure_count": 0,
      "consecutive_failures": 0,
      "consecutive_successes": 0,
      "first_failure": "2026-02-10T23:32:15+00:00",
      "last_failure": "2026-02-10T23:35:42+00:00",
      "last_success": null,
      "last_error": "error message",
      "disabled_at": "2026-02-10T23:35:42+00:00",
      "retry_after": "2026-02-10T23:40:42+00:00"
    }
  },
  "global_stats": {
    "total_executions": 100,
    "total_failures": 5,
    "hooks_disabled": 1,
    "last_updated": "2026-02-10T23:35:42+00:00"
  }
}
```

## Circuit Breaker Logic

### State Transitions

```
CLOSED --[failure_count >= threshold]--> OPEN
OPEN --[cooldown_elapsed]--> HALF_OPEN
HALF_OPEN --[success * 2]--> CLOSED
HALF_OPEN --[failure]--> OPEN
```

### Recording Success

1. Increment consecutive successes
2. Reset consecutive failures
3. Update last_success timestamp
4. If in HALF_OPEN state:
   - After 2 consecutive successes → transition to CLOSED
   - Reset failure_count and clear error state

### Recording Failure

1. Increment failure counts (total and consecutive)
2. Reset consecutive successes
3. Update timestamps and error message
4. If consecutive_failures >= threshold:
   - Transition to OPEN state
   - Set disabled_at timestamp
   - Calculate retry_after (disabled_at + cooldown period)

## Usage Examples

### Basic Operations

```python
from hook_state_manager import HookStateManager

# Initialize manager (uses default path)
manager = HookStateManager()

# Record successful execution
state, state_changed = manager.record_success("my_hook_command")

# Record failed execution
state, state_changed = manager.record_failure(
    "my_hook_command",
    error="Failed to spawn: No such file or directory",
    failure_threshold=3
)

# Check if circuit is open
state = manager.get_hook_state("my_hook_command")
if state.state == "open":
    print(f"Hook disabled until {state.retry_after}")

# Transition to testing mode
manager.transition_to_half_open("my_hook_command")

# Reset hook
manager.reset_hook("my_hook_command")
```

### Health Monitoring

```python
# Get health report
report = manager.get_health_report()
print(f"Total hooks: {report['total_hooks']}")
print(f"Active: {report['active_hooks']}")
print(f"Disabled: {report['disabled_hooks']}")

for hook in report['disabled_hook_details']:
    print(f"  - {hook['command']}")
    print(f"    Failures: {hook['failure_count']}")
    print(f"    Last error: {hook['last_error']}")

# Get only disabled hooks
disabled = manager.get_disabled_hooks()
for cmd, state in disabled:
    print(f"{cmd}: {state.consecutive_failures} failures")
```

### Custom State File Location

```python
from pathlib import Path

# Use custom state file path
manager = HookStateManager(
    state_file=Path("/custom/path/hook_state.json")
)
```

## Testing

Run the test suite:

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/test_state_manager.py -v

# Run specific test class
pytest tests/test_state_manager.py::TestStateInitialization -v

# Run with coverage
pytest tests/test_state_manager.py --cov=. --cov-report=html
```

## Integration with Circuit Breaker

This state manager is designed to be used by the circuit breaker wrapper:

1. **Before execution**: Check hook state to determine if execution should proceed
2. **After execution**: Record success or failure based on exit code
3. **State transitions**: Automatically manage circuit breaker state based on thresholds

See `ANTI_LOOP_GUARDRAILS.md` for complete integration documentation.

## Configuration

Default configuration values (hardcoded in state manager):

- **Failure threshold**: 3 consecutive failures to open circuit
- **Success threshold**: 2 consecutive successes to close from HALF_OPEN
- **Cooldown period**: 300 seconds (5 minutes) before testing recovery
- **State file**: `~/.claude/hook_state.json`

These will be made configurable via `~/.claude/guardrails.yaml` in Phase 2.

## Error Handling

The state manager handles various error conditions:

- **Corrupted state file**: Raises `ValueError` with descriptive message
- **Missing state file**: Automatically creates with empty state
- **Missing parent directory**: Creates parent directories as needed
- **Concurrent access**: Serializes access with file locking
- **Write failures**: Cleans up temporary files on error

## Thread Safety

The implementation is thread-safe for concurrent access:

- Multiple readers can read simultaneously (shared locks)
- Writers get exclusive locks to prevent race conditions
- Atomic writes prevent partial state corruption
- Tested with 10+ concurrent threads in unit tests

## Performance Considerations

- **Lock granularity**: Uses file-level locks (coarse-grained)
- **Lock duration**: Locks held for minimal time (read/write only)
- **File I/O**: All operations require disk I/O (acceptable for hook tracking)
- **State size**: Scales linearly with number of unique hooks

For typical usage (< 100 hooks), performance is negligible.

## Future Enhancements

Potential improvements for future versions:

1. **In-memory caching**: Cache state in memory with periodic flush
2. **Batch operations**: Support batching multiple updates
3. **State compression**: Compress old state for long-running systems
4. **State migration**: Automatic schema migration for backward compatibility
5. **Metrics export**: Export metrics to monitoring systems
6. **Configuration**: Load thresholds from config file

## License

Part of the Claude Agentic Framework - see repository root for license.
