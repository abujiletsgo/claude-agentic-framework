# Project Memory — claude-agentic-framework
<!-- Mid-term project memory: one entry per session. Auto-maintained. -->
<!-- Layer 2 (episodic): what changed, was fixed, was decided across sessions. -->

## 2026-04-10 (17:48 UTC) · @Tom Kwon
**Commit:** fix: caf-hud idle mode showing 0 for hooks/agents/skills (021da08c) by Tom Kwon
**Changed:**
  caf-hud/src/main.rs | 18 +++++++++---------
  1 file changed, 9 insertions(+), 9 deletions(-)

## 2026-04-10 (17:48 UTC) · @Tom Kwon
**Commit:** docs: orchestrate — enforce parallel-first; all agents per wave in one message (00e6b74e) by Tom Kwon
**Changed:**
  global-skills/orchestrate/SKILL.md | 19 ++++++++++++++++---
  1 file changed, 16 insertions(+), 3 deletions(-)

## 2026-04-10 (17:50 UTC) · @Tom Kwon
**Commit:** docs: quality-first priorities + planning-lead on opus (bf72318b) by Tom Kwon
**Changed:**
  data/model_tiers.yaml              |  1 +
  global-skills/orchestrate/SKILL.md | 10 ++++++----
  2 files changed, 7 insertions(+), 4 deletions(-)

## 2026-04-10 (17:52 UTC) · @Tom Kwon
**Commit:** docs: orchestrate — explicit dependency mapping in wave planning (51153535) by Tom Kwon
**Changed:**
  global-skills/orchestrate/SKILL.md | 5 ++++-
  1 file changed, 4 insertions(+), 1 deletion(-)

## 2026-04-10 (17:58 UTC) · @Tom Kwon
**Commit:** refactor(orchestrate): split 657-line SKILL.md into lean core + templates (2755665e) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                                  | 154 +++---
  global-skills/orchestrate/SKILL.md                 | 616 ++++-----------------
  .../orchestrate/templates/acceptance-criteria.md   |  23 +
  .../orchestrate/templates/delivery-format.md       |  26 +
  .../orchestrate/templates/escalation-format.md     |  15 +
  .../orchestrate/templates/evaluator-prompt.md      |  37 ++
  global-skills/orchestrate/templates/lead-prompt.md | 138 +++++
  .../orchestrate/templates/mission-brief.md         |   9 +
  .../orchestrate/templates/result-format.md         |  10 +
  9 files changed, 454 insertions(+), 574 deletions(-)

## 2026-04-12 (13:47 UTC) · @Tom Kwon
**Commit:** docs(arch-map): regenerate architecture map — caf-hud, lead.md, orchestrate split (7aa6606e) by Tom Kwon
**Changed:**
  .claude/ARCHITECTURE.md    | 768 +++++++++++++++++++--------------------------
  .claude/PROJECT_CONTEXT.md |   2 +-
  2 files changed, 326 insertions(+), 444 deletions(-)

## 2026-04-12 (14:22 UTC) · @Tom Kwon
**Commit:** feat(agents): add 16 domain-specific lead agents + fix orchestrate leads table (8481d577) by Tom Kwon
**Changed:**
  CLAUDE.md                          | 10 ++---
  data/model_tiers.yaml              | 26 +++++++++++-
  global-agents/architecture-lead.md | 80 +++++++++++++++++++++++++++++++++++++
  global-agents/ceo-review-lead.md   | 80 +++++++++++++++++++++++++++++++++++++
  global-agents/debugging-lead.md    | 81 +++++++++++++++++++++++++++++++++++++
  global-agents/design-lead.md       | 81 +++++++++++++++++++++++++++++++++++++
  global-agents/docs-lead.md         | 81 +++++++++++++++++++++++++++++++++++++
  global-agents/eng-review-lead.md   | 81 +++++++++++++++++++++++++++++++++++++
  global-agents/engineering-lead.md  | 82 ++++++++++++++++++++++++++++++++++++++
  global-agents/pairing-lead.md      | 81 +++++++++++++++++++++++++++++++++++++
  ... and 10 more files

## 2026-04-12 (14:32 UTC) · @Tom Kwon
**Commit:** feat(orchestrate): PO model — product owner, spec-first leads, domain-specific agents (b0523248) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                                  |  60 +--
  .claude/PO_BRIEF.md                                |  29 ++
  CLAUDE.md                                          |   4 +-
  bin/cmux-sprint                                    |  36 +-
  bin/orch-shared                                    |   0
  bin/sprint-event                                   |  24 ++
  dashboard/sprint_report.py                         | 424 +++++++++++++++++++++
  data/model_tiers.yaml                              |  12 +-
  global-agents/academic-researcher.md               |   6 +-
  global-agents/api-lead.md                          | 113 ++++++
  ... and 33 more files

