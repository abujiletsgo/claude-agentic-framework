# Claude Agentic Framework

v4.0 | One repo, one install, one source of truth. Opus-first on Max plan.

## Structure

```
global-hooks/        36 hooks across 16 events (hooks_ConfigChange:1, hooks_CwdChanged:1, hooks_FileChanged:1, hooks_PostCompact:1, hooks_PostToolUse:11, hooks_PostToolUseFailure:1, hooks_PreCompact:1, hooks_PreToolUse:3, hooks_SessionEnd:1, hooks_SessionStart:2, hooks_Stop:6, hooks_StopFailure:1, hooks_SubagentStart:1, hooks_SubagentStop:1, hooks_TaskCompleted:1, hooks_UserPromptSubmit:3)
global-agents/       9 agents (9 root + 0 team)
global-commands/     15 commands
global-skills/       11 skills
data/                model_tiers.yaml + caddy_config.yaml + knowledge-db/
templates/           settings.json.template (edit this, run install.sh)
```

## Mode: Yolo

`"allow": ["*"]` — full autonomy. Security: damage-control hooks (100+ patterns) > permissions > SHA-256 skill integrity > path protection (zero-access/read-only/no-delete).

## Model Tiers

```
  Opus (3): orchestrator, project-architect, rlm-root
Sonnet (4): critical-analyst, researcher, meta-agent, scout-report-suggest
 Haiku (1): docs-scraper
```

## Context Discipline

**Direct** (1-2 files, known location): Read. Fix. Done.
**Delegated** (5+ files, exploration): Grep/Glob first. Sub-agents for analysis. 2-3 sentence summaries only. Parallel.

## Execution Protocol

1. **3+ steps** = TaskList. Mark in_progress/completed.
2. **Parallel** -- independent subagents in one message. Never serialize parallelizable work.
3. **Validate** -- always verify implementation (tests, scripts). Never complete without validation.

## Key Rules

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

## Mistake Prevention

- **Edit settings.json directly?** → Stop. Edit template, run install.sh.
- **Delete a hook file?** → Stop. Stub it first (exit 0), reinstall, then delete.
- **Move framework directory?** → Stop. Update settings.json paths first.
- **Hook errors everywhere?** → Check `~/.claude/circuit_breakers/`. Delete state file or wait 60s.
- **`pip install` in a hook?** → Stop. Use `uv run` instead.

Full guide: `docs/framework-guide-ko.html` | Architecture: `.claude/ARCHITECTURE.md`
