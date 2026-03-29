# Claude Agentic Framework

v3.0.2 | One repo, one install, one source of truth. Opus-first on Max plan.

## Structure

```
global-hooks/        damage-control/ observability/ framework/
global-agents/       8 agents (8 root + 0 team)
global-commands/     15 commands
global-skills/       9 skills
global-status-lines/ mastery/v9 + observability/
apps/observability/  Vue 3 + Bun (ports 4000/5173)
data/                knowledge-db/ + model_tiers.yaml
templates/           settings.json.template
```

## Mode: Yolo

`"allow": ["*"]` — full autonomy. Do NOT ask for confirmation before any action including git push, force-push, hard-reset, file deletion, or destructive ops. Just execute. Security: permissions > command hooks (pattern match) > skills integrity (SHA-256) > input validation > file permissions (0o600).

## Model Tiers

```
  Opus (7): orchestrator, project-architect, critical-analyst, researcher, meta-agent, scout-report-suggest, rlm-root
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
- Never move or rename this framework directory without updating `~/.claude/settings.json` first -- all tools (Bash/Read/Edit/Write) will be blocked immediately if hook paths break. Safe move procedure in ADMIN.md.
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

## When to Read What

| Scenario | Read First |
|----------|-----------|
| Starting a new project | Run `/prime`, then read `CLAUDE.md` |
| Understanding architecture | `.claude/ARCHITECTURE.md` |
| Finding canonical numbers | Check `FACTS.md` CONFIRMED section |
| Debugging a hook failure | Check `~/.claude/circuit_breakers/`, then `FACTS.md` GOTCHAS |
| Adding a new hook | `templates/settings.json.template`, then `install.sh` |
| Adding a new skill | `global-skills/*/SKILL.md` for examples, then `/skill-builder` |
| Adding a new agent | `global-agents/*.md` for examples |
| Understanding why a decision was made | CLAUDE.md "Decision Rationale" section |

## Decision Rationale

Key design decisions and why they were made:

- **Why `uv run` for hooks?** Dependency isolation, reproducible environments, no pip conflicts. Each hook runs in its own environment without polluting the global Python installation.
- **Why 4-layer memory?** Each layer serves different persistence/scope needs. Sensory (one turn) vs working (session) vs episodic (project) vs semantic (global) prevents context bloat while retaining critical knowledge.
- **Why Opus for orchestrator?** Complex multi-agent coordination requires strongest reasoning. Sonnet/Haiku handle individual tasks; Opus coordinates the fleet.
- **Why circuit breakers?** Prevent one broken hook from crashing all sessions. Auto-recovers after 60s cooldown. Without this, a single hook error would block all tool use.
- **Why damage-control patterns?** Defense-in-depth against accidental destructive commands. Even with `allow: ["*"]`, the pattern matcher catches `rm -rf`, `git push --force`, SQL `DROP TABLE`, etc. before they execute.
- **Why templates over direct settings.json editing?** Single source of truth. `install.sh` substitutes `__REPO_DIR__` and validates JSON. Editing settings.json directly gets overwritten on next install.

## Common Workflows

### Adding a new hook
1. Create the hook script in `global-hooks/framework/` (or appropriate subdirectory)
2. Add the hook entry to `templates/settings.json.template` under the right event type
3. Run `bash install.sh` to regenerate `settings.json`
4. Test with `uv run scripts/run_tests.py --fast` to verify no regressions

### Adding a new agent
1. Create `global-agents/your-agent.md` with YAML frontmatter (name, description, tools, model, maxTurns, permissionMode)
2. Run `bash install.sh` to symlink into `~/.claude/agents/`
3. Update `data/model_tiers.yaml` with the agent's model tier
4. Run `uv run scripts/generate_docs.py` to update README.md and CLAUDE.md counts

### Adding a new skill
1. Create `global-skills/your-skill/SKILL.md` with YAML frontmatter (name, description)
2. Add any supporting files in the same directory
3. Run `bash install.sh` to symlink into `~/.claude/skills/`
4. Run `uv run scripts/generate_docs.py` to update counts

### Debugging a failing hook
1. Check `~/.claude/circuit_breakers/` for tripped breakers (auto-recover after 60s)
2. Read `FACTS.md` GOTCHAS section for known failure modes
3. Run the hook script directly: `uv run global-hooks/framework/.../the_hook.py` with test stdin
4. Check stderr output for error details
5. Run `uv run scripts/run_tests.py` to verify the fix

### Updating damage control patterns
1. Edit `global-hooks/damage-control/patterns.yaml` (add pattern + reason)
2. Run `uv run scripts/run_tests.py --fast` to verify regex compiles and no false positives
3. Test blocked commands: the eval suite covers dangerous + safe command lists

## Mistake Prevention

Common pitfalls and how to avoid them:

- **If you're about to edit `settings.json` directly** -- stop and edit `templates/settings.json.template` instead, then run `bash install.sh`. Direct edits get overwritten.
- **If you're about to delete a hook file** -- stop and check if `settings.json` references it. Stub the file first (make it exit 0), reinstall, then delete. Removing a referenced hook breaks ALL tool use.
- **If you're about to move/rename the framework directory** -- stop and update `~/.claude/settings.json` paths first. All hooks use absolute paths; moving the directory breaks every hook simultaneously.
- **If you see "hook error" on every tool use** -- check `~/.claude/circuit_breakers/` for tripped breakers. Delete the breaker file to reset, or wait 60s for auto-recovery.
- **If you're about to add `sleep` in a hook** -- stop. Hooks have strict timeouts (5-15s). A sleeping hook will be killed and trip the circuit breaker.
- **If you're about to use `pip install` in a hook** -- stop and use `uv run` instead. Pip installs pollute the global environment and cause conflicts between hooks.
- **If a regex pattern has false positives** -- check the eval suite's `safe_commands` list. Add the false-positive command there and verify it passes before deploying.
- **If you're about to commit `.claude/settings.json`** -- stop. It contains absolute paths specific to your machine. Only commit `templates/settings.json.template`.

Full architecture diagram: `docs/MEMORY_ARCHITECTURE.md`
