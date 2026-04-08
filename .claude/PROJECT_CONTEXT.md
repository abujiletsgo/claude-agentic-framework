<!-- GIT_HASH: 45cfaf15185ea53c7eca91145f82c8914529a1a3 -->
<!-- GENERATED: 2026-04-09 -->
<!-- PRIME_VERSION: 2.0 -->

# Project Context Cache

## Project Overview
- **Name**: CAF Team (CAF v5.0 — Sprint System + Research Intelligence)
- **Type**: Private fork of claude-agentic-framework with sprint orchestration + research intelligence
- **Primary Languages**: Bash (bin scripts), Python (lib, hooks, dashboard), YAML (configs), Markdown (skills, agents)
- **Tech Stack**: tmux, Textual TUI, mempalace/AAAK, gstack (subtree), MCP servers (paper-search, sourcegraph, papersflow, context7)
- **Status**: BUILD COMPLETE — 28 files, all validated. Next: restructure as CAF fork + gstack subtree.

## Build Status
28 files built across Phases 1-6 + fixes. All passing validation.
- Phase 1: sprint_config.yaml, gstack-bridge, sprint-event
- Phase 2: tmux-sprint (8 commands)
- Phase 3: sprint SKILL.md, sprint-lead.md, 3 hooks
- Phase 4: TUI dashboard (7 files)
- Phase 5: toon_utils.py, researcher.md, code-researcher.md, academic-researcher.md, 4 research skills
- Phase 6: caddy_config.yaml, model_tiers.yaml, mempalace.yaml, settings.json.template

## Architecture Decision: Private Fork
- caf-team = private fork of claude-agentic-framework (upstream remote "caf")
- gstack = git subtree at global-skills/gstack/ (upstream remote "gstack")
- Private additions (sprint, research) are commits on top
- `git pull caf main` updates CAF; `git subtree pull` updates gstack

## Next Task: Fork Restructure
Rename directories to match CAF layout:
- skills/ → global-skills/
- agents/ → global-agents/
- hooks/ → global-hooks/
- bin/, lib/, data/, dashboard/, templates/ stay the same
Then set up remotes and merge CAF history.

## Outstanding Items (post-restructure)
- global-skills/worktree/SKILL.md — add /worktree sprint subcommand
- global-skills/orchestrate/SKILL.md — add sprint strategy + research dispatch table
- scripts/generate_docs.py — register new skills/agents
- gstack-bridge: update to look in global-skills/gstack/ first

## Key Constraints
- AAAK for storage only, never IPC/prompts
- gstack is forked (subtree), can modify but prefer lead prompt injection
- All IPC plain text/JSON, debuggable with cat/jq
- Graceful degradation when tmux/gstack/mempalace absent
- Shell: shellcheck, Python: py_compile, YAML: yaml.safe_load
