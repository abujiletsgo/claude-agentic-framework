# Quick Start Guide

Get the Claude Agentic Framework running in under 5 minutes.

## Prerequisites

- **Claude Code CLI** (0.1.x+) -- [Install guide](https://docs.anthropic.com/en/docs/claude-code)
- **Python 3.10+** and **uv** -- `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Git**

## Install (30 seconds)

```bash
git clone https://github.com/yourusername/claude-agentic-framework.git
cd claude-agentic-framework
./install.sh
```

The installer will:
1. Validate all hook files exist
2. Generate `~/.claude/settings.json` from the template
3. Symlink commands, skills, and agents to `~/.claude/`
4. Regenerate README.md and CLAUDE.md from live repo counts
5. Verify dependencies

## First Session

Start a new Claude Code session (the framework loads on startup):

```bash
# Load project context (cached after first run)
/prime

# Get a quick orientation
/help
```

## Core Workflow

### Research something
```
/research "How does the authentication module work?"
```
Spawns a sub-agent to research in isolation. Your main context stays clean.

### Build with orchestration
```
/orchestrate "Add password reset functionality"
```
Coordinates multiple agents (researcher, builder, validator) automatically.

### Review your changes
```
/review
```
Runs complexity, security, duplication, and dead-code analyzers on changed files.

### Fix review findings
```
/refine
```
Auto-fixes issues found by `/review`.

### Commit
```
/commit
```
Generates a conventional commit message and stages relevant files.

### Run tests
```
/test
```
Detects your test framework and runs the suite.

### Debug errors
```
/debug
```
Analyzes the last error, traces root cause, proposes a fix.

### Check costs
```
/costs
```
Shows API usage by model tier with budget tracking.

## Command Reference

| Command | Purpose |
|---------|---------|
| `/prime` | Load project context (cached) |
| `/help` | Show all commands and agents |
| `/research` | Delegate research to sub-agent |
| `/orchestrate` | Multi-agent coordination |
| `/rlm` | Recursive analysis for huge codebases |
| `/fusion` | Best-of-N for critical code |
| `/plan` | Structured execution planning |
| `/review` | Automated code review |
| `/refine` | Auto-fix review findings |
| `/commit` | Smart conventional commits |
| `/test` | Run or generate tests |
| `/debug` | Error diagnosis and fix |
| `/costs` | API usage and budget tracking |
| `/loadbundle` | Restore session context |

## Architecture at a Glance

```
You (Claude Code)
 |
 +-- /prime loads project context
 |
 +-- /research, /orchestrate, /rlm spawn sub-agents
 |     |
 |     +-- Opus tier:   orchestrator, architect, analyst, rlm-root
 |     +-- Sonnet tier: researcher, meta-agent, scout
 |     +-- Haiku tier:  docs-scraper, validators
 |
 +-- Hooks run automatically:
 |     +-- PreToolUse:   damage control (security)
 |     +-- PostToolUse:  context bundle logging
 |     +-- Stop:         progress validation
 |     +-- SessionStart: skills integrity + doc freshness
 |
 +-- Skills auto-trigger on intent:
       +-- code-review, test-generator, security-scanner
       +-- error-analyzer, refactoring-assistant, knowledge-db
```

## Configuration

- **Settings**: Edit `templates/settings.json.template`, then run `./install.sh`
- **Model tiers**: Edit `data/model_tiers.yaml` to reassign agents to Opus/Sonnet/Haiku
- **Budgets**: Edit `data/budget_config.yaml` for cost limits

## Troubleshooting

**Commands not showing up?**
Run `./install.sh` and start a new Claude Code session.

**Hook errors on startup?**
Check that all Python files referenced in `templates/settings.json.template` exist.
Run `./install.sh` to validate.

**README.md shows wrong counts?**
Run `uv run scripts/generate_docs.py` to regenerate from live repo state.

**Want to add a new agent/command/skill?**
Add the file, run `./install.sh`, and the auto-doc system updates everything.

---

*For the full guide, see [guides/](guides/) and [docs/](docs/).*
