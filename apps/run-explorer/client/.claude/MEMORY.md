# Project Memory — client
<!-- Mid-term project memory: one entry per session. Auto-maintained. -->
<!-- Layer 2 (episodic): what changed, was fixed, was decided across sessions. -->

## 2026-04-13 (07:12 UTC) · @Tom Kwon
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

## 2026-04-13 (17:14 UTC) · @Tom Kwon
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

## 2026-04-16 (06:08 UTC) · @Tom Kwon
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
