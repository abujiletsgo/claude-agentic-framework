<!-- GIT_HASH: e4fa584b5a4faf462e9cac475177d68540b361c8 -->
<!-- GENERATED: 2026-04-09 -->
<!-- PRIME_VERSION: 2.0 -->

# Project Context Cache

## 🎯 Project Overview
- **Name**: CAF Team (Claude Agentic Framework v5.0 — Sprint System + Research Intelligence)
- **Type**: Private fork of claude-agentic-framework with sprint orchestration + research intelligence
- **Primary Languages**: Python (hooks, lib, scripts), Bash (install, bin), Rust (caf-hooks binary), TypeScript (apps/observability)
- **Tech Stack**: tmux, Textual TUI (dashboard), mempalace/AAAK, gstack (subtree at global-skills/gstack/), MCP servers (papers, sourcegraph, papersflow, context7), Bun (observability server), Vue (observability client), SQLite (events.db)
- **Status**: Fork restructure complete. Directories renamed (skills/→global-skills/, agents/→global-agents/, hooks/→global-hooks/). CAF upstream merged. Dashboard added (Textual). gstack subtree added.

## 📚 Documentation Available
- `CLAUDE.md` — primary project instructions (mode, structure, rules)
- `README.md` — generated via scripts/generate_docs.py
- `ADMIN.md` — admin/ops guide
- `QUICKSTART.md` — contributor quickstart
- `PLAN.md` — full sprint/implementation plan (55KB)
- `.claude/ARCHITECTURE.md` — blast-radius table, Mermaid diagram, IPC flow, data lineage, hook registry, duplication warnings (regenerated 2026-04-11, git 2755665e)
- `docs/framework-guide-ko.html` — full framework guide in Korean
- `guides/` — additional guides
- `global-skills/gstack/` — gstack subtree has its own CLAUDE.md, ARCHITECTURE.md, AGENTS.md, etc.

## 🔒 Security Audit (Local Skills)
**Status**: CLEAN — No local `.claude/skills/` (all skills in `global-skills/` managed by install.sh symlinks). Damage-control hooks active (100+ patterns in `global-hooks/damage-control/patterns.yaml`). SHA-256 skill integrity via `verify_skills.py` at SessionStart.

## 🔧 Claude Code Integration
- **Agents**: 18 (academic-researcher, agent-watchdog, builder, code-researcher, critical-analyst, debugger, docs-scraper, health-checker, meta-agent, onboard-builder, onboard-planner, orchestrator, project-architect, researcher, scout-report-suggest, sprint-lead, validator + orchestrator-reference)
- **Commands**: 17 (arch-map, commit, costs, debug, fusion, kr, live, loadbundle, orchestrate, plan, prime, refine, research, review, rlm, test, worktree)
- **Skills**: 30 (arch-map, buddy, change-validator, code-review, docs, error-analyzer, facts, gstack, health, issue-scoper, knowledge-db, makeskill, onboard, orchestrate, project-adapter, quickstart, refactoring-assistant, research-academic, research-code, research-docs, research-news, rollback, security-scanner, skill-builder, solve, sprint, test-generator, test-scout, tidy, worktree)
- **Hooks active**: hooks_SessionStart (check_gstack.py, launch_live_tui.py), hooks_SubagentStart (write_agent_live.py), hooks_SubagentStop (write_agent_live.py), hooks_UserPromptSubmit (write_prompt_group.py), damage-control framework
- **Rust binary**: `caf-hooks/` — 12 hooks, ~3040 LOC, 6-32x faster than Python equivalents
- **Install**: `bash install.sh` — symlinks all agents/commands/skills to `~/.claude/`, writes `~/.claude/settings.json`

## 🏗️ Architecture Highlights

Key blast-radius rules (from `.claude/ARCHITECTURE.md`):

