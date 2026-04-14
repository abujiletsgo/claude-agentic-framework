<!-- GIT_HASH: 7d286ff52652e80d74ac1e0a18eeac58acd9e5f8 -->
<!-- GENERATED: 2026-04-14 -->
<!-- PRIME_VERSION: 2.0 -->
<!-- ARCHITECTURE MAP: .claude/ARCHITECTURE.md — full dependency graph, blast-radius table, hook event matrix -->

# Project Context Cache

## 🎯 Project Overview
- **Name**: CAF Team (Claude Agentic Framework v5.0 — Consultant + Orchestration Model)
- **Type**: Private fork of claude-agentic-framework with consultant-first planning + execution orchestration
- **Primary Languages**: Python (hooks, lib, scripts), Bash (install, bin), Rust (caf-hooks binary), TypeScript (apps/run-explorer)
- **Tech Stack**: Rust binary (caf-hooks), MCP servers (papers, context7), Bun (run-explorer server), Vue 3 (run-explorer client), SQLite (events.db)
- **Status**: Active development. Consultant-first model complete. Lead agents removed, consultant agents added. caf-hud RETIRED. run-explorer is the sole dashboard. Session recording added.

## 📚 Documentation Available
- `CLAUDE.md` — Project rules, mode, model tiers, execution protocol (authoritative)
- `README.md` — User-facing overview
- `QUICKSTART.md` — New contributor onboarding
- `ADMIN.md` — Admin/maintenance notes
- `justfile` — All task automation (build, test, audit, install)
- `docs/framework-guide-ko.html` — Korean framework guide
- `.claude/ARCHITECTURE.md` — Full dependency map (1 commit behind HEAD, effectively FRESH)
- `.claude/FACTS.md` — Verified facts (CONFIRMED > GOTCHAS > PATHS > PATTERNS)
- `.claude/MEMORY.md` — Session summaries (max 30 entries)

## 🔒 Security Audit (Local Skills)
**Status**: CLEAN — No local `.claude/skills/` (all skills in `global-skills/` managed by install.sh symlinks). Damage-control hooks active (100+ patterns in `global-hooks/damage-control/patterns.yaml`). SHA-256 skill integrity via `verify_skills.py` at SessionStart.

## 🔧 Claude Code Integration
- **Hooks**: 48 hooks across 16 event types
  - SessionStart: `session_startup.py` (context injection), skill verify, repo_map
  - PreToolUse: damage-control, circuit_breaker, path protection, Rust hot-path hooks
  - PostToolUse: `auto_fact_extractor`, `activity_logger`, `session_recorder` (new), Rust hooks
  - Stop: `auto_memory_writer`, `validate_facts`
  - SubagentStart/Stop: tracker hooks
- **Agents**: 22 total in `global-agents/` (symlinked via install.sh)
  - Consultants (new): `frontend-consultant`, `backend-consultant`, `architecture-consultant`, `security-consultant`
  - Orchestration: `orchestrator`, `po`
  - Builders: `builder`, `debugger`, `validator`
  - Research: `researcher`, `critical-analyst`, `code-researcher`, `academic-researcher`
  - Support: `meta-agent`, `docs-scraper`, `health-checker`, `agent-watchdog`, `scout-report-suggest`
  - Onboarding: `onboard-builder`, `onboard-planner`
  - Architecture: `project-architect`
- **Skills**: 30 in `global-skills/`
- **Commands**: 16 in `global-commands/`
- **Config**: Edit `templates/settings.json.template` → `bash install.sh`. NEVER edit `~/.claude/settings.json` directly.

## 🏗️ Architecture Highlights

### Quick Reference: "If X changes, update Y"
| Changed | Must Also Update |
|---------|-----------------|
| `global-skills/orchestrate/SKILL.md` | Wave definitions, consultant routing, QA loop rules |
| `ORCH_BASE` (`~/.caf/orch/`) | `bin/orch-shared`, `apps/run-explorer/server/src/config.ts`, `install.sh` |
| `apps/run-explorer/server/src/handlers/*` | `apps/run-explorer/shared/types.ts` (API contracts) |
| `global-agents/<agent>.md` | Run `bash install.sh` to re-symlink to `~/.claude/agents/` |
| `global-skills/*/SKILL.md` | Run `bash install.sh` to re-symlink |
| `caf-hooks/src/` (any Rust hook) | `cargo build --release` from workspace root |
| `templates/settings.json.template` | Run `bash install.sh` |
| IPC schema (events.jsonl, meta.json) | `apps/run-explorer/server/src/services/runParser.ts` |
| `data/model_tiers.yaml` | Agent `model:` frontmatter fields in `global-agents/` |
| `lib/cmux_client.py` socket API | `bin/orch-shared`, `bin/cmux-sprint`, `lib/agent_display.py` |

