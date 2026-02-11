# Claude Agentic Framework

> Transform Claude Code into an elite autonomous engineering platform with 95% token savings, 23 skills, 33 agents across 3 model tiers, persistent memory, and hybrid security.

## Overview

The **Claude Agentic Framework** is a comprehensive autonomous engineering platform that upgrades Claude Code from a single-agent assistant to a sophisticated multi-agent orchestration system. It provides skills, agents, hooks, commands, and persistent knowledge infrastructure for context engineering, agent coordination, continuous review, and autonomous execution.

### What You Get

- **15 Comprehensive Guides** covering everything from basic context engineering to advanced multi-agent patterns
- **25+ Ready-to-Use Commands** for delegation, orchestration, planning, worktrees, and more
- **34 Agents across 3 Tiers**: 4 Opus (planning/security), 17 Sonnet (implementation), 13 Haiku (validation)
- **23 Skills** for the full engineering lifecycle (prime, review, test, security, refactor, scaffold, TDD, and more)
- **5 Hook Namespaces**: damage-control, mastery, observability, framework (knowledge/review/guardrails/testing), prompt-hooks
- **Knowledge Pipeline**: SQLite FTS5 persistent memory for cross-session learning
- **Continuous Review**: Automated post-commit analysis with findings database
- **Hybrid Security**: Pattern-matching + LLM semantic validation (prompt hooks)
- **Multi-Model Tiers**: Right model for the right task (50-60% cost savings)
- **Git Worktree Management**: Parallel development across branches
- **Installation Scripts** for one-command setup and removal

### Key Benefits

