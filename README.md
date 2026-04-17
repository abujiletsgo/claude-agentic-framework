# Claude Agentic Framework

> One repo, one install, one source of truth. Multi-agent orchestration platform for Claude Code.

## What You Get

- **22 Agents** — Opus-first (2 Opus + 4 Haiku)
- **17 Commands** for delegation, orchestration, and planning
- **28 Skills** for the full engineering lifecycle
- **10 Guides** covering context engineering to multi-agent patterns
- **46 Hooks** across 16 event types (damage-control, observability, framework)
- **Knowledge Pipeline**: SQLite FTS5 persistent memory for cross-session learning
- **Caddy Classifier**: Automatic task routing (direct / orchestrate / rlm / fusion)
- **RepoMap**: TreeSitter symbol index auto-generated for large repos (≥200 files)
- **Multi-Model Tiers**: Right model for the right task (50-60% cost savings)

## Quick Start

```bash
git clone https://github.com/yourusername/claude-agentic-framework.git
cd claude-agentic-framework
./install.sh
```

Then in Claude Code:

```bash
/prime              # Load project context (cached after first run)
/research "topic"   # Delegate research to sub-agent
/orchestrate "goal" # Multi-agent coordination
```

## Architecture

```
global-agents/       22 agents (22 root + 0 team)
global-commands/     17 commands
global-skills/       28 skills
global-hooks/        46 hooks across 16 events
guides/              10 engineering guides
docs/                5 reference docs
data/                model_tiers.yaml + knowledge-db/
templates/           settings.json.template
archive/             Archived commands, skills, hooks
```

## Model Tiers

```
    Opus (2): orchestrator, project-architect
  Sonnet (15): po, critical-analyst, researcher, meta-agent, scout-report-suggest, builder, debugger, onboard-builder, onboard-planner, academic-researcher, code-researcher, frontend-consultant, backend-consultant, architecture-consultant, security-consultant
   Haiku (4): docs-scraper, validator, agent-watchdog, health-checker
```

Config: `data/model_tiers.yaml`

## Commands

```
  - /arch-map
  - /commit
  - /costs
  - /debug
  - /fusion
  - /kr
  - /loadbundle
  - /ntask
  - /orchestrate
  - /plan
  - /prime
  - /refine
  - /research
  - /review
  - /rlm
  - /test
  - /worktree
```

## Skills

```
  - arch-map
  - change-validator
  - code-review
  - consult
  - docs
  - error-analyzer
  - facts
  - health
  - issue-scoper
  - knowledge-db
  - makeskill
  - onboard
  - orchestrate
  - project-adapter
  - quickstart
  - refactoring-assistant
  - research-academic
  - research-code
  - research-docs
  - research-news
  - rollback
  - security-scanner
  - skill-builder
  - solve
  - test-generator
  - test-scout
  - tidy
  - worktree
```

## How It Works

Every user interaction passes through a pipeline of hooks:

```
User prompt → [Caddy classifies task] → Claude processes
→ [PreToolUse: damage control + lock manager]
→ Tool executes
→ [PostToolUse: logging + error analysis + cost warnings + knowledge extraction]
→ Session end → [Store knowledge to SQLite]
→ Session start → [Inject past learnings + RepoMap for large repos]
```

See `docs/framework-guide-ko.html` for the complete framework guide.

## What Fires When

| Event | Hook | Matcher | Purpose |
|-------|------|---------|---------|
| SessionStart | session_startup.py | — | SHA-256 skill integrity check, init locks |
| SessionStart | repo_map.py | — | Symbol index for repos ≥200 source files |
| UserPromptSubmit | kr_mode.py | — | Korean language mode |
| UserPromptSubmit | auto_prime_inject.py | — | Inject PROJECT_CONTEXT.md; force /prime if missing |
| UserPromptSubmit | analyze_request.py | — | Caddy: classify task (direct/orchestrate/rlm/fusion) |
| UserPromptSubmit | auto_delegate.py | — | Inject delegation recommendation |
| PreToolUse | session_lock_manager.py | Read\|Edit\|Write | File conflict detection |
| PreToolUse | unified-damage-control.py | Bash\|Edit\|Write | Block destructive commands |
| PreToolUse | auto_review_team.py | Bash | Team coordination for risky commands |
| PostToolUse | session_lock_manager.py | (any) | Release file locks |
| PostToolUse | context-bundle-logger.py | Bash\|Write\|Edit | Snapshot session state |
| PostToolUse | auto_cost_warnings.py | * | Budget alerts |
| PostToolUse | auto_error_analyzer.py | Bash | Analyze Bash failures |
| PostToolUse | auto_refine.py | Write\|Edit | Trigger refine on writes |
| PostToolUse | auto_dependency_audit.py | Write\|Edit | Check deps on file changes |
| PostToolUse | auto_context_manager.py | Bash\|Write\|Edit | Compress cold tasks at 70% context |
| PostToolUse | auto_voice_notifications.py | Bash\|Write\|Edit | Voice alerts |
| PostToolUse | auto_team_review.py | Write\|Edit | Team review after writes |
| PostToolUse | auto_fact_extractor.py | Bash\|Write | Extract verified facts → .claude/FACTS.md |
| Stop | session_lock_manager.py | — | Cleanup all locks |
| Stop | check_lthread_progress.py | — | Validate RLM state |
| Stop | auto_memory_writer.py | — | Write session summary → .claude/MEMORY.md + KG diary |
| Stop | validate_facts.py | — | Prune 90-day stale entries from FACTS.md |
| Stop | voice_done.py | — | Audio notification on session end |
| SubagentStart | subagent_tracker.py | — | Track subagent spawning |
| SubagentStart | orch_depth_tracker.py | — | Track orchestration nesting depth |
| SubagentStop | subagent_tracker.py | — | Track subagent completion |
| SubagentStop | orch_depth_tracker.py | — | Track orchestration depth on stop |
| SubagentStop | session_cost_tracker.py | — | Record agent transcript cost |
| PreCompact | pre_compact_preserve.py | — | Preserve task state + extract decisions to KG |

