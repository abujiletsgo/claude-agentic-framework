<!-- GIT_HASH: 1097c55918e4d55ed6d311a8a5f3815e91271bda -->
<!-- GENERATED: 2026-04-09 -->
<!-- PRIME_VERSION: 2.0 -->

# Project Context Cache

## Project Overview
- **Name**: CAF Team (CAF v5.0 — Sprint System + Research Intelligence)
- **Type**: Private fork of claude-agentic-framework with sprint orchestration + research intelligence
- **Primary Languages**: Bash (bin scripts), Python (lib, hooks, dashboard), YAML (configs), Markdown (skills, agents)
- **Tech Stack**: tmux, Textual TUI, mempalace/AAAK, gstack (subtree, pending), MCP servers (paper-search, sourcegraph, papersflow, context7)
- **Status**: FORK RESTRUCTURE COMPLETE — CAF upstream merged, dirs renamed, all validated.

## Build Status
28 sprint/research files built. Fork restructure done:
- Directories renamed: skills/→global-skills/, agents/→global-agents/, hooks/→global-hooks/
- CAF upstream merged (7 conflicts resolved, kept ours)
- gstack-bridge updated for new paths
- CLAUDE.md updated for fork architecture

## Architecture: Private Fork
- caf-team = private fork of claude-agentic-framework (remote "caf")
- gstack = git subtree at global-skills/gstack/ (PENDING — need repo URL)
- Private additions (sprint, research) are commits on top
- `git pull caf main` updates CAF upstream

## Remaining Items
- gstack subtree: need repo URL to add
- Run generate_docs.py after all edits finalized
- Test sprint system end-to-end when tmux environment available

## Key Constraints
- AAAK for storage only, never IPC/prompts
- gstack is forked (subtree), can modify but prefer lead prompt injection
- All IPC plain text/JSON, debuggable with cat/jq
- Graceful degradation when tmux/gstack/mempalace absent
- Shell: shellcheck, Python: py_compile, YAML: yaml.safe_load
