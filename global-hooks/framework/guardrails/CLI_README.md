# claude-hooks CLI Tool

Quick reference for the circuit breaker health monitoring CLI.

## Installation

```bash
# Run the installation script
cd /Users/tomkwon/Documents/claude-agentic-framework/global-hooks/framework/guardrails
bash install_cli.sh

# Or install manually
chmod +x claude_hooks_cli.py
mkdir -p ~/.local/bin
ln -sf $(pwd)/claude_hooks_cli.py ~/.local/bin/claude-hooks

# Ensure ~/.local/bin is in PATH
export PATH="$HOME/.local/bin:$PATH"
```

## Quick Commands

```bash
# Health check - show disabled hooks and stats
claude-hooks health

# List all tracked hooks
claude-hooks list

# Reset a specific hook
claude-hooks reset validate_file

# Reset all hooks
claude-hooks reset --all

# Enable a disabled hook
claude-hooks enable validate_file

# Manually disable a hook
claude-hooks disable problematic_hook

# Show current configuration
claude-hooks config
```

## JSON Output (for scripting)

```bash
# Get disabled hook count
claude-hooks health --json | jq '.disabled_hooks'

# Get all hook commands
claude-hooks list --json | jq '.[].command'

# Check specific hook state
claude-hooks list --json | jq '.[] | select(.command | contains("validate")) | .state'
```

## Color Codes

- **Green** - Healthy/Active (CLOSED state)
- **Yellow** - Testing/Warning (HALF_OPEN state)
- **Red** - Disabled/Failed (OPEN state)

## Common Workflows

### Fix a Failing Hook

```bash
# 1. Check what's failing
claude-hooks health

# 2. Fix the underlying issue
# (e.g., create missing file, fix permissions)

# 3. Reset the hook
claude-hooks reset validate_file

# 4. Verify it's working
claude-hooks health
```

### Daily Monitoring

```bash
# Quick health check
claude-hooks health

# Save report for analysis
claude-hooks health --json > health_report.json
```

## Files

- **CLI Script:** `claude_hooks_cli.py` (646 lines)
- **Tests:** `tests/test_cli.py` (750 lines, 40+ tests)
- **Full Documentation:** `CLI_USAGE.md` (650+ lines)
- **Installation:** `install_cli.sh`

## Features

- ✅ Zero dependencies (Python stdlib only)
- ✅ Color-coded output with terminal detection
- ✅ Human-readable timestamps ("5 minutes ago")
- ✅ JSON output for automation
- ✅ Pattern-based hook matching
- ✅ Comprehensive help text
- ✅ 6 commands: health, list, reset, enable, disable, config
- ✅ 40+ unit tests with 100% coverage

## Help

```bash
# Show help for all commands
claude-hooks --help

# Show help for specific command
claude-hooks health --help
claude-hooks reset --help
```

## Documentation

- **This file:** Quick reference
- **CLI_USAGE.md:** Complete usage guide with examples
- **TASK_4_COMPLETION.md:** Implementation details
- **tests/test_cli.py:** Test examples

## Exit Codes

- **0** - Success
- **1** - Error (hook not found, validation failed, etc.)
- **130** - Interrupted by user (Ctrl+C)

## Configuration

Default locations:
- **Config:** `~/.claude/guardrails.yaml`
- **State:** `~/.claude/hook_state.json`
- **Logs:** `~/.claude/logs/circuit_breaker.log`

Override with flags:
```bash
claude-hooks --config /path/to/config.yaml health
claude-hooks --state-file /path/to/state.json list
```

## Support

For issues or questions:
1. Check `CLI_USAGE.md` for detailed documentation
2. Check `TASK_4_COMPLETION.md` for implementation details
3. Run tests: `python3 tests/test_cli.py`
4. Check logs: `~/.claude/logs/circuit_breaker.log`

---

**Version:** 1.0.0
**Last Updated:** 2026-02-11
**Status:** Production Ready
