# Caddy Meta-Orchestrator Integration Guide

## Overview

The Caddy meta-orchestrator consists of:
1. **Agent specification**: `global-agents/caddy.md` (Opus model)
2. **Request analyzer hook**: `global-hooks/framework/caddy/analyze_request.py` (UserPromptSubmit)
3. **Auto-delegation hook**: `global-hooks/framework/caddy/auto_delegate.py` (UserPromptSubmit)
4. **Progress monitor hook**: `global-hooks/framework/caddy/monitor_progress.py` (PostToolUse)
5. **Configuration**: `data/caddy_config.yaml`

## Hook Registration

To enable Caddy hooks, add the following entries to `templates/settings.json.template`:

### UserPromptSubmit (add after existing hooks)

```json
{
  "type": "command",
  "command": "uv run __REPO_DIR__/global-hooks/framework/caddy/analyze_request.py",
  "timeout": 5,
  "statusMessage": "Caddy analyzing request..."
},
{
  "type": "command",
  "command": "uv run __REPO_DIR__/global-hooks/framework/caddy/auto_delegate.py",
  "timeout": 5,
  "statusMessage": "Caddy planning delegation..."
}
```

### PostToolUse (add after existing hooks)

```json
{
  "type": "command",
  "command": "uv run __REPO_DIR__/global-hooks/framework/caddy/monitor_progress.py",
  "timeout": 5,
  "statusMessage": "Caddy monitoring progress..."
}
```

## Configuration

Copy or symlink the config file:

```bash
ln -sf "$(pwd)/data/caddy_config.yaml" ~/.claude/caddy_config.yaml
```

Or edit `~/.claude/caddy_config.yaml` directly.

## Logs

Caddy writes logs to `~/.claude/logs/caddy/`:
- `analyses.jsonl` - Every prompt classification
- `delegations.jsonl` - Every delegation plan generated
- `progress.json` - Live sub-agent progress tracking

## Decision Tree Summary

```
User prompt arrives
  |
  v
analyze_request.py classifies:
  complexity: simple | moderate | complex | massive
  task_type:  implement | fix | refactor | research | test | review | document | deploy | plan
  quality:    standard | high | critical
  |
  v
auto_delegate.py selects strategy:
  simple + standard     -> DIRECT (no overhead)
  research              -> /research (Explore agents)
  moderate/complex      -> /orchestrate (multi-agent)
  massive               -> /rlm (Ralph Loop)
  critical              -> /fusion (Best-of-N)
  plan                  -> brainstorm-before-code skill
  |
  v
Caddy agent or main agent follows the plan
  |
  v
monitor_progress.py tracks:
  - Sub-agents spawned/completed/failed
  - Files read/modified
  - Error patterns (3+ failures = alert)
  - Session health: healthy | degraded | unhealthy
```

## Testing

Test each hook with simulated input:

```bash
# Test analyze_request
echo '{"prompt": "Add authentication to the API", "session_id": "test"}' | \
  python3 global-hooks/framework/caddy/analyze_request.py

# Test auto_delegate
echo '{"prompt": "Build a REST API with tests", "session_id": "test"}' | \
  python3 global-hooks/framework/caddy/auto_delegate.py

# Test monitor_progress
echo '{"session_id": "test", "tool_name": "Task", "tool_input": {"subagent_type": "general-purpose", "description": "Research"}, "tool_output": "Done"}' | \
  python3 global-hooks/framework/caddy/monitor_progress.py
```
