# Claude Agentic Framework

v2.1.0 | One repo, one install, one source of truth.

## Structure

```
global-hooks/        damage-control/ observability/ framework/
global-agents/       11 agents (8 root + 3 team)
global-commands/     14 commands
global-skills/       17 skills + symlinks
global-status-lines/ mastery/v9 + observability/
apps/observability/  Vue 3 + Bun (ports 4000/5173)
data/                knowledge-db/ + model_tiers.yaml
templates/           settings.json.template
```

## Mode: Yolo

`"allow": ["*"]` + deny destructive ops + ask force-push/hard-reset. Security: permissions > command hooks (pattern match) > skills integrity (SHA-256) > input validation > file permissions (0o600).

## Model Tiers

```
Opus  (4): orchestrator, project-architect, critical-analyst, rlm-root
Sonnet (5): builder, researcher, meta-agent, project-skill-generator, scout-report-suggest
Haiku  (2): validator, docs-scraper
```

Config: `data/model_tiers.yaml`.

## Context Discipline (Always On)

Every interaction follows these principles to preserve tokens and attention:

1. **Search before read** -- Grep/Glob first. Never open a file blind.
2. **Small slices** -- Read max 50-100 lines at a time. Use offset+limit.
3. **Delegate heavy analysis** -- 5+ files or 200+ lines = spawn sub-agents. Keep primary context for coordination.
4. **Summaries not dumps** -- Sub-agents return 2-3 sentence findings, not raw code.
5. **Parallel sub-agents** -- Independent analyses in one message, not sequential.

/rlm enforces these as a strict formal loop. But the principles apply to ALL work by default.

## Execution Protocol

1. **Task Lists** -- 3+ steps = TaskList. Parallelize. Mark in_progress/completed.
2. **Parallel** -- Launch independent subagents simultaneously. Never serialize parallelizable work.
3. **Orchestrator** -- /orchestrate for complex multi-agent tasks.
4. **Validate** -- Spawn validator subagent after implementation. Never complete without validation.
5. **Teams** -- Builder (Sonnet) implements + Validator (Haiku) verifies, in parallel.

## Key Rules

- `uv run` for all Python execution
- Edit template not settings.json directly -- run `bash install.sh` to apply
- Never delete hook files the live settings.json references -- stub them first, delete after reinstall
- Knowledge DB: `data/knowledge-db/` via knowledge-db skill
