#!/usr/bin/env python3
"""
Auto-documentation generator for Claude Agentic Framework.

Scans the repository and generates accurate README.md and CLAUDE.md
from real file counts. Never lies about numbers again.

Usage:
    uv run scripts/generate_docs.py [--check]

Flags:
    --check   Dry-run mode: exits non-zero if docs are stale (for CI/hooks)
"""

import json
import os
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent


def count_root_agents():
    d = REPO_DIR / "global-agents"
    return sorted(p.stem for p in d.glob("*.md") if p.is_file())


def count_team_agents():
    d = REPO_DIR / "global-agents" / "team"
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.md") if p.is_file())


def count_commands():
    d = REPO_DIR / "global-commands"
    return sorted(p.stem for p in d.glob("*.md") if p.is_file())


def count_skills():
    d = REPO_DIR / "global-skills"
    return sorted(p.name for p in d.iterdir() if p.is_dir() and not p.name.startswith("."))


def count_guides():
    d = REPO_DIR / "guides"
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.md") if p.is_file())


def count_docs():
    d = REPO_DIR / "docs"
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.md") if p.is_file())


def count_hooks():
    t = REPO_DIR / "templates" / "settings.json.template"
    content = t.read_text().replace("__REPO_DIR__", str(REPO_DIR))
    data = json.loads(content)
    hooks = data.get("hooks", {})
    result = {}
    total = 0
    for event_type, matchers in hooks.items():
        count = sum(len(m.get("hooks", [])) for m in matchers)
        result[event_type] = count
        total += count
    result["total"] = total
    return result


def get_model_tiers():
    p = REPO_DIR / "data" / "model_tiers.yaml"
    if not p.exists():
        return {"opus": [], "sonnet": [], "haiku": []}
    content = p.read_text()
    result = {"opus": [], "sonnet": [], "haiku": []}
    current = None
    in_tiers = False
    for line in content.split("\n"):
        s = line.strip()
        if s == "agent_tiers:":
            in_tiers = True
            continue
        if in_tiers:
            if s in ("opus:", "sonnet:", "haiku:"):
                current = s.rstrip(":")
                continue
            if s.startswith("- ") and current:
                name = s[2:].split("#")[0].strip()
                result[current].append(name)
            elif s and not s.startswith("#") and not s.startswith("-"):
                in_tiers = False
                current = None
    return result


