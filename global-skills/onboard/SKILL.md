---
name: onboard
description: Initializes a new project with CAF structure. Detects tech stack, fetches framework conventions, generates CLAUDE.md, settings.json, PROJECT_CONTEXT.md, QUICKSTART.md, FACTS.md, and MEMORY.md. Trigger phrases: /onboard, onboard this project, set up CAF for this repo.
user-invocable: true
scope: global
---

# /onboard — CAF Project Initializer

Bootstraps a new project with full CAF structure in one command. Detects your tech stack, researches framework conventions, and generates all required context files so every subsequent agent session starts pre-calibrated.

## When to Use

- Starting CAF on a project that has no `.claude/` directory
- Joining an existing repo and needing to generate CAF context from scratch
- Resetting a project's CAF configuration after a major refactor

## Workflow

Execute these three phases in order. Each phase feeds the next.

---

### Phase 1 — Detect

Scan the current working directory for manifest files to identify the tech stack. Check in this priority order (stop at first match):

1. `package.json` → Node.js / npm (or yarn/pnpm if lockfile present)
2. `pyproject.toml` or `requirements.txt` → Python / uv
3. `Cargo.toml` → Rust / cargo
4. `go.mod` → Go
5. `pom.xml` → Java / Maven
6. `build.gradle` → Java / Gradle
7. `mix.exs` → Elixir / mix

Also check whether `.claude/` already exists and whether any existing `settings.json` references CAF hook paths (signals a prior CAF install).

---

### Phase 2 — Generate

Spawn the `onboard` agent to detect the stack, fetch conventions, and generate every project file in one pass — no separate plan-then-build relay:

```
Agent(
    name="onboard",
    subagent_type="onboard",
    model="sonnet",
    maxTurns=20,
    prompt="Onboard this repo: detect the tech stack from manifest files, fetch framework conventions via context7 if available, and generate CLAUDE.md, .claude/settings.json, .claude/PROJECT_CONTEXT.md, .claude/QUICKSTART.md, .claude/FACTS.md, and .claude/MEMORY.md in the current working directory. See global-agents/onboard.md for the exact file structures and anti-hallucination rules."
)
```

Verify the agent's completion report lists all six files before proceeding.

---

### Phase 3 — Report

After the onboard agent completes, show the user:

```
## Onboard Complete

Project: [project_name]
Stack: [language] + [framework]

### Files Created
- CLAUDE.md
- .claude/settings.json  (validated JSON)
- .claude/PROJECT_CONTEXT.md
- .claude/QUICKSTART.md
- .claude/FACTS.md
- .claude/MEMORY.md

### Next Steps
1. Review CLAUDE.md — update any placeholder sections
2. Run /project-adapter to generate /tmp/caf_project_context.md
3. Run your first task: /orchestrate [describe your goal]
```

If any file failed to generate, list it under "### Failed" with the reason.

---

## Examples

**New Node.js project**
```
/onboard
→ Detects package.json, fetches Express conventions via context7
→ Generates CLAUDE.md with npm install / npm test commands
→ Creates .claude/ structure with CAF hooks configured
→ Reports 6 files created
```

**Python monorepo**
```
/onboard
→ Detects pyproject.toml, fetches FastAPI + pytest conventions
→ Generates CLAUDE.md with uv run commands (never pip install)
→ Creates .claude/PROJECT_CONTEXT.md with 2,500+ tokens for cache hit
→ Reports 6 files created, QUICKSTART.md has 10 steps to first test
```
