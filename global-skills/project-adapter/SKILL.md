---
name: project-adapter
description: Generates a project-specific context file at /tmp/caf_project_context.md. Run once per session. All agents (builder, validator, debugger, dynamic subagents) read this file to pre-calibrate — right test commands, right conventions, right paths. Eliminates the "figure out the project" overhead from every agent.
user-invocable: true
---

Generate a project context snapshot and write it to `/tmp/caf_project_context.md`.

Spawn a Haiku agent to do this — it's fast, read-only, and shouldn't bloat the main context:

```
Agent(
    name="project-adapter",
    model="haiku",
    maxTurns=10,
    prompt="""You are a project context extractor. Your only job: read key project files and write a structured context snapshot.

DO NOT analyze, suggest improvements, or explain anything. Just extract and write.

## Step 1: Detect project type and stack

Check these files in order (stop when found):
- package.json → Node/JS/TS project
- pyproject.toml or setup.py → Python project  
- Cargo.toml → Rust project
- go.mod → Go project
- pom.xml or build.gradle → Java project
- mix.exs → Elixir project

Read whichever exists. Extract: project name, version, main language, key dependencies (top 5 by relevance).

## Step 2: Read project instructions

Read CLAUDE.md (or .claude/CLAUDE.md if root doesn't exist). Extract:
- Test command(s)
- Build/lint command(s)
- Any explicit conventions or rules
- Forbidden patterns or gotchas

## Step 3: Read verified facts

If .claude/FACTS.md exists, extract:
- All CONFIRMED facts
- All GOTCHAS entries

## Step 4: Read architecture (if exists)

If .claude/ARCHITECTURE.md exists, extract:
- Key entry points
- Module/directory structure (top level only)

## Step 5: Infer from structure (if no CLAUDE.md)

If no CLAUDE.md found, infer from file structure:
- Look for test directories: test/, tests/, __tests__/, spec/
- Look for main entry: src/main.*, app.*, index.*
- Look for config: .eslintrc*, ruff.toml, .clippy.toml, etc.
- Run `git log --oneline -5` for recent context

## Step 6: Write output

Write to /tmp/caf_project_context.md:

```markdown
# Project Context
GENERATED: [ISO timestamp]
PROJECT: [name]
STACK: [language] + [framework if any] + [key deps, comma-separated]

## Commands
```
test:  [exact command to run tests]
lint:  [exact command, or "not found"]
build: [exact command, or "not applicable"]
format:[exact command, or "not found"]
```

## Key Paths
- source: [main source directory]
- tests:  [test directory]
- config: [main config file]
- entry:  [main entry point file]

## Conventions (from CLAUDE.md)
[Bullet list — verbatim from CLAUDE.md rules section, or "none documented"]

## Known Gotchas (from FACTS.md)
[Bullet list from GOTCHAS section, or "none documented"]

## Confirmed Facts (from FACTS.md)
[Bullet list from CONFIRMED section, top 5 most recent, or "none"]

## Recent Activity (git log)
[Last 5 commits, one line each]
```

ANTI-HALLUCINATION RULES (strictly enforced):
- Every item in the output must have been read from a file this session. No memory, no inference.
- If a section has no data (no CLAUDE.md exists, no FACTS.md, etc.) → write `[not found]` for that section. Never invent content.
- For conventions: copy the exact text from CLAUDE.md. Do not paraphrase or summarize.
- For gotchas: copy the exact text from FACTS.md. Do not interpret.
- If a file you tried to read doesn't exist, write `[file not found: filename]` rather than guessing its contents.

Exit immediately after writing. No summary, no explanation.

IMPORTANT: Target 2,200–3,000 tokens (~8,800–12,000 characters) for this output file.

This is deliberate — Claude's prompt cache minimum thresholds are:
- Sonnet 4.6: 2,048 tokens minimum to cache
- Opus 4.6 / Haiku 4.5: 4,096 tokens minimum to cache

A file BELOW these thresholds never gets a cache hit and every agent pays full input price. A file above them caches after the first read (0.1× cost on all subsequent reads within the TTL window).

To hit ~2,500 tokens without padding: expand the Conventions section with full CLAUDE.md rule text (not summaries), include the full FACTS.md CONFIRMED section (not just top 5), and include the last 7 git commits instead of 5. Do NOT invent content — only include what actually exists in the project files.
"""
)
```

After the agent completes, confirm `/tmp/caf_project_context.md` was written and show the first 20 lines to the user.

If args are provided (e.g. `/project-adapter refresh`), delete the existing file first and regenerate.
