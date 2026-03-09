# Claude Agentic Framework

> One repo, one install, one source of truth. Multi-agent orchestration platform for Claude Code.

## What You Get

- **8 Agents** across 3 model tiers (Opus/Sonnet/Haiku)
- **15 Commands** for delegation, orchestration, and planning
- **8 Skills** for the full engineering lifecycle
- **15 Guides** covering context engineering to multi-agent patterns
- **26 Hooks** across 6 event types (damage-control, observability, framework)
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
global-agents/       8 agents (8 root + 0 team)
global-commands/     15 commands
global-skills/       8 skills
global-hooks/        26 hooks across 6 events
guides/              15 engineering guides
docs/                11 reference docs
data/                model_tiers.yaml + knowledge-db/
templates/           settings.json.template
apps/observability/  Vue 3 + Bun (ports 4000/5173)
archive/             Archived commands, skills, hooks
```

## Model Tiers

```
    Opus (3): orchestrator, project-architect, critical-analyst
  Sonnet (4): researcher, meta-agent, scout-report-suggest, rlm-root
   Haiku (1): docs-scraper
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
  - /orchestrate
  - /plan
  - /prime
  - /refine
  - /research
  - /review
  - /rlm
  - /test
```

## Skills

```
  - arch-map
  - code-review
  - error-analyzer
  - facts
  - knowledge-db
  - refactoring-assistant
  - security-scanner
  - test-generator
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

See `FRAMEWORK_REFERENCE.md` for the complete technical reference.

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
| Stop | auto_memory_writer.py | — | Write session summary → .claude/MEMORY.md |
| Stop | validate_facts.py | — | Prune 90-day stale entries from FACTS.md |
| Stop | voice_done.py | — | Audio notification on session end |
| PreCompact | pre_compact_preserve.py | — | Preserve task state into compaction prompt |

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
| `FRAMEWORK_REFERENCE.md` | Complete technical reference — start here as a new installer |
| `CLAUDE.md` | Claude Code execution protocol |
| `global-hooks/damage-control/README.md` | What commands are blocked and why |
| `global-hooks/framework/caddy/INTEGRATION.md` | Caddy classifier architecture |
| `global-hooks/framework/knowledge/README.md` | Knowledge pipeline details |
| `guides/` | 15 engineering guides (context, multi-agent, RLM, etc.) |
| `docs/` | 11 reference documents |

## HTML Docs

Interactive documentation (Korean):

| Page | Description |
|------|-------------|
| [`docs/index.html`](docs/index.html) | Overview — request lifecycle, features, quick install |
| [`docs/agents.html`](docs/agents.html) | Agents — 8 agents, model tiers, global/local, custom agents |
| [`docs/caddy.html`](docs/caddy.html) | Routing — Caddy classifier, 5 strategies, classification examples |
| [`docs/skills.html`](docs/skills.html) | Skills — 7 skills, creating custom skills, team workflows |
| [`docs/hooks.html`](docs/hooks.html) | Hooks — full 26-hook reference, circuit breakers, damage control |
| [`docs/memory-system-ko.html`](docs/memory-system-ko.html) | Memory system — 4-layer architecture, FACTS.md, team attribution |

## Guides

See `guides/` for 15 comprehensive engineering guides and `docs/` for 11 reference documents.

## Contributing

1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Run `uv run scripts/generate_docs.py` to update docs
5. Submit PR

---

*This README is auto-generated by `scripts/generate_docs.py`. Do not edit manually.*
*Run `uv run scripts/generate_docs.py` after adding/removing agents, commands, or skills.*

<!-- AUTO-DOC-STAMP:8a-15c-8s-26h -->
