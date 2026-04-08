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
global-skills/                   ← skill definitions (sprint, research-*)
global-agents/                   ← agent definitions (sprint-lead, code-researcher, academic-researcher)
global-hooks/                    ← hook scripts (SessionStart, SubagentStart, SubagentStop)
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

## Fork Architecture

caf-team is a **private fork** of claude-agentic-framework.

```
caf-team (this repo)
├── upstream remote "caf": claude-agentic-framework (public)
├── git subtree at global-skills/gstack/: gstack repo (when added)
└── private additions: sprint system, research agents, configs
```

### Syncing
- Pull CAF updates: `git pull caf main`
- Pull gstack updates: `git subtree pull --prefix=global-skills/gstack gstack main --squash`
- Never push private sprint/research code to CAF upstream
