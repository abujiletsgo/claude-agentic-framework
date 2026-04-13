<!-- GIT_HASH: d6ca118d3d61ace719015f4954a477a0436a67a1 -->
<!-- GENERATED: 2026-04-14 -->
<!-- PRIME_VERSION: 2.0 -->

# Project Context Cache

## 🎯 Project Overview
- **Name**: CAF Team (Claude Agentic Framework v5.0 — Consultant + Orchestration Model)
- **Type**: Private fork of claude-agentic-framework with consultant-first planning + execution orchestration
- **Primary Languages**: Python (hooks, lib, scripts), Bash (install, bin), Rust (caf-hooks binary), TypeScript (apps/run-explorer)
- **Tech Stack**: Rust binary (caf-hooks), MCP servers (papers, context7), Bun (run-explorer server), Vue (run-explorer client), SQLite (events.db)
- **Status**: Active development. Rebuilt orchestration model: consultant Wave 0 + researcher + parallel builders. caf-hud retired in favour of run-explorer dashboard.

## 📚 Documentation Available
- `README.md` — project overview (25 agents, 16 commands, 29 skills, 45 hooks)
- `CLAUDE.md` — project instructions (yolo mode, model tiers, execution protocol, epistemic discipline)
- `.claude/PROJECT_CONTEXT.md` — this file (auto-injected at session start)
- `.claude/ARCHITECTURE.md` — full dependency map (run `/arch-map` to regenerate)
- `.claude/FACTS.md` — verified facts (CONFIRMED > GOTCHAS > PATHS > PATTERNS)
- `.claude/MEMORY.md` — recent session summaries
- `docs/framework-guide-ko.html` — full framework guide (Korean)
- `guides/` — 10 engineering guides

## 🔒 Security Audit (Local Skills)
**Status**: CLEAN — No local `.claude/skills/` (all skills in `global-skills/` managed by install.sh symlinks). Damage-control hooks active (100+ patterns in `global-hooks/damage-control/patterns.yaml`). SHA-256 skill integrity via `verify_skills.py` at SessionStart.

## 🔧 Claude Code Integration
- **Hooks**: 45 hooks across 16 event types (132 Python hook files in global-hooks/)
  - PreToolUse: damage-control guardrails, circuit breaker
  - PostToolUse: auto_fact_extractor, cost_tracker, session observability
  - SessionStart: session_startup.py (injects PROJECT_CONTEXT), verify_skills.py
  - Stop: auto_memory_writer.py, validate_facts.py, write_retro
  - SubagentStart/Stop: inject_sprint_context, lead_memory_writer
- **Agents**: 25 agents (3 Opus: orchestrator, project-architect, po | 17 Sonnet | 4 Haiku + 1 reference)
- **Commands**: 16 (arch-map, commit, costs, debug, fusion, kr, loadbundle, orchestrate, plan, prime, refine, research, review, rlm, test, worktree)
- **Skills**: 29 (orchestrate, solve, research-*, test-*, health, tidy, facts, knowledge-db, makeskill, and more)

## 🏗️ Architecture Highlights

### Key Directories
- `global-hooks/` — 45 hooks across damage-control, framework, observability categories
- `global-agents/` — 25 agents symlinked to `~/.claude/agents/` via install.sh
- `global-skills/` — 29 skills symlinked to `~/.claude/skills/` via install.sh
- `global-commands/` — 16 commands symlinked to `~/.claude/commands/` via install.sh
- `caf-hooks/` — Rust binary replacing Python hooks on hot paths
- `bin/` — orch-shared (event stream), cmux-sprint, gen-lead, caf-eval
- `apps/run-explorer/` — Vue 3 + Bun dashboard (Timeline tab reads events.jsonl per run)
- `apps/run-explorer-solo/` — standalone variant (untracked, in progress)
- `data/` — model_tiers.yaml, sprint_config.yaml, knowledge-db/ (SQLite FTS5)
- `templates/` — settings.json.template (EDIT THIS, not settings.json directly)

### Critical "If X changes, update Y" rules
| Changed | Must Also Update |
|---------|-----------------|
| `templates/settings.json.template` | Run `bash install.sh` — never edit `~/.claude/settings.json` directly |
| `data/model_tiers.yaml` | `scripts/model-tiers.sh`, orchestrate SKILL.md references, `cost_tracker.py` tier names |
| `data/sprint_config.yaml` | `bin/cmux-sprint`, `bin/orch-shared` |
| IPC base path `/tmp/caf_orch` | `bin/cmux-sprint`, `bin/orch-shared`, `bin/orch-event`, `inject_sprint_context.py` |
| `caf-hooks/src/` | `cargo build --release` from workspace root |
| `global-agents/*.md`, `global-skills/*/SKILL.md`, `global-commands/*.md` | Run `bash install.sh` to re-symlink |
| `bin/orch-shared` (subcommand interface) | `bin/cmux-sprint`, orchestrate SKILL.md |

### Critical Paths
- **Install flow**: edit `templates/settings.json.template` → `bash install.sh` → symlinks all agents/skills/commands/hooks
- **Orchestrate flow**: `/orchestrate` → consultant Wave 0 (user dialogue) → researcher Wave 0b → spec approval → parallel builders → QA/validator loop → run-explorer Timeline shows events
- **Hook chain**: PreToolUse damage-control → tool executes → PostToolUse (fact extractor, cost tracker, observability) → Stop (memory writer, retro)
- **Rust binary path**: `caf-hooks/target/release/caf-hooks`
- **Dashboard**: `apps/run-explorer/` — Bun server reads `/tmp/caf_orch/<id>/events.jsonl`

## 💡 Key Insights
- **Private fork model**: caf-team is a private fork of CAF upstream (remote "caf"). `git pull caf main` to update. gstack is a git subtree at `global-skills/gstack/`. Never push caf-team to GitHub upstream.
- **Consultant model (new)**: Wave 0 is interactive user ↔ consultant dialogue, not autonomous lead planning. Consultants are read-only agents (no write tools) that ask clarifying questions and produce a spec.
- **No lead layer**: lead agents removed from the orchestration flow. Orchestrator → researchers + builders directly, gated by spec from consultants.
- **Self-healing build loop**: QA failure → consultants re-evaluate (no user) → updated spec → rebuild. Escalates to user after N failures.
- **caf-hud retired**: run-explorer Timeline tab replaced it. Orchestrator writes events.jsonl explicitly at each wave boundary.
- **Rust-first for hooks**: `caf-hooks` replaces Python hook implementations for speed-critical paths.
- **Model tiers enforce cost discipline**: Opus for orchestrator/PO/project-architect, Sonnet for builders/analysts, Haiku for validators/watchdogs.

## 🤝 Team Assessment
**Complexity Score**: 4.5 (multi-layer ×2 + multiple-tech ×1.5 + large-codebase ×1)

**Indicators**:
- ✅ Multi-layer architecture (Python hooks + Vue frontend + Bun server + SQLite)
- ✅ Multiple technologies (Python, Rust, TypeScript, Bash, Vue)
- ✅ Large codebase (~1000+ tracked files)

**Recommendation**: `/orchestrate` for multi-domain changes. Single-agent sufficient for targeted edits.

---

## Change Detection

This cache will be invalidated automatically when:
- Git commit hash changes (pull, commit, checkout)
- .claude/PROJECT_CONTEXT.md is deleted
- /prime is run with --force flag

To force re-analysis: `rm .claude/PROJECT_CONTEXT.md && /prime`
