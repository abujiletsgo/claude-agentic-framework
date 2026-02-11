# 2026 Upgrade Guide

**Date**: February 2026
**Version**: 2.0.0

This document summarizes every new feature, structural change, and migration step introduced in the 2026 overhaul of the Claude Agentic Framework.

---

## Table of Contents

- [What Changed](#what-changed)
- [New Features at a Glance](#new-features-at-a-glance)
- [Migration from v1 to v2](#migration-from-v1-to-v2)
- [Skills System (23 Skills)](#skills-system-23-skills)
- [Prompt Hooks (Hybrid Security)](#prompt-hooks-hybrid-security)
- [Knowledge Pipeline](#knowledge-pipeline)
- [Continuous Review System](#continuous-review-system)
- [Multi-Model Tiers](#multi-model-tiers)
- [Strategic Agents](#strategic-agents)
- [Agent Teams (Builder + Validator)](#agent-teams-builder--validator)
- [Worktree Management](#worktree-management)
- [Community Skill Patterns](#community-skill-patterns)
- [Project Skill Generator](#project-skill-generator)
- [Guardrails System](#guardrails-system)
- [Security Improvements](#security-improvements)
- [Updated Commands](#updated-commands)
- [Breaking Changes](#breaking-changes)
- [Configuration Changes](#configuration-changes)

---

## What Changed

The 2026 upgrade transforms the framework from a command-and-agent toolkit into a full autonomous engineering platform. The key changes:

| Area | v1 (2025) | v2 (2026) |
|------|-----------|-----------|
| Skills | 2 (prime, damage-control) | 23 (full engineering workflow) |
| Agents | 3 root + 0 team | 15 root + 2 team + 8 guardrails + 8 agbot |
| Commands | 8 | 25+ |
| Hooks | 3 namespaces | 5 namespaces + prompt hooks |
| Knowledge | None | SQLite FTS5 persistent memory |
| Review | None | Continuous post-commit review |
| Model Tiers | Single model | 3-tier (Opus/Sonnet/Haiku) per agent |
| Security | Pattern-only | Hybrid (pattern + LLM semantic) + skills integrity + skill auditing |
| Worktrees | None | Full git worktree management |
| Vulnerability Fixes | N/A | 3 P0 fixes (command injection, file overwrite, access control) |
| Security Tooling | None | skills.lock, audit_skill.py, verify_skills.py |

---

## New Features at a Glance

### 1. Skills System (23 Skills)
Self-describing, auto-triggerable capabilities. Each skill has a `SKILL.md` with frontmatter that Claude Code can discover and invoke automatically.

### 2. Prompt Hooks (Hybrid Security)
LLM-based semantic security validation alongside pattern-matching hooks. Catches obfuscated threats that regex cannot detect.

### 3. Knowledge Pipeline
SQLite FTS5 database for persistent cross-session memory. Hooks automatically extract learnings, inject relevant context, and observe patterns.

### 4. Continuous Review System
Post-commit code review powered by analyzers that check complexity, security, style, and performance. Findings stored in a persistent findings database.

### 5. Multi-Model Tiers
Every agent assigned to the right model tier (Opus/Sonnet/Haiku) for optimal cost-quality balance. 33 agents across 3 tiers.

### 6. Strategic Agents
Project-Architect and Critical-Analyst agents replace domain-specific (crypto) agents with versatile, project-agnostic intelligence.

### 7. Agent Teams
Builder + Validator pattern for implementation tasks. Project Skill Generator for creating project-specific automation.

### 8. Worktree Management
Git worktree skills for parallel development across multiple branches without stashing or context switching.

### 9. Security Hardening
Skills integrity verification (SHA-256 lock file), automatic skill auditing (Caddy), P0 vulnerability fixes (command injection, file overwrite, access control), input validation standards, file permission enforcement, and `--force` flag convention. See [SECURITY_BEST_PRACTICES.md](SECURITY_BEST_PRACTICES.md).

---

## Migration from v1 to v2

### Step 1: Backup Existing Installation

```bash
# The installer creates backups automatically, but do a manual one too
cp -r ~/.claude ~/.claude-v1-backup
```

### Step 2: Pull Latest Code

```bash
cd ~/Documents/claude-agentic-framework
git pull origin main
```

### Step 3: Run the Installer

```bash
./install.sh
```

The installer will:
1. Backup existing `~/.claude/` configuration
2. Symlink all new commands, agents, skills, and hooks
3. Regenerate `settings.json` from the updated template (includes prompt hooks, knowledge hooks, review hooks)
4. Create runtime directories (`data/knowledge-db/`, `data/logs/`, `data/tts_queue/`)
5. Set executable permissions on all hook scripts

### Step 4: Clean Up Old Artifacts

If you had v1 crypto agents installed, remove broken symlinks:

```bash
rm -f ~/.claude/agents/crypto
rm -f ~/.claude/commands/cook_research_only.md
rm -f ~/.claude/commands/crypto_research.md
rm -f ~/.claude/commands/cook.md
rm -f ~/.claude/commands/crypto_research_haiku.md
```

### Step 5: Verify Installation

```bash
# Check new skills are installed
ls ~/.claude/skills/ | wc -l
# Expected: 23+

# Check new agents
ls ~/.claude/agents/ | wc -l
# Expected: 15+ root agents

# Check settings.json has prompt hooks
grep -c '"type": "prompt"' ~/.claude/settings.json
# Expected: 3 (Bash, Edit, Write prompt hooks)

# Check knowledge database directory
ls ~/.claude/data/knowledge-db/
```

### Step 6: Configure Model Tiers

Model tiers are set in agent frontmatter. Review and adjust assignments:

```bash
# View centralized tier config
cat data/model_tiers.yaml

# Check a specific agent's tier
head -5 ~/.claude/agents/orchestrator.md
# Should show: model: opus
```

---

## Skills System (23 Skills)

Skills are auto-discoverable capabilities in `global-skills/`. Each has a `SKILL.md` with structured frontmatter that Claude Code uses for matching.

### Full Skill Inventory

| Skill | Purpose | Category |
|-------|---------|----------|
| `prime` | Load project context on-demand | Context |
| `meta-skill` | Create new skills from templates | Meta |
| `knowledge-db` | Persistent cross-session memory | Knowledge |
| `multi-model-tiers` | Configure agent model assignments | Config |
| `code-review` | Automated code review | Quality |
| `test-generator` | Generate test suites | Testing |
| `tdd-workflow` | Test-driven development workflow | Testing |
| `security-scanner` | Security vulnerability scanning | Security |
| `dependency-audit` | Dependency vulnerability audit | Security |
| `error-analyzer` | Analyze and fix errors | Debugging |
| `performance-profiler` | Performance profiling and optimization | Performance |
| `refactoring-assistant` | Automated refactoring | Code Quality |
| `documentation-writer` | Generate documentation | Documentation |
| `project-scaffolder` | Scaffold new projects | Project Setup |
| `git-workflow` | Git workflow management | Version Control |
| `brainstorm-before-code` | Pre-implementation brainstorming | Planning |
| `feasibility-analysis` | Feasibility assessment | Planning |
| `task-decomposition` | Break tasks into sub-tasks | Planning |
| `downstream-correction` | Fix downstream breakage | Maintenance |
| `verification-checklist` | Pre-completion verification | Quality |
| `video-processor` | Process video content | Media |
| `worktree-manager-skill` | Git worktree management | Version Control |
| `create-worktree-skill` | Create git worktrees | Version Control |

### How Skills Work

1. Claude Code reads `SKILL.md` frontmatter on startup
2. The `description` field tells Claude when to auto-trigger the skill
3. User can invoke explicitly: `/skill-name` or say trigger phrases
4. Skill workflow is defined in the markdown body

### Creating New Skills

Use the meta-skill:
```
"Create a new skill for [purpose]"
```

Or manually create `global-skills/my-skill/SKILL.md`:
```yaml
---
name: my-skill
description: "When to trigger this skill..."
---
# My Skill
[Workflow instructions]
```

---

## Prompt Hooks (Hybrid Security)

The 2026 upgrade adds LLM-based semantic validation as a second security layer alongside existing pattern-matching hooks.

### Architecture

```
PreToolUse Event
    |
    +---> Command Hook (pattern match, ~50ms)
    |
    +---> Prompt Hook (LLM evaluation, ~2-5s)
    |
    v
  Both must allow. Either blocking = operation blocked.
```

### What is Covered

- **Bash**: Obfuscated destructive commands, remote code execution, data exfiltration
- **Edit**: Removal of security checks, code injection, credential modifications
- **Write**: Overwriting configs, writing secrets, privilege escalation

### Configuration

Prompt hooks are defined in `settings.json` (generated from `templates/settings.json.template`):

```json
{
  "type": "prompt",
  "prompt": "Security review prompt with $ARGUMENTS placeholder...",
  "timeout": 10,
  "statusMessage": "LLM semantic validation..."
}
```

### Testing Prompt Hooks

```bash
uv run global-hooks/framework/testing/test_hooks.py -v
```

See `global-hooks/prompt-hooks/README.md` for full documentation.

---

## Knowledge Pipeline

Persistent cross-session memory using SQLite with FTS5 full-text search.

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `knowledge_db.py` | `global-hooks/framework/knowledge/` | Core database operations |
| `extract_learnings.py` | Same | Extract learnings from sessions |
| `store_learnings.py` | Same | Store learnings in database |
| `inject_knowledge.py` | Same | Inject relevant knowledge into context |
| `inject_relevant.py` | Same | Context-aware knowledge injection |
| `observe_patterns.py` | Same | Observe and record patterns |
| `analyze_session.py` | Same | Post-session analysis |
| `session_knowledge.py` | Same | Session-level knowledge operations |
| Knowledge DB Skill | `global-skills/knowledge-db/` | User-facing CLI and skill |

### Categories

| Category | Description |
|----------|-------------|
| `decision` | Architectural and design decisions |
| `learning` | Lessons learned from experience |
| `pattern` | Reusable code/workflow patterns |
| `error` | Known errors and their fixes |
| `context` | Project context and background |
| `preference` | User preferences and conventions |

### CLI Usage

```bash
# Store knowledge
uv run knowledge_cli.py store --category decision --title "Use FTS5" --content "..."

# Search knowledge
uv run knowledge_cli.py search "hook patterns"

# Recent entries
uv run knowledge_cli.py recent --limit 10
```

---

## Continuous Review System

Automated post-commit code review with persistent findings tracking.

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `review_engine.py` | `global-hooks/framework/review/` | Core review engine |
| `post_commit_review.py` | Same | Git post-commit hook |
| `findings_store.py` | Same | Persistent findings database |
| `findings_notifier.py` | Same | Notification of findings |
| `review_config.yaml` | Same | Review configuration |
| `analyzers/` | Same | Individual analyzer modules |

### Analyzers

The review engine runs multiple analyzers on each commit:
- Complexity analysis
- Security vulnerability detection
- Style and convention checking
- Performance anti-pattern detection

### Configuration

Edit `global-hooks/framework/review/review_config.yaml` to adjust:
- Which analyzers to run
- Severity thresholds
- File type filters
- Notification preferences

---

## Multi-Model Tiers

Every agent is assigned to the optimal model tier for its task type.

### Tier Distribution

```
Opus (12%):   4 agents  -- orchestrator, project-architect, critical-analyst, rlm-root
Sonnet (48%): 16 agents -- builder, researcher, meta-agent, + 13 more
Haiku (39%):  13 agents -- validator, docs-scraper, hello-world, + 10 more
Total: 33 agents
```

### Decision Matrix

| Task Complexity | Risk Level | Recommended Tier |
|----------------|-----------|-----------------|
| High | High | Opus |
| High | Low | Sonnet |
| Medium | High | Opus |
| Medium | Low | Sonnet |
| Low | Any | Haiku |

### Cost Savings

For a heavy session with 50% subagent delegation:
- **Before** (all-Opus): ~$27
- **After** (optimized tiers): ~$4-6
- **Savings**: 50-60%

### Configuration

Set in agent frontmatter:
```yaml
---
model: sonnet  # or opus, haiku
---
```

Centralized config: `data/model_tiers.yaml`

---

## Strategic Agents

Two new versatile agents replace the removed crypto-specific agents.

### Project-Architect
- **Location**: `global-agents/project-architect.md`
- **Tier**: Opus
- **Purpose**: Analyze projects, design custom agent ecosystems, create project-specific skills and automation
- **When to use**: After planning phase, when initializing work on a project

### Critical-Analyst
- **Location**: `global-agents/critical-analyst.md`
- **Tier**: Opus
- **Purpose**: Question every detail, assumption, and decision. Identify risks and alternative approaches.
- **When to use**: During planning, building, and decision-making

---

## Agent Teams (Builder + Validator)

### Pattern

```
Orchestrator (opus) --> plans and coordinates
    |
    +---> Builder (sonnet) --> implements the solution
    |
    +---> Validator (haiku) --> independently verifies
```

### Team Agents

| Agent | Location | Tier | Purpose |
|-------|----------|------|---------|
| Builder | `global-agents/team/builder.md` | Sonnet | Code implementation |
| Validator | `global-agents/team/validator.md` | Haiku | Read-only verification |
| Project Skill Generator | `global-agents/team/project-skill-generator.md` | Sonnet | Generate project-specific skills |

### Guardrails Agents (8 agents)

Located in `global-agents/team/guardrails/`:
- `circuit-breaker-agent.md` (Sonnet) -- State machine implementation
- `cli-tool-agent.md` (Sonnet) -- CLI interface
- `config-agent.md` (Haiku) -- YAML configuration
- `docs-agent.md` (Haiku) -- Documentation writing
- `integration-agent.md` (Sonnet) -- System integration
- `qa-validator-agent.md` (Haiku) -- QA validation
- `state-manager-agent.md` (Sonnet) -- State persistence
- `test-agent.md` (Haiku) -- Test execution

---

## Worktree Management

Git worktree support for parallel development across multiple branches.

### Skills

- `worktree-manager-skill` -- Full worktree lifecycle management
- `create-worktree-skill` -- Quick worktree creation

### Commands

- `/create-worktree` -- Create a new worktree
- `/list-worktrees` -- List all worktrees
- `/remove-worktree` -- Remove a worktree

### Documentation

See `global-skills/worktree-manager-skill/` for:
- `SKILL.md` -- Main skill definition
- `OPERATIONS.md` -- Detailed operation reference
- `REFERENCE.md` -- Quick reference
- `EXAMPLES.md` -- Usage examples
- `TROUBLESHOOTING.md` -- Common issues

---

## Community Skill Patterns

The framework now supports community-contributed patterns for creating skills:

### Planning Skills
- `brainstorm-before-code` -- Pre-implementation ideation
- `feasibility-analysis` -- Assess viability before building
- `task-decomposition` -- Break complex tasks into manageable pieces

### Quality Skills
- `verification-checklist` -- Pre-completion verification
- `downstream-correction` -- Fix cascading breakage from changes

### Development Skills
- `tdd-workflow` -- Test-driven development cycle
- `code-review` -- Structured code review
- `refactoring-assistant` -- Safe, systematic refactoring

---

## Project Skill Generator

The `project-skill-generator` agent (`global-agents/team/project-skill-generator.md`) automatically creates project-specific skills, hooks, and commands by analyzing a project's tech stack, patterns, and requirements.

### Usage

```
"Generate skills for this project"
"Create project-specific automation"
```

The generator:
1. Analyzes the project structure and tech stack
2. Identifies automation opportunities
3. Generates tailored SKILL.md files
4. Creates matching hooks and commands if needed

---

## Guardrails System

Anti-loop guardrails in `global-hooks/framework/guardrails/` prevent agents from entering infinite loops or making destructive repeated operations.

Documentation: `global-hooks/framework/ANTI_LOOP_GUARDRAILS.md`

---

## Security Improvements

The 2026 upgrade includes significant security hardening across the skill ecosystem.

### P0 Vulnerability Fixes

Three critical vulnerabilities were identified and fixed:

| Vulnerability | Skill | Fix | Version |
|---------------|-------|-----|---------|
| Command injection | worktree-manager-skill | Input validation via `scripts/validate_name.sh` (character allowlist, path containment) | 0.1.0 -> 0.2.0 |
| File overwrite | video-processor | Overwrite protection with `--force` flag, output path restriction to CWD, system directory blocking | 0.1.0 -> 0.2.0 |
| Missing access control | knowledge-db | `0o600` file permissions, import path restrictions, export limits | 0.1.0 -> 0.2.0 |

### New Security Tools

| Tool | Location | Purpose |
|------|----------|---------|
| `generate_skills_lock.py` | `scripts/` | Generate SHA-256 lock file for all skill files |
| `verify_skills.py` | `global-hooks/framework/security/` | Verify skill integrity against lock file (SessionStart hook) |
| `audit_skill.py` | `scripts/` | Audit a skill for security patterns (code injection, dangerous commands, etc.) |
| `skill_auditor.py` | `global-hooks/framework/caddy/` | Auditor module used by Caddy and CLI |

### New Security Commands

```bash
# Generate skills.lock with SHA-256 hashes of all skill files
just skills-lock

# Verify skills integrity against skills.lock
just skills-verify

# Audit a single skill for security issues
just audit-skill <skill-name>

# Audit all installed skills
just audit-all-skills
```

### Skills Integrity System

Every file in every skill is hashed with SHA-256 and stored in `~/.claude/skills.lock`. On session start, a verification hook compares current hashes and reports discrepancies (modified, deleted, new, missing, or unlocked files). See [SKILLS_INTEGRITY.md](SKILLS_INTEGRITY.md) for full documentation.

### Caddy Skill Auditing

The Caddy meta-orchestrator now automatically audits skills before recommending them. Skills with critical findings (code injection, `eval()`, `shell=True`) are blocked from recommendations. Skills with warnings are allowed but flagged. Configure in `data/caddy_config.yaml` under `skill_audit`.

### Input Validation Standards

Skills that accept user input now enforce strict validation:

- **Character allowlists**: Only permitted characters pass through (not blocklists)
- **Path containment**: Computed paths are verified to stay within expected directories
- **Path traversal blocking**: `..` sequences are rejected in all path inputs
- **System directory protection**: Write operations to `/bin`, `/etc`, `/usr`, `/var`, etc. are blocked

### File Permission Model

Sensitive data files are now created with `0o600` permissions (owner read/write only), enforced on every open operation. This applies to knowledge databases, durability logs, and lock files.

### --force Flag Convention

All destructive operations now default to safe behavior and require `--force` for the destructive path:

- Worktree removal aborts on uncommitted changes unless `--force`
- Video output files prompt before overwriting unless `--force`
- Branch deletion uses safe `-d` flag (fails on unmerged) unless `--force`

### Security Best Practices Guide

A comprehensive security guide has been created at [SECURITY_BEST_PRACTICES.md](SECURITY_BEST_PRACTICES.md) covering:

- How to safely use skills
- How to audit new skills before installation
- How to generate and verify `skills.lock`
- Input validation patterns for skill authors
- File permission model
- Vulnerability response process
- Security checklist for skill authors

---

## Updated Commands

### New Commands (v2)

| Command | Purpose |
|---------|---------|
| `/plan_w_team` | Plan with builder + validator team |
| `/build` | Build/compile project |
| `/quick-plan` | Fast lightweight planning |
| `/question` | Ask a focused question |
| `/sentient` | Advanced reasoning mode |
| `/start` | Initialize session |
| `/create-worktree` | Create git worktree |
| `/list-worktrees` | List git worktrees |
| `/remove-worktree` | Remove git worktree |
| `/refine` | Iteratively refine output |
| `/git_status` | Quick git status |
| `/all_tools` | List all available tools |
| `/convert_paths_absolute` | Convert paths to absolute |
| `/load_ai_docs` | Load AI documentation |
| `/update_status_line` | Update status line display |

### Existing Commands (carried over from v1)

| Command | Purpose |
|---------|---------|
| `/prime` | Load project context |
| `/research` | Delegate research |
| `/search` | Codebase search |
| `/analyze` | Deep analysis |
| `/orchestrate` | Multi-agent orchestration |
| `/fusion` | Best-of-N fusion |
| `/rlm` | Recursive language model |
| `/loadbundle` | Restore session |

---

## Breaking Changes

### 1. Crypto Agents Removed
All 7 crypto-specific agents and 4 crypto commands have been removed. Replaced by Project-Architect and Critical-Analyst.

### 2. settings.json Regenerated
The installer regenerates `settings.json` from the template. If you have custom settings, back them up first. The template now includes prompt hooks, knowledge hooks, and review hooks.

### 3. Model Field in Agent Frontmatter
Agents now require a `model` field in their YAML frontmatter:
```yaml
---
model: sonnet
---
```

### 4. Hook Namespaces Expanded
Hooks are now organized in 5 namespaces:
- `damage-control/` -- Security (pattern matching)
- `mastery/` -- Lifecycle tracking
- `observability/` -- Monitoring and metrics
- `framework/` -- Knowledge, review, guardrails, testing, validators
- `prompt-hooks/` -- LLM-based semantic validation (documented, configured in settings.json)

### 5. Data Directory
New `data/` directory at repo root for persistent state:
- `data/knowledge-db/` -- Knowledge database
- `data/model_tiers.yaml` -- Centralized model tier config
- `data/logs/` -- Runtime logs
- `data/tts_queue/` -- TTS audio queue

---

## Configuration Changes

### Environment Variables (unchanged from v1)

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
export MISSION_CONTROL_SERVER="http://localhost:4000"
export MISSION_CONTROL_ENABLED=true
```

### New Configuration Files

| File | Purpose |
|------|---------|
| `data/model_tiers.yaml` | Centralized model tier assignments |
| `global-hooks/framework/review/review_config.yaml` | Review system configuration |
| `templates/settings.json.template` | Source of truth for settings.json |

### settings.json Template

The template uses `__REPO_DIR__` placeholder, replaced by the installer with the actual repo path. Always edit the template, not `settings.json` directly.

---

## Summary

The 2026 upgrade brings:
- **23 skills** for a complete engineering workflow
- **Hybrid security** with LLM-based prompt hooks
- **Persistent memory** via SQLite FTS5 knowledge database
- **Continuous review** with automated post-commit analysis
- **Cost optimization** through 3-tier model assignments
- **Strategic agents** for project analysis and critical thinking
- **Worktree management** for parallel development
- **Guardrails** to prevent agent infinite loops
- **Skills integrity** via SHA-256 lock file and session-start verification
- **Automatic skill auditing** by Caddy meta-orchestrator
- **P0 vulnerability fixes** across worktree-manager, video-processor, and knowledge-db
- **Security best practices** guide with checklist for skill authors

To upgrade: `git pull && ./install.sh`

For questions or issues, see the troubleshooting section in the main README.md.