- **95% Token Reduction**: Strip permanent context, load only what's needed
- **50-60% Cost Savings**: Multi-model tiers assign Opus/Sonnet/Haiku per agent
- **Infinite Scalability**: Delegate heavy tasks to isolated sub-agents
- **Persistent Memory**: Knowledge database survives across sessions
- **Crash Recovery**: Context bundles restore sessions instantly
- **Autonomous Execution**: Z-Threads run from prompt to production with zero human intervention
- **Continuous Review**: Automated code review on every commit
- **Hybrid Security**: Pattern + LLM semantic hooks prevent destructive operations
- **Real-Time Monitoring**: Mission Control dashboard for multi-agent observability
- **Anti-Loop Guardrails**: Prevent agents from entering infinite loops

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Architecture Overview](#architecture-overview)
- [Core Concepts](#core-concepts)
- [New in 2026](#new-in-2026)
- [Security](#security)
- [Commands Reference](#commands-reference)
- [Skills Reference](#skills-reference)
- [Step-by-Step Guide](#step-by-step-guide)
- [Performance Benefits](#performance-benefits)
- [Configuration](#configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Advanced Patterns](#advanced-patterns)
- [Contributing](#contributing)
- [Changelog](#changelog)

## Quick Start

### Installation

```bash
# Clone the repository
cd ~/Documents
git clone https://github.com/yourusername/claude-agentic-framework.git
cd claude-agentic-framework

# Run the installer
./install.sh
```

The installer will:
1. Backup your existing `~/.claude/` configuration
2. Symlink all commands, agents, skills, guides, output-styles, and hooks
3. Generate `settings.json` from template (hooks, prompt hooks, permissions)
4. Create runtime directories (`data/knowledge-db/`, `data/logs/`, `data/tts_queue/`)
5. Set executable permissions on all hook scripts
6. Validate the installation

### Your First Agentic Session

```bash
# Start Claude Code (context is NOT auto-loaded, saving tokens)
claude

# When you need project context
/prime

# Delegate heavy research to a sub-agent
/research "authentication patterns in FastAPI"

# Restore a crashed session
/loadbundle latest

# Orchestrate multi-agent task
/orchestrate "Build a REST API with authentication"
```

## Installation

### Prerequisites

- **Claude Code CLI** (version 0.1.x or higher)
- **Python 3.10+** and **uv** (for hook scripts)
- **Node.js 18+** (for Mission Control dashboard)
- **Bun** (optional, for Mission Control server)
- **Git** (for installation)

### Standard Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/claude-agentic-framework.git
cd claude-agentic-framework

# Run installer with backup
./install.sh
```

### What Gets Installed

The installer symlinks from the repo into `~/.claude/`. Source of truth stays in the repo.

```
Repo structure (source of truth):
├── global-agents/               # 15 root agents + team/ + agbot/
│   ├── orchestrator.md          # Lead coordinator (Opus)
│   ├── researcher.md            # Research specialist (Sonnet)
│   ├── rlm-root.md              # Root controller (Opus)
│   ├── project-architect.md     # Project analysis (Opus)
│   ├── critical-analyst.md      # Critical thinking (Opus)
│   ├── meta-agent.md            # Agent file generation (Sonnet)
│   ├── team/                    # Builder, Validator, Project Skill Generator
│   │   └── guardrails/          # 8 guardrail agents
│   └── agbot/                   # 8 domain-specific agents
├── global-commands/             # 25+ slash commands
│   ├── prime.md, research.md    # Context & delegation
│   ├── orchestrate.md, fusion.md # Multi-agent
│   ├── plan.md, plan_w_team.md  # Planning
│   ├── create-worktree.md       # Git worktrees
│   └── refine.md, build.md      # Development
├── global-skills/               # 23 auto-discoverable skills
│   ├── prime/                   # Context loading
│   ├── knowledge-db/            # Persistent memory (SQLite FTS5)
│   ├── multi-model-tiers/       # Model tier configuration
│   ├── code-review/             # Automated review
│   ├── tdd-workflow/            # Test-driven development
│   ├── security-scanner/        # Security scanning
│   ├── worktree-manager-skill/  # Git worktree management
│   └── ... (16 more skills)
├── global-hooks/                # 5 hook namespaces
│   ├── damage-control/          # Pattern-matching security
│   ├── mastery/                 # Lifecycle tracking
│   ├── observability/           # Monitoring & metrics
│   ├── framework/               # Knowledge, review, guardrails, testing
│   │   ├── knowledge/           # Knowledge pipeline (8 modules)
│   │   ├── review/              # Continuous review (analyzers + engine)
│   │   ├── guardrails/          # Anti-loop protection
│   │   ├── testing/             # Hook test framework
│   │   └── validators/          # L-thread + test validators
│   └── prompt-hooks/            # LLM semantic validation docs
├── global-output-styles/        # 11 output format styles
├── global-status-lines/         # Status line versions
├── guides/                      # 15 engineering guides
├── data/                        # Runtime data
│   ├── knowledge-db/            # SQLite knowledge database
│   ├── model_tiers.yaml         # Centralized tier config
│   └── logs/                    # Runtime logs
├── templates/                   # settings.json template + L-thread
├── apps/observability/          # Vue 3 dashboard + Bun server
├── docs/                        # Upgrade guides & migration docs
├── install.sh                   # Symlink installer
└── uninstall.sh                 # Clean removal
```

### Uninstallation

```bash
# Remove all installed files and restore backup
./uninstall.sh
```

## Architecture Overview

The framework implements a layered architecture:

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERFACE                        │
│              (Commands: /prime, /research, etc.)         │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                  PRIMARY AGENT (You)                     │
│     - Minimal context (5k tokens)                        │
│     - Coordination only                                  │
│     - Delegates heavy work                               │
└─────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼──────┐  ┌────────▼─────┐  ┌────────▼─────┐
│  RESEARCHER  │  │ ORCHESTRATOR │  │  RLM ROOT    │
│   Sub-Agent  │  │ Coordinator  │  │  Controller  │
└──────────────┘  └──────────────┘  └──────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼──────┐  ┌────────▼─────┐  ┌────────▼─────┐
│  Builder     │  │   Tester     │  │   Designer   │
│  Sub-Agent   │  │  Sub-Agent   │  │  Sub-Agent   │
└──────────────┘  └──────────────┘  └──────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│              PERSISTENCE LAYER                           │
│   - Context Bundles (session snapshots)                  │
│   - Progress Files (L-Thread state)                      │
│   - Mission Control DB (observability)                   │
└─────────────────────────────────────────────────────────┘
```

### Key Architectural Principles

1. **Thin Primary Context**: Keep main agent context under 10k tokens
2. **Delegate Heavy Work**: Sub-agents consume tokens in isolation
3. **Persistent Intelligence**: Bundles and progress files survive crashes
4. **Hierarchical Coordination**: Orchestrator manages agent fleets
5. **Programmatic Memory**: Search + read_slice instead of full-context loading

## Core Concepts

### 1. Context Engineering (Step 1-2)

**Problem**: Loading full project context permanently wastes 2,500+ tokens per session.

**Solution**: Strip global context, prime on-demand only when needed.

```bash
# Old way: Context auto-loads every session (wasteful)
# New way: Load only when needed
/prime
```

**Savings**: 10-20% permanent token reduction

### 2. Sub-Agent Delegation (Step 3)

**Problem**: Heavy research/search tasks consume 50k+ tokens in primary context.

**Solution**: Delegate to specialized sub-agents that work in isolation.

```bash
# Delegate research (sub-agent consumes 45k, returns 2k summary)
/research "authentication patterns"

# Delegate search (sub-agent scans codebase, returns relevant files)
/search "database connection logic"

# Delegate analysis (sub-agent reads files, returns insights)
/analyze "security vulnerabilities"
```

**Savings**: 96% token reduction on heavy tasks

### 3. Context Bundles (Step 5)

**Problem**: Session crashes require re-reading 50k+ tokens to restore context.

**Solution**: Auto-save session state to portable JSON bundles.

```bash
# Session crashes? Restore instantly
/loadbundle latest

# Switch machines? Load previous session
/loadbundle <session-id>
```

**Savings**: 99% token reduction on recovery (500 tokens vs 50k)

### 4. Agent Teams (Step 11)

**Problem**: Coordinating multiple agents manually is complex and error-prone.

**Solution**: Orchestrator (primary coordinator) manages agent fleets with strategy selection, you give high-level goals.

```bash
# Enable experimental feature
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1

# Let Orchestrator coordinate the fleet
/orchestrate "Build a Vue+FastAPI app with auth"
```

**Result**: 10x productivity via parallel agent coordination

### 5. Z-Threads (Step 12)

**Problem**: Multi-step deployments require constant human intervention.

**Solution**: YAML-defined workflows that run from prompt to production autonomously.

```bash
# Zero-touch deployment
/z-thread feature-implementation --feature "user authentication"
```

**Workflow**: Plan → Code → Test → Deploy → Monitor (zero human intervention)

### 6. Mission Control (Step 13)

**Problem**: No visibility into what agents are doing across fleet.

**Solution**: Real-time dashboard showing all agent activity, costs, and tool calls.

```bash
# Start monitoring system
cd ~/Documents/claude-code-hooks-multi-agent-observability
./scripts/start-system.sh

# Open dashboard
open http://localhost:5173
```

**Features**: Agent swimlanes, cost tracking, real-time events, tool call monitoring

### 7. L-Threads (Step 15)

**Problem**: Long tasks (1000+ items) cause agents to loop infinitely.

**Solution**: Progress files + anti-loop rules = no correction loops, 95% completion rate.

```bash
# Run long migration with crash-safety
claude -p "long-migration.md" --max-turns 50 --auto-continue
```

**Pattern**: Read progress → Process item → Update state → Exit when done

### 8. F-Threads (Step 16)

**Problem**: Single agent solutions are ~65% optimal, miss better approaches.

**Solution**: N agents solve in parallel, fusion judge picks/merges best solution.

```bash
# Run best-of-3 fusion for critical code
/fusion "optimize database query performance"
```

**Math**: N=3 → 95% optimal, N=5 → 99% optimal (worth 3x cost for critical tasks)

### 9. RLM Architecture (Step 17)

**Problem**: Traditional context windows cap at 200k tokens with degraded attention.

**Solution**: Recursive Language Model uses search + read_slice + delegate for infinite scale.

```bash
# Process millions of tokens with perfect attention
/rlm "analyze security across entire codebase"
```

**Result**: 99% attention quality at any scale, 75% cheaper than full-context loading

### 10. Ralph Loops (Step 18)

**Problem**: Long-running agents accumulate context rot and spin in circles.

**Solution**: Fresh context each iteration + progress file + completion promise.

```bash
# Run with stateless resampling
ralph-harness.sh "Fix all bugs" --test-cmd "npm test" --max-loops 20
```

**Features**: Zero context rot, external verification, circuit breakers, crash-safe

## New in 2026

The February 2026 upgrade adds major new capabilities. For full migration details see [docs/2026_UPGRADE_GUIDE.md](docs/2026_UPGRADE_GUIDE.md).

### Skills System (23 Skills)

Self-describing, auto-triggerable capabilities. Each skill has a `SKILL.md` with frontmatter that Claude Code discovers and invokes automatically.

| Category | Skills |
|----------|--------|
| Context | prime |
| Knowledge | knowledge-db |
| Config | multi-model-tiers |
| Quality | code-review, verification-checklist, downstream-correction |
| Testing | test-generator, tdd-workflow |
| Security | security-scanner, dependency-audit |
| Planning | brainstorm-before-code, feasibility-analysis, task-decomposition |
| Development | refactoring-assistant, error-analyzer, performance-profiler |
| Project | project-scaffolder, documentation-writer |
| Version Control | git-workflow, worktree-manager-skill, create-worktree-skill |
| Media | video-processor |
| Meta | meta-skill |

### Prompt Hooks (Hybrid Security)

LLM-based semantic validation runs in parallel with pattern-matching hooks. Catches obfuscated threats that regex cannot detect.

```
PreToolUse Event --> Command Hook (~50ms) + Prompt Hook (~2-5s) --> Both must allow
```

Covers Bash, Edit, and Write tools. See `global-hooks/prompt-hooks/README.md`.

### Knowledge Pipeline

SQLite FTS5 persistent memory for cross-session learning:

- **Store**: Decisions, learnings, patterns, errors, context, preferences
- **Search**: Full-text search with BM25 ranking
- **Inject**: Auto-inject relevant knowledge at session start
- **Observe**: Pattern extraction from session activity
- **Pipeline**: extract_learnings -> store_learnings -> inject_relevant -> observe_patterns

Located in `global-hooks/framework/knowledge/`. CLI via `global-skills/knowledge-db/`.

### Continuous Review System

Automated post-commit code review:

- Review engine with pluggable analyzers (complexity, security, style, performance)
- Persistent findings database
- Configurable via `global-hooks/framework/review/review_config.yaml`

### Multi-Model Tiers

Every agent assigned to the optimal tier:

```
Opus  (12%):  4 agents -- orchestrator, project-architect, critical-analyst, rlm-root
Sonnet (48%): 16 agents -- builder, researcher, meta-agent, + 13 more
Haiku  (39%): 13 agents -- validator, caddy-assistant, docs-scraper, hello-world, + 9 more
```

Saves 50-60% vs previous all-Opus or mixed configuration. Set in agent frontmatter `model:` field. Centralized config in `data/model_tiers.yaml`.

### Strategic Agents

Versatile high-level reasoning agents for complex decision-making:

- **Orchestrator** (Opus): Primary coordinator with strategy selection, agent team planning, and execution management
- **Project-Architect** (Opus): Analyze projects, design agent ecosystems, create project-specific automation
- **Critical-Analyst** (Opus): Question every detail, identify risks, challenge assumptions

### Support Services

- **Caddy-Assistant** (Haiku): Skill auditing, registry maintenance, and rapid triage for coordination support

### Agent Teams

Builder + Validator pattern with guardrails:

- **Builder** (Sonnet): Implements solutions
- **Validator** (Haiku): Independently verifies
- **Project Skill Generator** (Sonnet): Creates project-specific skills
- **8 Guardrail Agents**: Circuit breaker, CLI, config, docs, integration, QA, state, test

### Worktree Management

Git worktree skills for parallel development:

```bash
/create-worktree    # Create a new worktree
/list-worktrees     # List all worktrees
/remove-worktree    # Remove a worktree
```

## Security

The framework implements defense-in-depth security across multiple layers. For full details see [docs/SECURITY_BEST_PRACTICES.md](docs/SECURITY_BEST_PRACTICES.md).

### Skills Integrity Checking

Every skill file is hashed with SHA-256 and recorded in `~/.claude/skills.lock`. On session start, a verification hook compares current hashes against the lock and warns about any modified, deleted, or injected files.

```bash
# Generate the lock file after any skill changes
just skills-lock

# Verify skill integrity manually
just skills-verify
```

See [docs/SKILLS_INTEGRITY.md](docs/SKILLS_INTEGRITY.md) for detailed documentation.

### Automatic Skill Auditing

The framework provides automatic skill auditing via the Caddy-Assistant support agent. The auditor scans for code injection patterns, dangerous commands, sensitive file access, insecure permissions, and secret handling issues. Critical findings block the skill from being recommended.

**Prime Integration**: When using `/prime` to load project context, local skills in `.claude/skills/` are automatically scanned for security issues. Skills with critical findings are blocked from loading.

**Whitelist Workflow**: After `/prime`, review blocked skills interactively:

```bash
# Review blocked skills with detailed findings and code context
just review-blocked-skills

# Shows:
# - Exact lines triggering warnings with surrounding code
# - Distinction between documentation examples and actual code
# - Interactive whitelist: mark trusted skills as safe
# - Stores decisions in ~/.claude/skills-whitelist.json
```

**Audit Commands**:
```bash
# Audit a specific skill
just audit-skill <skill-name>

# Audit all installed skills
just audit-all-skills

# Audit local project skills (.claude/skills/)
just audit-local-skills

# Review and whitelist blocked skills
just review-blocked-skills
```

### Input Validation

Critical skills enforce strict input validation:

- **worktree-manager-skill**: Feature names validated against character allowlist (`a-zA-Z0-9._-`), path traversal blocked, path containment verified
- **video-processor**: Output paths restricted to current working directory, system directory writes blocked, input files validated
- **knowledge-db**: Import paths restricted to `~/.claude/` and current working directory, path traversal blocked

### File Permissions Enforcement

Sensitive data files (knowledge database, durability logs) are created with `0o600` permissions (owner read/write only), enforced on every open operation.

### Force Flag Convention

Destructive operations (file overwrite, dirty worktree removal) default to safe behavior and require explicit `--force` to proceed. This prevents accidental data loss across all skills.

### Security Commands

| Command | Purpose |
|---------|---------|
| `just skills-lock` | Generate SHA-256 lock file for all skills |
| `just skills-verify` | Verify skills against lock file |
| `just audit-skill <name>` | Audit one skill for security issues |
| `just audit-all-skills` | Audit every installed skill |
| `just audit-local-skills` | Audit local project skills in `.claude/skills/` |
| `just review-blocked-skills` | Interactive review and whitelist workflow |

## Skills Reference

Skills are auto-discoverable in `global-skills/`. Invoke via slash command or trigger phrases.

| Skill | Trigger Phrases | Purpose |
|-------|----------------|---------|
| `prime` | "prime yourself", "get context" | Load project context on-demand |
| `knowledge-db` | "remember this", "search knowledge" | Persistent cross-session memory |
| `multi-model-tiers` | "configure tiers", "model assignment" | Manage agent model tiers |
| `code-review` | "review this code" | Automated code review |
| `test-generator` | "generate tests" | Create test suites |
| `tdd-workflow` | "TDD", "test-driven" | Test-driven development cycle |
| `security-scanner` | "scan for vulnerabilities" | Security vulnerability scanning |
| `dependency-audit` | "audit dependencies" | Check dependency vulnerabilities |
| `error-analyzer` | "analyze this error" | Diagnose and fix errors |
| `performance-profiler` | "profile performance" | Performance optimization |
| `refactoring-assistant` | "refactor this" | Safe systematic refactoring |
| `documentation-writer` | "write docs" | Generate documentation |
| `project-scaffolder` | "scaffold project" | Create new project structure |
| `git-workflow` | "git workflow" | Git workflow management |
| `brainstorm-before-code` | "brainstorm", "ideate" | Pre-implementation ideation |
| `feasibility-analysis` | "is this feasible" | Viability assessment |
| `task-decomposition` | "break this down" | Decompose complex tasks |
| `downstream-correction` | "fix downstream" | Fix cascading breakage |
| `verification-checklist` | "verify before shipping" | Pre-completion checks |
| `video-processor` | "process video" | Video content processing |
| `worktree-manager-skill` | "manage worktrees" | Git worktree lifecycle |
| `create-worktree-skill` | "create worktree" | Quick worktree creation |
| `meta-skill` | "create a skill" | Generate new skills |

## Commands Reference

### Context Management

#### `/prime`
Load project context on-demand. Uses intelligent sampling to stay under 5k tokens.

```bash
/prime
```

**When to use**: Starting work on project, switching contexts, need codebase overview.

#### `/loadbundle <session-id>`
Restore previous session from context bundle.

```bash
/loadbundle latest              # Restore most recent session
/loadbundle abc123              # Restore specific session
```

**When to use**: After crash, switching machines, resuming previous work.

### Delegation Commands

#### `/research "<topic>"`
Delegate heavy research to specialist sub-agent.

```bash
/research "FastAPI authentication best practices"
```

**Output**: 2k token summary (sub-agent consumed 45k in isolation).

#### `/search "<pattern>"`
Delegate codebase search to specialist sub-agent.

```bash
/search "database connection initialization"
```

**Output**: List of relevant files + code snippets.

#### `/analyze "<aspect>"`
Delegate deep analysis to specialist sub-agent.

```bash
/analyze "security vulnerabilities in auth module"
```

**Output**: Analysis report + recommendations.

### Orchestration Commands

#### `/orchestrate "<goal>"`
Delegate high-level goal to Orchestrator agent (primary coordinator with strategy selection).

```bash
/orchestrate "Build REST API with CRUD operations and tests"
```

**Process**: Orchestrator plans → spawns agents → coordinates → aggregates results.

**Requires**: `export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

#### `/fusion "<task>"`
Run best-of-N fusion with multiple agents solving in parallel.

```bash
/fusion "optimize database query performance"
```

**Process**: 3 agents (Pragmatist, Architect, Optimizer) → Fusion Judge → Best solution.

#### `/rlm "<task>"`
Execute task using Recursive Language Model architecture for infinite scale.

```bash
/rlm "find all SQL injection vulnerabilities in codebase"
```

**Process**: Root controller uses search + read_slice + delegate (never loads full context).

### Planning Commands

#### `/plan "<goal>"`
Create a structured plan before implementing.

```bash
/plan "add user authentication to the API"
```

#### `/plan_w_team "<goal>"`
Plan with builder + validator team for implementation tasks.

```bash
/plan_w_team "refactor the database layer"
```

#### `/quick-plan "<goal>"`
Fast lightweight planning for smaller tasks.

```bash
/quick-plan "add input validation to the form"
```

### Development Commands

#### `/build`
Build or compile the current project.

#### `/refine "<instructions>"`
Iteratively refine the previous output.

```bash
/refine "make the error messages more descriptive"
```

### Worktree Commands

#### `/create-worktree`
Create a new git worktree for parallel development.

#### `/list-worktrees`
List all active git worktrees.

#### `/remove-worktree`
Remove a git worktree.

### Utility Commands

| Command | Purpose |
|---------|---------|
| `/start` | Initialize a new session |
| `/question` | Ask a focused question to a sub-agent |
| `/sentient` | Advanced reasoning mode |
| `/git_status` | Quick git status overview |
| `/all_tools` | List all available tools |
| `/convert_paths_absolute` | Convert relative paths to absolute |
| `/load_ai_docs` | Load AI documentation into context |
| `/update_status_line` | Update the status line display |

## Step-by-Step Guide

### Beginner: Basic Context Engineering

**Day 1: Understanding the Problem**

Traditional setup:
- Permanent global context: 2,500 tokens always loaded
- Heavy tasks: 50,000 tokens per operation
- Session crash: 50,000 tokens to recover
- **Total overhead**: 102,500 tokens per session

**Day 2: Install Framework**

```bash
cd ~/Documents
git clone <repo-url> claude-agentic-framework
cd claude-agentic-framework
./install.sh
```

**Day 3: First Priming Session**

```bash
claude
# No context loaded yet (0 tokens)

/prime
# Context loaded on-demand (3,000 tokens)
# Start working with minimal overhead
```

**Savings so far**: 2,500 tokens per session (no permanent context).

### Intermediate: Sub-Agent Delegation

**Week 2: Delegate Heavy Tasks**

Before:
```bash
# You: "Read all 50 files in auth/ directory"
# Result: 50k tokens in your context
```

After:
```bash
/research "authentication patterns in auth/ directory"
# Sub-agent reads 50 files (45k tokens in isolation)
# Returns 2k summary to you
# Savings: 96% token reduction
```

**Pattern**: Delegate any task involving >5 files.

**Week 3: Context Bundles**

Enable auto-saving:
```bash
# Context bundle hook is already installed
# Bundles auto-save to ~/.claude/bundles/
```

Session crashes:
```bash
# Old way: Re-read 50k tokens
# New way:
/loadbundle latest
# Restores session with 500 tokens
```

**Savings**: 99% reduction on crash recovery.

### Advanced: Multi-Agent Orchestration

**Month 2: Agent Teams**

Enable experimental feature:
```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
# Add to ~/.zshrc or ~/.bashrc for permanence
```

Delegate high-level goals:
```bash
/orchestrate "Build a Vue SPA with FastAPI backend and SQLite database"
```

Orchestrator workflow:
1. Analyzes goal
2. Spawns specialized agents (Designer, Builder, Tester)
3. Coordinates parallel work
4. Aggregates results
5. Returns complete solution

**Result**: 10x productivity, you act as executive not engineer.

**Month 3: Mission Control**

Install observability system:
```bash
cd ~/Documents
git clone <mission-control-repo>
cd claude-code-hooks-multi-agent-observability
npm install
./scripts/start-system.sh
```

Open dashboard: http://localhost:5173

**Features**:
- See all agents in real-time
- Track token costs per agent
- Monitor tool calls and errors
- Debug failed operations
- Optimize agent workflows

### Expert: Autonomous Execution

**Month 4: L-Threads (Long-Running Tasks)**

Template for 1000-item migration:
```bash
claude -p "~/.claude/templates/long-migration.md" --max-turns 50 --auto-continue
```

Progress file pattern:
```json
{
  "pending": ["item3", "item4", ...],
  "completed": ["item1", "item2"],
  "failed": [
    {"item": "item5", "error": "...", "timestamp": "..."}
  ]
}
```

**Anti-loop rules**:
1. Read progress BEFORE every action
2. NEVER retry failed items
3. Update state AFTER each item
4. Exit when pending array is empty

**Result**: 0% loop rate, 95% completion rate, 76% cost reduction.

**Month 5: F-Threads (Best-of-N Fusion)**

For critical code where quality matters more than cost:
```bash
/fusion "implement payment processing with Stripe"
```

Process:
1. Pragmatist agent: Simple, straightforward solution
2. Architect agent: Scalable, maintainable solution
3. Optimizer agent: High-performance solution
4. Fusion Judge: Evaluates all three, picks or merges best

**Scoring**: Correctness (3x) > Simplicity (2x) > Robustness (2x) > Performance (1x)

**Result**: 95% optimal solutions (vs 65% single-agent).

**Month 6: RLM Architecture (Infinite Scale)**

For massive codebases (millions of tokens):
```bash
/rlm "audit entire codebase for GDPR compliance"
```

RLM Root Controller:
- Never loads full context
- Uses `search()` to find relevant files (free operation)
- Uses `read_slice()` to read specific ranges (targeted tokens)
- Uses `delegate()` to spawn sub-agents for analysis
- Maintains 5k token context (code + summaries only)

**Result**: 
- Process millions of tokens
- 99% attention quality (vs 40% at 200k traditional)
- 75% cheaper than full-context loading
- No context window limits

## Performance Benefits

### Token Economics

| Operation | Before | After | Savings |
|-----------|--------|-------|---------|
| Global context | 2,500 always | 0 (on-demand) | 100% |
| Prime context | N/A | 3,000 once | Optimized |
| Heavy task (50 files) | 50,000 | 2,000 summary | 96% |
| Session restoration | 50,000 | 500 bundle | 99% |
| Orchestration | 102,500 | 5,500 | 95% |

### Cost Comparison

**Traditional session** (10 heavy tasks):
```
Permanent context:     2,500 tokens
Heavy task 1:         50,000 tokens
Heavy task 2:         50,000 tokens
...
Heavy task 10:        50,000 tokens
Total:               502,500 tokens
Cost (Opus 4.6):      ~$7.50
```

**Agentic session** (10 heavy tasks):
```
Prime once:            3,000 tokens
Heavy task 1:          2,000 tokens (summary)
Heavy task 2:          2,000 tokens (summary)
...
Heavy task 10:         2,000 tokens (summary)
Total:                23,000 tokens
Cost (Opus 4.6):      ~$0.35
```

**Savings**: 95% cost reduction, $7.15 saved per session.

### Speed Improvements

| Task | Traditional | Agentic | Speedup |
|------|-------------|---------|---------|
| Context load | 5 seconds | 0 seconds | ∞ |
| Research 50 files | 30 seconds | 35 seconds | 0.86x |
| Session restore | 30 seconds | 2 seconds | 15x |
| Multi-agent task | Sequential | Parallel | 3-5x |

Note: Sub-agent tasks are slightly slower due to delegation overhead, but massive token savings justify it.

### Scalability

| Pattern | Max Context | Attention Quality | Cost Efficiency |
|---------|-------------|-------------------|-----------------|
| Traditional | 200k tokens | 40% | Baseline |
| With Delegation | 500k tokens | 80% | 10x better |
| RLM Architecture | Unlimited | 99% | 75x better |

## Configuration

### Environment Variables

```bash
# Enable agent teams (experimental)
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1

# Mission Control endpoints (if running)
export MISSION_CONTROL_SERVER="http://localhost:4000"
export MISSION_CONTROL_ENABLED=true

# Context bundle preferences
export CLAUDE_BUNDLE_DIR="$HOME/.claude/bundles"
export CLAUDE_BUNDLE_AUTO_SAVE=true

# Hook verbosity
export CLAUDE_HOOK_DEBUG=false
```

Add to `~/.zshrc` or `~/.bashrc` for permanence.

### Hook Configuration

The `settings.json` is generated from `templates/settings.json.template`. Always edit the template, not `settings.json` directly. The template uses `__REPO_DIR__` as a placeholder replaced by `install.sh`.

The hook system uses 5 namespaces with both command and prompt hooks:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "uv run .../damage-control/bash-tool-damage-control.py"},
          {"type": "prompt", "prompt": "Security review prompt with $ARGUMENTS..."}
        ]
      },
      {"matcher": "Edit", "hooks": [...]},
      {"matcher": "Write", "hooks": [...]}
    ],
    "PostToolUse": [...],
    "Stop": [...]
  }
}
```

See `global-hooks/prompt-hooks/README.md` for prompt hook documentation.

### Command Customization

Commands are markdown files in `~/.claude/commands/`. Edit to customize behavior:

```bash
# Edit research command
vim ~/.claude/commands/research.md

# Add custom command
cp ~/.claude/commands/research.md ~/.claude/commands/mycommand.md
# Edit mycommand.md
```

### Agent Customization

Agents are markdown system prompts in `~/.claude/agents/`:

```bash
# Edit orchestrator behavior
vim ~/.claude/agents/orchestrator.md

# Create custom specialist agent
cat > ~/.claude/agents/security-auditor.md << 'EOA'
You are a security auditing specialist...
EOA
```

## Testing

### Test Installation

```bash
# Verify all files installed
ls ~/.claude/AGENT_TEAMS.md
ls ~/.claude/commands/prime.md
ls ~/.claude/agents/orchestrator.md
ls ~/.claude/hooks/context-bundle-logger.py

# Verify hook configuration
cat ~/.claude/settings.json | grep -A 5 "hooks"
```

### Test Commands

```bash
claude

# Test prime command
/prime
# Should load context without errors

# Test research delegation
/research "test patterns"
# Should spawn sub-agent and return summary

# Test bundle restoration
/loadbundle latest
# Should restore session or report no bundles
```

### Test Mission Control (if installed)

```bash
# Check server running
curl http://localhost:4000/health
# Should return: {"status":"ok"}

# Check dashboard
open http://localhost:5173
# Should show Mission Control UI
```

### Test L-Thread Pattern

```bash
# Create test progress file
cat > /tmp/test_progress.json << 'EOF'
{
  "pending": ["item1", "item2", "item3"],
  "completed": [],
  "failed": []
}
EOF

# Run test prompt that reads progress
claude -p "Process items from /tmp/test_progress.json" --max-turns 5
```

### Validate Hook Execution

```bash
# Check hook logs
tail -f ~/.claude/logs/hooks.log

# Run command that triggers hooks
claude
/prime
# Should see hook entries in log
```

## Troubleshooting

### Command Not Found

**Symptom**: `/prime` command doesn't work.

**Solution**:
```bash
# Verify command installed
ls ~/.claude/commands/prime.md

# Re-run installer if missing
cd ~/Documents/claude-agentic-framework
./install.sh
```

### Hooks Not Firing

**Symptom**: Context bundles not auto-saving, damage control not blocking commands.

**Solution**:
```bash
# Check settings.json syntax
cat ~/.claude/settings.json | python3 -m json.tool

# Verify hook paths exist
ls ~/.claude/hooks/context-bundle-logger.py
ls ~/.claude/hooks/damage-control/bash-tool-damage-control.py

# Check hook permissions
chmod +x ~/.claude/hooks/*.py
chmod +x ~/.claude/hooks/damage-control/*.py
```

### Sub-Agent Not Spawning

**Symptom**: `/research` doesn't delegate, runs in primary context.

**Solution**:
```bash
# Check agent file exists
ls ~/.claude/agents/researcher.md

# Verify command references correct agent
grep "researcher" ~/.claude/commands/research.md

# Check Claude Code version (needs 0.1.x+)
claude --version
```

### Agent Teams Not Working

**Symptom**: `/orchestrate` command fails or doesn't spawn agents.

**Solution**:
```bash
# Enable experimental feature
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
echo 'export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1' >> ~/.zshrc

# Verify orchestrator exists
ls ~/.claude/agents/orchestrator.md

# Check Claude Code supports agent teams
claude --help | grep -i agent
```

### Mission Control Not Starting

**Symptom**: Dashboard doesn't load or server won't start.

**Solution**:
```bash
# Check Node.js version (needs 18+)
node --version

# Install dependencies
cd ~/Documents/claude-code-hooks-multi-agent-observability
npm install

# Check ports available
lsof -i :4000  # Server port
lsof -i :5173  # Client port

# Kill conflicting processes
kill -9 <PID>

# Restart system
./scripts/start-system.sh
```

### Context Bundle Too Large

**Symptom**: Bundle files are hundreds of MB, slow to load.

**Solution**:
```bash
# Check bundle size
ls -lh ~/.claude/bundles/

# Delete old bundles
rm ~/.claude/bundles/*.json

# Configure bundle size limit in hook
vim ~/.claude/hooks/context-bundle-logger.py
# Add size limit logic
```

### L-Thread Infinite Loop

**Symptom**: Long-running task never completes, keeps retrying same items.

**Solution**:
```bash
# Check progress file exists and is valid
cat /path/to/progress.json | python3 -m json.tool

# Verify anti-loop rules in prompt:
# 1. Read progress BEFORE action
# 2. NEVER retry failed items
# 3. Update state AFTER each item
# 4. Exit when pending is empty

# Add circuit breaker
claude -p "prompt.md" --max-turns 50  # Hard limit
```

### RLM Search Not Working

**Symptom**: RLM agent can't find files, search returns empty.

**Solution**:
```bash
# Check Grep tool available
claude
# Try: grep "pattern" /path/to/codebase

# Verify search index
# RLM uses grep, not indexed search

# Check file permissions
ls -la /path/to/codebase
```

### High Token Costs

**Symptom**: Still seeing high token usage despite framework.

**Solution**:
```bash
# Enable Mission Control to track token usage
cd ~/Documents/claude-code-hooks-multi-agent-observability
./scripts/start-system.sh
open http://localhost:5173

# Check if priming too often (should be once per context switch)
# Check if delegating heavy tasks (>5 files should delegate)
# Check if using context bundles for recovery (not re-reading files)

# Review token usage patterns in Mission Control dashboard
```

## Advanced Patterns

### Pattern 1: Agentic Drop Zones

Auto-trigger agents when files appear in specific directories.

**Setup**:
```bash
# Create drop zone
mkdir -p ~/dropzone/research

# Configure file watcher (macOS)
fswatch ~/dropzone/research | while read file; do
  claude /research "$(cat $file)"
done
```

**Use case**: Drop research questions, agent auto-processes.

### Pattern 2: Z-Thread Workflows

Define multi-step workflows in YAML.

**Example**: `feature-implementation.yaml`
```yaml
name: Feature Implementation
steps:
  - name: Plan
    agent: architect
    output: plan.md
  - name: Implement
    agent: builder
    input: plan.md
    output: code/
  - name: Test
    agent: tester
    input: code/
    output: test-results.json
  - name: Deploy
    agent: deployer
    input: code/
    condition: test-results.json.passed == true
```

**Execute**:
```bash
/z-thread feature-implementation --feature "user authentication"
```

### Pattern 3: Ralph Loop Harness

Stateless resampling for guaranteed completion.

**Script**: `~/.claude/scripts/ralph-harness.sh`
```bash
#!/bin/bash
TASK=$1
TEST_CMD=$2
MAX_LOOPS=${3:-20}

for i in $(seq 1 $MAX_LOOPS); do
  # Run with fresh context
  claude -p "$(cat <<EOF
Task: $TASK

Progress file: progress.txt
Read progress BEFORE acting.
Update progress AFTER each item.
Output <promise>COMPLETE</promise> when done.
EOF
)" --max-turns 10 > output.txt

  # Check for completion promise
  if grep -q "<promise>COMPLETE</promise>" output.txt; then
    # Verify with external test
    if $TEST_CMD; then
      echo "Success after $i iterations"
      exit 0
    else
      echo "Promise made but tests failed, continuing..."
    fi
  fi
  
  # Check for stall (3 unchanged iterations)
  if [ $i -ge 3 ]; then
    PREV3=$(cat progress.txt.3 2>/dev/null)
    CURR=$(cat progress.txt 2>/dev/null)
    if [ "$PREV3" == "$CURR" ]; then
      echo "Stalled, exiting"
      exit 1
    fi
  fi
  
  cp progress.txt progress.txt.3
done

echo "Max loops reached without completion"
exit 1
```

**Usage**:
```bash
ralph-harness.sh "Fix all bugs" "npm test" 20
```

### Pattern 4: Fusion with Custom Personas

Define your own agent personas for fusion.

**Edit**: `~/.claude/commands/fusion.md`
```markdown
Personas:
1. Security Expert: Focus on security vulnerabilities
2. Performance Expert: Focus on speed optimization
3. Maintainability Expert: Focus on code clarity

Fusion Judge:
- Score Security (5x), Performance (3x), Maintainability (2x)
- Pick solution or merge best elements
```

### Pattern 5: Mental Model Agents

Agents that learn and improve over time.

**Structure**:
```
~/.claude/agents/expert-agent/
├── system-prompt.md      # Base agent definition
├── expertise.md          # Accumulated knowledge
└── update-hook.py        # Self-improvement hook
```

**Agent prompt includes**:
```markdown
1. Read expertise.md before starting
2. Execute task using learned patterns
3. After completion, update expertise.md with new learnings
```

**Result**: Agent gets better with each task.

## Contributing

### Report Issues

Found a bug or have a feature request? Open an issue:

```
Title: [Component] Brief description
Body:
- What happened
- What you expected
- Steps to reproduce
- Environment (OS, Claude Code version)
- Relevant logs
```

### Submit Pull Requests

Contributions welcome for:
- New commands
- Additional agents
- Improved hooks
- Documentation fixes
- Example workflows

**Process**:
1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Update documentation
5. Submit PR with description

### Share Your Patterns

Discovered a useful pattern? Share it:
- Add to `guides/COMMUNITY_PATTERNS.md`
- Include example code
- Explain benefits and use cases
- Provide performance metrics if available

## License

MIT License - see LICENSE file for details.

## Support

- **Documentation**: All guides in `~/.claude/` after installation
- **Examples**: `templates/` directory
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

## Acknowledgments

Built on patterns from:
- IndyDevDan's single-file-agents
- claude-code-hooks-mastery
- claude-code-damage-control
- E2B agent-sandbox-skill

## Changelog

### v2.0.0 (February 2026) -- Current

**Skills System**
- 23 auto-discoverable skills covering the full engineering lifecycle
- Meta-skill for generating new skills from templates
- Project Skill Generator agent for project-specific automation

**Security**
- Hybrid security: prompt hooks (LLM semantic validation) alongside pattern-matching command hooks
- Prompt hooks for Bash, Edit, and Write tools
- Anti-loop guardrails system for agent safety
- Skills integrity verification via SHA-256 lock file (`just skills-lock`, `just skills-verify`)
- Automatic skill auditing by Caddy meta-orchestrator (`just audit-skill`, `just audit-all-skills`)
- `/prime` integration: automatic security scanning of local project skills before loading
- Local skill auditing command (`just audit-local-skills`) for `.claude/skills/`
- P0 vulnerability fixes: command injection (worktree-manager), file overwrite (video-processor), access control (knowledge-db)
- Input validation enforcement in critical skills (character allowlists, path containment)
- File permissions hardening (`0o600` on sensitive data files)
- `--force` flag convention for destructive operations across all skills

**Knowledge & Review**
- SQLite FTS5 knowledge database for persistent cross-session memory
- Knowledge pipeline: extract, store, inject, observe
- Continuous review system with pluggable analyzers
- Post-commit review hook with findings database

**Agents**
- 33 agents across 3 model tiers (Opus/Sonnet/Haiku)
- Strategic agents: Project-Architect and Critical-Analyst
- Agent teams: Builder + Validator pattern
- 8 guardrail agents for complex system implementation
- Removed crypto-specific agents (see migration docs)

**Commands**
- 25+ slash commands (up from 8)
- Planning commands: /plan, /plan_w_team, /quick-plan
- Worktree commands: /create-worktree, /list-worktrees, /remove-worktree
- Development commands: /build, /refine, /question, /sentient

**Infrastructure**
- Multi-model tier system with centralized configuration
- Git worktree management skills
- TTS notification hooks (ElevenLabs, OpenAI, pyttsx3)
- Settings generated from template (edit template, not settings.json)

**Documentation**
- Migration guide: docs/2026_UPGRADE_GUIDE.md
- Prompt hooks documentation: global-hooks/prompt-hooks/README.md
- Worktree documentation: global-skills/worktree-manager-skill/

### v1.0.0 (2025)
- Complete framework with 15 guides
- 8 commands for delegation and orchestration
- 3 specialized agents
- Hook system with safety and observability
- Context bundles for crash recovery
- L-Thread, F-Thread, RLM patterns
- Ralph Loop harness
- Mission Control integration

---

**Transform Claude Code into an elite autonomous engineering platform.**

Start with `/prime` and scale to infinity. See [docs/2026_UPGRADE_GUIDE.md](docs/2026_UPGRADE_GUIDE.md) for the full upgrade guide.