## 2026-04-13 (01:42 UTC) · @Tom Kwon
**Commit:** feat(po): question batching — PO answers Tier 1 autonomously, batches Tier 2 for user (6e8a8d07) by Tom Kwon
**Changed:**
  global-agents/po.md                | 56 +++++++++++++++++++++++++++++++-------
  global-skills/orchestrate/SKILL.md | 37 +++++++++++++++----------
  2 files changed, 69 insertions(+), 24 deletions(-)

## 2026-04-13 (04:35 UTC) · @Tom Kwon
**Commit:** feat(orchestrate): 3-wave model — exploration → contracts → build (9114b6f4) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                                  |  36 +++--
  bin/orch-shared                                    |  25 +++-
  data/model_tiers.yaml                              |   3 +
  global-agents/po.md                                |  73 +++++++---
  global-skills/orchestrate/SKILL.md                 | 150 +++++++++------------
  global-skills/orchestrate/templates/lead-prompt.md |  82 +++++++++--
  6 files changed, 241 insertions(+), 128 deletions(-)

## 2026-04-13 (04:38 UTC) · @Tom Kwon
**Commit:** feat(orch-shared): add status, merge-results, read-events + conflict detection (48f8e8d6) by Tom Kwon
**Changed:**
  bin/orch-shared                                    | 277 ++++++++++++++++++++-
  dashboard/activity_report.py                       |  48 +++-
  dashboard/sprint_report.py                         |  11 +-
  data/benchmarks/rubric.md                          |  50 ++++
  data/benchmarks/task-01-status/prompt.md           |  17 ++
  data/benchmarks/task-01-status/reference-score.md  |  26 ++
  data/benchmarks/task-02-conflict-detect/prompt.md  |  16 ++
  .../task-02-conflict-detect/reference-score.md     |  27 ++
  data/benchmarks/task-03-read-events/prompt.md      |  35 +++
  .../task-03-read-events/reference-score.md         |  30 +++
  ... and 1 more files

## 2026-04-13 (04:45 UTC) · @Tom Kwon
**Commit:** feat(orch-shared): unified event stream + write-retro + fix orch-event deprecation (f3b1f6f4) by Tom Kwon
**Changed:**
  bin/orch-event  |   2 +-
  bin/orch-shared | 164 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
  2 files changed, 165 insertions(+), 1 deletion(-)

## 2026-04-13 (04:46 UTC) · @Tom Kwon
**Commit:** feat(orch-shared): auto-write retro on cleanup (e033da8d) by Tom Kwon
**Changed:**
  bin/orch-shared | 6 ++++++
  1 file changed, 6 insertions(+)

## 2026-04-13 (06:04 UTC) · @Tom Kwon
**Commit:** feat(dashboard): replace working memory panel with live event feed (3cb43efa) by Tom Kwon
**Changed:**
  dashboard/activity_report.py | 76 +++++++++++++++++++++++++++++++++-----------
  1 file changed, 57 insertions(+), 19 deletions(-)

## 2026-04-13 (14:52 UTC) · @Tom Kwon
**Commit:** feat(orchestrate): dynamic leads, CWD-scoped dashboards, event stream (1be1369c) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                                  | 86 +++++++++++-----------
  .claude/PO_BRIEF.md                                |  5 ++
  .claude/agents/cmux-lead.md                        | 48 ++++++++++++
  .claude/agents/dashboard-lead.md                   | 49 ++++++++++++
  .claude/agents/hooks-lead.md                       | 48 ++++++++++++
  .gitignore                                         |  5 ++
  CLAUDE.md                                          | 10 +--
  README.md                                          | 12 +--
  bin/gen-lead                                       | 70 ++++++++++++++++++
  bin/orch-shared                                    |  9 ++-
  ... and 8 more files

## 2026-04-13 (17:05 UTC) · @Tom Kwon
**Commit:** feat(orchestrate): persistent leads, vision-first PO, lead consolidation (d6ca118d) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                                  |  22 +-
  .claude/PRODUCT_VISION.md                          |  49 +++++
  .claude/PROJECT_CONTEXT.md                         | 110 +++++-----
  .gitignore                                         |   3 +
  CLAUDE.md                                          |   8 +-
  README.md                                          |  14 +-
  bin/caf-eval                                       | 221 +++++++++++++++++++
  bin/cmux-sprint                                    |  61 +++++-
  bin/gen-lead                                       |  71 +-----
  bin/orch-shared                                    |  37 ++++
  ... and 29 more files

