---
name: makeskill
description: "Autonomous project analyzer that generates project-specific skills and agents. Use when: 'analyze this project', 'generate skills', 'what skills would help', 'makeskill', 'create project skills', 'skill recommendations'. Scans code structure, git history, Claude memory, and recurring pain points to propose and create targeted local skills and agents."
user-invocable: true
---

# MakeSkill — Project Skill Factory

Analyzes any project deeply with 4 parallel sub-agents, identifying recurring pain points and automation opportunities. Proposes a ranked list of project-specific skills and agents, then generates them on approval. Everything generated is immediately usable via slash command or automatic dispatch.

## When to Use

- User says: `/makeskill`, "analyze this project", "generate skills for this project", "what skills would help here", "create project-specific skills"
- When starting work on a new project and wanting tailored automation
- When recurring patterns or bugs suggest automation opportunities
- When re-running to detect new patterns after project evolution (`--refresh`)

## Flags

| Flag | Behavior |
|------|----------|
| _(none)_ | Phase 1 only — analyze, propose, wait for user selection |
| `--auto` | Phase 1 + Phase 2 without user approval |
| `--refresh` | Re-run analysis, detect new patterns, propose updates to existing generated skills |
| `--list` | Show previously generated skills/agents from `.claude/skills/makeskill-manifest.json` |

If args include `--list`: read `.claude/skills/makeskill-manifest.json` (if it exists), display the table of generated items, and stop. No analysis needed.

## Workflow

### Step 0: Prerequisites

Check if `/tmp/caf_project_context.md` exists. If it does not exist, spawn project-adapter first and wait for it to complete before continuing:

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

If .claude/FACTS.md exists, extract all CONFIRMED facts and all GOTCHAS entries.

## Step 4: Read architecture (if exists)

If .claude/ARCHITECTURE.md exists, extract key entry points and module/directory structure (top level only).

## Step 5: Infer from structure (if no CLAUDE.md)

If no CLAUDE.md found, infer from file structure: look for test directories (test/, tests/, __tests__/, spec/), main entry (src/main.*, app.*, index.*), config files (.eslintrc*, ruff.toml, etc.). Run `git log --oneline -5` for recent context.

## Step 6: Write output

Write to /tmp/caf_project_context.md with sections: Project Context header, GENERATED timestamp, PROJECT name, STACK, Commands (test/lint/build/format), Key Paths (source/tests/config/entry), Conventions (from CLAUDE.md verbatim), Known Gotchas (from FACTS.md verbatim), Confirmed Facts (from FACTS.md, top 5 most recent), Recent Activity (last 5 commits).

ANTI-HALLUCINATION: Every item must have been read from a file this session. Write [not found] for missing sections. Never invent content.

Exit immediately after writing. No summary, no explanation.
"""
)
```

If args include `--refresh`:
1. Read `.claude/skills/makeskill-changelog.json` for the last run's git hash
2. Run `git diff <last-hash>..HEAD --name-only` to identify changed files/modules
3. Delete `/tmp/caf_makeskill_*.md` files to clear stale cache
4. Pass the changed-files list to each scout agent so they deep-dive on changes but light-scan unchanged areas
5. If no changelog exists, treat as first run (full scan)

### Step 1: Broad Scan — 4 Parallel Haiku Scouts + Step 1.5: Opus Deep Review

Read `SCOUT_PROMPTS.md` in this directory for the complete scout agent prompts and Opus deep-review prompt. Spawn ALL FOUR Haiku scouts in ONE message (parallel), then one Opus deep-reviewer after they complete.


### Step 2: Synthesis (root agent)

After all 4 agents complete, you (the root agent) do the following:

1. Read all 4 output files:
   - `/tmp/caf_makeskill_code.md`
   - `/tmp/caf_makeskill_git.md`
   - `/tmp/caf_makeskill_memory.md`
   - `/tmp/caf_makeskill_patterns.md`

2. Deduplicate: merge opportunities that describe the same automation. If code-structure-analyzer and git-history-analyzer both flag the same file as a problem area, that's stronger evidence — merge and note "2 signals".

3. For each unique opportunity, determine type:
   - **SKILL**: workflow automation, coding standards enforcement, project commands, code generation → user invokes via `/skill-name`
   - **AGENT**: isolated research, specialized analysis, read-only audit, one-shot investigation → runs unattended

4. Rank by priority:
   - **P1 (Critical)**: Multiple signals from different agents, or memory shows it has already caused bugs/pain
   - **P2 (High)**: Single strong signal with clear evidence
   - **P3 (Medium)**: Pattern detected but no confirmed pain yet

5. Write ranked proposal list to `/tmp/caf_makeskill_proposals.md`:

```markdown
# MakeSkill Proposals
GENERATED: [ISO timestamp]
PROJECT: [from project context]

## Ranked Proposals

| # | Name | Type | Priority | Problem | Frequency | Est. Savings | Auto-trigger? |
|---|------|------|----------|---------|-----------|-------------|---------------|
| 1 | [kebab-case-name] | SKILL | P1 | [one sentence] | [N times/3mo] | [~X tokens/run] | Yes/No |
| 2 | [kebab-case-name] | AGENT | P2 | [one sentence] | [N times/3mo] | [~X tokens/run] | Yes/No |
...

## Evidence Summary
[For each P1 item: which agents flagged it and what they found]
```

6. Present the proposals table to the user. If args include `--auto`, skip user approval and proceed to Phase 2 with all proposals. Otherwise, ask: "Which proposals should I generate? Reply with numbers (e.g., '1 3 5'), 'all', or 'none'."

### Step 3: Generation (after user approval or --auto)

For each approved proposal, spawn one builder agent per proposal — ALL in ONE message (parallel).

**Skill builders** write to `.claude/skills/<skill-name>/SKILL.md`.
**Agent builders** write to `.claude/agents/<agent-name>.md`.

Each builder receives the full proposal details, the project context path, and these security rules:

```
Agent(
    name="skill-builder-[name]",
    model="sonnet",
    maxTurns=12,
    prompt="""You are a skill/agent file generator. Build one file and exit.

