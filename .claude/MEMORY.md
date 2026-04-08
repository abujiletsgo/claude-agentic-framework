# Project Memory — claude-agentic-framework
<!-- Mid-term project memory: one entry per session. Auto-maintained. -->
<!-- Layer 2 (episodic): what changed, was fixed, was decided across sessions. -->

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

## 2026-04-03 (05:52 UTC) · @Tom Kwon
**Commit:** v4.1: Epistemic guard hook, CAF mode, auto-prime improvements (4ca6dd4) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                                  |  15 ++
  CLAUDE.md                                          |  28 ++-
  README.md                                          |  11 +-
  data/caddy_config.yaml                             |   1 +
  global-hooks/framework/automation/auto_escalate.py |  11 ++
  global-hooks/framework/automation/auto_prime.py    |  67 ++++++-
  global-hooks/framework/caddy/analyze_request.py    |  21 +++
  global-hooks/framework/caddy/auto_delegate.py      |  21 +++
  global-hooks/framework/caf_mode.py                 | 111 +++++++++++
  .../framework/guardrails/epistemic_guard.py        | 135 ++++++++++++++
  ... and 7 more files

## 2026-04-03 (05:59 UTC) · @Tom Kwon
**Commit:** feat: v4.1 role-based multi-agent team with self-correction and token efficiency (8d118a7) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                                  |  15 +
  CLAUDE.md                                          |  12 +-
  README.md                                          |  29 +-
  data/model_tiers.yaml                              |   6 +-
  global-agents/agent-watchdog.md                    | 128 ++++++
  global-agents/builder.md                           | 109 +++++
  global-agents/debugger.md                          | 111 +++++
  global-agents/orchestrator.md                      | 500 +++++++++++++++++++--
  global-agents/solve.md                             | 199 ++++++--
  global-agents/validator.md                         | 100 +++++
  ... and 14 more files

## 2026-04-03 (06:00 UTC) · @Tom Kwon
**Commit:** fix: sync orchestrator, caddy, and tier configs with actual skills/agents (d2794d2) by Tom Kwon
**Changed:**
  CLAUDE.md                     |  2 +-
  data/caddy_config.yaml        | 37 +++++++++++++++++++++----------------
  data/model_tiers.yaml         |  3 ++-
  global-agents/orchestrator.md | 33 ++++++++++++++++++++-------------
  4 files changed, 44 insertions(+), 31 deletions(-)

## 2026-04-03 (07:56 UTC) · @Tom Kwon
**Commit:** docs: auto-regenerate from repo state (bd1745c) by Tom Kwon
**Changed:**
  README.md | 4 ++--
  1 file changed, 2 insertions(+), 2 deletions(-)

## 2026-04-07 (05:46 UTC) · @Tom Kwon
**Commit:** perf: eliminate token bloat in research/orchestration pipeline (eb9c33c) by Tom Kwon
**Changed:**
  .claude/FACTS.md                      |   4 +
  .claude/MEMORY.md                     |  30 +++++
  data/caddy_config.yaml                |  12 ++
  data/model_tiers.yaml                 |   5 +-
  global-agents/orchestrator.md         | 169 +++++++++++++++++++-----
  global-agents/researcher.md           | 234 ++++++++++++----------------------
  global-agents/rlm-root.md             |   7 +-
  global-agents/scout-report-suggest.md |  27 +++-
  global-commands/orchestrate.md        |   3 +
  global-commands/research.md           | 157 ++++++++++++++---------
  ... and 1 more files

## 2026-04-07 (06:56 UTC) · @Tom Kwon
**Commit:** fix: enforce orchestrator delegation with structural guardrails (bc9ae25) by Tom Kwon
**Changed:**
  .claude/MEMORY.md                                  |   15 +
  CLAUDE.md                                          |    7 +-
  README.md                                          |   15 +-
  global-agents/orchestrator-reference.md            |  516 +++++++++
  global-agents/orchestrator.md                      | 1167 +++++++-------------
  global-agents/solve.md                             |  169 +--
  global-hooks/framework/caddy/analyze_request.py    |   11 +
  .../framework/guardrails/enforce_orchestrate.py    |  129 +++
  .../framework/guardrails/orch_depth_tracker.py     |  157 +++
  .../guardrails/orchestrator_tool_guard.py          |  134 +++
  ... and 4 more files

