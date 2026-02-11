# Anti-Loop Guardrails System

## Problem Statement

Claude Code hooks can create infinite loops when:
1. A hook fails with non-zero exit code
2. The error message is displayed to the agent
3. The agent responds to the error
4. The response triggers the same hook again
5. Loop repeats indefinitely

**Real example:** `validate_file_contains.py` missing → hook fails → error displayed → agent responds → hook fails again → infinite loop

## Solution Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Hook Execution Flow                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               Circuit Breaker Wrapper                        │
│  - Check failure state before execution                      │
│  - Update counters on success/failure                        │
│  - Auto-disable after threshold                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  State Manager                               │
│  - Track failures per hook command                           │
│  - Persist state to disk                                     │
│  - Provide reset/query API                                   │
└─────────────────────────────────────────────────────────────┘
```

### 1. Circuit Breaker Pattern

**States:**
- **CLOSED** (normal): Hook executes normally
- **OPEN** (disabled): Hook is disabled, returns immediate success
- **HALF_OPEN** (testing): After cooldown, try one execution to test recovery

**Transitions:**
```
CLOSED --[failure_count >= threshold]--> OPEN
OPEN --[cooldown_elapsed]--> HALF_OPEN
HALF_OPEN --[success]--> CLOSED
HALF_OPEN --[failure]--> OPEN
```

**Configuration:**
```yaml
# ~/.claude/guardrails.yaml
circuit_breaker:
  failure_threshold: 3          # Failures before opening circuit
  cooldown_seconds: 300         # Time before testing recovery (5 min)
  success_threshold: 2          # Consecutive successes to close circuit
  enabled: true                 # Global enable/disable
```

### 2. State Management

**State file:** `~/.claude/hook_state.json`

```json
{
  "hooks": {
    "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/validators/validate_file_contains.py": {
      "state": "open",
      "failure_count": 5,
      "consecutive_failures": 5,
      "consecutive_successes": 0,
      "first_failure": "2026-02-10T23:32:15Z",
      "last_failure": "2026-02-10T23:35:42Z",
      "last_success": null,
      "last_error": "Failed to spawn: No such file or directory",
      "disabled_at": "2026-02-10T23:35:42Z",
      "retry_after": "2026-02-10T23:40:42Z"
    }
  },
  "global_stats": {
    "total_executions": 1523,
    "total_failures": 12,
    "hooks_disabled": 1,
    "last_updated": "2026-02-10T23:35:42Z"
  }
}
```

**State operations:**
- `get_state(hook_cmd)` → circuit breaker state
- `record_success(hook_cmd)` → update counters, maybe close circuit
- `record_failure(hook_cmd, error)` → update counters, maybe open circuit
- `reset_hook(hook_cmd)` → clear all state for hook
- `reset_all()` → clear all state
- `get_health_report()` → summary of all hooks

### 3. Wrapper Script Architecture

**File:** `global-hooks/framework/circuit_breaker_wrapper.py`

```python
#!/usr/bin/env -S uv run --script
"""
Circuit breaker wrapper for hook commands.

Usage:
  # In settings.json, wrap any hook command:
  Before:  "uv run path/to/hook.py --args"
  After:   "uv run global-hooks/framework/circuit_breaker_wrapper.py -- uv run path/to/hook.py --args"

Features:
  - Tracks failure counts per command
  - Auto-disables after threshold failures
  - Cooldown period before retry
  - Graceful degradation (returns success when disabled)
  - Detailed logging of state transitions
"""

def main():
    # 1. Parse command from args (everything after --)
    # 2. Load state for this command
    # 3. Check circuit breaker state
    # 4. If OPEN: return success immediately (with log)
    # 5. If CLOSED or HALF_OPEN: execute command
    # 6. Record success/failure
    # 7. Update circuit breaker state
    # 8. Return result
```

### 4. Health Monitoring CLI

**Command:** `claude-hooks health`

```bash
# Show health status
claude-hooks health

