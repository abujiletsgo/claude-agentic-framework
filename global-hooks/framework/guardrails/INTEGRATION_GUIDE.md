# Guardrails Integration Guide

## Quick Start

The fastest way to integrate guardrails into your Claude Code hooks:

```bash
cd ~/Documents/claude-agentic-framework/global-hooks/framework/guardrails

# Run the integration script
python3 integrate_guardrails.py
```

This will automatically:
- Create a backup of your settings.json
- Wrap all hook commands with the circuit breaker wrapper
- Enable anti-loop protection for all hooks

---

## What Gets Integrated

The integration script wraps each hook command with the circuit breaker wrapper:

**Before:**
```json
{
  "command": "uv run /path/to/hook.py --args"
}
```

**After:**
```json
{
  "command": "uv run .../circuit_breaker_wrapper.py -- uv run /path/to/hook.py --args"
}
```

---

## Manual Integration

If you prefer to integrate manually:

### 1. Install Dependencies

```bash
cd ~/Documents/claude-agentic-framework/global-hooks/framework/guardrails

# Install Python packages
uv pip install -r requirements.txt

# Install CLI tool
bash install_cli.sh
```

### 2. Create Configuration

```bash
# Copy default config
mkdir -p ~/.claude
cp default_config.yaml ~/.claude/guardrails.yaml

# Edit if needed
vim ~/.claude/guardrails.yaml
```

### 3. Wrap Hooks in settings.json

Edit `~/.claude/settings.json` and wrap each hook command:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "uv run /path/to/circuit_breaker_wrapper.py -- uv run /path/to/original_hook.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

**Wrapper path:** `$REPO/global-hooks/framework/guardrails/circuit_breaker_wrapper.py`

---

## Verification

After integration, verify the system is working:

```bash
# Check health status
claude-hooks health

# Should show:
# Total Hooks: 20+
# Active: 20+
# Disabled: 0
```

### Test Circuit Breaker

```bash
# Test with a failing command
for i in {1..3}; do
  uv run .../circuit_breaker_wrapper.py -- bash -c "exit 1"
done

# Fourth attempt should skip execution
uv run .../circuit_breaker_wrapper.py -- bash -c "exit 1"
# Output: {"result": "continue", "message": "Hook disabled due to repeated failures..."}

# Check health
claude-hooks health
# Should show 1 disabled hook

# Reset for cleanup
claude-hooks reset "bash -c exit 1"
```

---

## Configuration

Edit `~/.claude/guardrails.yaml` to customize:

```yaml
circuit_breaker:
  enabled: true
  failure_threshold: 3        # Failures before opening circuit
  cooldown_seconds: 300       # Time before retry (5 minutes)
  success_threshold: 2        # Successes needed to close circuit
  exclude:                    # Hooks to exclude from circuit breaker
    - "some-hook-pattern"

logging:
  file: ~/.claude/logs/circuit_breaker.log
  level: INFO
  format: "%(asctime)s | %(levelname)s | %(hook_cmd)s | %(message)s"

state_file: ~/.claude/hook_state.json
```

---

## Monitoring

### CLI Commands

```bash
# Health dashboard
claude-hooks health

# List all tracked hooks
claude-hooks list

# List only disabled hooks
claude-hooks list --disabled

# Show configuration
claude-hooks config

# JSON output (for scripting)
claude-hooks health --json
claude-hooks list --json
```

### State File

View raw state data:

```bash
cat ~/.claude/hook_state.json | python3 -m json.tool
```

Structure:
```json
{
  "hooks": {
    "hook_command": {
      "state": "closed|open|half_open",
      "failure_count": 0,
      "consecutive_failures": 0,
      "consecutive_successes": 0,
      "first_failure": "2026-02-11T02:00:00+00:00",
      "last_failure": "2026-02-11T02:05:00+00:00",
      "last_success": null,
      "last_error": "error message",
      "disabled_at": "2026-02-11T02:05:00+00:00",
      "retry_after": "2026-02-11T02:10:00+00:00"
    }
  },
  "global_stats": {
    "total_executions": 1000,
    "total_failures": 5,
    "hooks_disabled": 1,
    "last_updated": "2026-02-11T02:05:00+00:00"
  }
}
```

