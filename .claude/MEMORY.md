# Project Memory — claude-agentic-framework
<!-- Mid-term project memory: one entry per session. Auto-maintained. -->
<!-- Layer 2 (episodic): what changed, was fixed, was decided across sessions. -->

## 2026-04-07 (17:31 UTC) · @Tom Kwon
**Commit:** chore: flesh out mempalace.yaml rooms + commit session memory (3d94e5b) by Tom Kwon
**Changed:**
  .claude/MEMORY.md | 78 +++++++++++++++++++++++++++++++++++++++++++++++++++++++
  mempalace.yaml    | 34 ++++++++++++++++++++++++
  2 files changed, 112 insertions(+)

## 2026-04-07 (17:34 UTC) · @Tom Kwon
**Commit:** feat: add AAAK session-start compression for all projects (a2355bf) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                               |   7 +
  global-hooks/framework/automation/auto_prime.py |  25 ++
  install.sh                                      |  35 ++-
  tests/test_aaak_integration.py                  | 319 ++++++++++++++++++++++++
  4 files changed, 384 insertions(+), 2 deletions(-)

## 2026-04-08 (02:43 UTC) · @Tom Kwon
**Commit:** fix: auto-detect mempalace Python version instead of hardcoding 3.12 (4f4e944) by Tom Kwon
**Changed:**
  global-hooks/framework/aaak_compress.py      | 14 +++++++++++---
  global-hooks/framework/facts/fact_kg_sync.py | 14 +++++++++++---
  install.sh                                   | 16 ++++++++++------
  tests/test_aaak_integration.py               |  9 ++++++---
  4 files changed, 38 insertions(+), 15 deletions(-)

## 2026-04-08 (03:15 UTC) · @Tom Kwon
**Commit:** feat: project-local mempalace integration — SubagentStop storage + SubagentStart KG inject (f544ef8) by Tom Kwon
**Changed:**
  .gitignore                                         |   3 +
  CLAUDE.md                                          |   2 +-
  README.md                                          |   6 +-
  global-agents/researcher.md                        |   2 +-
  .../framework/context/pre_compact_preserve.py      |  17 +-
  .../framework/memory/auto_memory_writer.py         |  16 +-
  .../framework/memory/kg_session_context.py         |  20 +-
  global-hooks/framework/memory/palace_init.py       | 192 +++++++
  .../framework/memory/subagent_kg_inject.py         | 118 ++++
  .../framework/memory/subagent_palace_store.py      | 114 ++++
  ... and 3 more files

## 2026-04-08 (03:23 UTC) · @Tom Kwon
**Commit:** chore: tidy repo + generate full framework report (fc9686a) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                     |  22 +-
  README.md                             |  19 +-
  mempalace.yaml => data/mempalace.yaml |   0
  docs/framework-report.html            | 403 ++++++++++++++++++++++++++++++++++
  scripts/generate_docs.py              |  19 +-
  5 files changed, 446 insertions(+), 17 deletions(-)

## 2026-04-08 (08:11 UTC) · @Tom Kwon
**Commit:** docs: complete framework-guide-ko.html v4.1 update (f3b8091) by Tom Kwon
**Changed:**
  .claude/MEMORY.md            |  17 ++--
  docs/framework-guide-ko.html | 203 +++++++++++++++++++++++++++++++++++--------
  2 files changed, 179 insertions(+), 41 deletions(-)

## 2026-04-08 (09:01 UTC) · @Tom Kwon
**Commit:** docs: auto-regenerate from repo state (bf704b6) by Tom Kwon
**Changed:**
  README.md | 6 +++---
  1 file changed, 3 insertions(+), 3 deletions(-)

## 2026-04-08 (10:17 UTC) · @Tom Kwon
**Commit:** feat: wire 12 Rust hooks into settings.json.template (235717f) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                | 15 +++++-------
  install.sh                       |  9 ++++++-
  templates/settings.json.template | 51 +++++++++++++++++++++-------------------
  3 files changed, 41 insertions(+), 34 deletions(-)

## 2026-04-08 (10:24 UTC) · @Tom Kwon
**Commit:** feat: 8 new Rust hooks, /doctor diagnostic (22 checks), token optimization (1966f33) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                              |  19 +-
  CLAUDE.md                                      |   4 +-
  README.md                                      |  10 +-
  caf-hooks/src/hooks/audit_config_change.rs     | 121 ++++
  caf-hooks/src/hooks/auto_error_analyzer.rs     |   9 +-
  caf-hooks/src/hooks/auto_escalate.rs           | 242 +++++++
  caf-hooks/src/hooks/auto_fact_extractor.rs     | 534 +++++++++++++++
  caf-hooks/src/hooks/doctor.rs                  | 882 +++++++++++++++++++++++++
  caf-hooks/src/hooks/enforce_orchestrate.rs     |  22 +-
  caf-hooks/src/hooks/epistemic_guard.rs         |  24 +
  ... and 17 more files

## 2026-04-08 (10:28 UTC) · @Tom Kwon
**Commit:** chore: remove FRAMEWORK_REFERENCE.md and framework-report.html (749b85e) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                            |   22 +-
  FRAMEWORK_REFERENCE.md                       | 1041 --------------------------
  README.md                                    |    4 +-
  caf-hooks/.claude/FACTS.md                   |   17 +
  caf-hooks/.claude/MEMORY.md                  |   11 +
  caf-hooks/.claude/settings.json              |    7 +
  docs/framework-report.html                   |  403 ----------
  global-skills/tidy/SKILL.md                  |    6 +-
  global-skills/tidy/tidy_analyzer.py          |    4 +-
  scripts/generate_docs.py                     |    4 +-
  ... and 20 more files

## 2026-04-08 (10:51 UTC) · @Tom Kwon
**Commit:** docs: update framework-guide-ko.html for v4.2 (1a3a036) by Tom Kwon
**Changed:**
  docs/framework-guide-ko.html | 127 +++++++++++++++++++++++++++++++------------
  1 file changed, 93 insertions(+), 34 deletions(-)

## 2026-04-08 (13:21 UTC) · @Tom Kwon
**Commit:** docs: add 20 skill workflow diagrams + mempalace/AAAK sections to guide (074d3c5) by Tom Kwon
**Changed:**
  docs/framework-guide-ko.html | 1375 ++++++++++++++++++++++++++++++++++++++++++
  1 file changed, 1375 insertions(+)

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
