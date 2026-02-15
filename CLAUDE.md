# Claude Agentic Framework

v2.1.0 | One repo, one install, one source of truth.

## Structure

```
global-hooks/        damage-control/ observability/ framework/
global-agents/       8 agents (8 root + 0 team, team archived)
global-commands/     8 commands (core workflow only)
global-skills/       6 skills (essentials only)
global-status-lines/ mastery/v9 + observability/
apps/observability/  Vue 3 + Bun (ports 4000/5173)
data/                knowledge-db/ + model_tiers.yaml
templates/           settings.json.template
archive/             11 skills + 6 commands (rarely used)
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

### Auto-Orchestration (Seamless Team Coordination)

**CRITICAL**: Automatically invoke orchestrator for complex tasks WITHOUT asking user confirmation. Analyze request complexity and auto-delegate.

**Auto-Trigger Orchestration When**:
- **Multi-step** (5+ distinct steps) AND **multi-file** (4+ files affected)
- **Unknown scope** requiring exploration before implementation
- **Security-sensitive** (auth, API keys, permissions, encryption)
- **Performance-critical** (profiling needed + optimization + validation)
- **Full-stack** (frontend + backend + database changes)
- **Large refactoring** (15+ files, architectural changes)
- **Audits/scans** (security-scanner, code-review, dependency-audit)

**Auto-Orchestration Workflow**:
```
1. Detect qualifying task (silent analysis)
2. Invoke orchestrator agent (no confirmation needed)
3. Orchestrator spawns specialized team in parallel
4. Orchestrator synthesizes results
5. Report completion to user
```

**Examples**:
- ✅ "Add OAuth2 authentication" → Auto-orchestrate (security + multi-file + complex)
- ✅ "Optimize database queries" → Auto-orchestrate (profiling + testing needed)
- ✅ "Security audit the API" → Auto-orchestrate (scan + analyze + report)
- ❌ "Fix typo in README" → Direct (simple, 1 file)
- ❌ "Add logging to function X" → Direct (simple, 1 file)

### Execution Rules

1. **Task Lists** -- 3+ steps = TaskList. Parallelize. Mark in_progress/completed.
2. **Parallel** -- Launch independent subagents simultaneously. Never serialize parallelizable work.
3. **Auto-Orchestrate** -- Complex tasks trigger orchestrator automatically (no user prompt).
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
