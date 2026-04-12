# Project Memory — claude-agentic-framework
<!-- Mid-term project memory: one entry per session. Auto-maintained. -->
<!-- Layer 2 (episodic): what changed, was fixed, was decided across sessions. -->

## 2026-04-08 (17:04 UTC) · @Tom Kwon
**Commit:** fix: Textual ANSI_COLOR + transparent, buddy pane verified, add cteam --reset (34e622ec) by Tom Kwon
**Changed:**
  bin/cteam                |  5 +++++
  dashboard/sprint_tui.css | 44 +++++++++++++++++++++++++++++++++++++++-----
  dashboard/sprint_tui.py  |  1 +
  3 files changed, 45 insertions(+), 5 deletions(-)

## 2026-04-08 (17:07 UTC) · @Tom Kwon
**Commit:** fix: force transparent on ALL Textual widgets — wildcard + explicit overrides (3d517f6e) by Tom Kwon
**Changed:**
  dashboard/sprint_tui.css | 49 +++++++++++++++++++++++++++++++++++++-----------
  1 file changed, 38 insertions(+), 11 deletions(-)

## 2026-04-08 (17:08 UTC) · @Tom Kwon
**Commit:** feat: live agent dashboard for /orchestrate visibility (2ff65fdc) by Tom Kwon
**Changed:**
  dashboard/live_tui.py                              | 147 +++++++++++++++++++++
  global-commands/live.md                            |  41 ++++++
  .../hooks_SubagentStart/write_agent_live.py        |  76 +++++++++++
  .../hooks_SubagentStop/write_agent_live.py         |  70 ++++++++++
  templates/settings.json.template                   |  22 +++
  5 files changed, 356 insertions(+)

## 2026-04-08 (17:13 UTC) · @Tom Kwon
**Commit:** feat: auto-launch live TUI on session start inside tmux (763d8a35) by Tom Kwon
**Changed:**
  global-hooks/hooks_SessionStart/launch_live_tui.py | 55 ++++++++++++++++++++++
  templates/settings.json.template                   | 11 +++++
  2 files changed, 66 insertions(+)

## 2026-04-08 (17:15 UTC) · @Tom Kwon
**Commit:** refactor: move live TUI launch from hook to cteam script (f53a8f0f) by Tom Kwon
**Changed:**
  global-hooks/hooks_SessionStart/launch_live_tui.py | 54 ++--------------------
  1 file changed, 3 insertions(+), 51 deletions(-)

## 2026-04-08 (17:16 UTC) · @Tom Kwon
**Commit:** dashboard: rewrite panels with RichLog for true terminal transparency (b6634e52) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                 | 300 ++++++++++++++++----------------------
  CLAUDE.md                         |   8 +-
  README.md                         |  24 +--
  bin/cteam                         |  13 +-
  dashboard/sprint_tui.css          |  58 ++------
  dashboard/widgets/lead_panel.py   |  42 ++++--
  dashboard/widgets/report_panel.py |  59 +++++---
  7 files changed, 233 insertions(+), 271 deletions(-)

## 2026-04-08 (17:22 UTC) · @Tom Kwon
**Commit:** dashboard: detect terminal background via OSC 11 for color matching (91589787) by Tom Kwon
**Changed:**
  dashboard/sprint_tui.py | 47 +++++++++++++++++++++++++++++++++++++++++++++++
  1 file changed, 47 insertions(+)

## 2026-04-08 (17:32 UTC) · @Tom Kwon
**Commit:** dashboard: use $background theme variable instead of transparent/OSC11 (63a4074e) by Tom Kwon
**Changed:**
  dashboard/sprint_tui.css | 44 ++++++++++++++++++++++++--------------------
  dashboard/sprint_tui.py  | 47 -----------------------------------------------
  2 files changed, 24 insertions(+), 67 deletions(-)

## 2026-04-08 (17:43 UTC) · @Tom Kwon
**Commit:** feat: CAF Dashboard Layout A — unified big-screen TUI (7b94e74d) by Tom Kwon
**Changed:**
  bin/cteam-dashboard                   | 162 +-----------------------
  dashboard/__init__.py                 |   1 +
  dashboard/caf_dashboard.css           |  58 +++++++++
  dashboard/caf_dashboard.py            | 101 +++++++++++++++
  dashboard/cost_estimator.py           | 130 ++++++++++++++++++++
  dashboard/widgets/agents_widget.py    |  71 +++++++++++
  dashboard/widgets/event_log_widget.py | 166 +++++++++++++++++++++++++
  dashboard/widgets/leads_grid.py       | 184 ++++++++++++++++++++++++++++
  dashboard/widgets/right_sidebar.py    | 224 ++++++++++++++++++++++++++++++++++
  dashboard/widgets/summary_panel_v2.py | 160 ++++++++++++++++++++++++
  ... and 3 more files

## 2026-04-08 (17:45 UTC) · @Tom Kwon
**Commit:** fix: use python3 for dashboard (textual installed there), fix @work import (7c63b9bd) by Tom Kwon
**Changed:**
  bin/cteam-dashboard             | 2 +-
  dashboard/widgets/leads_grid.py | 2 +-
  2 files changed, 2 insertions(+), 2 deletions(-)

## 2026-04-09 (13:49 UTC) · @Tom Kwon
**Commit:** fix: add sys.path insert so dashboard runs from any working directory (e4fa584b) by Tom Kwon
**Changed:**
  dashboard/caf_dashboard.py | 4 ++++
  1 file changed, 4 insertions(+)

## 2026-04-09 (16:52 UTC) · @Tom Kwon
**Commit:** chore: remove Textual TUI dashboard and buddy system (1e8065b3) by Tom Kwon
**Changed:**
  .gitignore                                         |   8 +
  CLAUDE.md                                          |   6 +-
  README.md                                          |  16 +-
  bin/caf-ref                                        |  65 ++
  bin/cteam                                          |  71 --
  bin/cteam-buddy                                    | 300 --------
  bin/cteam-dashboard                                |   6 -
  bin/cteam-sidebar                                  | 437 -----------
  dashboard/__init__.py                              |   1 -
  dashboard/caf_dashboard.css                        |  58 --
  ... and 25 more files

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
