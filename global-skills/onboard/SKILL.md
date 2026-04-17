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

Execute these four phases in order. Each phase feeds the next.

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

### Phase 2 — Research

Spawn the `onboard-planner` agent to analyze the repo and produce a structured plan:

```
Agent(
    name="onboard-planner",
    model="sonnet",
    maxTurns=15,
    prompt="""
    Analyze this repo and produce an onboarding plan.

    1. Scan cwd for manifest files (package.json, pyproject.toml, Cargo.toml, go.mod,
       pom.xml, build.gradle, mix.exs). Read whichever matches first.
    2. Extract: project name, version, description, key dependencies (top 5).
    3. Infer: test command, build command, install command, lint command.
    4. If context7 MCP is available:
       - Call mcp__plugin_context7_context7__resolve-library-id with the primary framework name
       - Call mcp__plugin_context7_context7__query-docs for "project conventions" and "testing"
       - Include top 5 conventions in the plan
       If context7 is unavailable, skip gracefully and note "context7: unavailable".
    5. Write /tmp/onboard_plan.md with this exact structure:

    # Onboard Plan
    project_name: [name from manifest]
    stack:
      language: [e.g. Python, Node.js, Rust]
      framework: [e.g. FastAPI, Express, Actix — or "none detected"]
      pkg_manager: [e.g. uv, npm, cargo]
      test_runner: [e.g. pytest, jest, cargo test]
      build_cmd: [exact command or "not applicable"]
      test_cmd: [exact command]
      install_cmd: [exact command]
    conventions:
      - [convention 1 from context7 or standard defaults]
      - [convention 2]
      - [convention 3]
      - [convention 4]
      - [convention 5]

    6. Return a 2-sentence summary of what was detected.
    """
)
```

Verify `/tmp/onboard_plan.md` was written before proceeding.

---

### Phase 3 — Generate

Spawn the `onboard-builder` agent to write all project files:

```
Agent(
    name="onboard-builder",
    model="sonnet",
    maxTurns=20,
    prompt="""
    Read /tmp/onboard_plan.md first. Then generate all of the following files
    in the current working directory. For each file: check if it already exists,
    show a 3-line preview of what will be written, then write it.

    ## Files to generate

    ### 1. CLAUDE.md
    Sections (in order):
    - Title: # [project_name]
    - One-line tagline
    - ## Tech Stack (table with language, framework, pkg_manager, test_runner)
    - ## Build Commands (bash block with install_cmd, test_cmd, build_cmd)
    - ## Code Style (5 conventions from the plan)
    - ## Architecture (top-level directory listing — run `ls` to get real dirs)
    - ## Memory
      - .claude/FACTS.md — verified facts (CONFIRMED > GOTCHAS > PATHS > PATTERNS)
      - .claude/MEMORY.md — session summaries (git-diff-based, max 30 entries)

    Anti-hallucination: every command must be copied verbatim from the plan.
    Do not invent commands.

    ### 2. .claude/settings.json
    Steps:
    a. Read the CAF template at ~/.caf/templates/settings.json.template
       (fall back to templates/settings.json.template in the current working directory if not found)
    b. Replace __REPO_DIR__ with the actual cwd path.
       Use Python json.dumps() for safe escaping:
         python3 -c "import json, sys; print(json.dumps(sys.argv[1]))" "$(pwd)"
       Use the resulting JSON string (without outer quotes) as the replacement value.
    c. Validate the result is valid JSON:
         python3 -m json.tool .claude/settings.json > /dev/null
    d. Write to .claude/settings.json only after validation passes.

    ### 3. .claude/PROJECT_CONTEXT.md
    Header block (required):
      GIT_HASH: [output of `git rev-parse HEAD` or "not a git repo"]
      GENERATED: [ISO timestamp]
      PRIME_VERSION: 1.0
    Sections:
    - ## Project Overview ([project_name] — tagline, 2-3 sentences from manifest description)
    - ## Tech Stack (from plan)
    - ## Build Commands (exact commands from plan)
    - ## Key Paths (source, tests, config, entry — inferred from ls output)
    - ## Architecture (top-level dirs with one-line descriptions)
    - ## Remaining Items (empty — "none at init")
    - ## Key Constraints (list conventions from plan)
    Target size: 2,200–3,000 tokens to exceed Sonnet 4.6 cache minimum (2,048 tokens).
    Expand sections with full detail to hit this target.

    ### 4. .claude/QUICKSTART.md
    Content (max 10 steps to first passing test):
    - ## Prerequisites (uv or relevant package manager, Claude Code, CAF)
    - ## First Run
      1. Clone the repo (or cd into it)
      2. Run install_cmd
      3. Run test_cmd — confirm all pass
    - ## CAF Setup
      4. /project-adapter (generates /tmp/caf_project_context.md)
      5. /orchestrate [your first task]
    - ## Key Files
      - CLAUDE.md — project conventions
      - .claude/PROJECT_CONTEXT.md — auto-injected context
      - .claude/FACTS.md — verified facts
    - ## Commands Cheat Sheet (test, lint, build from plan)
    - ## Common Gotchas (3 entries — use known framework gotchas or write placeholders)

    ### 5. .claude/FACTS.md (stub)
    ```markdown
    # Facts
    GENERATED: [ISO timestamp]

    ## CONFIRMED
    - project_name: [project_name from plan]
    - stack: [language] + [framework]
    - test_cmd: [test_cmd from plan]
    - install_cmd: [install_cmd from plan]

    ## GOTCHAS
    [none documented yet — add entries as discovered]

    ## PATHS
    - source: [source dir]
    - tests: [tests dir]

    ## PATTERNS
    [none documented yet]

    ## STALE
    [none]
    ```

    ### 6. .claude/MEMORY.md (stub)
    ```markdown
    # Memory
    [YYYY-MM-DD] INIT: Project onboarded via /onboard. Stack: [language]+[framework].
    Files created: CLAUDE.md, .claude/settings.json, .claude/PROJECT_CONTEXT.md,
    .claude/QUICKSTART.md, .claude/FACTS.md, .claude/MEMORY.md
    ```

    After writing all files, run:
      ls -la .claude/
    to confirm all files exist. Report file sizes.
    """
)
```

---

### Phase 4 — Report

After the onboard-builder agent completes, show the user:

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