## 2026-04-07 (07:08 UTC) · @Tom Kwon
**Commit:** feat: add /makeskill skill — autonomous project skill factory (3b8e64a) by Tom Kwon
**Changed:**
  CLAUDE.md                        |   2 +-
  README.md                        |   7 +-
  global-skills/makeskill/SKILL.md | 685 +++++++++++++++++++++++++++++++++++++++
  3 files changed, 690 insertions(+), 4 deletions(-)

## 2026-04-07 (07:08 UTC) · @Tom Kwon
**Commit:** fix: prevent hook errors on fresh installs (8acaa95) by Tom Kwon
**Changed:**
  .../framework/guardrails/integrate_guardrails.py   |   2 +-
  global-hooks/framework/korean/kr_mode.py           |   6 ++
  install.sh                                         | 120 +++++++++++++++++++--
  3 files changed, 118 insertions(+), 10 deletions(-)

## 2026-04-07 (07:15 UTC) · @Tom Kwon
**Commit:** fix: resolve SessionStart and UserPromptSubmit hook errors (6f618d2) by Tom Kwon
**Changed:**
  global-hooks/framework/caddy/analyze_request.py        | 2 +-
  global-hooks/framework/caddy/auto_delegate.py          | 2 +-
  global-hooks/framework/caddy/monitor_progress.py       | 2 +-
  global-hooks/framework/session/session_startup.py      | 2 +-
  global-hooks/framework/teams/anti_loop_team.py         | 2 +-
  global-hooks/framework/teams/delegate_mode_enforcer.py | 2 +-
  global-hooks/framework/teams/task_validator.py         | 2 +-
  global-hooks/framework/teams/teammate_monitor.py       | 2 +-
  global-status-lines/mastery/status_line_custom.py      | 2 +-
  global-status-lines/mastery/status_line_v9.py          | 2 +-
  ... and 1 more files

## 2026-04-07 (07:27 UTC) · @Tom Kwon
**Commit:** docs: auto-regenerate from repo state (d4e2933) by Tom Kwon
**Changed:**
  CLAUDE.md | 2 +-
  README.md | 6 +++---
  2 files changed, 4 insertions(+), 4 deletions(-)

## 2026-04-07 (07:40 UTC) · @Tom Kwon
**Commit:** fix: inject dynamic PATH into settings.json for hook execution (cf7bb14) by Tom Kwon
**Changed:**
  install.sh | 32 +++++++++++++++++++++++++++++++-
  1 file changed, 31 insertions(+), 1 deletion(-)

## 2026-04-07 (16:07 UTC) · @Tom Kwon
**Commit:** fix: make damage-control and circuit-breaker fail-open on errors (e7244a2) by Tom Kwon
**Changed:**
  .../damage-control/unified-damage-control.py       | 24 +++++++++++++++-------
  .../guardrails/circuit_breaker_wrapper.py          |  9 +++++++-
  2 files changed, 25 insertions(+), 8 deletions(-)

## 2026-04-07 (16:51 UTC) · @Tom Kwon
**Commit:** feat: integrate mempalace AAAK dialect + temporal knowledge graph (9a263a2) by Tom Kwon
**Changed:**
  global-hooks/framework/aaak_compress.py            | 131 +++++++++++++++
  .../framework/context/pre_compact_preserve.py      |  45 +++++
  .../framework/facts/auto_fact_extractor.py         |  10 ++
  global-hooks/framework/facts/fact_kg_sync.py       | 184 +++++++++++++++++++++
  global-hooks/framework/facts/validate_facts.py     |  13 ++
  install.sh                                         |   2 +-
  templates/settings.json.template                   |   4 +
  7 files changed, 388 insertions(+), 1 deletion(-)

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
