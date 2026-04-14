# Plan: CAF v5.1 — What's Next

**Status**: Draft (generated from current system state for /autoplan review)
**Date**: 2026-04-14
**Branch**: main
**Purpose**: Surface what's working, what's incomplete, and get direction on what to build next.

---

## Where We Are Right Now

CAF is a private fork of claude-agentic-framework. It has evolved significantly from the original sprint/tmux plan. Current state:

### What's Live and Working

**Orchestration layer (the big bet)**
- `/orchestrate` skill uses a consultant-first model: Wave 0a is user ↔ consultant dialogue, Wave 0b is researcher parallelism, Wave 1+ is builders. Consultants ask questions and produce specs — they don't write code.
- Runs are persisted to `~/.caf/orch/{id}/` with full audit trail (meta.json, events.jsonl, prompts/, results/, shared/)
- `bin/orch-shared` is the IPC bus: init, broadcast, ask-pm, merge-results, write-retro

**Rust hook binary (caf-hooks)**
- 25 hooks compiled to a single Rust binary. Covers all 14 event types.
- Key behaviors: session recording, memory persistence, fact extraction, cost tracking, damage control (100+ patterns), orchestrator depth/tool guards, epistemic injection.
- New this session: `session_recorder.rs` records every session to `~/.caf/sessions/{id}.jsonl`

**Run Explorer (the dashboard)**
- Vue 3 + Bun app at `:3001` (server) / `:5173` (client dev)
- Reads `~/.caf/orch/` for run history, `~/.caf/sessions/` for session history
- Sessions layer is new and uncommitted: SessionListView, SessionDetailView, sessionParser.ts, sessions handler
- Has: run list/detail, live event feed, cost tracking, lead accordion, comparison view, health view

**Global hooks (Python)**
- 128 Python hook scripts across the framework
- session_startup.py orchestrates SessionStart: lock → verify → prime → inject_skills
- Memory/facts are auto-written at Stop, auto-injected at SessionStart

**Agent ecosystem**
- 22 agents: orchestrator, po, 4 consultants (arch, backend, frontend, security), builder, debugger, validator, researcher, academic-researcher, code-researcher, meta-agent, and others
- Lead agents were REMOVED (architecture-lead, backend-lead, etc.) — replaced by read-only consultants that ask questions not write code

**Research intelligence**
- 4 domain research skills: research-academic, research-code, research-news, research-docs
- academic-researcher + code-researcher agents (MCP-backed)
- lib/toon_utils.py for token-efficient inter-agent data encoding

**cmux integration** (caf-team specific — not upstream CAF)
- `bin/cmux-sprint` replaces the old tmux-sprint concept
- cmux is the default terminal multiplexer for caf-team

**Install + ops**
- `bash install.sh` builds Rust binary, links all global-* dirs, generates settings.json
- `install.sh doctor` runs full health check via caf-hooks doctor subcommand
- Tests: 14 test modules in tests/audit/ covering hooks, orchestration, session pipeline

---

## What's Incomplete / In-Flight

### Session layer (uncommitted)
- `session_recorder.rs` records sessions to `~/.caf/sessions/` — new, uncommitted
- `sessionParser.ts` + `SessionListView.vue` + `SessionDetailView.vue` — new, uncommitted
- No shared schema between recorder (Rust) and parser (TypeScript) — field names are implicit
- Session data not yet surfaced anywhere meaningful beyond the list view

### Known gaps (from architecture review today)
- Port numbers hardcoded in two places (server config + client config)
- `~/.caf/orch/` base path defined in both `config.ts` and `bin/orch-shared` — not DRY
- Damage control patterns split across Rust (settings.json rules) and Python (patterns.yaml) — must be kept in sync manually
- `specs/PLAN.md` is stale — describes tmux-based sprint system that was superseded by cmux + consultant model

### Missing / uncertain
- No project-level grouping in session view (sessions from different projects mixed)
- No way to correlate a session to the orch runs it spawned
- TUI dashboard (Textual/sprint_tui.py) from old plan — never built, replaced by run-explorer
- `apps/observability/` exists as a separate app — its relationship to run-explorer is unclear. Duplication?
- `bin/cdash`, `bin/cteam`, `bin/open-task-pane` — bins that may no longer be used now that cmux-sprint is the primary orchestration surface
- mempalace integration — `.mempalace/` directory exists with knowledge_graph.sqlite3 but unclear what actively writes/reads it now that sprint hooks were removed

---

## Proposed Next Directions (for review)

These are guesses. I want /autoplan to help me validate which is right.

**Option A: Finish what's started**
Commit the session layer, add schema validation between Rust/TS, correlate sessions to orch runs in the UI, clean up the port/path duplication.

**Option B: Strengthen the consultant model**
The consultant-first orchestration is the core bet. Make it better: better question batching, better spec → builder handoff, better acceptance criteria validation.

**Option C: Observability consolidation**
`apps/observability/` and `apps/run-explorer/` partially overlap. Merge or clearly delineate. The observability app reads events.db (SQLite from hook events), run-explorer reads file-based JSONL. Pick one source of truth.

**Option D: cmux-sprint as the primary /sprint**
The old sprint plan described a PM → Lead → Worker hierarchy via tmux panes. cmux can do this. Build it properly as a `/sprint` skill on top of cmux.

**Option E: Upstream contribution**
Extract the terminal-agnostic parts back to claude-agentic-framework (upstream). caf-team becomes the cmux-opinionated layer on top.

---

## Key Questions for /autoplan CEO Review

1. Is the consultant model (read-only consultants → spec → builders) the right architecture, or does it add friction without adding quality?
2. Is run-explorer the right dashboard surface, or should it be integrated into cmux-sprint as panels?
3. What is the relationship between caf-team and upstream claude-agentic-framework? Is caf-team meant to be upstreamed or permanently diverged?
4. Are the 128 Python hooks + 25 Rust hooks too complex? What's the maintenance cost at this scale?
5. What does "done" look like for caf-team? Ship it as a product? Use it internally? Open source it?
