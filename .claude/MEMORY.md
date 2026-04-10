# Project Memory — claude-agentic-framework
<!-- Mid-term project memory: one entry per session. Auto-maintained. -->
<!-- Layer 2 (episodic): what changed, was fixed, was decided across sessions. -->

## 2026-04-08 (15:55 UTC) · @Tom Kwon
**Commit:** chore: update gstack-bridge paths + CLAUDE.md for fork architecture (1097c55) by Tom Kwon
**Changed:**
  CLAUDE.md         | 30 ++++++++++++++++--------------
  bin/gstack-bridge | 11 ++++++++++-
  2 files changed, 26 insertions(+), 15 deletions(-)

## 2026-04-08 (15:59 UTC) · @Tom Kwon
**Commit:** feat: add sprint strategy to orchestrate, /worktree sprint subcommand, refresh docs (d8042d3) by Tom Kwon
**Changed:**
  .claude/PROJECT_CONTEXT.md         |  43 +++++--------
  CLAUDE.md                          | 122 ++++++++++++++++++++++++-------------
  README.md                          |  21 ++++---
  global-skills/orchestrate/SKILL.md |  51 ++++++++++++++++
  global-skills/worktree/SKILL.md    |  23 +++++++
  5 files changed, 181 insertions(+), 79 deletions(-)

## 2026-04-08 (16:10 UTC) · @Tom Kwon
**Commit:** Merge commit '76adabd56f1b36ab94769217057f738168e20f4a' as 'global-skills/gstack' (7553e3c1) by Tom Kwon
**Changed:**
  global-skills/gstack/.env.example                  |    5 +
  global-skills/gstack/.github/actionlint.yaml       |    4 +
  global-skills/gstack/.github/docker/Dockerfile.ci  |   63 +
  .../gstack/.github/workflows/actionlint.yml        |    8 +
  .../gstack/.github/workflows/ci-image.yml          |   40 +
  .../gstack/.github/workflows/evals-periodic.yml    |  129 +
  global-skills/gstack/.github/workflows/evals.yml   |  240 ++
  .../gstack/.github/workflows/skill-docs.yml        |   33 +
  global-skills/gstack/.gitignore                    |   26 +
  global-skills/gstack/AGENTS.md                     |   49 +
  ... and 405 more files

## 2026-04-08 (16:12 UTC) · @Tom Kwon
**Commit:** fix: gstack-bridge check supports subtree installs (9d5e2a66) by Tom Kwon
**Changed:**
  bin/gstack-bridge | 6 ++++--
  1 file changed, 4 insertions(+), 2 deletions(-)

## 2026-04-08 (16:13 UTC) · @Tom Kwon
**Commit:** feat: add cteam launcher — tmux workspace with dashboard pane (6a555f05) by Tom Kwon
**Changed:**
  bin/cteam | 37 +++++++++++++++++++++++++++++++++++++
  1 file changed, 37 insertions(+)

## 2026-04-08 (16:15 UTC) · @Tom Kwon
**Commit:** feat: cteam sidebar with session/project manager + 3-pane layout (a59bb209) by Tom Kwon
**Changed:**
  bin/cteam         |  28 +++++--
  bin/cteam-sidebar | 247 ++++++++++++++++++++++++++++++++++++++++++++++++++++++
  2 files changed, 268 insertions(+), 7 deletions(-)

## 2026-04-08 (16:19 UTC) · @Tom Kwon
**Commit:** feat: clickable curses sidebar with mouse support (bad92f01) by Tom Kwon
**Changed:**
  bin/cteam         |   3 +
  bin/cteam-sidebar | 673 ++++++++++++++++++++++++++++++++++--------------------
  2 files changed, 434 insertions(+), 242 deletions(-)

## 2026-04-08 (16:25 UTC) · @Tom Kwon
**Commit:** feat: /buddy companion system — cat, dog, owl, ghost, robot with live dashboard widget (cb5fc2c1) by Tom Kwon
**Changed:**
  bin/cteam                    |  19 ++-
  bin/cteam-buddy              | 257 ++++++++++++++++++++++++++++++++
  global-skills/buddy/SKILL.md |  88 +++++++++++
  lib/buddies.py               | 339 +++++++++++++++++++++++++++++++++++++++++++
  4 files changed, 696 insertions(+), 7 deletions(-)

## 2026-04-08 (16:28 UTC) · @Tom Kwon
**Commit:** feat: proper idle dashboard — shows git status, auto-launches sprint TUI when sprint starts (f3157cc7) by Tom Kwon
**Changed:**
  bin/cteam           |   4 +-
  bin/cteam-dashboard | 157 ++++++++++++++++++++++++++++++++++++++++++++++++++++
  2 files changed, 158 insertions(+), 3 deletions(-)

## 2026-04-08 (16:34 UTC) · @Tom Kwon
**Commit:** feat: animated buddies — 96 frames, idle cycling, drift, oneshot reactions, pet responses (5a2d09c8) by Tom Kwon
**Changed:**
  bin/cteam-buddy | 209 +++++++++++------
  lib/buddies.py  | 685 ++++++++++++++++++++++++++++++++++++++++++++++++--------
  2 files changed, 727 insertions(+), 167 deletions(-)

## 2026-04-08 (16:37 UTC) · @Tom Kwon
**Commit:** fix: transparent backgrounds for Ghostty, shrink buddy pane, remove buddy buttons (353655ed) by Tom Kwon
**Changed:**
  bin/cteam           |  4 ++--
  bin/cteam-buddy     | 30 +++++-------------------------
  bin/cteam-dashboard |  8 +++-----
  bin/cteam-sidebar   | 12 ++++++------
  4 files changed, 16 insertions(+), 38 deletions(-)

## 2026-04-08 (16:55 UTC) · @Tom Kwon
**Commit:** fix: fully theme-adaptive — zero hardcoded colors, inherits terminal palette + transparency (15e6d5d8) by Tom Kwon
**Changed:**
  bin/cteam-buddy     | 25 +++++++++++++------------
  bin/cteam-dashboard | 21 +++++++++++----------
  bin/cteam-sidebar   | 37 +++++++++++++++++++------------------
  3 files changed, 43 insertions(+), 40 deletions(-)

## 2026-04-08 (16:59 UTC) · @Tom Kwon
**Commit:** fix: buddy pane split order, sprint TUI transparent backgrounds (32f34fe2) by Tom Kwon
**Changed:**
  bin/cteam                | 34 +++++++++++++++++++---------------
  dashboard/sprint_tui.css | 25 +++++++++++--------------
  2 files changed, 30 insertions(+), 29 deletions(-)

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
