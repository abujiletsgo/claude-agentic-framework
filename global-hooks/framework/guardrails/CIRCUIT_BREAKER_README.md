# Circuit Breaker for Claude Code Hooks

Automatic failure detection and infinite loop prevention for Claude Code hooks.

## Quick Start

### 1. Wrap a Hook

In your `settings.json`, wrap any hook command with the circuit breaker wrapper:

**Before:**
```json
{
  "hooks": {
    "Stop": [{
      "type": "command",
      "command": "uv run $CLAUDE_PROJECT_DIR/.claude/hooks/validators/validate_file.py"
    }]
  }
}
```

**After:**
```json
{
  "hooks": {
    "Stop": [{
      "type": "command",
      "command": "uv run /path/to/circuit_breaker_wrapper.py -- uv run $CLAUDE_PROJECT_DIR/.claude/hooks/validators/validate_file.py"
    }]
  }
}
```

### 2. Configure (Optional)

Create `~/.claude/guardrails.yaml`:

```yaml
circuit_breaker:
  enabled: true
  failure_threshold: 3        # Failures before opening circuit
  cooldown_seconds: 300       # 5 minutes before testing recovery
  success_threshold: 2        # Successes to close circuit
  exclude: []                 # Hooks to exclude from circuit breaker
```

### 3. Monitor

Check hook status:
```bash
# View state file
cat ~/.claude/hook_state.json

# View logs
tail -f ~/.claude/logs/circuit_breaker.log
```

## How It Works

### Circuit States

1. **CLOSED** (Normal)
   - Hook executes normally
   - Failures are counted
   - Opens after threshold failures

2. **OPEN** (Disabled)
   - Hook execution skipped
   - Returns success immediately (graceful degradation)
   - Waits for cooldown period

3. **HALF_OPEN** (Testing)
   - After cooldown, attempts recovery
   - Executes hook as test
   - Success closes circuit, failure reopens

### State Transitions

```
CLOSED --[3 failures]--> OPEN
OPEN --[5 min cooldown]--> HALF_OPEN
HALF_OPEN --[2 successes]--> CLOSED
HALF_OPEN --[1 failure]--> OPEN
```

## Features