Read /tmp/caf_project_context.md for project conventions.
Read /tmp/caf_makeskill_proposals.md for the full proposal details.

Your assignment: [PROPOSAL DETAILS — name, type, problem, evidence]

## If generating a SKILL (type=SKILL)

Write to .claude/skills/[name]/SKILL.md with this structure:

```yaml
---
name: [name]
description: "[Pushy description with trigger phrases: use when 'X', 'Y', 'Z'. Does: [what it does].]"
user-invocable: true
---
```

Follow with:
- # [Display Name] — [tagline]
- 2-3 sentence intro tied to the evidence from this project
- ## When to Use — at least 3 specific trigger conditions
- ## Workflow — numbered steps with concrete bash commands or tool calls
- ## Examples — at least 2 examples with user invocation + what happens

## If generating an AGENT (type=AGENT)

Write to .claude/agents/[name].md with this structure:

```yaml
---
name: [name]
description: "[What this agent does, when it runs, what it produces]"
model: sonnet
maxTurns: 15
---
```

Follow with the agent's full prompt (self-contained — the agent never reads a skill file).

## Security rules (MANDATORY — violating any = invalid output)

- NEVER include eval(), exec(), or dynamic code execution
- NEVER include shell injection vectors (unquoted variables in bash)
- NEVER include hardcoded secrets, API keys, or credentials
- NEVER include `rm -rf` without explicit bounded path
- NEVER include `curl | bash` or piped execution from remote sources
- All file paths must be explicit, not constructed from user input without validation
- All bash commands must be specific and bounded

## Quality rules

- Description must include at least 3 trigger phrases ("use when: '...'")
- Workflow must have at least 2 steps
- At least 2 examples
- Stay focused: one skill = one workflow
- Use project-specific paths and conventions from /tmp/caf_project_context.md

Exit immediately after writing the file.
"""
)
```

### Step 3.5: Validation (mandatory)

After all builders complete, spawn one Haiku validator:

```
Agent(
    name="makeskill-validator",
    model="haiku",
    maxTurns=8,
    prompt="""You are a skill/agent file validator. Check all files generated by makeskill and report pass/fail for each.

Read /tmp/caf_makeskill_proposals.md to get the list of generated files.

For each generated file, check ALL of the following. Report PASS or FAIL with reason:

