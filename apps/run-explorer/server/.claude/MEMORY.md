# Project Memory — server
<!-- Mid-term project memory: one entry per session. Auto-maintained. -->
<!-- Layer 2 (episodic): what changed, was fixed, was decided across sessions. -->

## 2026-04-13 (17:28 UTC) · @Tom Kwon
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

## 2026-04-13 (17:33 UTC) · @Tom Kwon
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

## 2026-04-14 (05:18 UTC) · @Tom Kwon
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
