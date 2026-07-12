<!-- GIT_HASH: abdbeb39a2b23bf91acea01b436e259e9385cbea -->
<!-- GENERATED: 2026-07-12 -->
<!-- PRIME_VERSION: 2.0 -->
<!-- ARCHITECTURE MAP: .claude/ARCHITECTURE.md — full dependency graph, blast-radius table, hook event matrix (STALE: 27 commits behind) -->

# Project Context Cache

## 🎯 Project Overview
- **Name**: CAF Team (Claude Agentic Framework v5.2+ — Consultant + Orchestration Model, Level 7 autonomous)
- **Type**: Private fork of claude-agentic-framework with consultant-first planning + execution orchestration
- **Primary Languages**: Python (hooks, lib, scripts), Bash (install, bin), Rust (caf-hooks binary), TypeScript (apps/run-explorer)
- **Tech Stack**: Rust binary (caf-hooks), MCP servers (papers, context7), Bun + Vue 3 (run-explorer), SQLite events.db (observability server only — client retired), JSONL session/orch dirs in `~/.caf/`
- **Current branch**: `overnight-audit-2026-06-11` (19 commits ahead of last prime — full overnight audit landed here, not yet merged to main)
- **Status**: Active. Post-audit state: Rust damage-control fixed (was silently dropping most patterns), test suite repaired 53→0 failures (173 passed), skills refactored in 5 tranches (A–E), gstack de-vendored (self-manages via /gstack-upgrade, caf keeps only /gemini overlay), 3 commands removed as skill-superseded, voice TTS wired to Notification event. 9 open decisions flagged in `AUDIT-NOTES.md`.

## 📚 Documentation Available
- `README.md` — top-level overview (modified, uncommitted)
- `CLAUDE.md` — project instructions, model tiers, epistemic discipline, mistake prevention (modified, uncommitted)
- `AUDIT-NOTES.md` — full overnight audit log + 9 flagged decisions
- `QUICKSTART.md`, `ADMIN.md`
- `.claude/ARCHITECTURE.md` — dependency graph + blast-radius table (**STALE — 27 commits behind, run /arch-map**)
- `.claude/FACTS.md` — verified episodic facts
- `.claude/MEMORY.md` — recent session summaries
- `.claude/PRODUCT_VISION.md`, `.claude/PO_BRIEF.md` — product context
- `docs/` — caf-deck.html, caf-guide.html, framework-guide-ko.html, etc.
- `guides/` — engineering guides
- `specs/CURRENT-STATE-PLAN.md` — current planning artifact

