# Project Facts
<!-- MANAGED: claude-agentic-framework | updated: 2026-03-29 | layer: episodic -->
<!-- Injected at session start as authoritative ground truth. -->

## CONFIRMED
- Python executor is `uv run` (not python3/pip/poetry) [2026-02-24]
- `bash install.sh` regenerates config, symlinks, and docs from templates [2026-02-24]
- Never edit `~/.claude/settings.json` directly — overwritten by install.sh [2026-02-24]
- Config source of truth: `templates/settings.json.template` [2026-02-24]
- All hooks invoked as: `uv run __REPO_DIR__/path/to/hook.py` [2026-02-24]
- Framework v3.0.2: 30 hooks, 8 agents (7 opus, 1 haiku), 9 skills, 15 commands [2026-03-29]
- Knowledge pipeline split-brain FIXED — all modules use get_canonical_db_path() [2026-03-29]
- run_tests.py is REAL — 67 functional tests, `python3 scripts/run_tests.py` [2026-03-29]
- Default model: opus (Max plan, no cost optimization needed) [2026-03-29]
- 3 new hook events: SubagentStop, ConfigChange, PostToolUseFailure [2026-03-29]
- Agent teams enabled via env var in settings template [2026-03-29]
- Auto-skill generator fires on Stop, detects repeated patterns, creates SKILL.md [2026-03-29]
- CVE-2025-59536/CVE-2026-21852 mitigations in damage-control patterns [2026-03-29]
- Memory layer testing methodology: 15-question process, target 14/15 [2026-03-29]
- Researcher maxTurns=25 (not 50), must check context layers before searching [2026-04-03]
- Context-first protocol: agents read PROJECT_CONTEXT.md/FACTS.md/ARCHITECTURE.md BEFORE any codebase search [2026-04-03]
- Orchestrator injects pre-digested context into all sub-agent prompts to prevent redundant reads [2026-04-03]

## GOTCHAS
- NEVER delete a hook file referenced in live settings.json — stub first, reinstall, delete after [2026-02-24]
- `observe_patterns.py` and `analyze_session.py` NOT wired — knowledge pipeline only runs LEARN + EVOLVE [2026-02-24]
- Circuit breaker disables hooks after 3 failures for 60s — delete `~/.claude/circuit_breakers/{hook}.json` to reset [2026-02-24]
- Damage control blocks CVE flag names and "eval" even in commit messages — rephrase to avoid [2026-03-29]
- Research agents that skip context-first protocol waste 3-8 turns re-discovering known project info [2026-04-03]
- meta-agent.md has two `model:` lines — frontmatter (opus) is the real one, body line is template instructions [2026-03-29]

## PATHS & ARCHITECTURE
- Hook config: `templates/settings.json.template` [2026-02-24]
- Model tiers: `data/model_tiers.yaml` (7 opus, 1 haiku on Max plan) [2026-03-29]
- Knowledge DB: `~/.claude/data/knowledge-db/knowledge.db` (canonical path) [2026-03-29]
- Test suite: `scripts/run_tests.py` (67 tests, --fast/--verbose flags) [2026-03-29]
- Memory testing guide: `guides/MEMORY_LAYER_TESTING.md` [2026-03-29]
- Auto-skill generator: `global-hooks/framework/automation/auto_skill_generator.py` [2026-03-29]
- Skill builder: `global-skills/skill-builder/SKILL.md` [2026-03-29]
- Config audit log: `~/.claude/data/logs/config_audit.jsonl` [2026-03-29]
- Agent tracking: `~/.claude/data/agent_tracking.jsonl` [2026-03-29]
- Circuit breakers: `~/.claude/circuit_breakers/` [2026-02-24]
- Agents: `global-agents/` → `~/.claude/agents/` [2026-02-24]
- Skills: `global-skills/` → `~/.claude/skills/` [2026-02-24]

## PATTERNS
- Template change: edit `templates/settings.json.template` → `bash install.sh` → restart session [2026-02-24]
- Safe hook removal: stub as no-op → install → delete next session [2026-02-24]
- Reset broken hook: delete `~/.claude/circuit_breakers/{hook_name}.json` [2026-02-24]
- Force prime refresh: `rm .claude/PROJECT_CONTEXT.md && /prime` [2026-02-24]
- Run test suite: `python3 scripts/run_tests.py` (full) or `--fast` (skip slow) [2026-03-29]
- Create new skill: `/skill-builder` or manually in `.claude/skills/<name>/SKILL.md` [2026-03-29]

## STALE
- "Knowledge pipeline split-brain" GOTCHA — FIXED in v3.0 [2026-03-29]
- "run_tests.py is a no-op stub" — REPLACED with real 67-test suite [2026-03-29]
- "default_model: sonnet" — changed to opus for Max plan [2026-03-29]
- "4 sonnet agents" — all upgraded to opus [2026-03-29]