1. **Frontmatter valid**: File starts with ---, has name field, has description field, YAML parses correctly
2. **No security violations**: Grep file content for: eval(, exec(, curl | bash, rm -rf /, unquoted $VARIABLE in bash blocks. If found → FAIL.
3. **Workflow completeness**: Skill files must have ≥2 workflow steps. Agent files must have a substantive prompt (>100 words).
4. **Examples present**: Skill files must contain at least 2 examples. Agent files exempt.
5. **Description quality**: Description field must contain at least one trigger phrase pattern ("use when", "when user says", or similar).
6. **File size**: File must be <2000 tokens (estimate: <8000 characters). If larger → FAIL.
7. **No duplicate**: Check .claude/skills/ and .claude/agents/ — does a file with this name already exist outside the one just created?

## Output format

Write to /tmp/caf_makeskill_validation.md:

```markdown
# Validation Report
GENERATED: [ISO timestamp]

| File | Frontmatter | Security | Completeness | Examples | Description | Size | Result |
|------|-------------|----------|-------------|---------|-------------|------|--------|
| [path] | PASS/FAIL | PASS/FAIL | PASS/FAIL | PASS/FAIL | PASS/FAIL | PASS/FAIL | PASS/FAIL |

## Failures (detail)
[For each FAIL row: what check failed and why]

## Overall: PASS / FAIL (N of M files passed)
```

Exit immediately after writing.
"""
)
```

Read `/tmp/caf_makeskill_validation.md`. If any file FAILs, report the failures to the user and note which items need manual review. Do not re-run builders — flag for human review.

### Step 3.6: Manifest + CLAUDE.md Update

1. Write `.claude/skills/makeskill-manifest.json`:

```json
{
  "generated": "ISO_TIMESTAMP",
  "project": "PROJECT_NAME",
  "items": [
    {
      "name": "skill-name",
      "type": "SKILL|AGENT",
      "path": ".claude/skills/skill-name/SKILL.md",
      "problem": "one sentence",
      "priority": "P1|P2|P3",
      "validation": "PASS|FAIL"
    }
  ]
}
```

2. Write `.claude/skills/makeskill-changelog.json`:

```json
{
  "last_run": "ISO_TIMESTAMP",
  "git_hash": "CURRENT_GIT_HASH",
  "modules_analyzed": ["list", "of", "directories"],
  "proposals_generated": 6,
  "items_created": 3
}
```

3. Check if project CLAUDE.md exists (root `CLAUDE.md` or `.claude/CLAUDE.md`). Append a `## Generated Skills (by /makeskill)` section:

```markdown
## Generated Skills (by /makeskill)

Generated: [ISO timestamp] | Run `/makeskill --list` to see all generated items.

| Name | Type | Problem Solved |
|------|------|---------------|
| /[name] | SKILL | [problem] |
| [name] | AGENT | [problem] |
```

If the section already exists (re-run with `--refresh`), replace it with the updated version.

## Examples

### Example 1: First-time analysis on a Python FastAPI project

User: `/makeskill`

1. project-adapter runs (if `/tmp/caf_project_context.md` missing) — detects Python + FastAPI + pytest
2. 4 parallel agents run: code-structure-analyzer finds 47 similar endpoint files; git-history-analyzer finds "fix: migration" commits 8x in 3 months; memory-analyzer finds GOTCHA about alembic commands; pattern-detector finds no test fixtures despite 200+ tests
3. Root agent synthesizes → 6 proposals: `endpoint-scaffolder` (P1), `migration-helper` (P1), `fixture-factory` (P2), `test-coverage-checker` (P2), `api-doc-generator` (P3), `churn-auditor` (P3)
4. User selects: "1 2 4"
5. 3 parallel builders generate: `.claude/skills/endpoint-scaffolder/SKILL.md`, `.claude/skills/migration-helper/SKILL.md`, `.claude/skills/test-coverage-checker/SKILL.md`
6. Validator checks all 3 → PASS
7. Manifest written, CLAUDE.md updated

### Example 2: Refresh after 2 months of project evolution

User: `/makeskill --refresh`

1. `/tmp/caf_makeskill_*.md` files deleted (refresh clears cache)
2. project-adapter regenerates context
3. 4 parallel agents re-run — detect new patterns: React components added since last run, new GitHub Actions workflow gaps
4. Root agent synthesizes → proposes 2 new skills + 1 update to existing `test-coverage-checker`
5. With `--refresh`, existing items shown as "UPDATE" in proposal table
6. User selects new items; existing `test-coverage-checker` updated in place

## Completion Report

After Phase 2.6 completes, output:

```markdown
## MakeSkill Report

**Project**: [name]
**Analysis**: [N patterns detected across 4 agents]

### Generated Items
| Name | Type | Priority | Problem Solved | Validation |
|------|------|----------|---------------|------------|
| /[name] | SKILL | P1 | [problem] | PASS |

### Agent Team Performance
| Agent | Model | Result |
|-------|-------|--------|
| code-structure-analyzer | sonnet | [N opportunities found] |
| git-history-analyzer | sonnet | [N patterns found] |
| memory-analyzer | sonnet | [N pain points found] |
| pattern-detector | sonnet | [N gaps found] |
| skill-builder-* | sonnet | [N files written] |
| makeskill-validator | haiku | [N/M passed] |

### Next Steps
- Use `/[skill-name]` to invoke generated skills
- Run `/makeskill --list` to see all generated items
- Run `/makeskill --refresh` after major project changes
```
