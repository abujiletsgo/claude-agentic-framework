<!-- GIT_HASH: ec477d8be4ff1662e4464226ebbf879ffbb8f5bd -->
<!-- GENERATED: 2026-07-13 -->
<!-- PRIME_VERSION: 2.0 -->
<!-- ARCHITECTURE MAP: .claude/ARCHITECTURE.md — dependency graph + blast-radius table -->

# Project Context Cache

## 🎯 Project Overview
- **Name**: CAF Team (Claude Agentic Framework v5.3 — post native-parity audit)
- **Type**: Private fork of claude-agentic-framework, consultant-first planning + lean execution layer
- **Governing rule**: **If native Claude Code does it, we don't.** The framework carries only what the platform lacks: interactive consultant dialogue (Wave 0a), adversarial review, damage-control, postmortem lookback, CAF infra. Review/security-review/simplify/debug/research/memory/tasks/scheduling/orchestration fan-out are native.
- **Languages**: Python (hooks, scripts), Rust (caf-hooks binary), Bash (install, bin), TypeScript (apps/run-explorer)
- **Status**: main @ ec477d8b. 2026-07-12 audit landed: damage-control armed (was dormant), 22→8 agents, 31→16 skills, 14→9 commands, 47→31 hook firings, model tiers on Claude 5 family, postmortem observability layer.

## 🔒 Security
- **damage-control WIRED + verified**: PreToolUse (Bash|Edit|Write) → Rust `caf-hooks damage-control`, runs FIRST. 118 patterns via fancy-regex (regex crate has no lookahead — patterns silently dropped before; now compile failures warn loudly). Verified: force-push both spellings, hard reset, recursive delete, UPDATE-without-WHERE block; --force-with-lease passes.
- **Tamper-proof against the agent by design**: patterns.yaml read-only, damage-control/ no-delete, settings.json zero-access, template-neutering blocked by permission classifier. Pattern changes are a HUMAN action.
- **Known false positives**: prose containing `eval`, commit messages quoting delete commands, chmod on repo's own bin/. Workaround: Edit/Write tools, not shell heredocs. See AUDIT-NOTES FL11.

## 🔧 Claude Code Integration
- **Agents (8)**: fable: critical-analyst · opus: architecture-consultant, security-consultant · sonnet: frontend-consultant, backend-consultant, builder (self-testing, has dead-ends retry ledger), onboard (planner+builder merged), academic-researcher. Haiku tier intentionally EMPTY (relay agents retired).
- **Skills (16)**: arch-map, caf-health (renamed from health — was shadowing gstack's), consult, facts, gemini, knowledge-db, makeskill (absorbed skill-builder), onboard, orchestrate, **postmortem** (failure lookback), project-adapter, qa-cycle, rollback, tidy, ui-flow-audit, worktree
- **Commands (9)**: commit, costs, fusion, kr, loadbundle, ntask, plan, refine, rlm
- **Hooks (31 firings / 16 events)**: 0.148s per Bash call (was 0.584s). Caddy classifier: telemetry always, injection only ≥80% confidence, only recommends skills that exist on disk ($CADDY_CONFIG overrides config path for tests).
- **Default model**: fable (template-pinned; install.sh no longer resets it)
- **gstack**: third-party (garrytan/gstack v1.58.3), self-managed at ~/.claude/skills/gstack, 54 sub-skills, zero name collisions with CAF. Never edit locally — upstream issues instead.

## 🗺️ Key paths
- Session recording: SessionStart/UserPromptSubmit/Stop → `caf-hooks session-recorder` → ~/.caf/sessions/*.jsonl → run-explorer
- **Lookback**: `python3 bin/postmortem [--last N|--since 3h|--all]` — correlates native transcript (~/.claude/projects/<slug>/*.jsonl, has EVERY tool call + error) with CAF sinks; family histogram first. Skill: postmortem. Rotation: `uv run scripts/rotate_logs.py [--apply]` (dry-run default).
- Install: edit templates/settings.json.template → `bash install.sh` (never edit settings.json). install.sh injects CAF_HOOKS_DIR.
- Eval: caf-evolve at ~/Documents/ai_upgrade/tools/evolve — `uv run python -m runner.framework_eval --caf-repo <worktree> --n 3`. Verdicts significance-gated (paired bootstrap + t-test must agree). Needs Docker. Rust layer measurable via infra/bin/caf-hooks-linux-arm64 (rebuild overwrites macOS binary — cargo build --release after!).
- Docs: CLAUDE.md/README.md are GENERATED — edit scripts/generate_docs.py (TIER_ORDER covers fable). Pre-push hook regenerates.

## 💡 Gotchas
- Test the Rust binary at `<repo>/target/release/caf-hooks` — stale `caf-hooks/target/` has twice served months-old code (pending human rm).
- `global-hooks/damage-control/unified-damage-control.py` is inert, pending human rm (guard blocks agent deletion).
- events.db has no producer (run-explorer expects it) — open item FL13.
- orchestrate skill is ~60% native-Workflow reimplementation; refactor (FL15) gated on n=3 eval verdict.
- Eval noise floor: same config re-run moves one task ±12 pts. Never trust n=1 deltas; the significance gate exists for this.

## ✅ Ready to Execute
Agent primed. Context loaded. Ready for instructions.

---

## Change Detection
Invalidated when the git hash changes or this file is deleted. Regenerate by rewriting this file at HEAD (the /prime command was retired — PROJECT_CONTEXT.md is auto-injected at SessionStart by session_startup.py).
