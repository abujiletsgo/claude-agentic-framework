# PO Brief — CAF Team (Claude Agentic Framework)

## What This Project Is
Private fork of the Claude Agentic Framework with sprint orchestration, research intelligence, and a cmux-native dashboard. Used to coordinate multi-agent teams for complex software tasks.

## Active Domain Leads
- frontend-lead: N/A (no frontend app — this is a CLI/TUI framework)
- backend-lead: Python (hooks, lib/, bin/ scripts)
- data-lead: SQLite (events.db), YAML configs (data/)
- infra-lead: Bash install scripts, settings.json template, Rust binaries (caf-hooks/, caf-hud/)
- qa-lead: pytest (tests/)
- security-lead: damage-control hooks, SHA-256 skill integrity, path protection

## Custom Leads
- hooks-lead: base=backend-lead, domain="global-hooks/, caf-hooks/ (Rust binary), hook event system"
- cmux-lead: base=backend-lead, domain="bin/cmux-sprint, lib/cmux_client.py, tmux session management"
- dashboard-lead: base=backend-lead, domain="dashboard/ scripts, apps/observability/ (Bun+Vue+SQLite)"

## What "Good" Looks Like
- All hooks execute under 100ms (Rust binary paths preferred for hot paths)
- No direct settings.json edits — always via templates/settings.json.template + install.sh
- New agents/skills follow existing frontmatter conventions
- Tests pass: uv run pytest tests/

## Team Norms
- uv run for all Python — never pip install
- Edit templates/settings.json.template → bash install.sh (never edit settings.json directly)
- Never delete hook files that settings.json references — stub first, reinstall, then delete
- Big outputs (>1000 tokens) → save to /tmp/claude/ and reference

## Out of Scope
- No Textual TUI dashboard (removed 2026-04-09)
- No mempalace (removed in v5.0 CAF upstream merge)
- gstack is no longer vendored here — it self-manages via /gstack-upgrade at ~/.claude/skills/gstack. Don't re-add a global-skills/gstack/ subtree. caf's only gstack-derived skill is the /gemini overlay (global-skills/gemini/).
