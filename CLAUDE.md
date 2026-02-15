# Claude Agentic Framework

v2.1.0 | One repo, one install, one source of truth.

## Structure

```
global-hooks/        damage-control/ observability/ framework/
global-agents/       11 agents (8 root + 3 team)
global-commands/     14 commands
global-skills/       6 skills
global-status-lines/ mastery/v9 + observability/
apps/observability/  Vue 3 + Bun (ports 4000/5173)
data/                knowledge-db/ + model_tiers.yaml
templates/           settings.json.template
```

## Mode: Yolo

`"allow": ["*"]` + deny destructive ops + ask force-push/hard-reset. Security: permissions > command hooks (pattern match) > skills integrity (SHA-256) > input validation > file permissions (0o600).

## Model Tiers

```
  Opus (4): orchestrator, project-architect, critical-analyst, rlm-root
Sonnet (5): researcher, meta-agent, scout-report-suggest, builder, project-skill-generator
 Haiku (2): docs-scraper, validator
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
2. Spawn specialized team in PARALLEL (one message, multiple agents)
3. Agents work simultaneously on different parts
4. Synthesize results
5. Report completion
```

**Examples**:
- ✅ "Add OAuth2" → Auto-spawn: researcher + security + builder + tester (parallel)
- ✅ "Security audit" → Auto-spawn: scanner + reviewer + validator (parallel)
- ❌ "Fix typo" → Direct (simple, 1 file)

### Execution Rules

1. **Task Lists** -- 3+ steps = TaskList. Parallelize. Mark in_progress/completed.
2. **TRUE Parallel** -- Spawn independent agents in ONE message simultaneously.
3. **Auto-Orchestrate** -- Complex tasks trigger parallel teams automatically (no user prompt).
4. **Validate** -- Always spawn validator in parallel with builders.
5. **Teams** -- Builder + Validator work simultaneously, not sequentially.

## Compaction Preservation

When context compacts, preserve: task list state, modified file paths, test commands, validation results, key decisions.

## Key Rules

- `uv run` for all Python execution
- Edit template not settings.json directly -- run `bash install.sh` to apply
- Never delete hook files the live settings.json references -- stub them first, delete after reinstall
- Knowledge DB: `data/knowledge-db/` via knowledge-db skill
- Big outputs (>1000 tokens) -- save to `/tmp/claude/` and reference, don't flood context
- `/prime` caching: First prime = full analysis + cache save. Subsequent = instant load. Auto-invalidates on git changes. Cache: `.claude/PROJECT_CONTEXT.md`
