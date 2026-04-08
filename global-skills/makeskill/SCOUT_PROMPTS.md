# MakeSkill — Scout Agent Prompts

These are the agent prompts used by Steps 1 and 1.5 of the makeskill workflow.
The root SKILL.md references this file. Do not modify independently.

---

## Step 1: 4 Parallel Haiku Scouts

Spawn ALL FOUR in ONE message (parallel):

### Scout 1: code-structure-analyzer

```
Agent(
    name="code-structure-analyzer",
    model="haiku",
    maxTurns=10,
    prompt="""You are a code structure analyst. Analyze this project's code structure and write findings to /tmp/caf_makeskill_code.md.

Read /tmp/caf_project_context.md first.

Analyze: source file map, entry points, data models, repeated boilerplate, missing patterns, complex modules (>300 lines).

Output format — write to /tmp/caf_makeskill_code.md:
- Project Scale (total files, modules with counts)
- Entry Points
- Repeated Boilerplate (automation candidates)
- Missing Patterns (gap candidates)
- Complex Modules (refactoring candidates)
- Skill Opportunities (raw)

Exit immediately after writing."""
)
```

### Scout 2: git-history-analyzer

```
Agent(
    name="git-history-analyzer",
    model="haiku",
    maxTurns=10,
    prompt="""You are a git history analyst. Analyze git history for patterns and write to /tmp/caf_makeskill_git.md.

Read /tmp/caf_project_context.md first.

Run: git log --oneline -100, churn hotspots (3mo), recurring fix targets, commit message patterns, release patterns.

Output format — write to /tmp/caf_makeskill_git.md:
- Churn Hotspots (file, changes, risk)
- Recurring Fix Targets
- Commit Message Patterns
- Workflow Frequency Estimates (N times/3mo x M prompts each)
- Release/Deployment Pattern
- Skill Opportunities (raw)

Exit immediately after writing."""
)
```

### Scout 3: memory-analyzer

```
Agent(
    name="memory-analyzer",
    model="haiku",
    maxTurns=10,
    prompt="""You are a project memory analyst. Extract recurring pain points from memory files and write to /tmp/caf_makeskill_memory.md.

Read /tmp/caf_project_context.md first.

Analyze: FACTS.md (gotchas, confirmed facts), MEMORY.md (recurring themes, pain points), solve-history/ (recurring problem types), knowledge-db/ (recurring queries).

Output format — write to /tmp/caf_makeskill_memory.md:
- Recurring Gotchas (from FACTS.md)
- Recurring Workflows (from MEMORY.md)
- Token Savings Estimates (sessions x prompts x ~500 tokens)
- Recurring Problem Types (from solve-history)
- Recurring Knowledge Queries
- Skill Opportunities (raw)

If a memory file does not exist, write [not found]. Exit immediately after writing."""
)
```

### Scout 4: pattern-detector

```
Agent(
    name="pattern-detector",
    model="haiku",
    maxTurns=10,
    prompt="""You are a framework pattern detector. Identify framework-specific automation opportunities and write to /tmp/caf_makeskill_patterns.md.

Read /tmp/caf_project_context.md first.

Detect: framework-specific opportunities (React/Python/Go/Rust/CLI/Monorepo patterns), existing skill/agent gaps, test coverage gaps, CI/CD automation gaps, documentation gaps.

Output format — write to /tmp/caf_makeskill_patterns.md:
- Existing Skills/Agents (do not duplicate)
- Framework Opportunities
- Test Coverage Gaps
- CI/CD Gaps
- Documentation Gaps
- Skill Opportunities (raw)

Exit immediately after writing."""
)
```

---

## Step 1.5: Opus Deep Review

After all 4 scouts complete, spawn ONE Opus agent:

```
Agent(
    name="deep-reviewer",
    model="opus",
    maxTurns=20,
    prompt="""You are an expert project analyst. 4 Haiku scouts did a broad scan. Your job: review, deepen, and cross-reference.

Read: /tmp/caf_project_context.md, /tmp/caf_makeskill_code.md, /tmp/caf_makeskill_git.md, /tmp/caf_makeskill_memory.md, /tmp/caf_makeskill_patterns.md

Tasks:
1. Cross-reference: find areas flagged by 2+ scouts (high-confidence)
2. Deep-dive: where scouts lacked detail, read actual files to confirm/deny
3. Quantify: for each opportunity — frequency, token savings estimate, auto-trigger potential
4. Enhance each analysis file with ## Deep Review Notes section
5. Write /tmp/caf_makeskill_deep_review.md with:
   - Cross-Signal Opportunities table
   - Deep-Dive Findings (CONFIRMED/DENIED)
   - Quantitative Metrics table

Exit after writing all files."""
)
```
