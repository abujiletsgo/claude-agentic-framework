<!-- GIT_HASH: 1be1369cec7c5bda78a6bf8087484293dede3b78 -->
<!-- GENERATED: 2026-04-13 -->
<!-- PRIME_VERSION: 2.0 -->

# Project Context Cache

## 🎯 Project Overview
- **Name**: CAF Team (Claude Agentic Framework v5.0 — Sprint System + Research Intelligence)
- **Type**: Private fork of claude-agentic-framework with sprint orchestration + research intelligence
- **Primary Languages**: Python (hooks, lib, scripts), Bash (install, bin), Rust (caf-hooks binary, caf-hud TUI), TypeScript (apps/observability)
- **Tech Stack**: tmux/cmux, Rust TUI (caf-hud), MCP servers (papers, context7), Bun (observability server), Vue (observability client), SQLite (events.db)
- **Status**: Active development. 34 commits since last prime. Key additions: dynamic leads, CWD-scoped dashboards, event stream, PO model with question batching, 3-wave orchestration model, caf-hud always-on TUI.

## 📚 Documentation Available
- `CLAUDE.md` — project instructions (model tiers, autonomy rules, epistemic discipline)
- `README.md` — full project overview
- `QUICKSTART.md` — setup guide
- `ADMIN.md` — admin/maintenance notes
- `.claude/ARCHITECTURE.md` — full dependency map (10 commits behind — run `/arch-map` to regenerate)
- `docs/` — framework guide (HTML), additional docs
- `guides/` — usage guides
- `justfile` — all dev commands

## 🔒 Security Audit (Local Skills)
**Status**: CLEAN — No local `.claude/skills/` (all skills in `global-skills/` managed by install.sh symlinks). Damage-control hooks active (100+ patterns in `global-hooks/damage-control/patterns.yaml`). SHA-256 skill integrity via `verify_skills.py` at SessionStart.

## 🔧 Claude Code Integration
- **Hooks**: 45 hooks across 16 events (global-hooks/). Rust binary (caf-hooks) dispatches performance-critical hooks 6-32x faster than Python
- **Global agents**: 40 agents (global-agents/) + 3 project-local agents (.claude/agents/: cmux-lead, dashboard-lead, hooks-lead)
- **Commands**: 16 commands (global-commands/)
- **Skills**: 29 skills (global-skills/)
- **Install**: `bash install.sh` — symlinks all globals to ~/.claude/

## 🏗️ Architecture Highlights

**Key directories**:
- `global-hooks/` — 45 hooks, Rust + Python, damage-control, epistemic guard, memory writer
- `global-agents/` — 40 agents (orchestrator, leads, builders, validators)
- `global-skills/` — 29 skills including orchestrate, research, plan, commit
- `global-commands/` — 16 commands
- `bin/` — executable scripts: cteam, cmux-sprint, orch-shared, caf-ref, cdash, gen-lead, session-event, sprint-event
- `caf-hooks/` — Rust binary workspace member (hook dispatcher)
- `caf-hud/` — Rust TUI dashboard (always-on, idle mode, job tabs)
- `apps/` — observability (Bun/Vue), run-explorer, run-explorer-solo
- `data/` — model_tiers.yaml, caddy_config.yaml, knowledge-db
- `templates/` — settings.json.template (edit this, NOT settings.json directly)
- `lib/` — shared Python libraries
- `scripts/` — maintenance and automation scripts

**Critical "If X changes, update Y" rules**:
| Changed | Must Also Update |
|---------|-----------------|
| `templates/settings.json.template` | Run `bash install.sh` — never edit `~/.claude/settings.json` directly |
| IPC base path `/tmp/caf_orch` | `bin/cmux-sprint`, `bin/orch-shared`, `bin/orch-event`, spawn_hud.py, inject_sprint_context.py, `caf-hud/src/main.rs` (6 files) |
| `data/model_tiers.yaml` | `scripts/model-tiers.sh`, orchestrate SKILL.md references, `cost_tracker.py` tier names |
| `caf-hooks/src/` (any Rust hook) | `cargo build --release` from workspace root |
| `global-agents/*.md` | Run `bash install.sh` to re-symlink |
| `global-skills/*/SKILL.md` | Run `bash install.sh` to re-symlink |
| `bin/orch-shared` (subcommand interface) | `bin/cmux-sprint`, orchestrate SKILL.md, lead-prompt.md template |

**Architecture map**: STALE (~10 commits behind) — run `/arch-map` to regenerate.

## 💡 Key Insights
- **Private fork model**: caf-team is a private fork of CAF upstream (remote "caf"). `git pull caf main` to update. gstack is a git subtree at `global-skills/gstack/`. Never push caf-team to GitHub upstream.
- **Rust-first for performance**: `caf-hooks` replaces Python hook implementations for speed-critical paths. `caf-hud` is always-on Rust TUI with idle mode.
- **PO orchestration model**: `/orchestrate` spawns PO → spec-first domain leads → parallel builders. PO answers Tier 1 questions autonomously, batches Tier 2 for user.
- **3-wave orchestration**: exploration → contracts → build. Dynamic leads generated via `bin/gen-lead`.
- **Event stream**: `bin/orch-shared` provides unified event stream; `bin/session-event` and `bin/sprint-event` for pub/sub. Dashboard now shows live event feed instead of working memory.
- **Settings.json safety**: ALWAYS edit `templates/settings.json.template` and run `bash install.sh`. Never edit settings.json directly. Never delete hook files without stubbing first.
- **cmux over tmux locally**: cmux socket API confirmed viable for local sessions. Use tmux for headless/CI.

## 🤝 Team Recommendation
**Complexity Score**: 8.0 — Full Development Team (but /orchestrate handles this automatically)

---

## Change Detection

This cache will be invalidated automatically when:
- Git commit hash changes (pull, commit, checkout)
- .claude/PROJECT_CONTEXT.md is deleted

To force re-analysis: `rm .claude/PROJECT_CONTEXT.md && /prime`
