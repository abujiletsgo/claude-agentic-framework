# Skill Audit & Modernization — 2026-06-15  ✅ COMPLETE

## Phase 1 — Inventory ✅  (29 CAF-authored skills; gstack vendored excluded)
## Phase 2 — Research ✅  (authoring std + Claude Code platform + model/API, post-Mar-2026)
## Phase 3 — Audit ✅  (4 parallel batches, report at /tmp/claude/skill-audit.md)
## Phase 4 — Remediation ✅ (4 commits, audit-first approved by user)
- [x] A — name conformance (8) + research-docs context7 routing + arg-hints (3)   3decb108
- [x] B — delete dead cmux-skill; fix orchestrate Gemini/rollback/worktree/solve/onboard  785411dc->amended
- [x] C — gstack collision cascades (code-review/security-scanner/health when_to_use)  7651f6a7
- [x] D — progressive-disclosure splits (5 skills) + remove 4 dead output.json  562b56e0
- [x] skills.lock baseline regenerated

## Deferred / flagged (not in approved scope)
- Tranche E polish: drop remaining `version:` fields (9 skills), add effort/context:fork/allowed-tools
- orchestrate/templates/lead-prompt.md: orphaned (never linked), still refs removed cmux-sprint — needs delete-or-wire decision
- .claude/agents/cmux-lead.md: dead cmux agent (agents out of this skill-scoped pass)
