# Project Memory — caf-hooks
<!-- Mid-term project memory: one entry per session. Auto-maintained. -->
<!-- Layer 2 (episodic): what changed, was fixed, was decided across sessions. -->

## 2026-04-08 (10:21 UTC) · @Tom Kwon
**Commit:** feat: wire 12 Rust hooks into settings.json.template (235717f) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                | 15 +++++-------
  install.sh                       |  9 ++++++-
  templates/settings.json.template | 51 +++++++++++++++++++++-------------------
  3 files changed, 41 insertions(+), 34 deletions(-)

## 2026-04-09 (04:41 UTC) · @Tom Kwon
**Commit:** feat: CAF v5.0 research intelligence upgrade (e4437ca) by Tom Kwon
**Changed:**
  .gitignore                                         |   4 +-
  CLAUDE.md                                          |   5 +-
  global-agents/academic-researcher.md               |  50 ++++++++++
  global-agents/code-researcher.md                   |  52 ++++++++++
  global-agents/critical-analyst.md                  |  12 +++
  global-agents/meta-agent.md                        |  12 +++
  global-agents/researcher.md                        |  42 +++++++-
  global-skills/research-academic/SKILL.md           |  50 ++++++++++
  .../research-academic/templates/output.json        |  19 ++++
  global-skills/research-code/SKILL.md               |  54 ++++++++++
  ... and 8 more files

## 2026-04-22 (15:17 UTC) · @Tom Kwon
**Commit:** feat(orchestrate): Level 7 autonomous execution gaps — nudge log, CONCERNS flow, evaluator opt-in, Simple self-healing (4d77ad74) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                         |  22 ++++--
  bin/orch-shared                           |   6 ++
  caf-hooks/src/hooks/orch_depth_tracker.rs |  55 +++++++++++++++
  caf-hooks/src/hooks/subagent_tracker.rs   |  77 +++++++++++++++++++++
  global-skills/orchestrate/SKILL.md        | 109 ++++++++++++++++++++++++++++--
  5 files changed, 257 insertions(+), 12 deletions(-)
