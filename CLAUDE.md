# Claude Agentic Framework

v4.0 | One repo, one install, one source of truth. Opus-first on Max plan.

## Structure

```
global-hooks/        31 hooks across 16 events (hooks_ConfigChange:1, hooks_CwdChanged:1, hooks_FileChanged:1, hooks_Notification:1, hooks_PostCompact:1, hooks_PostToolUse:3, hooks_PostToolUseFailure:1, hooks_PreCompact:1, hooks_PreToolUse:3, hooks_SessionStart:2, hooks_Stop:5, hooks_StopFailure:1, hooks_SubagentStart:2, hooks_SubagentStop:3, hooks_TaskCompleted:1, hooks_UserPromptSubmit:4)
global-agents/       8 agents (8 root + 0 team)
global-commands/     9 commands
global-skills/       15 skills
data/                model_tiers.yaml + caddy_config.yaml + knowledge-db/
templates/           settings.json.template (edit this, run install.sh)
```

## Mode: Yolo

`"allow": ["*"]` — full autonomy. Security: damage-control hooks (100+ patterns) > permissions > SHA-256 skill integrity > path protection (zero-access/read-only/no-delete).

## Model Tiers

```
 Fable (1): critical-analyst
  Opus (2): architecture-consultant, security-consultant
Sonnet (5): frontend-consultant, backend-consultant, builder, onboard, academic-researcher
```

## Context Discipline

**Direct** (1-2 files, known location): Read. Fix. Done.
**Delegated** (5+ files, exploration): Grep/Glob first. Sub-agents for analysis. 2-3 sentence summaries only. Parallel.

## Execution Protocol

1. **3+ steps** = write plan to `tasks/todo.md` with checkable items. Mark complete as you go.
2. **Parallel** -- independent subagents in one message. Never serialize parallelizable work.
3. **Validate** -- always verify implementation (tests, scripts). Never complete without validation.
4. **Self-improvement** -- after any user correction: append lesson to `~/.claude/lessons.md` (pattern → rule to prevent recurrence).

## Key Rules

- **`/orchestrate` is MANDATORY**: When user types `/orchestrate`, IMMEDIATELY call `Skill(skill="orchestrate")` BEFORE any other tool. Never ignore it. Never do the work yourself. Never treat it as decorative text. The orchestrator agent spawns parallel teams — you are not the orchestrator.
- `uv run` for all Python. Never `pip install`.
- Edit `templates/settings.json.template` → `bash install.sh`. Never edit settings.json directly.
- Never delete hook files settings.json references. Stub first, delete after reinstall.
- Never move framework directory without updating settings.json paths first.
- Big outputs (>1000 tokens) → save to `/tmp/claude/` and reference.
- When context compacts: preserve task list, modified files, test commands, key decisions.

## Auto-Prime Context

At session start, `session_startup.py` injects `.claude/PROJECT_CONTEXT.md` as authoritative project context. Use it immediately. Don't re-read files for info already in primed context.

## Memory (On-Demand)

Session start is lean. Only PROJECT_CONTEXT.md auto-injected. Read episodic memory when needed:
- `.claude/FACTS.md` — verified facts (CONFIRMED > GOTCHAS > PATHS > PATTERNS)
- `.claude/MEMORY.md` — recent session summaries (git-diff-based, max 30 entries)

Memory writes are automatic: `auto_fact_extractor.py` (PostToolUse) → FACTS.md, `auto_memory_writer.py` (Stop) → MEMORY.md, `validate_facts.py` (Stop) → prunes >90 days.

Trust: CONFIRMED facts > CLAUDE.md rules > inference. Local agents/skills override global.

## Epistemic Discipline

Label claims: **OBSERVED** (cite source) / **INFERRED** (state reasoning chain) / **SPECULATIVE** (flag explicitly). Never present an inference as an observation. When data is ambiguous, say so directly.

## Mistake Prevention

- **Edit settings.json directly?** → Stop. Edit template, run install.sh.
- **Delete a hook file?** → Stop. Stub it first (exit 0), reinstall, then delete.
- **Move framework directory?** → Stop. Update settings.json paths first.
- **Hook errors everywhere?** → Check `~/.claude/circuit_breakers/`. Delete state file or wait 60s.
- **`pip install` in a hook?** → Stop. Use `uv run` instead.

Full guide: `docs/framework-guide-ko.html` | Architecture: `.claude/ARCHITECTURE.md`
