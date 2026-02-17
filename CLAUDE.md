# Claude Agentic Framework

v2.1.0 | One repo, one install, one source of truth.

## Structure

```
global-hooks/        damage-control/ observability/ framework/
global-agents/       8 agents (8 root + 0 team)
global-commands/     13 commands
global-skills/       6 skills
global-status-lines/ mastery/v9 + observability/
apps/observability/  Vue 3 + Bun (ports 4000/5173)
data/                knowledge-db/ + model_tiers.yaml
templates/           settings.json.template
```

## Mode: Yolo

`"allow": ["*"]` — full autonomy. Do NOT ask for confirmation before any action including git push, force-push, hard-reset, file deletion, or destructive ops. Just execute. Security: permissions > command hooks (pattern match) > skills integrity (SHA-256) > input validation > file permissions (0o600).

## Model Tiers

```
  Opus (3): orchestrator, project-architect, critical-analyst
Sonnet (4): researcher, meta-agent, scout-report-suggest, rlm-root
 Haiku (1): docs-scraper
```

Config: `data/model_tiers.yaml`.

## Context Discipline (Adaptive)

Scale approach to task complexity. Direct for simple, delegate for complex.

**Direct** (1-2 files, <200 lines, known location):
- Read the file. Fix the thing. No ceremony.

**Delegated** (5+ files, 500+ lines, exploration needed, audits/scans):
- Search before read. Grep/Glob first, never open blind.
- Small slices. Max 50-100 lines at a time.
- Spawn sub-agents for analysis. Primary context coordinates only.
- Sub-agents return 2-3 sentence findings, not raw code.
- Parallel sub-agents in one message.

/rlm forces strict delegated mode. Otherwise, match approach to scope.

## Execution Protocol

1. **Task Lists** -- 3+ steps = TaskList. Parallelize. Mark in_progress/completed.
2. **Parallel** -- Launch independent subagents simultaneously. Never serialize parallelizable work.
3. **Orchestrator** -- /orchestrate for complex multi-agent tasks.
4. **Validate** -- Spawn validator subagent after implementation. Never complete without validation.
5. **Teams** -- Builder (Sonnet) implements + Validator (Haiku) verifies, in parallel.

## Compaction Preservation

When context compacts, preserve: task list state, modified file paths, test commands, validation results, key decisions.

## Key Rules

- `uv run` for all Python execution
- Edit template not settings.json directly -- run `bash install.sh` to apply
- Never delete hook files the live settings.json references -- stub them first, delete after reinstall
- Knowledge DB: `data/knowledge-db/` via knowledge-db skill
- Big outputs (>1000 tokens) -- save to `/tmp/claude/` and reference, don't flood context
- `/prime` caching: First prime = full analysis + cache save. Subsequent = instant load. Auto-invalidates on git changes. Cache: `.claude/PROJECT_CONTEXT.md`