## 🔒 Security Audit (Local Skills)
**Status**: CLEAN
- `.claude/skills/damage-control/` (local skill): pattern hits are all documentation examples in cookbook/*.md and SKILL.md (install one-liners, test fixtures for the very patterns it blocks) — no dangerous executable code. INFO only.
- New untracked skills `global-skills/qa-cycle/` and `global-skills/ui-flow-audit/` (SKILL.md only, no executables): scanned CLEAN.
- 26 skills changed since last prime (audit tranches A–E): markdown refactors — no dangerous patterns introduced.
- Damage-control hooks active (patterns.yaml + Rust mirror in `caf-hooks/src/hooks/damage_control.rs` — **Rust side was near-inert until fix `35aa8bce`, now working**). SHA-256 skill integrity via verify_skills.py at SessionStart.

## 🔧 Claude Code Integration
- **Hooks**: 47 hooks across 17 events. Rust dispatcher in `caf-hooks/`; Python framework in `global-hooks/framework/`; damage-control in `global-hooks/damage-control/`. Audit fixed 5 Python hook bugs + cost-rounding precedence in caf-hooks.
- **Agents** (22 total):
  - **Opus (2)**: orchestrator, project-architect
  - **Sonnet (15)**: po, critical-analyst, researcher, meta-agent, scout-report-suggest, builder, debugger, onboard-builder, onboard-planner, academic-researcher, code-researcher, frontend-consultant, backend-consultant, architecture-consultant, security-consultant
  - **Haiku (4)**: docs-scraper, validator, agent-watchdog, health-checker
- **Commands** (14 — down from 17; 3 removed as superseded by skills in `24799b6e`)
- **Skills** (31 dirs in global-skills/, incl. 2 NEW untracked: **qa-cycle** — plan-driven full-matrix QA with regression loop; **ui-flow-audit** — navigation/interaction flow audit). Audit tranches: name conformance + routing (A), dead cmux/sprint removal + rollback fix (B), gstack trigger-collision resolution (C), progressive disclosure + dead-file cleanup (D), version-noise removal (E).
- **gstack is NOT vendored** — de-vendored in `abdbeb39`; self-manages via /gstack-upgrade (v1.58 at ~/.claude/skills/gstack); caf ships only the /gemini overlay; caf wins name collisions.

## 🏗️ Architecture Highlights

### Top blast-radius rules (from `.claude/ARCHITECTURE.md` — map is 27 commits stale, verify before relying)
| Changed | Must Also Update |
|---------|-----------------|
| `caf-hooks/src/types.rs` | All hook impls in `caf-hooks/src/hooks/` — recompile with `cargo build -r` |
| `caf-hooks/src/main.rs` (subcommand list) | Hook entries in `templates/settings.json.template` + `install.sh` |
| `apps/run-explorer/shared/types.ts` | Both `server/src/` handlers and `client/src/` composables/views |
| `~/.caf/sessions/*.jsonl` format | `sessionParser.ts` (reader) + `session_recorder.rs` (writer) — no shared schema |
| `templates/settings.json.template` | Run `bash install.sh` — never edit `settings.json` directly |
| `data/model_tiers.yaml` | `global-agents/*.md` model fields + Caddy routing |

### Critical paths
- **Path A — Session Recording**: SessionStart → `caf-hooks session-recorder` → `~/.caf/sessions/{id}.jsonl` → run-explorer `sessionParser.ts` → /api/sessions
- **Path B — Orchestration**: `/orchestrate` → `bin/orch-shared init` → `~/.caf/orch/{id}/` → consultants + builders → `runParser.ts` → run-explorer UI
- **Path C — Memory + Facts**: Stop hook → `auto_memory_writer` → `MEMORY.md`; PostToolUse → `auto_fact_extractor` → `FACTS.md`. Both injected at SessionStart.
- **Path D — Cost Tracking**: SubagentStop → `session_cost_tracker.rs` → `~/.claude/logs/cost_tracking.jsonl` → observability/cost.ts → `/api/costs/*`
- **Path E — Damage Control**: PreToolUse → `damage_control.rs` (Rust regex, runs first) + Python patterns — **add new patterns to BOTH**
- **Path F — Install**: Edit `templates/settings.json.template` → `bash install.sh` → cargo build + symlinks → generates `~/.claude/settings.json`

### Key directories
- `caf-hooks/` — Rust hook binary (single dispatcher for all events)
- `global-hooks/` — Python hooks (framework + damage-control + notifications)
- `global-agents/` (22) | `global-skills/` (31) | `global-commands/` (14)
- `apps/run-explorer/` — Bun server :3001 + Vue3 client :5173 (sole dashboard; 8 bugs fixed in audit)
- `apps/observability/server/` — Bun + SQLite events.db :3002 (client dir DELETED)
- `bin/` — `orch-shared` (event bus), `advisor`
- `templates/settings.json.template` — master config | `data/model_tiers.yaml` — model assignments
- `lib/`, `scripts/`, `tests/` — supporting code (669 tracked files total, down from 1083 after gstack de-vendor + cleanup)

### Architecture map status
🗺️ **STALE — 27 commits behind HEAD.** The audit branch restructured skills and de-vendored gstack; run `/arch-map` to regenerate before relying on the dependency graph.

## 💡 Key Insights
- **Overnight audit (this branch)**: Rust damage-control was near-inert (silently dropped most patterns — fixed); epistemic-guard stems never matched (fixed); suite went 53 failures → 0 (173 passed); pytest collection unblocked (no import-time sys.exit). 9 decisions await review in `AUDIT-NOTES.md`.
- **gstack de-vendored**: subtree removed; gstack self-manages (v1.58); caf ships only /gemini overlay. Its ~54 sub-skills surface directly from ~/.claude/skills/gstack.
- **Voice TTS fix**: notifications now fire on the Notification event (were never firing before `89bcebb5`); macOS `say` voice, no clone.
- **Consultant model**: Wave 0a is interactive user ↔ consultant dialogue producing a spec — consultants never write code. Orchestrator spawns parallel researchers + builders from the spec. Lead agents removed.
- **Single dashboard policy**: run-explorer is the sole dashboard; caf-hud retired; observability client deleted (server still feeds events.db :3002).
- **No shared session schema**: `session_recorder.rs` writes, `sessionParser.ts` reads, `shared/types.ts` defines — all three must move together.
- **Mode is yolo**: `"allow": ["*"]`. Security = damage-control hooks + SHA-256 skill integrity + path protection.
- **Always `uv run` for Python**, never `pip install`. Always edit `templates/settings.json.template` then `bash install.sh`.
- **Uncommitted work in tree**: CLAUDE.md, README.md, MEMORY.md, auto_voice_notifications.py modified; qa-cycle + ui-flow-audit skills untracked — likely intended for the audit branch, commit before merging.

## 🤝 Team Recommendation
**Complexity Score**: 7.5 — multi-layer (2.0) + multiple-tech (1.5) + large-codebase (1.0) + framework-internal complexity (3.0); security concerns 0

**Indicators Detected**:
- ✅ Multi-layer architecture (Rust binary + Python hooks + TS server + Vue client)
- ✅ Multiple technologies (Rust, Python, TypeScript, Bash, Vue3)
- ✅ Large codebase (669 tracked files)
- ❌ Security concerns (CLEAN audit, damage-control active and now actually working)
- ✅ Framework-internal complexity (47 hooks / 17 events, 22 agents, 31 skills, install pipeline)

**Recommendation**: Single-agent sufficient for routine work. For multi-layer changes (hooks + run-explorer + agents simultaneously), spawn a team via `/orchestrate`.

## ✅ Ready to Execute
Agent primed. Context loaded. Ready for instructions.

---

## Change Detection

This cache will be invalidated automatically when:
- Git commit hash changes (pull, commit, checkout)
- .claude/PROJECT_CONTEXT.md is deleted
- /prime is run with --force flag

To force re-analysis: `rm .claude/PROJECT_CONTEXT.md && /prime`