## 2026-04-13 (17:30 UTC) · @Tom Kwon
**Commit:** feat(orchestrate): consultant model, run-explorer merged dashboard, run detail expansion (2dc39d53) by Tom Kwon
**Changed:**
  .claude/ARCHITECTURE.md                            | 479 ++++-------
  .claude/MEMORY.md                                  |  32 +-
  .claude/PROJECT_CONTEXT.md                         | 113 +--
  CLAUDE.md                                          |   8 +-
  Cargo.lock                                         | 490 +-----------
  Cargo.toml                                         |   2 +-
  README.md                                          |  14 +-
  apps/run-explorer/.gitignore                       |   3 +
  apps/run-explorer/client/.claude/FACTS.md          |  15 +
  apps/run-explorer/client/.claude/MEMORY.md         |  33 +
  ... and 99 more files

## 2026-04-13 (17:37 UTC) · @Tom Kwon
**Commit:** feat(orch): persist runs to ~/.caf/orch, write-retro on every run (9bfd87a0) by Tom Kwon
**Changed:**
  apps/run-explorer/server/src/config.ts             |  3 +-
  apps/run-explorer/server/src/services/runParser.ts | 35 ++++++++++++++++++----
  bin/orch-shared                                    |  2 +-
  global-skills/orchestrate/SKILL.md                 |  1 +
  4 files changed, 33 insertions(+), 8 deletions(-)

## 2026-04-13 (17:39 UTC) · @Tom Kwon
**Commit:** feat(orchestrate): merge upstream parallelism discipline into consultant model (d13a9e69) by Tom Kwon
**Changed:**
  global-skills/orchestrate/SKILL.md | 132 ++++++++++++++++++++++++++-----------
  1 file changed, 93 insertions(+), 39 deletions(-)

## 2026-04-14 (07:20 UTC) · @Tom Kwon
**Commit:** feat(session): orchestration logging, project grouping, install.sh doctor, arch-map v4.2 (7d286ff5) by Tom Kwon
**Changed:**
  .claude/ARCHITECTURE.md                            | 203 +++++++++++-----
  .claude/MEMORY.md                                  |  58 ++---
  .gitignore                                         |   1 +
  .../client/src/views/RunDetailView.vue             |   5 +-
  apps/run-explorer/client/src/views/RunListView.vue | 257 ++++++++++++++-------
  apps/run-explorer/server/.claude/MEMORY.md         |  15 ++
  apps/run-explorer/shared/types.ts                  |   1 +
  install.sh                                         |  55 +++++
  8 files changed, 423 insertions(+), 172 deletions(-)

## 2026-04-14 (07:21 UTC) · @Tom Kwon
**Commit:** chore: remove dead sprint/cmux/mempalace systems + ship session layer (12e1736d) by Tom Kwon
**Changed:**
  .claude/ARCHITECTURE.md                            |  517 ++++----
  .claude/FACTS.md                                   |    6 +-
  .claude/MEMORY.md                                  |   28 +-
  .claude/PROJECT_CONTEXT.md                         |  141 ++-
  CLAUDE.md                                          |    6 +-
  README.md                                          |   11 +-
  apps/run-explorer/client/src/App.vue               |    1 +
  .../client/src/composables/useSessions.ts          |   29 +
  apps/run-explorer/client/src/router/index.ts       |    4 +
  .../client/src/views/SessionDetailView.vue         |  201 +++
  ... and 49 more files

## 2026-04-14 (07:26 UTC) · @Tom Kwon
**Commit:** chore(tidy): update doc counts, commit autoplan output (a056aee9) by Tom Kwon
**Changed:**
  CLAUDE.md                   |   4 +-
  specs/CURRENT-STATE-PLAN.md | 108 ++++++++++++++++++++++++++++++++++++++++++++
  2 files changed, 110 insertions(+), 2 deletions(-)

## 2026-04-14 (07:44 UTC) · @Tom Kwon
**Commit:** fix(hooks): remove deleted hook refs from template, regenerate settings (f69c539e) by Tom Kwon
**Changed:**
  CLAUDE.md                        |  6 +++---
  templates/settings.json.template | 18 ------------------
  2 files changed, 3 insertions(+), 21 deletions(-)

## 2026-04-14 (session) · @Tom Kwon
**Work:** gstack /codex skill — Gemini-first second opinion. Rewrote SKILL.md.tmpl (v1→v2): gemini -p as primary, --codex flag as opt-in override. Updated preamble.ts: "Codex Review"→"Gemini Review" in plan footer table, "codex exec/review"→"/codex skill (gemini -p)" in Plan Mode Safe Ops. Regenerated all 28 gstack SKILL.md files. Set ~/.gstack/config.yaml second_opinion_tool: gemini. Also configured gstack second_opinion_tool: auto→gemini in prior exchange.
**Changed:** global-skills/gstack/codex/SKILL.md.tmpl, global-skills/gstack/scripts/resolvers/preamble.ts, all gstack SKILL.md files (regen), ~/.gstack/config.yaml

