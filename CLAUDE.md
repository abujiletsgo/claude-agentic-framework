# CAF Team — Sprint System + Research Intelligence

## What This Is

Implementation of CAF v5.0: Sprint System + Research Intelligence upgrade.
The full plan is in `PLAN.md` — read it before doing anything.

## Project Structure

```
PLAN.md                          ← definitive implementation plan (read first)
CLAUDE.md                        ← this file

# Implementation targets (to be created):
bin/                             ← shell scripts (gstack-bridge, sprint-event, tmux-sprint)
lib/                             ← Python utilities (toon_utils.py)
dashboard/                       ← Textual TUI app
  widgets/                       ← TUI widget modules
data/                            ← config YAML files
skills/                          ← skill definitions (sprint, research-*)
agents/                          ← agent definitions (sprint-lead, code-researcher, academic-researcher)
hooks/                           ← hook scripts (SessionStart, SubagentStart, SubagentStop)
```

## Key Rules

- **Read PLAN.md first** — it has detailed specs for every component
- `uv run` for all Python — never `pip install`
- Shell scripts must pass `shellcheck`
- Hook scripts must `py_compile` cleanly
- YAML configs must parse: `python3 -c "import yaml; yaml.safe_load(open('file'))"`
- AAAK is for STORAGE only (mempalace palace writes) — never for prompts, IPC, or anything humans/Claude reads in real-time
- gstack is NEVER modified — only discovered via `bin/gstack-bridge`
- All IPC files are plain text / JSON — debuggable with `cat` and `jq`
- Every component must work when optional dependencies (gstack, tmux, mempalace) are absent

## Build Order

Phase 1 (parallel): sprint_config.yaml, gstack-bridge, sprint-event
Phase 2 (depends on 1): tmux-sprint
Phase 3 (depends on 1, parallel to 2): sprint skill, sprint-lead agent, hooks
Phase 4 (depends on 1, parallel to 2-3): TUI dashboard
Phase 5 (fully parallel): TOON utils, research agents, research skills
Phase 6 (depends on all): integration into CAF (caddy, model_tiers, settings.json.template)
Phase 7: validation

## After Build

All outputs from this repo need to be copied to their final locations in
`~/Documents/claude-agentic-framework/`:
- `bin/*` → `bin/`
- `data/*` → `data/`
- `skills/*` → `global-skills/`
- `agents/*` → `global-agents/`
- `hooks/*` → `global-hooks/`
- `lib/*` → `lib/`
- `dashboard/*` → `dashboard/`

Then run `bash install.sh` in the CAF repo to apply settings changes.
