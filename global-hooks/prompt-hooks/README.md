# Prompt-Based Hooks: Hybrid Approach

## Overview

This system uses a **hybrid approach** for Claude Code security hooks:

1. **Command hooks** (fast, deterministic): Pattern-matching scripts that check against `patterns.yaml` rules. These run in ~50ms and catch known dangerous patterns.
2. **Prompt hooks** (semantic, LLM-based): Claude evaluates the tool input with a security-focused prompt. These run in ~2-5s and catch obfuscated, novel, or context-dependent threats that patterns miss.

Both hooks run **in parallel** for each tool invocation. If either one blocks, the operation is blocked.

## Architecture

```
PreToolUse Event (e.g., Bash "rm -rf /")
    |
    +---> Command Hook (pattern match)  ---> Block/Allow  (fast, ~50ms)
    |         bash-tool-damage-control.py
    |         Uses patterns.yaml
    |
    +---> Prompt Hook (LLM evaluation)  ---> Block/Allow  (semantic, ~2-5s)
              Claude Haiku evaluates the command
              Catches obfuscated/novel threats
    |
    v
  Both must allow for the operation to proceed.
  Either blocking = operation blocked.
```

## Configuration

Prompt hooks are configured in `~/.claude/settings.json` (or the template at `templates/settings.json.template`).

### Prompt Hook Schema

```json
{
  "type": "prompt",
  "prompt": "Your evaluation prompt here. Use $ARGUMENTS for the hook input JSON.",
  "timeout": 10,
  "statusMessage": "LLM semantic validation..."
}
```

### Required Fields

| Field     | Type   | Description |
|-----------|--------|-------------|
| `type`    | string | Must be `"prompt"` |
| `prompt`  | string | The evaluation prompt. Must include `$ARGUMENTS` placeholder |
| `timeout` | number | Seconds before canceling (default: 30) |

### Response Format

The LLM must respond with JSON:

```json
{"ok": true}
```

or

```json
{"ok": false, "reason": "Brief explanation of why this was blocked"}
```

**Important**: The response format is `ok: true/false`, NOT the deprecated `decision: approve/block`.

## Current Prompt Hooks

### PreToolUse: Bash

Catches:
- Obfuscated destructive commands (base64 decode piped to bash)
- Remote code execution (curl/wget piped to sh)
- Variable expansion hiding destructive intent
- Data exfiltration via network requests
- Chained destructive operations in pipes/subshells
- System-level config modifications

### PreToolUse: Edit

Catches:
- Removal of security checks, auth logic, or input validation
- Code injection vulnerabilities (eval, exec, os.system with user input)
- Replacement of working code with empty stubs
- Credential file modifications
- SQL injection, XSS, path traversal introduction
- Disabling logging or audit trails

### PreToolUse: Write

Catches:
- Overwriting config files with empty/minimal content
- Writing secrets to version-controlled files
- Creating files outside project scope
- Replacing large files with stubs
- Privilege escalation via cron/systemd/sudoers files
- Overwriting generated files (lock files, build artifacts)

## Adding New Prompt Hooks

### Step 1: Identify the gap

Pattern-based hooks are faster and more reliable for known threats. Only add a prompt hook when:
- The threat cannot be expressed as a regex pattern
- The threat requires understanding context or intent
- The threat involves obfuscation or encoding

### Step 2: Write the prompt

Follow this template:

```
You are a [role] for [tool type]. Analyze this [operation]: $ARGUMENTS

RESPOND WITH ONLY JSON.

Block (ok: false) if the [operation] would:
- [Specific dangerous behavior 1]
- [Specific dangerous behavior 2]
- ...

Allow (ok: true) if the [operation]:
- [Specific safe behavior 1]
- [Specific safe behavior 2]
- ...

Respond: {"ok": true} or {"ok": false, "reason": "brief explanation"}
```

Guidelines:
- Be specific about what to block and what to allow
- Include the `$ARGUMENTS` placeholder (Claude Code substitutes the hook input JSON)
- Use `RESPOND WITH ONLY JSON` to prevent verbose explanations
- Keep the prompt focused -- shorter prompts are faster and more reliable
- List block criteria before allow criteria (fail-closed mindset)

### Step 3: Add to settings

Add the prompt hook AFTER the command hook in the matcher group:

```json
{
  "matcher": "YourTool",
  "hooks": [
    {
      "type": "command",
      "command": "your-pattern-check.py",
      "timeout": 5,
      "statusMessage": "Pattern check..."
    },
    {
      "type": "prompt",
      "prompt": "Your prompt here with $ARGUMENTS...",
      "timeout": 10,
      "statusMessage": "LLM validation..."
    }
  ]
}
```

### Step 4: Test

Add test cases to `global-hooks/framework/testing/mock_inputs.json` and run:

```bash
uv run global-hooks/framework/testing/test_hooks.py --config-only
uv run global-hooks/framework/testing/test_hooks.py -v
```

## Testing

### Run all tests

```bash
uv run global-hooks/framework/testing/test_hooks.py
```

### Run configuration validation only

```bash
uv run global-hooks/framework/testing/test_hooks.py --config-only
```

### Run specific category

```bash
uv run global-hooks/framework/testing/test_hooks.py --category bash_obfuscated
```

### List all test IDs

```bash
uv run global-hooks/framework/testing/test_hooks.py --list
```

## Rollback Procedure

If prompt hooks cause issues:

### Option 1: Disable all hooks temporarily

Add to `~/.claude/settings.json`:
```json
{
  "disableAllHooks": true
}
```

### Option 2: Remove prompt hooks only (keep command hooks)

Remove the `{"type": "prompt", ...}` entries from PreToolUse matcher groups. The command hooks remain and provide pattern-based protection.

### Option 3: Restore from backup

```bash
# List backups
ls -la ~/.claude/settings.json.backup-*

# Restore most recent
cp ~/.claude/settings.json.backup-YYYYMMDD-HHMMSS ~/.claude/settings.json
```

**Note**: Changes to hooks require restarting Claude Code to take effect. Claude Code captures a snapshot of hooks at startup.

## Performance Considerations

- Command hooks: ~50ms (pattern matching, deterministic)
- Prompt hooks: ~2-5s (LLM call, variable)
- Both run in parallel, so total latency is max(command, prompt) not sum
- Prompt hooks use a fast model (Haiku by default) to minimize latency
- The 10s timeout prevents prompt hooks from blocking indefinitely
- Circuit breaker wrapper on command hooks auto-disables after repeated failures

## Security Model

The hybrid approach provides defense-in-depth:

1. **Permissions layer** (`deny`/`ask` rules in settings): First line, blocks known destructive patterns at the permission level
2. **Command hooks** (patterns.yaml): Second line, comprehensive regex patterns for known threats
3. **Prompt hooks** (LLM evaluation): Third line, semantic understanding catches novel/obfuscated threats

Each layer is independent. A failure in one layer does not compromise the others.
