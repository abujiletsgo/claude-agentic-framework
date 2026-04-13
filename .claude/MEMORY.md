# Project Memory — claude-agentic-framework
<!-- Mid-term project memory: one entry per session. Auto-maintained. -->
<!-- Layer 2 (episodic): what changed, was fixed, was decided across sessions. -->

## 2026-04-09 (16:57 UTC) · @Tom Kwon
**Commit:** Merge CAF upstream: v5.0 research intelligence + mempalace removal (ca3e1ea3) by Tom Kwon
**Changed:**
  caf-hooks/.claude/MEMORY.md                        |   15 +
  caf-hooks/src/hooks/voice_done.rs                  |   98 +-
  data/mempalace.yaml                                |   51 -
  docs/framework-guide-ko.html                       |  658 +-----------
  global-agents/academic-researcher.md               |   98 +-
  global-agents/code-researcher.md                   |   85 +-
  global-agents/critical-analyst.md                  |   12 +
  global-agents/meta-agent.md                        |   12 +
  global-agents/researcher.md                        |  386 +++----
  global-hooks/framework/aaak_compress.py            |  139 ---
  ... and 31 more files

## 2026-04-09 (17:16 UTC) · @Tom Kwon
**Commit:** docs: auto-regenerate from repo state (8699b21d) by Tom Kwon
**Changed:**
  CLAUDE.md |  2 +-
  README.md | 16 ++++++----------
  2 files changed, 7 insertions(+), 11 deletions(-)

## 2026-04-10 (05:14 UTC) · @Tom Kwon
**Commit:** feat: cmux sprint system + mempalace stub cleanup (9d879894) by Tom Kwon
**Changed:**
  bin/cmux-sprint                                    | 293 ++++++++++++++++++
  bin/sprint-view                                    | 327 +++++++++++++++++++++
  data/sprint_config.yaml                            |  16 +-
  .../hooks_SubagentStop/sprint_palace_store.py      |  99 +------
  global-skills/sprint/SKILL.md                      |  27 +-
  lib/agent_display.py                               | 171 +++++++++++
  lib/cmux_client.py                                 | 112 +++++++
  PLAN.md => specs/PLAN.md                           |   0
  tests/test_cmux_integration.py                     | 266 +++++++++++++++++
  9 files changed, 1206 insertions(+), 105 deletions(-)

## 2026-04-10 (07:25 UTC) · @Tom Kwon
**Commit:** feat: cmux-native dashboard — always-on report + sprint panels via cteam (82d5d2fa) by Tom Kwon
**Changed:**
  CLAUDE.md                                          |   2 +-
  README.md                                          |   6 +-
  bin/cmux-sprint                                    |   2 +
  bin/cteam                                          |  64 ++++
  dashboard/activity_report.py                       | 187 ++++++++++
  dashboard/sprint_dashboard.py                      | 373 ++++++++++++++++++++
  dashboard/sprint_overview.py                       | 154 +++++++++
  dashboard/sprint_report.py                         | 383 +++++++++++++++++++++
  .../framework/automation/activity_logger.py        | 114 ++++++
  global-skills/sprint/SKILL.md                      |  40 +--
  ... and 2 more files

## 2026-04-10 (16:48 UTC) · @Tom Kwon
**Commit:** feat: cmux-native per-task report panes + session tracker (4fece86a) by Tom Kwon
**Changed:**
  .gitignore                                         |   4 +
  bin/cdash                                          |  60 ++
  bin/cmux-sprint                                    | 545 ++++++------
  bin/cteam                                          |  46 +-
  bin/open-task-pane                                 |  83 ++
  bin/orch-event                                     |  33 +
  bin/session-event                                  |  70 ++
  bin/sprint-event                                   |   9 +
  dashboard/activity_report.py                       | 703 +++++++++++++---
  dashboard/sprint_report.py                         | 916 +++++++++++++--------
  ... and 4 more files

## 2026-04-10 (17:04 UTC) · @Tom Kwon
**Commit:** chore: remove ghost sprint-lead from model_tiers.yaml (bbb8d4e0) by Tom Kwon
**Changed:**
  data/model_tiers.yaml | 1 -
  1 file changed, 1 deletion(-)

## 2026-04-10 (17:21 UTC) · @Tom Kwon
**Commit:** feat: caf-hud — always-on Rust TUI with idle mode + job tabs + auto-launch (96e46936) by Tom Kwon
**Changed:**
  .gitignore                                        |    3 +
  Cargo.lock                                        | 1260 +++++++++++++++++++++
  Cargo.toml                                        |    9 +
  bin/cmux-sprint                                   |   56 +-
  caf-hooks/Cargo.toml                              |    6 -
  caf-hud/Cargo.toml                                |   12 +
  caf-hud/src/main.rs                               |  882 +++++++++++++++
  global-hooks/framework/session/session_startup.py |    1 +
  global-hooks/framework/session/spawn_hud.py       |   70 ++
  global-skills/orchestrate/SKILL.md                |   26 +-
  ... and 1 more files

## 2026-04-10 (17:33 UTC) · @Tom Kwon
**Commit:** docs: auto-regenerate from repo state (82d6a85d) by Tom Kwon
**Changed:**
  CLAUDE.md | 2 +-
  README.md | 6 +++---
  2 files changed, 4 insertions(+), 4 deletions(-)

## 2026-04-10 (17:39 UTC) · @Tom Kwon
**Commit:** docs: auto-regenerate from repo state (ca4b3cf6) by Tom Kwon
**Changed:**
  CLAUDE.md | 2 +-
  README.md | 6 +++---
  2 files changed, 4 insertions(+), 4 deletions(-)

## 2026-04-10 (17:41 UTC) · @Tom Kwon
**Commit:** docs: orchestrate — explicit parallel researchers in Wave 0, use haiku model (992de748) by Tom Kwon
**Changed:**
  global-skills/orchestrate/SKILL.md | 11 ++++++++---
  1 file changed, 8 insertions(+), 3 deletions(-)

## 2026-04-10 (17:44 UTC) · @Tom Kwon
**Commit:** docs: auto-regenerate from repo state (60856569) by Tom Kwon
**Changed:**
  CLAUDE.md | 2 +-
  README.md | 2 +-
  2 files changed, 2 insertions(+), 2 deletions(-)

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