| Changed | Must Also Update | Command |
|---------|-----------------|---------|
| `templates/settings.json.template` | All hook paths validated at install | `bash install.sh` |
| `data/model_tiers.yaml` | `scripts/generate_docs.py` reads this → README/CLAUDE.md tier tables | `uv run scripts/generate_docs.py` |
| `global-hooks/damage-control/patterns.yaml` | `unified-damage-control.py` runtime load | `uv run scripts/run_tests.py --fast` |
| Any `global-agents/*.md` | Re-symlink + regenerate docs | `bash install.sh && uv run scripts/generate_docs.py` |
| Any `global-skills/*/` | Re-symlink + regenerate docs | `bash install.sh && uv run scripts/generate_docs.py` |
| `caf-hooks/src/**/*.rs` | Rebuild Rust binary | `cd caf-hooks && cargo build --release` |
| `.claude/PROJECT_CONTEXT.md` | Written by `/prime`, read by `auto_prime_inject.py` at SessionStart | `/prime` to regenerate |

Critical workflow paths:
- **Install/update**: Edit `templates/settings.json.template` → `bash install.sh` (never edit settings.json directly)
- **Run Python**: `uv run <script>` (never `pip install`)
- **Generate docs**: `uv run scripts/generate_docs.py`
- **Run tests**: `uv run scripts/run_tests.py --fast`
- **Sprint orchestration**: `/sprint` skill → spawns tmux sessions with sprint-lead agents
- **Live dashboard**: Auto-launched by `launch_live_tui.py` at SessionStart; `write_agent_live.py` tracks subagent activity

🗺️ Architecture map: EXISTS at `.claude/ARCHITECTURE.md` (date-stamped 2026-04-08, no git hash in header — consider `/arch-map` to regenerate with current hash).

## 💡 Key Insights
- **Private fork model**: caf-team is a private fork of CAF upstream (remote "caf"). `git pull caf main` to update upstream. gstack is a git subtree at `global-skills/gstack/` (~400+ files added recently).
- **Rust binary for performance**: `caf-hooks/` replaces Python hook implementations for speed-critical paths (damage-control, memory writer, fact extractor, epistemic guard). 6-32x faster.
- **Dashboard recently added**: Textual TUI dashboard (dashboard/caf_dashboard.py) added in last 5 commits. Some dashboard files appear deleted in working tree (unstaged changes) — check `git status` before assuming they're gone.
- **Sprint system**: `global-skills/sprint/` orchestrates work by spawning tmux panes with sprint-lead agents (full root Claude sessions). Graceful degradation when tmux absent.
- **AAAK/mempalace**: Storage only — never IPC/prompts. All IPC is plain text/JSON, debuggable with cat/jq.
- **Auto-memory pipeline**: `auto_fact_extractor.py` (PostToolUse) → FACTS.md; `auto_memory_writer.py` (Stop) → MEMORY.md; `validate_facts.py` (Stop) prunes >90 days.

## 🤝 Team Recommendation
**Complexity Score**: 8.0

**Indicators Detected**:
- ✅ Multi-layer architecture (observability frontend/backend + Rust hooks + Python lib + TUI dashboard) — weight 2.0
- ✅ Multiple technologies (Python, Bash, Rust, TypeScript/Vue, YAML, SQL) — weight 1.5
- ✅ Large codebase (1060 tracked files) — weight 1.0
- ✅ Security concerns (damage-control system, circuit breakers, pattern matching) — weight 2.0
- ✅ Custom/complex stack (tmux sprint system, gstack subtree, Rust hooks, Textual TUI) — weight 1.5

**Recommendation**: Full Development Team for large changes; single-agent sufficient for targeted edits given well-documented blast-radius table in ARCHITECTURE.md.

---

## Change Detection

This cache will be invalidated automatically when:
- Git commit hash changes (pull, commit, checkout)
- .claude/PROJECT_CONTEXT.md is deleted
- /prime is run with --force flag

To force re-analysis: `rm .claude/PROJECT_CONTEXT.md && /prime`
