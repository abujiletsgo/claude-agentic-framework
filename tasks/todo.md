# Framework Audit vs Current Claude Code Standard — 2026-07-12

Goal: zero redundancy with native Claude Code, full autonomy, highest quality output.
Deliverables: (1) per-item KEEP/RETIRE/MERGE audit, (2) applied cleanup (user confirms deletions), (3) eval harness for measuring harness/workflow quality.

Prior pass (2026-06-15 skill audit) archived below — this audit is broader: hooks, agents, commands, skills, orchestration model, model tiers, memory layers.

## Phase 1 — Parallel research + inventory audit
- [x] Native Claude Code feature baseline → audit/01-native-baseline.md
- [ ] Hooks audit: 47 hooks / 17 events + Rust caf-hooks duplication (IN PROGRESS)
- [x] Skills (31) + commands (14) audit → audit/03-skills-commands-audit.md (13 RETIRE, 4 MERGE, 4 DEMOTE)
- [x] Agents (22) + orchestration audit → audit/04-agents-orchestration-audit.md (22→~9 roster, model_tiers stale)
- [x] Evolve/PoLL eval assets located → audit/05-eval-assets.md (REUSE framework_eval, 2-worktree 3-way plan)

## Phase 2 — Synthesis
- [ ] Merge reports into single redundancy matrix with verdicts
- [ ] Flag latency/token overhead per kept component
- [ ] AskUserQuestion: confirm RETIRE list before deleting anything

## Phase 3 — Apply
- [ ] Apply approved removals (stub hooks first, reinstall, then delete — per CLAUDE.md rule)
- [ ] Update templates/settings.json.template + bash install.sh
- [ ] Update model_tiers.yaml to current model family (Fable 5 / Opus 4.8 / Sonnet 5 / Haiku 4.5)
- [ ] Validate: test suite green, hooks fire, install clean

## Phase 4 — Eval harness
- [ ] Design eval (reuse PoLL panel if assets found; corpus = public benchmarks per prior decision)
- [ ] Build + run baseline vs cleaned harness comparison
- [ ] Report

Reports land in scratchpad/audit/*.md

---

# ARCHIVED: Skill Audit & Modernization — 2026-06-15  ✅ COMPLETE
(4 remediation tranches shipped; deferred items now absorbed into the 2026-07-12 audit above:
tranche E polish DONE in 2aaeed4a; still open — orchestrate/templates/lead-prompt.md orphan,
.claude/agents/cmux-lead.md dead agent)