# Output:
Hook Health Report
==================
Total Hooks: 45
Active: 44
Disabled: 1

DISABLED HOOKS:
  [OPEN] validate_file_contains.py
    Failures: 5 consecutive, 5 total
    Last Error: Failed to spawn: No such file or directory
    Disabled Since: 2026-02-10 23:35:42 (5 minutes ago)
    Retry After: 2026-02-10 23:40:42 (in 2 minutes)

COMMANDS:
  Reset single hook:  claude-hooks reset validate_file_contains.py
  Reset all:          claude-hooks reset --all
  Force enable:       claude-hooks enable validate_file_contains.py --force
```

### 5. Failure Detection Logic

```python
def should_execute(hook_state):
    """Determine if hook should execute based on circuit breaker state."""
    if hook_state.state == "closed":
        return True

    if hook_state.state == "open":
        # Check if cooldown elapsed
        if time_since(hook_state.disabled_at) >= COOLDOWN_SECONDS:
            # Transition to half-open
            hook_state.state = "half_open"
            return True
        return False

    if hook_state.state == "half_open":
        # In testing mode, allow execution
        return True

    return False

def record_result(hook_state, success, error=None):
    """Update state based on execution result."""
    if success:
        hook_state.consecutive_successes += 1
        hook_state.consecutive_failures = 0
        hook_state.last_success = now()

        if hook_state.state == "half_open":
            if hook_state.consecutive_successes >= SUCCESS_THRESHOLD:
                # Circuit is healthy, close it
                hook_state.state = "closed"
                hook_state.failure_count = 0
    else:
        hook_state.consecutive_failures += 1
        hook_state.consecutive_successes = 0
        hook_state.failure_count += 1
        hook_state.last_failure = now()
        hook_state.last_error = error

        if hook_state.consecutive_failures >= FAILURE_THRESHOLD:
            # Too many failures, open circuit
            hook_state.state = "open"
            hook_state.disabled_at = now()
            hook_state.retry_after = now() + COOLDOWN_SECONDS
```

## Implementation Phases

### Phase 1: State Management
- [ ] Create `hook_state_manager.py` with state CRUD operations
- [ ] Implement JSON persistence to `~/.claude/hook_state.json`
- [ ] Add state locking for concurrent access
- [ ] Write unit tests for state operations

### Phase 2: Circuit Breaker Wrapper
- [ ] Create `circuit_breaker_wrapper.py`
- [ ] Implement circuit breaker logic
- [ ] Add command parsing and execution
- [ ] Add comprehensive logging
- [ ] Test with failing hooks

### Phase 3: Health Monitoring
- [ ] Create `health_cli.py` for status reporting
- [ ] Implement reset/enable commands
- [ ] Add status line integration (optional)
- [ ] Create usage examples

### Phase 4: Integration
- [ ] Update settings.json to use wrapper
- [ ] Add configuration file support
- [ ] Write migration guide
- [ ] Test with all existing hooks

### Phase 5: Documentation
- [ ] Write setup guide
- [ ] Document configuration options
- [ ] Create troubleshooting guide
- [ ] Add examples for common scenarios

## Configuration File

**File:** `~/.claude/guardrails.yaml`

```yaml
# Anti-loop guardrails configuration
circuit_breaker:
  # Enable circuit breaker globally
  enabled: true

  # Number of consecutive failures before opening circuit
  failure_threshold: 3

  # Cooldown period (seconds) before testing recovery
  cooldown_seconds: 300  # 5 minutes

  # Consecutive successes needed to close circuit from half-open
  success_threshold: 2

  # Hooks to exclude from circuit breaker (always execute)
  exclude:
    - "damage-control/bash-tool-damage-control.py"
    - "damage-control/edit-tool-damage-control.py"

# Logging configuration
logging:
  # Log file for circuit breaker activity
  file: "~/.claude/logs/circuit_breaker.log"

  # Log level (DEBUG, INFO, WARNING, ERROR)
  level: "INFO"

  # Log format
  format: "%(asctime)s | %(levelname)s | %(hook_cmd)s | %(message)s"