### Critical Paths
1. **Orchestration**: `/orchestrate` → `global-skills/orchestrate/SKILL.md` → Wave 0 consultant dialogue → spec → orchestrator spawns parallel builders → QA gate → retro written to `~/.caf/orch/<id>/`
2. **Run Explorer**: `apps/run-explorer/server` (Bun, port 3001) + `apps/run-explorer/client` (Vue 3, port 5174) — reads from `~/.caf/orch/` IPC directory
3. **Sessions**: New `session_recorder.rs` Rust hook → writes session events → `sessionParser.ts` → `handlers/sessions.ts` → Vue SessionListView/SessionDetailView
4. **Hooks pipeline**: SessionStart → `session_startup.py` injects `PROJECT_CONTEXT.md` → damage-control (PreToolUse) → Rust binary hooks (hot-path) → Python hooks (complex logic)
5. **Install**: `bash install.sh` → symlinks global-agents/skills/commands/hooks → builds Rust binary → generates settings.json from template

### Directory Map
```
global-agents/       22 agents (symlinked to ~/.claude/agents/)
global-skills/       30 skills (symlinked to ~/.claude/skills/)
global-commands/     16 commands (symlinked to ~/.claude/commands/)
global-hooks/        damage-control, framework hooks
caf-hooks/src/hooks/ 21 Rust hooks (session_recorder.rs is new)
apps/run-explorer/
  client/            Vue 3 + TypeScript (port 5174)
  server/            Bun server (port 3001) — reads ~/.caf/orch/
    handlers/        compare, costs, events, leads, live, orchEvents, runs, sessions
    services/        costTracker, dbReader, evalParser, orchEventReader, runParser, sessionParser, tokenEstimator
  shared/            Shared TypeScript types
lib/                 cmux_client.py, agent_display.py, toon_utils.py
bin/                 orch-shared, cmux-sprint
data/                model_tiers.yaml, sprint_config.yaml, knowledge-db/
templates/           settings.json.template
scripts/             session_startup.py, auto_memory_writer.py, etc.
tests/audit/         Audit test suite (uv run)
```

🗺️ Architecture map is 1 commit behind current HEAD — FRESH.

## 💡 Key Insights
- **Lead agents removed**: All 8 lead agents (`architecture-lead`, `backend-lead`, `frontend-lead`, `debugging-lead`, `docs-lead`, `performance-lead`, `refactoring-lead`, `release-lead`) deleted. Replaced by 4 read-only consultant agents. No more autonomous lead planning.
- **Consultant model**: Wave 0 is interactive user ↔ consultant dialogue. Consultants ask questions and produce spec — they do NOT write code. Orchestrator uses spec to spawn parallel researchers + builders.
- **caf-hud retired**: Rust TUI (`caf-hud/`) removed entirely. Run Explorer (Vue+Bun) is now the sole dashboard.
- **Session recording**: New `session_recorder.rs` Rust hook + `sessionParser.ts` + Vue SessionListView/SessionDetailView. Sessions are queryable alongside runs.
- **Private fork model**: `caf` remote is read-only upstream. Never push caf-team to GitHub. `git pull caf main` to update.
- **Rust binary is hot-path**: `caf-hooks` binary handles PreToolUse + PostToolUse for performance. After ANY Rust change: `cargo build --release` from workspace root.

## 🤝 Team Recommendation
**Complexity Score**: 4.5 (multi-layer×2 + multiple-tech×1.5 + large-codebase×1)

**Indicators**:
- ✅ Multi-layer architecture (Vue + Bun + Rust + Python hooks)
- ✅ Multiple technologies (Rust, TypeScript, Vue, Python, Bash)
- ✅ Large codebase (1149 tracked files)
- ❌ Security concerns (clean)
- ❌ Unfamiliar stack (Tom is the author)

**Recommendation**: Tom is the CAF author — single-agent workflow is appropriate. Use `/orchestrate` for multi-domain tasks.

---

## Change Detection

This cache will be invalidated automatically when:
- Git commit hash changes (pull, commit, checkout)
- .claude/PROJECT_CONTEXT.md is deleted
- /prime is run with --force flag

To force re-analysis: `rm .claude/PROJECT_CONTEXT.md && /prime`
