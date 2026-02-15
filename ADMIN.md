# Admin Guide

Operations guide for teams running the Claude Agentic Framework.

## Installation for Teams

### Per-developer setup
```bash
git clone <repo-url>
cd claude-agentic-framework
./install.sh
```

Each developer gets their own `~/.claude/settings.json` generated from the shared template.

### Shared configuration
All config lives in the repo:
- `templates/settings.json.template` -- hook wiring, permissions
- `data/model_tiers.yaml` -- agent-to-model assignments
- `data/budget_config.yaml` -- cost limits and alerts

Changes to these files take effect after `./install.sh`.

## Cost Management

### Budget controls
Edit `data/budget_config.yaml`:
```yaml
budgets:
  daily: 10.00
  weekly: 50.00
  monthly: 150.00
```

### Monitoring
```
/costs              # Current session/day
/costs --week       # Weekly breakdown
/costs --by-agent   # Per-agent usage
/costs --by-tier    # Per-tier usage
```

Cost data: `~/.claude/logs/cost_tracking.jsonl` (append-only JSONL, one line per API call).

### Reducing costs
1. Move agents to lower tiers in `data/model_tiers.yaml`
2. Reduce `tier_limits` in `data/budget_config.yaml`
3. Use `/research` (Sonnet) instead of `/orchestrate` (Opus) for simple tasks

## Adding/Removing Components

### Add an agent
1. Create `global-agents/<name>.md` (or `global-agents/team/<name>.md`)
2. Add to `data/model_tiers.yaml` under the appropriate tier
3. Run `./install.sh`
4. Docs auto-update (README.md, CLAUDE.md regenerated)

### Add a command
1. Create `global-commands/<name>.md`
2. Run `./install.sh`
3. Docs auto-update

### Add a skill
1. Create `global-skills/<name>/SKILL.md`
2. Run `./install.sh`
3. Docs auto-update

### Remove a component
1. Delete the file
2. Remove from `data/model_tiers.yaml` if it is an agent
3. Run `./install.sh`
4. Docs auto-update

## Hook Management

Active hooks (from `templates/settings.json.template`):

| Event | Hook | Purpose | Timeout |
|-------|------|---------|---------|
| PreToolUse | unified-damage-control.py | Block destructive commands | 5s |
| PostToolUse | context-bundle-logger.py | Log context bundles | 5s |
| Stop | check_lthread_progress.py | Validate task progress | 5s |
| SessionStart | verify_skills.py | SHA-256 skill integrity check | 5s |
| SessionStart | validate_docs.py | Warn if README.md is stale | 5s |

### Adding a hook
1. Create the Python script in `global-hooks/`
2. Add to `templates/settings.json.template`
3. Run `./install.sh`

### Removing a hook
1. Make the script a no-op stub (return `{"result": "continue"}`)
2. Run `./install.sh` to regenerate settings.json
3. Start a new session
4. Now safe to delete the file

Never delete a hook file while a session references it.

## Auto-Documentation

The framework auto-generates README.md and CLAUDE.md from live repo state.

- **Generator**: `scripts/generate_docs.py`
- **Trigger**: Runs during `./install.sh` (step 6/7)
- **Validation**: SessionStart hook warns if docs are stale
- **Manual run**: `uv run scripts/generate_docs.py`
- **CI check**: `uv run scripts/generate_docs.py --check` (exits non-zero if stale)

## Audit Trail

### What is logged
- Cost tracking: `~/.claude/logs/cost_tracking.jsonl`
- Context bundles: logged by PostToolUse hook
- Session events: `logs/` directory per session

### Retention
Logs are append-only JSONL. Rotate or archive as needed:
```bash
# Archive logs older than 30 days
find ~/.claude/logs -name "*.jsonl" -mtime +30 -exec gzip {} +
```

## Security

- Skills integrity verified on session start (SHA-256)
- Destructive commands blocked by PreToolUse hook
- Settings generated from template (no manual edits to drift)
- Regenerate skills lock: `uv run scripts/generate_skills_lock.py`

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Commands missing | Run `./install.sh`, start new session |
| Hook errors on start | Check files in `templates/settings.json.template` exist |
| Wrong counts in README | Run `uv run scripts/generate_docs.py` |
| Cost data empty | PostToolUse hook must be active (check settings.json) |
| Agent not found | Check symlink in `~/.claude/agents/` and model_tiers.yaml |
