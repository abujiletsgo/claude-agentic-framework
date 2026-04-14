<!-- /autoplan restore point: /Users/tomkwon/.gstack/projects/abujiletsgo-caf-team/main-autoplan-restore-20260414-163557.md -->
# Plan: CAF v5.1 — Stability + Dashboard Consolidation

**Status**: Active (direction decided 2026-04-14)
**Branch**: main
**Commit**: f69c539e
**Decided direction**: Option A (finish session layer) + Option C (merge observability → run-explorer)

---

## Decided Direction

- **Audience**: Small team, private use
- **Consultant model**: Good as-is. Keep Wave 0a → spec → builders flow unchanged.
- **Dashboard**: Merge `apps/observability/` into `apps/run-explorer/`. One app, one source of truth.
- **Priority**: Stability + cleanup over new features.
- **cmux**: Still in use as a terminal multiplexer. `cmux-skill` is live. cmux-based agent orchestration (spawning leads into panes) failed — removed. /orchestrate with Agent() calls is the orchestration path.

---

## Current State (post-2026-04-14 cleanup)

### What's live and working
- `/orchestrate` skill: PO + consultant model → spec → parallel builders. Runs persisted to `~/.caf/orch/`.
- `caf-hooks` Rust binary: 48 hooks, 16 event types. session_recorder.rs committed this session.
- `run-explorer`: Vue 3 + Bun at :3001 (server) / :5173 (client). Reads `~/.caf/orch/` + `~/.caf/sessions/`.
  - SessionListView + SessionDetailView committed this session.
- `global-hooks/`: 50 Python hooks.
- 21 agents, 16 commands, 30 skills. cmux-skill still active.
- `bash install.sh`: builds Rust binary, links symlinks, generates settings.json.

### Removed this session (dead experiments)
- `bin/cmux-sprint`, `bin/caf-eval`, `bin/caf-ref`, `bin/cdash`, `bin/cteam`, `bin/gen-lead`, `bin/gstack-bridge`, `bin/open-task-pane`, 3 event scripts
- `lib/cmux_client.py` (cmux agent IPC — only the orchestration client, not cmux itself)
- `check_gstack.py`, `inject_sprint_context.py` (dead hook scripts)
- `specs/PLAN.md` (stale 1278-line tmux sprint plan)
- `.mempalace/` (knowledge graph experiment, nothing wrote to it)

---

## What's Incomplete

### P0 — Implicit session schema (fragile)
- `session_recorder.rs` writes JSONL fields with no contract
- `sessionParser.ts` reads those fields with no contract
- If Rust changes a field name, TypeScript silently reads `undefined`
- **Fix**: Define `apps/run-explorer/shared/types.ts` session schema types that mirror what session_recorder.rs writes. Add a smoke test that parses a real session file.

### P1 — Dashboard consolidation
- `apps/observability/` reads `events.db` (SQLite written by hook PostToolUse events)
- `apps/run-explorer/` reads file-based JSONL (`~/.caf/orch/`, `~/.caf/sessions/`)
- Two apps, two data sources, overlapping purpose
- **Fix**: Identify what observability shows that run-explorer doesn't. Add missing views to run-explorer. Delete `apps/observability/`.
- **Key decision**: SQLite vs JSONL? JSONL is already working, human-readable, append-only. SQLite is queryable. Lean JSONL unless there's a specific query need.

### P1 — Session ↔ orch correlation
- A session in run-explorer has no link to the /orchestrate run it was spawned inside
- **Fix**: session_recorder.rs writes `orch_run_id` when `CAF_ORCH_ID` env var is set. run-explorer shows the link in both directions.

### P2 — Hardcoded ports + paths
- `apps/run-explorer/server/src/index.ts`: port 3001 hardcoded
- Client API base URL hardcoded
- `~/.caf/orch/` path defined in both `config.ts` and `bin/orch-shared`
- **Fix**: env vars with documented defaults. One config file.

### P2 — Project grouping in session view
- Sessions from all projects mixed together
- session_recorder.rs writes `project_root` field — verify this is wired through to the UI

---

## Implementation Phases

### Phase 1: Schema contract (P0, ~2h CC)
1. Audit all fields session_recorder.rs writes to JSONL
2. Add TypeScript types to `apps/run-explorer/shared/types.ts` mirroring those fields
3. Update sessionParser.ts to use the typed interface
4. Add smoke test: read a real `~/.caf/sessions/*.jsonl` file, verify parse doesn't produce undefined fields

### Phase 2: Dashboard consolidation (P1, ~4h CC)
1. Audit `apps/observability/`: what views does it have that run-explorer lacks?
2. Implement missing views in run-explorer (hook event log? per-tool cost breakdown?)
3. Verify JSONL covers the same data as events.db for those views
4. Delete `apps/observability/`
5. Update CLAUDE.md, README, install.sh

### Phase 3: Session ↔ orch correlation (P1, ~3h CC)
1. session_recorder.rs: read `CAF_ORCH_ID` from env, write to session JSONL if set
2. orch-shared init: export `CAF_ORCH_ID` for subprocesses
3. SessionDetailView: show "spawned by orch run X" link if `orch_run_id` present
4. RunDetailView: show list of sessions spawned during this run

### Phase 4: Config cleanup (P2, ~1h CC)
1. `run-explorer/server/src/config.ts`: read port + orch path from env vars
2. `run-explorer/client`: use `VITE_API_URL` env var for API base
3. `bin/orch-shared`: source orch path from same env var or well-known location
4. Document all env vars in README

---

## Premises (for CEO review)

1. JSONL is the right long-term storage format (not SQLite). Simpler, human-readable, already working.
2. The consultant model is correct and stable.
3. One dashboard is strictly better than two partial ones.
4. The session layer is the highest-value incomplete piece (schema fragility is a real risk).
5. Session ↔ orch correlation is genuinely useful for debugging multi-agent runs.

---

## Out of Scope

- cmux as agent orchestration (done, removed)
- Upstream contribution to claude-agentic-framework (diverge for now)
- Strengthening consultant model (good enough)
- New agent types
- TUI dashboard

---

## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|---------|
| 1 | CEO | cmux orchestration removed | Mechanical | P3 (pragmatic) | Tested and failed, burned tokens | Keep cmux-sprint |
| 2 | CEO | JSONL over SQLite | Taste → decided | P5 (explicit) | Already working, human-readable | SQLite (queryable but adds tooling) |
| 3 | CEO | Merge dashboards | Mechanical | P4 (DRY) | Two apps doing same thing | Keep separate |
| 4 | CEO | Consultant model unchanged | Mechanical | P3 (pragmatic) | Working well, no evidence of friction | Strengthen |
