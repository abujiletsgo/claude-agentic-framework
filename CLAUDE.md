# Claude Agentic Framework

v2.1.0 | One repo, one install, one source of truth.

## Structure

```
global-hooks/        damage-control/ observability/ framework/
global-agents/       8 agents (8 root + 0 team)
global-commands/     14 commands
global-skills/       7 skills
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

## Auto-Prime Context

At session start, `session_startup.py` injects the cached project context via `additionalContext` — it appears as a `<system-reminder>` labelled "SessionStart hook additional context". **This is authoritative project knowledge.** Use it immediately when answering questions about project structure, hooks, agents, commands, and architecture. Do not re-read files for information already covered in the primed context.

## Memory Layers

The framework uses a **4-layer cognitive memory system**. Each layer has a different scope and lifetime.

```
Layer 3 — SEMANTIC  — ~/.claude/memory/MEMORY.md          (global, cross-project, always in CLAUDE.md)
Layer 2 — EPISODIC  — .claude/FACTS.md + MEMORY.md        (this project, on-demand)
Layer 1 — WORKING   — TaskList + compressed summaries      (current session, ephemeral)
Layer 0 — SENSORY   — current tool output                  (one turn, ephemeral)
```

**Session start: lean by design.**
Only project context (PROJECT_CONTEXT.md via auto_prime) is injected automatically.
Episodic memory (FACTS.md, MEMORY.md) is read **on-demand** — when starting project work,
proactively read these files rather than relying on memory:

```
Read .claude/FACTS.md    # verified facts: confirmed behaviors, gotchas, key paths
Read .claude/MEMORY.md   # recent sessions: what changed, what was fixed, decisions made
```

**Memory writes are always automatic (no token cost):**
- `auto_fact_extractor.py` (PostToolUse: Bash|Write) → extracts facts to `.claude/FACTS.md`
- `auto_memory_writer.py` (Stop) → writes session summary to `.claude/MEMORY.md`
- `validate_facts.py` (Stop) → prunes entries older than 90 days

**Trust hierarchy:** CONFIRMED facts > global MEMORY rules > inference
**FACTS.md categories:** CONFIRMED (execution-verified) | GOTCHAS (failure modes) | PATHS | PATTERNS | STALE

**Layers (override rules):**
- Agents: Global (`~/.claude/agents/`) always available. Local (`.claude/agents/`) override globals.
- Skills: Global (`~/.claude/skills/`) always available. Local (`.claude/skills/`) override globals.

## Session Scenarios

**New project:** `/prime` → creates PROJECT_CONTEXT.md → FACTS.md initialized with template.
**Resuming project:** auto_prime injects PROJECT_CONTEXT.md. Read FACTS.md + MEMORY.md for project-specific context.
**Large project (≥200 files):** RepoMap generated at session start. Check FACTS.md PATHS before exploring. Use delegated mode.
**Long session (context ≥70%):** auto_context_manager.py compresses cold tasks → pre_compact_preserve.py preserves key state.

Full architecture diagram: `docs/MEMORY_ARCHITECTURE.md`
