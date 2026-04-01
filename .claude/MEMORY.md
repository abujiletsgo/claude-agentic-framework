# Project Memory — claude-agentic-framework
<!-- Mid-term project memory: one entry per session. Auto-maintained. -->
<!-- Layer 2 (episodic): what changed, was fixed, was decided across sessions. -->

## 2026-02-24 (16:12 UTC) · @Tom Kwon
**Commit:** docs: add HTML docs link table to README (9d2dc82) by Tom Kwon
**Changed:**
  README.md                | 13 +++++++++++++
  scripts/generate_docs.py | 13 +++++++++++++
  2 files changed, 26 insertions(+)

## 2026-02-25 (07:19 UTC) · @Tom Kwon
**Commit:** chore: update session memory files (fed7e58) by Tom Kwon
**Changed:**
  .claude/FACTS.md  |   4 +
  .claude/MEMORY.md | 291 ++++++++++++++++++++++++++++++++++++++++++++++++++----
  2 files changed, 275 insertions(+), 20 deletions(-)

## 2026-02-25 (07:29 UTC) · @Tom Kwon
**Commit:** chore: ignore generated .claude/settings.json, update memory (520dcd3) by Tom Kwon
**Changed:**
  .claude/MEMORY.md | 68 +++++++++++++++++++++++--------------------------------
  .gitignore        |  1 +
  2 files changed, 29 insertions(+), 40 deletions(-)

## 2026-02-25 (07:39 UTC) · @Tom Kwon
**Commit:** docs: fix stale agent/hook counts, add RLM explanation, update roles doc (3de4b38) by Tom Kwon
**Changed:**
  docs/2026_UPGRADE_GUIDE.md         |  26 +--
  docs/ROLES_AND_RESPONSIBILITIES.md | 425 +++++++++----------------------------
  docs/agents.html                   |  84 ++++++++
  guides/RLM_ARCHITECTURE.md         |   2 +-
  4 files changed, 197 insertions(+), 340 deletions(-)

## 2026-02-25 (08:06 UTC) · @Tom Kwon
**Commit:** docs: fix stale references across guides and docs (5092a90) by Tom Kwon
**Changed:**
  docs/SECURITY_BEST_PRACTICES.md | 21 ++++++------
  docs/WORKTREE_TEST.md           |  4 ++-
  guides/AGENT_TEAMS.md           |  2 +-
  guides/AGENT_TEAMS_SETUP.md     |  2 +-
  guides/MASTER_SUMMARY.md        | 73 ++++++++++++++++++++---------------------
  guides/MISSION_CONTROL.md       |  2 +-
  6 files changed, 51 insertions(+), 53 deletions(-)

## 2026-02-25 (08:09 UTC) · @Tom Kwon
**Commit:** docs: warn about moving framework directory breaking all tools (9e946e6) by Tom Kwon
**Changed:**
  ADMIN.md  | 41 +++++++++++++++++++++++++++++++++++++++++
  CLAUDE.md |  1 +
  2 files changed, 42 insertions(+)

## 2026-02-25 (08:16 UTC) · @Tom Kwon
**Commit:** docs: auto-regenerate from repo state (483dfd1) by Tom Kwon
**Changed:**
  CLAUDE.md | 1 -
  1 file changed, 1 deletion(-)

## 2026-03-04 (07:13 UTC) · @Tom Kwon
**Commit:** docs: persist framework-move warning through auto-doc regeneration (3a0a13a) by Tom Kwon
**Changed:**
  CLAUDE.md                | 1 +
  scripts/generate_docs.py | 1 +
  2 files changed, 2 insertions(+)

## 2026-03-09 (05:53 UTC) · @Tom Kwon
**Commit:** fix: deduplicate memory entries, auto-install prerequisites (093d268) by Tom Kwon
**Changed:**
  .claude/FACTS.md                                   |   3 +-
  .claude/MEMORY.md                                  | 288 +++------------------
  .../framework/memory/auto_memory_writer.py         |  41 ++-
  install.sh                                         |  77 +++++-
  4 files changed, 152 insertions(+), 257 deletions(-)

## 2026-03-27 (01:30 UTC) · @Tom Kwon
**Commit:** feat: add arch-map command/skill, update prime with caching improvements (eb5971b) by Tom Kwon
**Changed:**
  .claude/FACTS.md                                |   4 +-
  .claude/MEMORY.md                               |   9 +
  CLAUDE.md                                       |   4 +-
  README.md                                       |  12 +-
  global-commands/arch-map.md                     |  50 ++++
  global-commands/prime.md                        |  42 +++
  global-hooks/framework/automation/auto_prime.py |  65 +++++
  global-skills/arch-map/SKILL.md                 | 353 ++++++++++++++++++++++++
  8 files changed, 531 insertions(+), 8 deletions(-)

## 2026-03-29 (16:57 UTC) · @Tom Kwon
**Commit:** v3.0.2: Regenerate all docs, update FACTS.md, bump version (543e963) by Tom Kwon
**Changed:**
  .claude/FACTS.md         | 78 +++++++++++++++++++++++++-----------------------
  CLAUDE.md                | 76 +++++++++++++++++++++++++++++++++++++++++++---
  README.md                | 22 +++++++-------
  scripts/generate_docs.py |  2 +-
  4 files changed, 125 insertions(+), 53 deletions(-)

## 2026-03-30 (12:14 UTC) · @Tom Kwon
**Commit:** v4.0: Major upgrade — 16 events, async hooks, new agents, project cleanup (687c93b) by Tom Kwon
**Changed:**
  .claude/ARCHITECTURE.md                            |  476 +++++
  .claude/MEMORY.md                                  |    9 +
  CLAUDE.md                                          |  173 +-
  README.md                                          |   30 +-
  archive/docs/FRAMEWORK_GUIDE_KR.md                 | 1116 ++++++++++
  .../docs}/KNOWLEDGE_DB_VERIFICATION.md             |    0
  {docs => archive/docs}/KNOWLEDGE_PIPELINE_TEST.md  |    0
  {docs => archive/docs}/REVIEW_SYSTEM_TEST.md       |    0
  {docs => archive/docs}/RLM_AUTO_TRIGGERING.md      |    0
  {docs => archive/docs}/SKILLS_INTEGRITY.md         |    0
  ... and 42 more files

## 2026-03-31 (16:29 UTC) · @Tom Kwon
**Commit:** fix: add --no-project to all uv run hook commands (dc88499) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                | 15 ++++++++
  templates/settings.json.template | 74 ++++++++++++++++++++--------------------
  2 files changed, 52 insertions(+), 37 deletions(-)

## 2026-04-01 (05:44 UTC) · @Tom Kwon
**Commit:** v4.0: Add solve agent with parallel orchestration, tidy skill, model tier updates (ea6f7f2) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                     |   7 +
  CLAUDE.md                             |   7 +-
  README.md                             |  15 +-
  data/model_tiers.yaml                 |  50 +--
  global-agents/critical-analyst.md     |   2 +-
  global-agents/meta-agent.md           |   2 +-
  global-agents/researcher.md           |   2 +-
  global-agents/scout-report-suggest.md |   2 +-
  global-agents/solve.md                | 569 ++++++++++++++++++++++++++++++++++
  global-skills/solve/SKILL.md          |  15 +
  ... and 4 more files
