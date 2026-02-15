# 2026 Upgrade Guide

**Date**: February 2026
**Version**: 2.1.0

This document summarizes the current state of the Claude Agentic Framework after the 2026 overhaul and subsequent cleanup.

---

## Current State (v2.1.0)

| Area | Count | Details |
|------|-------|---------|
| Agents | 11 | 8 root + 3 team, across 3 tiers |
| Commands | 14 | Delegation, orchestration, review, testing, debugging |
| Skills | 6 | code-review, error-analyzer, knowledge-db, refactoring-assistant, security-scanner, test-generator |
| Hooks | 5 | Across 4 event types (PreToolUse, PostToolUse, Stop, SessionStart) |
| Guides | 15 | Context engineering, multi-agent patterns, orchestration |
| Docs | 9 | Reference documentation |

Note: These counts are maintained automatically by `scripts/generate_docs.py`.
Run `uv run scripts/generate_docs.py` to verify against live repo state.

---

## Model Tiers

| Tier | Agents | Use For |
|------|--------|---------|
| Opus (4) | orchestrator, project-architect, critical-analyst, rlm-root | Planning, architecture, security, complex reasoning |
| Sonnet (5) | researcher, meta-agent, scout-report-suggest, builder, project-skill-generator | Implementation, research, analysis, skill generation |
| Haiku (2) | docs-scraper, validator | Validation, scraping, read-only ops |

Config: `data/model_tiers.yaml`

---

## What Changed from v1

| Area | v1 (2025) | v2.1.0 (2026) |
|------|-----------|---------------|
| Agents | 3 root | 8 root + 3 team |
| Commands | 8 | 14 |
| Skills | 2 | 6 |
| Hooks | 3 events | 4 events, 5 hooks total |
| Knowledge | None | SQLite FTS5 persistent memory |
| Review | None | Continuous post-commit review |
| Model Tiers | Single model | 3-tier (Opus/Sonnet/Haiku) |
| Security | Pattern-only | Pattern + SHA-256 skills integrity |
| Auto-docs | None | generate_docs.py + SessionStart validation |
| Cost tracking | None | Append-only JSONL + budget controls |

---

## Migration from v1

```bash
cp -r ~/.claude ~/.claude-v1-backup
cd claude-agentic-framework
git pull origin main
./install.sh
```

The installer handles everything: config generation, symlinks, doc regeneration, dependency checks.

---

## Key Features

### Auto-Documentation
README.md and CLAUDE.md are generated from live repo state by `scripts/generate_docs.py`.
The SessionStart hook warns if docs are stale. install.sh regenerates on every run.

### Cost Tracking
Append-only JSONL logging in `~/.claude/logs/cost_tracking.jsonl`.
Budget controls in `data/budget_config.yaml`. CLI via `/costs` command.

### Knowledge Pipeline
SQLite FTS5 database in `data/knowledge-db/` for persistent cross-session memory.
Managed via the `knowledge-db` skill.

### Continuous Review
Post-commit analyzers check complexity, security, duplication, dead code, and architecture.
Run `/review` manually or `/refine` to auto-fix findings.

### Security
- Skills integrity: SHA-256 lock file verified on session start
- Damage control: PreToolUse hook blocks destructive commands
- Input validation: Character allowlists, path containment
- File permissions: 0o600 on sensitive data

---

## Configuration

| File | Purpose |
|------|---------|
| `templates/settings.json.template` | Source of truth for settings.json |
| `data/model_tiers.yaml` | Agent-to-model tier assignments |
| `data/budget_config.yaml` | Cost limits and alerts |

Edit templates, then run `./install.sh` to apply.

---

## Breaking Changes from v2.0.0 to v2.1.0

1. **Reduced from 52 hooks to 5** -- prompt hooks and mastery hooks removed for token efficiency
2. **Reduced from 25 agents to 11** -- guardrails agents and duplicates consolidated
3. **Reduced from 24 commands to 14** -- worktree, crypto, and redundant commands archived
4. **Skills reduced from 23 to 6** -- planning, scaffolding, and niche skills archived
5. **No LLM prompt hooks** -- removed for token efficiency
6. **No mastery logging hooks** -- observability send_event only

---

*This document is manually maintained. For auto-generated counts, see README.md.*