# State file location
state_file: "~/.claude/hook_state.json"
```

## Safety Features

### 1. Graceful Degradation
When a circuit is OPEN, the wrapper:
- Returns exit code 0 (success)
- Outputs `{"result": "continue", "message": "Hook disabled due to repeated failures"}`
- Logs the skip event
- Does NOT block the agent

### 2. Automatic Recovery
- After cooldown, circuit automatically tries to recover
- One successful execution doesn't immediately close circuit
- Requires `SUCCESS_THRESHOLD` consecutive successes
- Prevents flaky hooks from oscillating

### 3. Manual Override
```bash
# Force enable a disabled hook (use with caution)
claude-hooks enable validate_file_contains.py --force

# Reset all failure counters (fresh start)
claude-hooks reset --all
```

### 4. Excluded Hooks
Critical safety hooks (e.g., damage-control) can be excluded from circuit breaker:
- Always execute regardless of failures
- Still logged for monitoring
- Prevents disabling critical safety checks

## Usage Examples

### Example 1: Wrap a Single Hook

**Before:**
```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/validators/validate_file_contains.py --directory specs"
      }]
    }]
  }
}
```

**After:**
```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "uv run /Users/tomkwon/Documents/claude-agentic-framework/global-hooks/framework/circuit_breaker_wrapper.py -- uv run $CLAUDE_PROJECT_DIR/.claude/hooks/validators/validate_file_contains.py --directory specs"
      }]
    }]
  }
}
```

### Example 2: Check Health Status

```bash
$ claude-hooks health

Hook Health Report
==================
Total Hooks: 45
Active: 44
Disabled: 1

DISABLED HOOKS:
  [OPEN] validate_file_contains.py
    Failures: 5 consecutive, 5 total
    Last Error: Failed to spawn: No such file or directory
    Disabled Since: 2026-02-10 23:35:42 (5 minutes ago)
    Retry After: 2026-02-10 23:40:42 (in 2 minutes)
```

### Example 3: Reset After Fixing

```bash
# Fix the hook (e.g., create missing file)
ln -s ~/Documents/claude-code-hooks-mastery/.claude/hooks/validators/validate_file_contains.py \
      ~/.claude/hooks/validators/validate_file_contains.py

# Reset the circuit breaker
claude-hooks reset validate_file_contains.py

# Verify it's enabled
claude-hooks health
```

## Benefits

1. **Prevents Infinite Loops** - Auto-disables failing hooks
2. **Self-Healing** - Automatic recovery with cooldown
3. **Visibility** - Clear health reporting
4. **Non-Blocking** - Failed hooks don't block agent
5. **Configurable** - Tunable thresholds and behavior
6. **Safe Defaults** - Conservative failure thresholds
7. **Production Ready** - Comprehensive logging and state management

## Migration Path

1. **Phase 1:** Deploy circuit breaker wrapper alongside existing hooks
2. **Phase 2:** Gradually wrap non-critical hooks
3. **Phase 3:** Monitor health dashboard, tune thresholds
4. **Phase 4:** Wrap all hooks except safety-critical ones
5. **Phase 5:** Add circuit breaker to new hooks by default

## Testing Strategy

### Unit Tests
- State manager CRUD operations
- Circuit breaker state transitions
- Failure/success counting logic
- Configuration parsing

### Integration Tests
- Full hook execution with wrapper
- State persistence across runs
- Concurrent hook executions
- Recovery from failures

### Chaos Tests
- Simulate infinite loop scenarios
- Test with missing files
- Test with permission errors
- Test with timeouts

## Future Enhancements

1. **Metrics Export** - Prometheus/StatsD integration
2. **Alerting** - Notify when hooks fail repeatedly
3. **Backoff Strategies** - Exponential backoff for cooldown
4. **Hook Dependencies** - Disable dependent hooks when parent fails
5. **Dashboard UI** - Web interface for monitoring
6. **Smart Recovery** - ML-based failure prediction