---

## Management

### Reset Hooks

```bash
# Reset specific hook
claude-hooks reset "hook-command-pattern"

# Reset all hooks
claude-hooks reset --all
```

### Manual Control

```bash
# Force enable a disabled hook
claude-hooks enable "hook-command-pattern"

# Manually disable a hook
claude-hooks disable "hook-command-pattern"
```

---

## Troubleshooting

### Issue: "PyYAML is required"

**Solution:** The CLI uses inline dependencies with uv. Make sure the shebang is:
```python
#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["pyyaml>=6.0.0", "pydantic>=2.0.0"]
# ///
```

### Issue: Hook executions not being tracked

**Cause:** Hooks not wrapped with circuit_breaker_wrapper.py

**Solution:**
```bash
# Re-run integration
python3 integrate_guardrails.py

# Or manually wrap in settings.json
```

### Issue: Circuit opens too quickly

**Cause:** Failure threshold too low

**Solution:** Increase in `~/.claude/guardrails.yaml`:
```yaml
circuit_breaker:
  failure_threshold: 5  # Increase from default 3
```

### Issue: Cooldown too long/short

**Solution:** Adjust in config:
```yaml
circuit_breaker:
  cooldown_seconds: 600  # 10 minutes instead of 5
```

---

## Reverting Integration

If you need to remove guardrails:

```bash
# Restore backup
cp ~/.claude/settings.json.backup-before-guardrails ~/.claude/settings.json

# Or manually remove wrapper prefixes from settings.json
```

---

## How It Works

### Circuit Breaker States

```
┌─────────┐  3+ failures   ┌──────┐  cooldown   ┌────────────┐
│ CLOSED  │───────────────▶│ OPEN │────────────▶│ HALF_OPEN  │
│(active) │                │(skip)│             │(testing)   │
└─────────┘                └──────┘             └────────────┘
     ▲                                                  │
     │                                                  │
     └────────────────────2 successes───────────────────┘
```

### Execution Flow

1. **Tool use detected** → Circuit breaker wrapper invoked
2. **Check state:**
   - CLOSED: Execute hook normally
   - OPEN: Check if cooldown elapsed
     - Yes: Transition to HALF_OPEN, execute
     - No: Skip execution, return success with message
   - HALF_OPEN: Execute (testing recovery)
3. **Execute hook** and capture result
4. **Record result:**
   - Success: Increment success counter
     - In HALF_OPEN: If 2+ successes → close circuit
   - Failure: Increment failure counter
     - If consecutive_failures >= threshold → open circuit
5. **Return result** to Claude Code

### Key Feature: Graceful Degradation

When circuit is OPEN, the wrapper returns:
```json
{
  "result": "continue",
  "message": "Hook disabled due to repeated failures. Circuit open, hook disabled until [timestamp]",
  "success": true
}
```

This prevents infinite loops while keeping the agent informed!

---

## Integration Checklist

- [ ] Dependencies installed (`requirements.txt`)
- [ ] CLI tool installed (`install_cli.sh`)
- [ ] Configuration file created (`~/.claude/guardrails.yaml`)
- [ ] Integration script run (`integrate_guardrails.py`)
- [ ] Backup created (`settings.json.backup-before-guardrails`)
- [ ] Health check shows tracked hooks (`claude-hooks health`)
- [ ] Circuit breaker test passed (3 failures → circuit opens)
- [ ] Test hook reset (`claude-hooks reset`)

---

## Support

For issues or questions:
- Check logs: `~/.claude/logs/circuit_breaker.log`
- View state: `~/.claude/hook_state.json`
- CLI help: `claude-hooks --help`
- Documentation: `CIRCUIT_BREAKER_README.md`, `CLI_USAGE.md`