## Subsystems

| Subsystem | Purpose |
|-----------|---------|
| **Damage Control** | Block/confirm destructive Bash commands; protect sensitive file paths |
| **Caddy Classifier** | Classify every prompt on 4 dimensions; route to right strategy |
| **Knowledge Pipeline** | Persistent cross-session learning via SQLite FTS5 |
| **RepoMap** | TreeSitter symbol index auto-generated for repos ≥200 source files |
| **Circuit Breakers** | Prevent runaway hook execution; auto-recovers after 60s |
| **Session Management** | Init, file conflict detection, cleanup |

## Key Concepts

1. **Context Engineering** -- Strip permanent context, load on-demand with `/prime`
2. **Sub-Agent Delegation** -- Heavy tasks run in isolation via `/research`
3. **Multi-Agent Orchestration** -- `/orchestrate` coordinates agent fleets
4. **RLM Architecture** -- `/rlm` for infinite-scale codebase analysis
5. **F-Threads (Fusion)** -- `/fusion` for best-of-N critical code
6. **Knowledge Pipeline** -- Persistent cross-session memory via SQLite FTS5
7. **Anti-Loop Guardrails** -- Circuit breakers prevent infinite agent loops
8. **Caddy Classifier** -- Auto-routes each prompt to the right execution strategy
9. **RepoMap** -- TreeSitter symbol index injected for large repos automatically

## Installation

### Prerequisites

- Claude Code CLI (0.1.x+)
- Python 3.10+ and `uv`
- Git

### Install

```bash
./install.sh
```

The installer:
1. Validates all hook files exist
2. Generates `settings.json` from template
3. Symlinks commands, skills, and agents to `~/.claude/`
4. Verifies dependencies (uv, python3, git)

### Uninstall

```bash
./uninstall.sh
```

## Configuration

- **settings.json**: Generated from `templates/settings.json.template` — edit template, not settings.json directly
- **Model tiers**: `data/model_tiers.yaml` — centralized agent-to-model mapping
- **Damage control patterns**: `global-hooks/damage-control/patterns.yaml`
- **Knowledge pipeline**: `~/.claude/knowledge_pipeline.yaml`
- **Caddy classifier**: `~/.claude/caddy_config.yaml`

## Documentation

| File | Contents |
|------|---------|
| `docs/framework-guide-ko.html` | Complete framework guide — start here as a new installer |
| `CLAUDE.md` | Claude Code execution protocol |
| `global-hooks/damage-control/README.md` | What commands are blocked and why |
| `global-hooks/framework/caddy/INTEGRATION.md` | Caddy classifier architecture |
| `global-hooks/framework/knowledge/README.md` | Knowledge pipeline details |
| `guides/` | 10 engineering guides (context, multi-agent, RLM, etc.) |
| `docs/` | 5 reference documents |

## HTML Docs

Interactive documentation (Korean):

| Page | Description |
|------|-------------|
| [`docs/framework-guide-ko.html`](docs/framework-guide-ko.html) | 종합 운영 가이드 — 전체 architecture, hooks, agents, memory, context, workflows (Korean + English) |
| [`docs/MEMORY_ARCHITECTURE.md`](docs/MEMORY_ARCHITECTURE.md) | Memory system — 4-layer architecture, compaction pipeline |
| [`docs/SECURITY_BEST_PRACTICES.md`](docs/SECURITY_BEST_PRACTICES.md) | Security — damage control, path protection, patterns |
| [`docs/ROLES_AND_RESPONSIBILITIES.md`](docs/ROLES_AND_RESPONSIBILITIES.md) | Agent roles — orchestrator, researcher, scout, architect |

## Guides

See `guides/` for 10 comprehensive engineering guides and `docs/` for 5 reference documents.

## Contributing

1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Run `uv run scripts/generate_docs.py` to update docs
5. Submit PR

---

*This README is auto-generated by `scripts/generate_docs.py`. Do not edit manually.*
*Run `uv run scripts/generate_docs.py` after adding/removing agents, commands, or skills.*

<!-- AUTO-DOC-STAMP:22a-17c-28s-46h -->