## 2026-04-14 (13:37 UTC) · @Tom Kwon
**Commit:** feat(v5.1): session schema contract, delete observability, config env vars (c6f9f678) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                                  |   65 +-
  README.md                                          |    3 +-
  apps/observability/client/.env.sample              |    3 -
  apps/observability/client/.gitignore               |   24 -
  apps/observability/client/README.md                |    5 -
  apps/observability/client/fix-visibility.sh        |   23 -
  apps/observability/client/index.html               |   13 -
  apps/observability/client/package-lock.json        | 2685 --------------------
  apps/observability/client/package.json             |   27 -
  apps/observability/client/postcss.config.js        |    6 -
  ... and 67 more files

## 2026-04-14 (13:46 UTC) · @Tom Kwon
**Commit:** feat(gstack): switch /codex second opinion to Gemini CLI (a825ab88) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                                  |  40 +-
  global-skills/gstack/SKILL.md                      |   4 +-
  global-skills/gstack/autoplan/SKILL.md             |   4 +-
  global-skills/gstack/benchmark/SKILL.md            |   4 +-
  global-skills/gstack/browse/SKILL.md               |   4 +-
  global-skills/gstack/canary/SKILL.md               |   4 +-
  global-skills/gstack/checkpoint/SKILL.md           |   4 +-
  global-skills/gstack/codex/SKILL.md                | 439 +++++++++-----------
  global-skills/gstack/codex/SKILL.md.tmpl           | 445 +++++++++------------
  global-skills/gstack/cso/SKILL.md                  |   4 +-
  ... and 26 more files

## 2026-04-17 (04:21 UTC) · @Tom Kwon
**Commit:** refactor(gstack): rename /codex skill to /gemini (d1e0727d) by Tom Kwon
**Changed:**
  global-skills/gstack/SKILL.md                        |  4 ++--
  global-skills/gstack/autoplan/SKILL.md               |  4 ++--
  global-skills/gstack/benchmark/SKILL.md              |  4 ++--
  global-skills/gstack/browse/SKILL.md                 |  4 ++--
  global-skills/gstack/canary/SKILL.md                 |  4 ++--
  global-skills/gstack/checkpoint/SKILL.md             |  4 ++--
  global-skills/gstack/cso/SKILL.md                    |  4 ++--
  global-skills/gstack/design-consultation/SKILL.md    |  4 ++--
  global-skills/gstack/design-html/SKILL.md            |  4 ++--
  global-skills/gstack/design-review/SKILL.md          |  4 ++--
  ... and 25 more files

## 2026-04-21 (16:33 UTC) · @Tom Kwon
**Commit:** feat(v5.2): session cost tracking, gstack fix, tidy memory audit, orch improvements (68534240) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                                  |   52 +-
  .gitignore                                         |    1 +
  CLAUDE.md                                          |    2 +-
  README.md                                          |   10 +-
  apps/run-explorer/client/.claude/MEMORY.md         |   15 +
  .../client/src/composables/useSessions.ts          |    6 +-
  .../client/src/views/RunDetailView.vue             |   91 +-
  .../client/src/views/SessionDetailView.vue         |   11 +-
  .../client/src/views/SessionListView.vue           |  154 +-
  apps/run-explorer/server/.claude/MEMORY.md         |   15 +
  ... and 41 more files

## 2026-05-20 (08:31 UTC) · @Tom Kwon
**Commit:** feat(orchestrate): Level 7 autonomous execution gaps — nudge log, CONCERNS flow, evaluator opt-in, Simple self-healing (4d77ad74) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                         |  22 ++++--
  bin/orch-shared                           |   6 ++
  caf-hooks/src/hooks/orch_depth_tracker.rs |  55 +++++++++++++++
  caf-hooks/src/hooks/subagent_tracker.rs   |  77 +++++++++++++++++++++
  global-skills/orchestrate/SKILL.md        | 109 ++++++++++++++++++++++++++++--
  5 files changed, 257 insertions(+), 12 deletions(-)

## 2026-06-10 (15:02 UTC) · @Tom Kwon
**Commit:** chore(gitignore): ignore .claude/scheduled_tasks.lock (runtime lock) (4c6b256e) by Tom Kwon
**Changed:**
  .gitignore | 3 +++
  1 file changed, 3 insertions(+)