def generate_readme(d):
    tier_lines = []
    for tier in ["opus", "sonnet", "haiku"]:
        agents = d.get(f"{tier}_agents", [])
        if agents:
            names = ", ".join(agents)
            tier_lines.append(f"  {tier.title():>6} ({len(agents)}): {names}")
    tier_block = "\n".join(tier_lines) if tier_lines else "  (none configured)"

    cmd_block = "\n".join(f"  - /{c}" for c in d.get("command_list", []))
    skill_block = "\n".join(f"  - {s}" for s in d.get("skill_list", []))

    return f'''# Claude Agentic Framework

> One repo, one install, one source of truth. Multi-agent orchestration platform for Claude Code.

## What You Get

- **{d['AGENT_COUNT']} Agents** across 3 model tiers (Opus/Sonnet/Haiku)
- **{d['COMMAND_COUNT']} Commands** for delegation, orchestration, and planning
- **{d['SKILL_COUNT']} Skills** for the full engineering lifecycle
- **{d['GUIDE_COUNT']} Guides** covering context engineering to multi-agent patterns
- **{d['HOOK_COUNT']} Hooks** across {d['HOOK_EVENT_COUNT']} event types (damage-control, observability, framework)
- **Knowledge Pipeline**: SQLite FTS5 persistent memory for cross-session learning
- **Multi-Model Tiers**: Right model for the right task (50-60% cost savings)

## Quick Start

```bash
git clone https://github.com/yourusername/claude-agentic-framework.git
cd claude-agentic-framework
./install.sh
```

Then in Claude Code:

```bash
/prime              # Load project context (cached after first run)
/research "topic"   # Delegate research to sub-agent
/orchestrate "goal" # Multi-agent coordination
```

## Architecture

```
global-agents/       {d['AGENT_COUNT']} agents ({d['ROOT_AGENT_COUNT']} root + {d['TEAM_AGENT_COUNT']} team)
global-commands/     {d['COMMAND_COUNT']} commands
global-skills/       {d['SKILL_COUNT']} skills
global-hooks/        {d['HOOK_COUNT']} hooks across {d['HOOK_EVENT_COUNT']} events
guides/              {d['GUIDE_COUNT']} engineering guides
docs/                {d['DOC_COUNT']} reference docs
data/                model_tiers.yaml + knowledge-db/
templates/           settings.json.template
apps/observability/  Vue 3 + Bun (ports 4000/5173)
archive/             Archived commands, skills, hooks
```

## Model Tiers

```
{tier_block}
```

Config: `data/model_tiers.yaml`

## Commands

```
{cmd_block}
```

## Skills

```
{skill_block}
```

## Hooks

| Event | Count | Purpose |
|-------|-------|---------|
| PreToolUse | {d.get('hooks_PreToolUse', 0)} | Damage control, security validation |
| PostToolUse | {d.get('hooks_PostToolUse', 0)} | Context bundle logging |
| Stop | {d.get('hooks_Stop', 0)} | L-thread progress validation |
| SessionStart | {d.get('hooks_SessionStart', 0)} | Skills integrity verification |

## Key Concepts

1. **Context Engineering** -- Strip permanent context, load on-demand with `/prime`
2. **Sub-Agent Delegation** -- Heavy tasks run in isolation via `/research`
3. **Multi-Agent Orchestration** -- `/orchestrate` coordinates agent fleets
4. **RLM Architecture** -- `/rlm` for infinite-scale codebase analysis
5. **F-Threads (Fusion)** -- `/fusion` for best-of-N critical code
6. **Knowledge Pipeline** -- Persistent cross-session memory via SQLite FTS5
7. **Anti-Loop Guardrails** -- Circuit breakers prevent infinite agent loops

## Installation

### Prerequisites

- Claude Code CLI (0.1.x+)
- Python 3.10+ and `uv`
- Git

### Install

```bash
./install.sh
```

The installer:
1. Validates all hook files exist
2. Generates `settings.json` from template
3. Symlinks commands, skills, and agents to `~/.claude/`
4. Verifies dependencies (uv, python3, git)

### Uninstall

```bash
./uninstall.sh
```

## Configuration

- **settings.json**: Generated from `templates/settings.json.template` -- edit template, not settings.json directly
- **Model tiers**: `data/model_tiers.yaml` -- centralized agent-to-model mapping
- **Agent teams**: `export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

## Guides

See `guides/` for {d['GUIDE_COUNT']} comprehensive engineering guides and `docs/` for {d['DOC_COUNT']} reference documents.

## Contributing

1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Run `uv run scripts/generate_docs.py` to update docs
5. Submit PR

---

*This README is auto-generated by `scripts/generate_docs.py`. Do not edit manually.*
*Run `uv run scripts/generate_docs.py` after adding/removing agents, commands, or skills.*

<!-- AUTO-DOC-STAMP:{d['AGENT_COUNT']}a-{d['COMMAND_COUNT']}c-{d['SKILL_COUNT']}s-{d['HOOK_COUNT']}h -->
'''


def generate_claude_md(d):
    tier_lines = []
    for tier in ["opus", "sonnet", "haiku"]:
        agents = d.get(f"{tier}_agents", [])
        if agents:
            names = ", ".join(agents)
            tier_lines.append(f"{tier.title():>6} ({len(agents)}): {names}")
    tier_block = "\n".join(tier_lines) if tier_lines else "(none configured)"

    return f"""# Claude Agentic Framework

v2.1.0 | One repo, one install, one source of truth.

## Structure

```
global-hooks/        damage-control/ observability/ framework/
global-agents/       {d['AGENT_COUNT']} agents ({d['ROOT_AGENT_COUNT']} root + {d['TEAM_AGENT_COUNT']} team)
global-commands/     {d['COMMAND_COUNT']} commands
global-skills/       {d['SKILL_COUNT']} skills
global-status-lines/ mastery/v9 + observability/
apps/observability/  Vue 3 + Bun (ports 4000/5173)
data/                knowledge-db/ + model_tiers.yaml
templates/           settings.json.template
```

## Mode: Yolo

`"allow": ["*"]` + deny destructive ops + ask force-push/hard-reset. Security: permissions > command hooks (pattern match) > skills integrity (SHA-256) > input validation > file permissions (0o600).

## Model Tiers

```
{tier_block}
```

Config: `data/model_tiers.yaml`.

## Context Discipline (Adaptive)

Scale approach to task complexity. Direct for simple, delegate for complex.

**Direct** (1-2 files, <200 lines, known location):
- Read the file. Fix the thing. No ceremony.

**Delegated** (5+ files, 500+ lines, exploration needed, audits/scans):
- Search before read. Grep/Glob first, never open blind.
- Small slices. Max 50-100 lines at a time.
- Spawn sub-agents for analysis. Primary context coordinates only.
- Sub-agents return 2-3 sentence findings, not raw code.
- Parallel sub-agents in one message.

/rlm forces strict delegated mode. Otherwise, match approach to scope.

## Execution Protocol

1. **Task Lists** -- 3+ steps = TaskList. Parallelize. Mark in_progress/completed.
2. **Parallel** -- Launch independent subagents simultaneously. Never serialize parallelizable work.
3. **Orchestrator** -- /orchestrate for complex multi-agent tasks.
4. **Validate** -- Spawn validator subagent after implementation. Never complete without validation.
5. **Teams** -- Builder (Sonnet) implements + Validator (Haiku) verifies, in parallel.

## Compaction Preservation

When context compacts, preserve: task list state, modified file paths, test commands, validation results, key decisions.

## Key Rules

- `uv run` for all Python execution
- Edit template not settings.json directly -- run `bash install.sh` to apply
- Never delete hook files the live settings.json references -- stub them first, delete after reinstall
- Knowledge DB: `data/knowledge-db/` via knowledge-db skill
- Big outputs (>1000 tokens) -- save to `/tmp/claude/` and reference, don't flood context
- `/prime` caching: First prime = full analysis + cache save. Subsequent = instant load. Auto-invalidates on git changes. Cache: `.claude/PROJECT_CONTEXT.md`
"""