- **Automatic Failure Detection**: Tracks consecutive failures per hook
- **Threshold-Based Opening**: Circuit opens after configurable failures (default: 3)
- **Cooldown Period**: Waits before testing recovery (default: 5 minutes)
- **Recovery Testing**: Gradual recovery via half-open state
- **Graceful Degradation**: Returns success when circuit open (doesn't block agent)
- **Independent State**: Each hook has its own circuit breaker
- **Hook Exclusion**: Critical hooks can be excluded
- **Comprehensive Logging**: All state changes logged

## Usage Examples

### Example 1: Basic Hook Wrapping

```bash
# Wrap a Python validator
uv run circuit_breaker_wrapper.py -- uv run hooks/validate.py --file test.py

# Wrap a bash script
uv run circuit_breaker_wrapper.py -- bash -c "test -f file.txt"

# Wrap any command
uv run circuit_breaker_wrapper.py -- python check.py --strict
```

### Example 2: Programmatic Usage

```python
from circuit_breaker import CircuitBreaker
from hook_state_manager import HookStateManager
from config_loader import load_config

# Initialize
config = load_config()
manager = HookStateManager(config.get_state_file_path())
breaker = CircuitBreaker(manager, config)

hook_cmd = "uv run hooks/validator.py"

# Check if should execute
result = breaker.should_execute(hook_cmd)
if not result.should_execute:
    print(f"Skipping: {result.message}")
    sys.exit(0)

# Execute hook
try:
    subprocess.run(hook_cmd.split(), check=True)
    breaker.record_success(hook_cmd)
except subprocess.CalledProcessError as e:
    breaker.record_failure(hook_cmd, str(e))
    sys.exit(1)
```

### Example 3: Configuration

```yaml
# ~/.claude/guardrails.yaml

circuit_breaker:
  # Enable/disable globally
  enabled: true

  # Open circuit after 5 failures (instead of default 3)
  failure_threshold: 5

  # Wait 10 minutes before testing recovery (instead of 5)
  cooldown_seconds: 600

  # Require 3 successes to close (instead of 2)
  success_threshold: 3

  # Exclude critical hooks from circuit breaker
  exclude:
    - "damage-control"
    - "safety-checks"

logging:
  file: "~/.claude/logs/circuit_breaker.log"
  level: "INFO"
```

### Example 4: Environment Variable Overrides

```bash
# Override failure threshold
export GUARDRAILS_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5

# Override cooldown period
export GUARDRAILS_CIRCUIT_BREAKER_COOLDOWN_SECONDS=600

# Disable circuit breaker
export GUARDRAILS_CIRCUIT_BREAKER_ENABLED=false

# Run hook
uv run circuit_breaker_wrapper.py -- uv run hooks/validator.py
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `enabled` | `true` | Enable circuit breaker globally |
| `failure_threshold` | `3` | Consecutive failures before opening |
| `cooldown_seconds` | `300` | Wait time before testing recovery |
| `success_threshold` | `2` | Consecutive successes to close |
| `exclude` | `[]` | Hook patterns to exclude |

See [CONFIG.md](CONFIG.md) for complete configuration documentation.

## State File

The circuit breaker stores state in `~/.claude/hook_state.json`:

```json
{
  "hooks": {
    "uv run hooks/validator.py": {
      "state": "open",
      "failure_count": 5,
      "consecutive_failures": 5,
      "consecutive_successes": 0,
      "first_failure": "2026-02-10T23:32:15Z",
      "last_failure": "2026-02-10T23:35:42Z",
      "last_success": null,
      "last_error": "Failed to spawn: No such file",
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

## Logging

All circuit breaker activity is logged to `~/.claude/logs/circuit_breaker.log`:

```
2026-02-10 23:35:32 | INFO | test_hook | Circuit closed, executing normally
2026-02-10 23:35:33 | DEBUG | test_hook | Failure recorded (consecutive: 1/3). Error: test error
2026-02-10 23:35:34 | DEBUG | test_hook | Failure recorded (consecutive: 2/3). Error: test error
2026-02-10 23:35:35 | WARNING | test_hook | Circuit opened after 3 failures. Hook disabled for 300s. Last error: test error
2026-02-10 23:35:36 | DEBUG | test_hook | Circuit open, hook disabled until 2026-02-10 23:40:35 UTC
2026-02-10 23:40:36 | INFO | test_hook | Cooldown elapsed, transitioning to HALF_OPEN for recovery test
2026-02-10 23:40:37 | INFO | test_hook | Circuit half-open, testing recovery
2026-02-10 23:40:38 | DEBUG | test_hook | Success recorded (consecutive: 1)
2026-02-10 23:40:39 | INFO | test_hook | Circuit closed after 2 successes
```

## Troubleshooting

### Circuit opened unexpectedly

Check the log file to see what errors caused failures:
```bash
tail -100 ~/.claude/logs/circuit_breaker.log | grep "error"
```

Fix the underlying issue, then the circuit will automatically recover after cooldown.

### Hook still disabled after fixing issue

The circuit needs to test recovery. Wait for the cooldown period, or manually reset:
```bash
# View state
cat ~/.claude/hook_state.json

# Delete state to force reset (temporary - CLI tool coming soon)
rm ~/.claude/hook_state.json
```

### Circuit not working

1. Check that circuit breaker is enabled:
   ```bash
   cat ~/.claude/guardrails.yaml | grep enabled
   ```

2. Check logs for errors:
   ```bash
   tail -50 ~/.claude/logs/circuit_breaker.log
   ```

3. Verify wrapper is being used:
   ```bash
   cat settings.json | grep circuit_breaker_wrapper
   ```

### Exclude a hook from circuit breaker

Add to configuration:
```yaml
circuit_breaker:
  exclude:
    - "path/to/critical/hook"
```

Or use environment variable:
```bash
# Note: Not supported yet, will be in future version
```

## Best Practices

### When to Use

- **Wrap all validators**: Prevent validator failures from blocking work
- **Wrap external tools**: Network calls, API checks, etc.
- **Wrap flaky hooks**: Hooks with intermittent failures

### When NOT to Use

- **Critical safety hooks**: Use exclusion list instead
- **Hooks that must always run**: Use exclusion list
- **Fast, reliable hooks**: Overhead may not be worth it (though it's minimal)

### Tuning Guidelines

**For flaky hooks** (intermittent failures):
```yaml
circuit_breaker:
  failure_threshold: 5-10      # More tolerant
  success_threshold: 3-5       # Require proof of stability
```

**For stable hooks** (rarely fail):
```yaml
circuit_breaker:
  failure_threshold: 3         # Default is fine
  success_threshold: 2         # Default is fine
```

**For fast recovery**:
```yaml
circuit_breaker:
  cooldown_seconds: 60-120     # 1-2 minutes
  success_threshold: 2         # Default
```

**For conservative recovery**:
```yaml
circuit_breaker:
  cooldown_seconds: 600-1800   # 10-30 minutes
  success_threshold: 3-5       # Require more proof
```

## Examples

See [examples/circuit_breaker_example.py](examples/circuit_breaker_example.py) for a complete demonstration.

Run the example:
```bash
cd guardrails
python examples/circuit_breaker_example.py
```

## Architecture

The circuit breaker consists of three main components:

1. **circuit_breaker.py**: Core state machine logic
2. **circuit_breaker_wrapper.py**: CLI wrapper for hook execution
3. **hook_state_manager.py**: Persistent state management

See [TASK_3_COMPLETION.md](TASK_3_COMPLETION.md) for detailed implementation documentation.

## Testing

Run the test suite:
```bash
cd guardrails
pytest tests/test_circuit_breaker.py -v
```

## Further Reading

- [CONFIG.md](CONFIG.md) - Complete configuration reference
- [TASK_3_COMPLETION.md](TASK_3_COMPLETION.md) - Implementation details
- [ANTI_LOOP_GUARDRAILS.md](../ANTI_LOOP_GUARDRAILS.md) - Architecture design
