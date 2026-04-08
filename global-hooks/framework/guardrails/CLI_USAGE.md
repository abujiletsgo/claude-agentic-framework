# CLI Usage Guide - claude-hooks

The `claude-hooks` command-line tool provides health monitoring and management capabilities for the circuit breaker system.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands](#commands)
  - [health](#health---show-hook-health-status)
  - [list](#list---list-all-tracked-hooks)
  - [reset](#reset---reset-hook-state)
  - [enable](#enable---enable-disabled-hook)
  - [disable](#disable---manually-disable-hook)
  - [config](#config---show-configuration)
- [Global Options](#global-options)
- [Output Formats](#output-formats)
- [Common Workflows](#common-workflows)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## Installation

### 1. Create Symlink

```bash
# Make CLI script executable
chmod +x ~/Documents/claude-agentic-framework/global-hooks/framework/guardrails/claude_hooks_cli.py

# Create symlink in ~/.local/bin
mkdir -p ~/.local/bin
ln -sf ~/Documents/claude-agentic-framework/global-hooks/framework/guardrails/claude_hooks_cli.py \
       ~/.local/bin/claude-hooks
```

### 2. Add to PATH

Ensure `~/.local/bin` is in your PATH:

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"

# Reload shell
source ~/.bashrc  # or source ~/.zshrc
```

### 3. Verify Installation

```bash
claude-hooks --help
```

---

## Quick Start

```bash
# Check health status of all hooks
claude-hooks health

# List all tracked hooks
claude-hooks list

# Reset a specific hook
claude-hooks reset validate_file

# Reset all hooks
claude-hooks reset --all

# Enable a disabled hook
claude-hooks enable validate_file

# View current configuration
claude-hooks config
```

---

## Commands

### health - Show Hook Health Status

Display comprehensive health report for all hooks.

**Usage:**
```bash
claude-hooks health [--json]
```

**Output includes:**
- Total hook count
- Active vs disabled hooks
- Global statistics (total executions, failures, failure rate)
- Detailed information about disabled hooks:
  - Failure counts
  - Last error message
  - Time since disabled
  - Time until retry

**Examples:**
```bash
# Show health status (formatted output)
claude-hooks health

# Output as JSON
claude-hooks health --json

# Disable colors
claude-hooks health --no-color
```

**Sample Output:**
```
Hook Health Report
============================================================
Total Hooks: 45
Active: 44
Disabled: 1

Global Statistics
Total Executions: 1523
Total Failures: 12
Failure Rate: 0.79%
Last Updated: 5 minutes ago

DISABLED HOOKS:

  [OPEN] validate_file_contains.py
    Full Command: uv run $CLAUDE_PROJECT_DIR/.claude/hooks/validators/validate_file_contains.py
    Failures: 5 consecutive, 5 total
    Last Error: Failed to spawn: No such file or directory
    Disabled Since: 5 minutes ago
    Retry After: in 2 minutes

COMMANDS:
  Reset single hook:  claude-hooks reset validate_file
  Reset all:          claude-hooks reset --all
  Enable hook:        claude-hooks enable validate_file
  Show all hooks:     claude-hooks list
```

---

### list - List All Tracked Hooks

Display all hooks currently tracked by the circuit breaker system.

**Usage:**
```bash
claude-hooks list [--json]
```

**Output includes:**
- Hook command
- Circuit breaker state (CLOSED, OPEN, HALF-OPEN)
- Failure counts
- Success counts
- Last success/failure timestamps

**Examples:**
```bash
# List all hooks (formatted output)
claude-hooks list

# Output as JSON
claude-hooks list --json
```

**Sample Output:**
```
All Tracked Hooks (3)
================================================================================

[OPEN] validate_file_contains.py
  Full: uv run ~/.claude/hooks/validators/validate_file_contains.py
  Failures: 5 total, 5 consecutive
  Successes: 0 consecutive
  Last Failure: 2 minutes ago

[CLOSED] check_lthread_progress.py
  Full: uv run ~/.claude/hooks/validators/check_lthread_progress.py
  Failures: 0 total, 0 consecutive
  Successes: 3 consecutive
  Last Success: 30 seconds ago

[CLOSED] bash_tool_damage_control.py
  Full: uv run ~/.claude/hooks/damage-control/bash_tool_damage_control.py
  Failures: 1 total, 0 consecutive
  Successes: 10 consecutive
  Last Success: 1 minute ago
  Last Failure: 1 hour ago
```

---

### reset - Reset Hook State

Reset the state of specific hook(s) or all hooks. This clears failure counters and re-enables disabled hooks.

**Usage:**
```bash
# Reset specific hook (pattern matching)
claude-hooks reset <hook_pattern>

# Reset all hooks
claude-hooks reset --all
```

**Parameters:**
- `hook_pattern`: String to match against hook commands (partial match supported)
- `--all`: Reset all tracked hooks

**Examples:**
```bash
# Reset specific hook by name
claude-hooks reset validate_file_contains.py

# Reset using partial match
claude-hooks reset validate_file

# Reset all hooks
claude-hooks reset --all
```

**Behavior:**
- If pattern matches one hook: resets that hook
- If pattern matches multiple hooks: shows error and lists matches
- If pattern matches no hooks: shows error and lists available hooks
- With `--all`: resets all hooks without confirmation

**Sample Output:**
```bash
$ claude-hooks reset validate_file
Successfully reset hook:
  validate_file_contains.py
```

---

### enable - Enable Disabled Hook

Enable a disabled hook by resetting its state. Alias for `reset` with additional safety checks.

**Usage:**
```bash
claude-hooks enable <hook_pattern> [--force]
```

**Parameters:**
- `hook_pattern`: String to match against hook commands
- `--force`: Enable even if not disabled (skip state check)

**Examples:**
```bash
# Enable a disabled hook
claude-hooks enable validate_file

# Force enable (even if not disabled)
claude-hooks enable validate_file --force
```

**Behavior:**
- Checks if hook is actually disabled (state == OPEN)
- Without `--force`: refuses to enable non-disabled hooks
- With `--force`: resets hook regardless of state

**Sample Output:**
```bash
$ claude-hooks enable validate_file
Successfully enabled hook:
  validate_file_contains.py

$ claude-hooks enable active_hook
Hook is not disabled (state: closed).
Use --force to reset anyway.
```

---

### disable - Manually Disable Hook

Manually disable a hook by opening its circuit. Useful for temporarily disabling problematic hooks.

**Usage:**
```bash
claude-hooks disable <hook_pattern>
```

**Parameters:**
- `hook_pattern`: String to match against hook commands

**Examples:**
```bash
# Disable a specific hook
claude-hooks disable validate_file

# Shows enable command for later
claude-hooks disable validate_file
```

**Behavior:**
- Records enough failures to open the circuit
- Hook will not execute until enabled again
- Shows command to re-enable the hook

**Sample Output:**
```bash
$ claude-hooks disable validate_file
Successfully disabled hook:
  validate_file_contains.py

To re-enable: claude-hooks enable validate_file
```

---

### config - Show Configuration

Display the current guardrails configuration.

**Usage:**
```bash
claude-hooks config [--json]
```

**Output includes:**
- Circuit breaker settings
  - Enabled status
  - Failure threshold
  - Cooldown period
  - Success threshold
  - Excluded hooks
- Logging settings
  - Log file path
  - Log level
- State file location

**Examples:**
```bash
# Show configuration (formatted output)
claude-hooks config

# Output as JSON
claude-hooks config --json
```

**Sample Output:**
```
Guardrails Configuration
============================================================

Circuit Breaker
  Enabled: True
  Failure Threshold: 3
  Cooldown: 300 seconds
  Success Threshold: 2
  Excluded Hooks:
    - damage-control/bash-tool-damage-control.py
    - damage-control/edit-tool-damage-control.py

Logging
  File: ~/.claude/logs/circuit_breaker.log
  Level: INFO

State
  State File: ~/.claude/hook_state.json
```

---

## Global Options

These options apply to all commands:

### --config

Specify custom configuration file path.

```bash
claude-hooks --config /path/to/guardrails.yaml health
```

**Default:** `~/.claude/guardrails.yaml`

### --state-file

Specify custom state file path.

```bash
claude-hooks --state-file /path/to/hook_state.json health
```

**Default:** `~/.claude/hook_state.json`

### --json

Output in JSON format instead of formatted text. Useful for scripting and integration.

```bash
claude-hooks health --json | jq '.disabled_hooks'
```

### --no-color

Disable colored output. Automatically disabled when output is not a terminal (pipe/redirect).

```bash
claude-hooks health --no-color > report.txt
```

---

## Output Formats

### Text Format (Default)

Human-readable formatted output with:
- Colors (green=healthy, red=disabled, yellow=warning)
- Tables and sections
- Human-readable timestamps ("5 minutes ago")
- Truncated long commands for readability

Best for: Interactive terminal use

### JSON Format (--json)

Machine-readable JSON output with:
- Complete data without truncation
- ISO 8601 timestamps
- Structured nested objects
- All fields preserved

Best for: Scripts, automation, integration with other tools

**Example:**
```bash
# Get disabled hook count
claude-hooks health --json | jq '.disabled_hooks'

# Get all hook commands
claude-hooks list --json | jq '.[].command'

# Check if specific hook is disabled
claude-hooks list --json | jq '.[] | select(.command | contains("validate_file")) | .state'
```

---

## Common Workflows

### Workflow 1: Investigate Failures

```bash
# 1. Check overall health
claude-hooks health

# 2. List all hooks to see details
claude-hooks list

# 3. View configuration
claude-hooks config

# 4. Check circuit breaker logs
tail -f ~/.claude/logs/circuit_breaker.log
```

### Workflow 2: Fix and Reset a Failing Hook

```bash
# 1. Identify the failing hook
claude-hooks health

# 2. Fix the underlying issue
# (e.g., create missing file, fix permissions, etc.)

# 3. Reset the hook state
claude-hooks reset validate_file

# 4. Verify it's working
claude-hooks health
```

### Workflow 3: Temporarily Disable a Hook

```bash
# 1. Disable the hook
claude-hooks disable problematic_hook

# 2. Work without the hook
# ...

# 3. Re-enable when ready
claude-hooks enable problematic_hook
```

### Workflow 4: Clean Slate

```bash
# Reset all hooks to start fresh
claude-hooks reset --all

# Verify all are cleared
claude-hooks health
```

### Workflow 5: Scripted Monitoring

```bash
#!/bin/bash
# Check if any hooks are disabled and alert

disabled_count=$(claude-hooks health --json | jq '.disabled_hooks')

if [ "$disabled_count" -gt 0 ]; then
    echo "WARNING: $disabled_count hook(s) disabled!"
    claude-hooks health
    # Send alert, notification, etc.
fi
```

---

## Examples

### Example 1: Daily Health Check

```bash
# Show health status with colors
claude-hooks health
```

### Example 2: Reset After Fixing a Hook

```bash
# You fixed the missing file
ln -s ~/correct/path/validate_file_contains.py ~/.claude/hooks/validators/

# Reset the hook
claude-hooks reset validate_file

# Verify it's enabled
claude-hooks health
```

### Example 3: Export State for Analysis

```bash
# Export all hook data as JSON
claude-hooks list --json > hook_state_backup.json

# Export health report
claude-hooks health --json > health_report.json

# Analyze with jq
cat health_report.json | jq '.global_stats'
```

### Example 4: Find Hooks Matching Pattern

```bash
# List all validator hooks
claude-hooks list | grep validator

# Or with JSON
claude-hooks list --json | jq '.[] | select(.command | contains("validator"))'
```

### Example 5: Integration with Monitoring System

```bash
#!/bin/bash
# Send metrics to monitoring system

health_data=$(claude-hooks health --json)

total_hooks=$(echo "$health_data" | jq '.total_hooks')
disabled_hooks=$(echo "$health_data" | jq '.disabled_hooks')
failure_rate=$(echo "$health_data" | jq '.global_stats.total_failures / .global_stats.total_executions * 100')

# Send to your monitoring system
curl -X POST https://monitoring.example.com/metrics \
  -d "hooks.total=$total_hooks" \
  -d "hooks.disabled=$disabled_hooks" \
  -d "hooks.failure_rate=$failure_rate"
```

---

## Troubleshooting

### Command Not Found

**Problem:** `claude-hooks: command not found`

**Solution:**
```bash
# Ensure symlink exists
ls -la ~/.local/bin/claude-hooks

# Ensure ~/.local/bin is in PATH
echo $PATH | grep .local/bin

# Add to PATH if missing
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### State File Not Found

**Problem:** `Error initializing state manager: No such file or directory`

**Solution:**
```bash
# State file is created automatically on first use
# Ensure parent directory exists
mkdir -p ~/.claude

# Or specify custom location
claude-hooks --state-file /path/to/state.json health
```

### Configuration Error

**Problem:** `Error loading configuration: ...`

**Solution:**
```bash
# Check if config file exists
ls -la ~/.claude/guardrails.yaml

# Validate configuration
python3 ~/Documents/claude-agentic-framework/global-hooks/framework/guardrails/config_loader.py --validate

# Create default configuration
python3 ~/Documents/claude-agentic-framework/global-hooks/framework/guardrails/config_loader.py --create-default
```

### Hook Not Resetting

**Problem:** `No hooks found matching 'pattern'`

**Solution:**
```bash
# List all hooks to see exact names
claude-hooks list

# Use more specific pattern
claude-hooks reset validate_file_contains.py

# Or use partial match from list output
claude-hooks reset validate_file
```

### Multiple Matches Error

**Problem:** `Multiple hooks match pattern 'validate'`

**Solution:**
```bash
# Be more specific with pattern
claude-hooks reset validate_file_contains

# Or see full list and use complete name
claude-hooks list
claude-hooks reset "uv run ~/.claude/hooks/validators/validate_file_contains.py"
```

### Permission Denied

**Problem:** `Permission denied: ~/.claude/hook_state.json`

**Solution:**
```bash
# Fix file permissions
chmod 644 ~/.claude/hook_state.json

# Fix directory permissions
chmod 755 ~/.claude
```

### Colors Not Working

**Problem:** Colors don't show in terminal

**Solution:**
```bash
# Check if terminal supports colors
echo $TERM

# Colors auto-disable for pipes/redirects
claude-hooks health  # colors work
claude-hooks health | less  # colors disabled (auto)

# Manually disable if needed
claude-hooks health --no-color
```

---

## Additional Resources

- **Architecture:** See `ANTI_LOOP_GUARDRAILS.md` for system design
- **Configuration:** See `CONFIG.md` for configuration options
- **Circuit Breaker:** See `CIRCUIT_BREAKER_README.md` for circuit breaker details
- **Development:** See `tests/test_cli.py` for test examples

---

## Exit Codes

The CLI uses standard exit codes:

- **0**: Success
- **1**: Error (hook not found, validation failed, etc.)
- **130**: Interrupted by user (Ctrl+C)

**Examples:**
```bash
# Use in scripts
if claude-hooks reset my_hook; then
    echo "Reset successful"
else
    echo "Reset failed"
    exit 1
fi

# Check exit code
claude-hooks health
echo $?  # 0 for success
```

---

## Tips and Best Practices

1. **Regular Health Checks:** Run `claude-hooks health` regularly to catch issues early
2. **Use Patterns:** Hook patterns support partial matching - use shortest unique string
3. **JSON for Scripts:** Always use `--json` in scripts for reliable parsing
4. **Reset vs Enable:** `reset` clears all state, `enable` is just for disabled hooks
5. **Backup State:** Export state with `--json` before bulk operations
6. **Monitor Logs:** Check `~/.claude/logs/circuit_breaker.log` for detailed history
7. **Configuration:** Keep `guardrails.yaml` in version control for team consistency

---

**Last Updated:** 2026-02-11
**Version:** 1.0.0