def main():
    check_mode = "--check" in sys.argv

    root_agents = count_root_agents()
    team_agents = count_team_agents()
    all_agents = root_agents + team_agents
    commands = count_commands()
    skills = count_skills()
    guides = count_guides()
    docs = count_docs()
    hooks = count_hooks()

    tiers = get_model_tiers()
    valid_tiers = {
        t: [a for a in agents if a in all_agents]
        for t, agents in tiers.items()
    }

    ghost_agents = [a for t in tiers.values() for a in t if a not in all_agents]

    data = {
        "AGENT_COUNT": len(all_agents),
        "ROOT_AGENT_COUNT": len(root_agents),
        "TEAM_AGENT_COUNT": len(team_agents),
        "COMMAND_COUNT": len(commands),
        "SKILL_COUNT": len(skills),
        "GUIDE_COUNT": len(guides),
        "DOC_COUNT": len(docs),
        "HOOK_COUNT": hooks.get("total", 0),
        "HOOK_EVENT_COUNT": len([k for k in hooks if k != "total"]),
        "command_list": commands,
        "skill_list": skills,
        "opus_agents": valid_tiers["opus"],
        "sonnet_agents": valid_tiers["sonnet"],
        "haiku_agents": valid_tiers["haiku"],
    }
    for event, count in hooks.items():
        if event != "total":
            data[f"hooks_{event}"] = count

    print("=== Claude Agentic Framework: Auto-Documentation ===")
    print(f"  Root agents:  {len(root_agents):>3}  {root_agents}")
    print(f"  Team agents:  {len(team_agents):>3}  {team_agents}")
    print(f"  Commands:     {len(commands):>3}  {commands}")
    print(f"  Skills:       {len(skills):>3}  {skills}")
    print(f"  Guides:       {len(guides):>3}")
    print(f"  Docs:         {len(docs):>3}")
    print(f"  Hooks:        {hooks.get('total', 0):>3}  ({', '.join(f'{k}:{v}' for k, v in hooks.items() if k != 'total')})")
    if ghost_agents:
        print(f"\n  WARNING: {len(ghost_agents)} ghost agents in model_tiers.yaml:")
        for g in ghost_agents:
            print(f"    - {g}")
    print()

    if check_mode:
        readme_path = REPO_DIR / "README.md"
        stamp = f"<!-- AUTO-DOC-STAMP:{data['AGENT_COUNT']}a-{data['COMMAND_COUNT']}c-{data['SKILL_COUNT']}s-{data['HOOK_COUNT']}h -->"
        if readme_path.exists() and stamp in readme_path.read_text():
            print("OK: README.md is current")
            if ghost_agents:
                print(f"WARNING: model_tiers.yaml has {len(ghost_agents)} ghost references")
            return 0
        print("STALE: README.md counts do not match repository state")
        return 1

    readme = generate_readme(data)
    claude = generate_claude_md(data)

    (REPO_DIR / "README.md").write_text(readme)
    print(f"  Generated: README.md")

    (REPO_DIR / "CLAUDE.md").write_text(claude)
    print(f"  Generated: CLAUDE.md")

    if ghost_agents:
        print(f"\n  ACTION NEEDED: Clean {len(ghost_agents)} ghost agents from data/model_tiers.yaml:")
        for g in ghost_agents:
            print(f"    - {g}")

    print("\nDone. README.md and CLAUDE.md regenerated from repository state.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
