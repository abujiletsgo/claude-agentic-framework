# Archive

This directory contains rarely-used commands and skills that were moved out of the main workflow to reduce clutter.

## Why Archived?

These items are functional but not essential for daily workflow:
- **Manual-trigger only**: Require explicit invocation, rarely auto-triggered
- **One-time use**: Configuration or setup tasks done once
- **Niche use cases**: Specialized workflows not commonly needed
- **Redundant**: Functionality available through other means

## Restoring Archived Items

If you need an archived item:

```bash
# Restore a command
mv archive/commands/item.md global-commands/

# Restore a skill
mv archive/skills/skill-name global-skills/

# Re-run installer to update symlinks
bash install.sh
```

## Archived Commands (6)

| Command | Reason | Restore If... |
|---------|--------|---------------|
| `/question` | Can just ask directly | You want explicit question delegation |
| `/build` | Usually done via terminal | You want Claude to build for you |
| `/load_ai_docs` | One-time documentation loading | You need to refresh docs |
| `/create-worktree` | Git worktree management | You use git worktrees heavily |
| `/list-worktrees` | Git worktree management | You use git worktrees heavily |
| `/remove-worktree` | Git worktree management | You use git worktrees heavily |

## Archived Skills (11)

| Skill | Reason | Restore If... |
|-------|--------|---------------|
| `brainstorm-before-code` | Manual trigger, pre-implementation ideation | You want structured brainstorming |
| `feasibility-analysis` | Manual trigger, viability assessment | You need feasibility scoring |
| `task-decomposition` | Manual trigger, task breakdown | You want automatic task breakdown |
| `documentation-writer` | Manual trigger, doc generation | You want auto-generated docs |
| `dependency-audit` | Manual trigger, security scanning | You need dependency vulnerability checks |
| `performance-profiler` | Manual trigger, performance analysis | You need profiling and optimization |
| `git-workflow` | Already know git, redundant | You want git workflow guidance |
| `downstream-correction` | Niche use case, cascading fixes | You have complex dependency chains |
| `verification-checklist` | Manual trigger, pre-completion checks | You want automated verification |
| `multi-model-tiers` | One-time config, model tier setup | You need to reconfigure model tiers |
| `meta-skill` | Niche use case, skill generation | You want to create new skills |

## Archive Policy

**Archived items**:
- ✅ Still maintained and functional
- ✅ Available for restoration anytime
- ✅ Documented with restore instructions
- ❌ Not symlinked to `~/.claude/`
- ❌ Not shown in slash command autocomplete

## Current Active Setup

**Commands (8)**: prime, research, plan, orchestrate, fusion, rlm, loadbundle, refine

**Skills (6)**: code-review, error-analyzer, knowledge-db, refactoring-assistant, security-scanner, test-generator

**Reduction**: 39 items → 14 items (64% fewer options)
