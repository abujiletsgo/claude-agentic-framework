# Guardrails Configuration Documentation

Complete guide to configuring the anti-loop guardrails system.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Configuration File](#configuration-file)
3. [Configuration Options](#configuration-options)
4. [Environment Variables](#environment-variables)
5. [Configuration Priority](#configuration-priority)
6. [Validation](#validation)
7. [Tuning Guidelines](#tuning-guidelines)
8. [Examples](#examples)
9. [Troubleshooting](#troubleshooting)

## Quick Start

### Create Default Configuration

```bash
# Create configuration file with safe defaults
python -m guardrails.config_loader --create-default

# This creates: ~/.claude/guardrails.yaml
```

### Validate Configuration

```bash
# Validate your configuration
python -m guardrails.config_loader --validate

# Dump loaded configuration (merged from all sources)
python -m guardrails.config_loader --dump
```

### Use in Python

```python
from guardrails.config_loader import load_config

# Load configuration (auto-merges defaults + file + env)
config = load_config()

# Access configuration values
if config.circuit_breaker.enabled:
    threshold = config.circuit_breaker.failure_threshold
    cooldown = config.circuit_breaker.cooldown_seconds
```

## Configuration File

**Default location:** `~/.claude/guardrails.yaml`

**Format:** YAML

**Structure:**
```yaml
circuit_breaker:
  enabled: true
  failure_threshold: 3
  cooldown_seconds: 300
  success_threshold: 2
  exclude: []

logging:
  file: "~/.claude/logs/circuit_breaker.log"
  level: "INFO"
  format: "%(asctime)s | %(levelname)s | %(hook_cmd)s | %(message)s"

state_file: "~/.claude/hook_state.json"
```

## Configuration Options

### Circuit Breaker Section

#### `circuit_breaker.enabled`
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable or disable circuit breaker globally
- **When to change:** Set to `false` to completely disable circuit breaker (not recommended)

#### `circuit_breaker.failure_threshold`
- **Type:** Integer
- **Range:** 1-100
- **Default:** `3`
- **Description:** Number of consecutive failures before opening circuit (disabling hook)
- **When to change:**
  - Increase (5-10) for flaky hooks with intermittent failures
  - Decrease (1-2) for strict failure handling
  - Set high (50-100) for hooks that should rarely be disabled

#### `circuit_breaker.cooldown_seconds`
- **Type:** Integer
- **Range:** 0-86400 (0 to 24 hours)
- **Default:** `300` (5 minutes)
- **Description:** Time to wait after disabling a hook before testing recovery
- **When to change:**
  - Decrease (60-120) for fast recovery attempts
  - Increase (600-1800) for conservative recovery (gives more time to fix issues)
  - Set to 0 for immediate retry (not recommended)

#### `circuit_breaker.success_threshold`
- **Type:** Integer
- **Range:** 1-100
- **Default:** `2`
- **Description:** Consecutive successes needed to re-enable a hook after recovery
- **When to change:**
  - Increase (3-5) to require more evidence of stability before re-enabling
  - Decrease (1) for faster re-enabling (may cause oscillation)

#### `circuit_breaker.exclude`
- **Type:** List of strings
- **Default:** `[]` (empty list)
- **Description:** Hook commands or patterns to exclude from circuit breaker
- **Format:** List of hook script names or full command patterns
- **Example:**
  ```yaml
  exclude:
    - "damage-control/bash-tool-damage-control.py"
    - "damage-control/edit-tool-damage-control.py"
    - "validators/critical_check.py"
  ```
- **When to use:**
  - Critical safety hooks that should never be disabled
  - Hooks with acceptable failure rates
  - Hooks that handle their own retry logic

### Logging Section

#### `logging.file`
- **Type:** String (file path)
- **Default:** `~/.claude/logs/circuit_breaker.log`
- **Description:** Path to log file for circuit breaker activity
- **Supports:** `~` expansion and environment variables (`$HOME`, etc.)
- **Example:**
  ```yaml
  file: "$HOME/.claude/logs/guardrails.log"
  file: "/var/log/claude/circuit_breaker.log"
  ```

#### `logging.level`
- **Type:** String (enum)
- **Valid values:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Default:** `INFO`
- **Description:** Minimum log level to record
- **Levels:**
  - `DEBUG`: Detailed information for debugging (very verbose)
  - `INFO`: General informational messages (recommended)
  - `WARNING`: Warning messages only
  - `ERROR`: Error messages only
  - `CRITICAL`: Critical errors only
- **When to change:**
  - Set to `DEBUG` when troubleshooting issues
  - Set to `WARNING` or `ERROR` to reduce log verbosity in production

#### `logging.format`
- **Type:** String (Python logging format)
- **Default:** `"%(asctime)s | %(levelname)s | %(hook_cmd)s | %(message)s"`
- **Description:** Format string for log messages
- **Available fields:**
  - `%(asctime)s`: Timestamp
  - `%(levelname)s`: Log level (INFO, ERROR, etc.)
  - `%(hook_cmd)s`: Hook command (custom field)
  - `%(message)s`: Log message
  - `%(name)s`: Logger name
  - `%(funcName)s`: Function name
  - `%(lineno)d`: Line number
- **Example:**
  ```yaml
  format: "[%(asctime)s] %(levelname)s: %(message)s"
  format: "%(asctime)s | %(hook_cmd)s | %(message)s"
  ```

### State File

#### `state_file`
- **Type:** String (file path)
- **Default:** `~/.claude/hook_state.json`
- **Description:** Path to JSON file storing circuit breaker state
- **Supports:** `~` expansion and environment variables
- **Example:**
  ```yaml
  state_file: "$HOME/.claude/state/hooks.json"
  state_file: "/tmp/hook_state.json"
  ```

## Environment Variables

All configuration options can be overridden using environment variables.

### Format

```
GUARDRAILS_<SECTION>_<KEY>=<VALUE>
```

### Type Conversion

- **Boolean:** `true`/`false`, `yes`/`no`, `1`/`0`, `on`/`off` (case-insensitive)
- **Integer:** Numeric strings (e.g., `"5"`, `"600"`)
- **String:** Any other value

### Examples

```bash
# Disable circuit breaker
export GUARDRAILS_CIRCUIT_BREAKER_ENABLED=false

# Change failure threshold
export GUARDRAILS_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5

# Change cooldown period
export GUARDRAILS_CIRCUIT_BREAKER_COOLDOWN_SECONDS=600

# Change log level
export GUARDRAILS_LOGGING_LEVEL=DEBUG

# Change state file location
export GUARDRAILS_STATE_FILE=/tmp/hook_state.json
```

### Use Cases

- **CI/CD environments:** Set different thresholds for automated testing
- **Development:** Enable DEBUG logging temporarily
- **Production:** Override file paths for custom deployment
- **Emergency:** Quickly disable circuit breaker without editing files

## Configuration Priority

Configuration is merged in the following order (highest priority first):

1. **Environment variables** (highest priority)
2. **Configuration file** (`~/.claude/guardrails.yaml`)
3. **Built-in defaults** (lowest priority)

### Merging Behavior

- Environment variables override specific keys
- Configuration file overrides defaults
- Missing values use defaults
- Nested objects are merged (not replaced)

### Example

**Built-in defaults:**
```yaml
circuit_breaker:
  failure_threshold: 3
  cooldown_seconds: 300
```

**Configuration file (`~/.claude/guardrails.yaml`):**
```yaml
circuit_breaker:
  failure_threshold: 5
```

**Environment variables:**
```bash
export GUARDRAILS_CIRCUIT_BREAKER_COOLDOWN_SECONDS=600
```

**Resulting configuration:**
```yaml
circuit_breaker:
  failure_threshold: 5      # From file
  cooldown_seconds: 600     # From environment
  success_threshold: 2      # From defaults
  enabled: true             # From defaults
```

## Validation

The configuration system validates all values on load.

### Validation Rules

- **Type checking:** Values must match expected types
- **Range checking:** Numeric values must be within valid ranges
- **Enum checking:** String values must be from allowed set
- **Required fields:** All required fields must be present

### Error Messages

Invalid configuration produces helpful error messages:

```
Configuration validation error:
  circuit_breaker.failure_threshold: Input should be less than or equal to 100
  logging.level: Invalid log level: TRACE. Must be one of {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
```

### Manual Validation

```bash
# Validate configuration file
python -m guardrails.config_loader --validate

# Output on success:
# Configuration is valid!

# Output on error:
# Configuration validation error:
#   circuit_breaker.failure_threshold: Input should be less than or equal to 100
```

## Tuning Guidelines

### For Flaky Hooks (Intermittent Failures)

Increase tolerance for transient failures:

```yaml
circuit_breaker:
  failure_threshold: 10      # More failures allowed
  success_threshold: 5       # Require more successes
  cooldown_seconds: 300      # Standard cooldown
```

### For Stable Hooks (Rarely Fail)

Keep defaults for quick response to real failures:

```yaml
circuit_breaker:
  failure_threshold: 3       # Default
  success_threshold: 2       # Default
  cooldown_seconds: 300      # Default
```

### For Critical Hooks (Must Stay Enabled)

Use exclusion list:

```yaml
circuit_breaker:
  exclude:
    - "damage-control/bash-tool-damage-control.py"
    - "damage-control/edit-tool-damage-control.py"
```

Or set very high threshold:

```yaml
circuit_breaker:
  failure_threshold: 100     # Effectively never disable
```

### For Fast Recovery

Reduce cooldown and success requirements:

```yaml
circuit_breaker:
  failure_threshold: 3       # Standard
  success_threshold: 1       # Quick re-enable (may oscillate)
  cooldown_seconds: 60       # 1 minute cooldown
```

### For Conservative Recovery

Increase cooldown and success requirements:

```yaml
circuit_breaker:
  failure_threshold: 3       # Standard
  success_threshold: 5       # Require proof of stability
  cooldown_seconds: 1800     # 30 minute cooldown
```

### For Development/Testing

Enable verbose logging:

```yaml
logging:
  level: DEBUG
  file: "~/.claude/logs/circuit_breaker_debug.log"
```

### For Production

Use INFO logging and standard settings:

```yaml
circuit_breaker:
  failure_threshold: 3
  success_threshold: 2
  cooldown_seconds: 300

logging:
  level: INFO
  file: "/var/log/claude/circuit_breaker.log"
```

## Examples

### Example 1: Development Configuration

**File:** `~/.claude/guardrails.yaml`

```yaml
circuit_breaker:
  enabled: true
  failure_threshold: 5       # More tolerant for dev
  cooldown_seconds: 120      # Faster recovery
  success_threshold: 2
  exclude: []

logging:
  file: "~/.claude/logs/circuit_breaker_dev.log"
  level: "DEBUG"             # Verbose logging
  format: "%(asctime)s | %(levelname)s | %(hook_cmd)s | %(message)s"

state_file: "~/.claude/hook_state_dev.json"
```

### Example 2: Production Configuration

**File:** `~/.claude/guardrails.yaml`

```yaml
circuit_breaker:
  enabled: true
  failure_threshold: 3       # Conservative
  cooldown_seconds: 600      # 10 minute cooldown
  success_threshold: 3       # Require proof of stability
  exclude:
    - "damage-control/bash-tool-damage-control.py"
    - "damage-control/edit-tool-damage-control.py"

logging:
  file: "/var/log/claude/circuit_breaker.log"
  level: "INFO"              # Standard logging
  format: "%(asctime)s | %(levelname)s | %(hook_cmd)s | %(message)s"

state_file: "/var/lib/claude/hook_state.json"
```

### Example 3: CI/CD Configuration

Use environment variables for dynamic configuration:

```bash
#!/bin/bash
# CI/CD script

# Disable circuit breaker in tests (we want to see all failures)
export GUARDRAILS_CIRCUIT_BREAKER_ENABLED=false

# Or use strict settings
export GUARDRAILS_CIRCUIT_BREAKER_FAILURE_THRESHOLD=1
export GUARDRAILS_CIRCUIT_BREAKER_COOLDOWN_SECONDS=0

# Enable debug logging
export GUARDRAILS_LOGGING_LEVEL=DEBUG

# Use temporary state file
export GUARDRAILS_STATE_FILE=/tmp/ci_hook_state.json

# Run tests
pytest tests/
```

### Example 4: Emergency Override

Quickly disable circuit breaker without editing files:

```bash
# Temporarily disable circuit breaker
export GUARDRAILS_CIRCUIT_BREAKER_ENABLED=false

# Run Claude with circuit breaker disabled
claude-code

# Unset to restore normal behavior
unset GUARDRAILS_CIRCUIT_BREAKER_ENABLED
```

## Troubleshooting

### Problem: Configuration Not Loading

**Symptoms:** Changes to config file have no effect

**Solutions:**
1. Check file location: `~/.claude/guardrails.yaml`
2. Validate YAML syntax: `python -m guardrails.config_loader --validate`
3. Check environment variables: `env | grep GUARDRAILS`
4. Dump effective config: `python -m guardrails.config_loader --dump`

### Problem: Invalid Configuration Error

**Symptoms:** Error message on startup

**Solutions:**
1. Check error message for specific field
2. Verify value types (boolean, integer, string)
3. Verify value ranges (e.g., failure_threshold must be 1-100)
4. Check enum values (e.g., log level must be DEBUG/INFO/WARNING/ERROR/CRITICAL)

### Problem: Environment Variables Not Working

**Symptoms:** Environment variables don't override config

**Solutions:**
1. Check variable name format: `GUARDRAILS_CIRCUIT_BREAKER_ENABLED`
2. Check value format: `true` not `True` or `TRUE` (case-insensitive)
3. Verify variable is exported: `export GUARDRAILS_CIRCUIT_BREAKER_ENABLED=true`
4. Check variable is set: `echo $GUARDRAILS_CIRCUIT_BREAKER_ENABLED`

### Problem: Wrong Values After Merge

**Symptoms:** Configuration values not as expected

**Solutions:**
1. Dump effective configuration: `python -m guardrails.config_loader --dump`
2. Check priority: Environment > File > Defaults
3. Verify file syntax is correct
4. Check for typos in keys

### Problem: Missing Configuration File

**Symptoms:** File not found warnings

**Solutions:**
1. Create default config: `python -m guardrails.config_loader --create-default`
2. Or ignore warnings - system will use built-in defaults
3. Check path expansion: `~/.claude/guardrails.yaml` expands correctly

### Problem: Permission Errors

**Symptoms:** Cannot read/write config or state files

**Solutions:**
1. Check file permissions: `ls -la ~/.claude/`
2. Ensure directory exists: `mkdir -p ~/.claude/logs`
3. Check file ownership
4. Use custom paths if needed: `export GUARDRAILS_STATE_FILE=/tmp/state.json`

## Python API Reference

### Loading Configuration

```python
from guardrails.config_loader import load_config, ConfigLoader

# Load with defaults
config = load_config()

# Load from custom path
config = load_config(Path("/custom/path/guardrails.yaml"))

# Using ConfigLoader directly
loader = ConfigLoader(Path("/custom/path/guardrails.yaml"))
config = loader.load()
```

### Creating Default Config

```python
from guardrails.config_loader import create_default_config_file
from pathlib import Path

# Create at default location
create_default_config_file()

# Create at custom location
create_default_config_file(Path("/custom/path/guardrails.yaml"))
```

### Accessing Configuration

```python
config = load_config()

# Circuit breaker settings
if config.circuit_breaker.enabled:
    threshold = config.circuit_breaker.failure_threshold
    cooldown = config.circuit_breaker.cooldown_seconds
    success_threshold = config.circuit_breaker.success_threshold
    exclude_list = config.circuit_breaker.exclude

# Logging settings
log_file = config.logging.file
log_level = config.logging.level
log_format = config.logging.format

# State file
state_file = config.state_file

# Get paths as Path objects
state_path = config.get_state_file_path()
log_path = config.get_log_file_path()
```

### Validation

```python
from pydantic import ValidationError
from guardrails.config_loader import load_config

try:
    config = load_config()
except ValidationError as e:
    for error in e.errors():
        loc = ".".join(str(x) for x in error["loc"])
        msg = error["msg"]
        print(f"{loc}: {msg}")
```

## Best Practices

1. **Start with defaults:** Use safe defaults and tune as needed
2. **Use version control:** Track config file changes in git
3. **Document changes:** Add comments explaining non-standard values
4. **Test changes:** Validate config after changes
5. **Monitor logs:** Watch circuit breaker activity in logs
6. **Review periodically:** Check if thresholds still make sense
7. **Use exclusions carefully:** Only exclude truly critical hooks
8. **Environment for overrides:** Use env vars for temporary changes
9. **Backup state file:** Preserve circuit breaker state across resets
10. **Update gradually:** Change one setting at a time and observe

## See Also

- [Anti-Loop Guardrails System](ANTI_LOOP_GUARDRAILS.md) - Architecture overview
- [State Manager](state_manager.md) - State persistence documentation
- [Circuit Breaker](circuit_breaker.md) - Circuit breaker implementation
- [CLI Tool](cli_tool.md) - Health monitoring and management commands
