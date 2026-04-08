---
name: change-validator
description: Before committing or handing off: verifies that changes match the plan, no unintended blast radius, tests pass, and conventions are followed. Project-aware — uses /tmp/caf_project_context.md and /tmp/caf_plan.md. Outputs a go/no-go decision.
user-invocable: true
---

Validate staged/recent changes against the plan and project conventions. Produces a go/no-go decision before commit or handoff.

Check if `/tmp/caf_project_context.md` exists. If not, run project-adapter first.

Spawn a Haiku agent for validation:

```
Agent(
    name="change-validator",
    model="haiku",
    maxTurns=12,
    prompt="""You are a pre-commit change validator. Check that recent changes are safe, intentional, and match the plan.

Read these files first:
1. /tmp/caf_project_context.md — conventions, test command, known gotchas
2. /tmp/caf_plan.md — what was supposed to be built (if exists)
3. /tmp/caf_issue_context.md — what the issue was (if exists)

## Checks to run

### 1. Diff scope
Run: git diff HEAD (or git diff --staged if args include --staged)
- List every file changed
- For each, classify: intended (in plan) | unintended (not in plan) | uncertain

### 2. Convention violations (from project context)
For each changed file, grep for patterns listed in ## Conventions of project context.
Flag any violations with file:line.

### 3. Gotcha triggers (from project context)
For each changed file, check ## Known Gotchas.
Flag if any change touches a known gotcha area.

### 4. Blast radius
For each changed file:
- Grep for its imports in the codebase
- Count dependents
- Flag files with 3+ dependents as notable

### 5. Tests pass
Run test command from project context.
Report pass/fail count.

### 6. Plan alignment (if /tmp/caf_plan.md exists)
Compare changed files to "Files to Change" in the plan.
- Files changed that were NOT in plan: flag as unplanned
- Files in plan that were NOT changed: flag as incomplete

## Write report

Write to /tmp/caf_change_validation.md:

```markdown
# Change Validation Report
GENERATED: [ISO timestamp]
DECISION: GO | NO-GO | WARN

## Summary
- Files changed: N
- Unplanned changes: N
- Convention violations: N
- Gotcha triggers: N
- Tests: PASS X/Y | FAIL

## Unplanned Changes (if any)
- [file] — not in plan, verify intentional

## Convention Violations (if any)
- [file:line] — [convention text from project context]

## Gotcha Triggers (if any)
- [file] — [gotcha text from project context]

## High Blast Radius Files
- [file] — [N] dependents

## Plan Alignment (if plan exists)
- Covered: [list]
- Incomplete: [list — in plan but not changed]

## Decision Rationale
[One sentence: why GO / NO-GO / WARN]
```

DECISION rules:
- GO: tests pass, no unplanned changes, no convention violations
- WARN: tests pass but has unplanned changes or 1-2 minor violations
- NO-GO: tests fail, OR critical convention violation, OR gotcha triggered

Exit immediately after writing.
"""
)
```

Show the user the DECISION line and any NO-GO reasons after the agent completes.

If args include `--staged`, validate only staged changes.

If args include `--fix` and the validation report contains convention violations:
1. Read `/tmp/caf_change_validation.md` — extract the "Convention Violations" section
2. Write a proper plan file at `/tmp/caf_fix_plan.md`:
   ```markdown
   # CAF Plan
   SESSION_ID: fix-[timestamp]
   TASK: Fix convention violations found by change-validator
   CREATED: [ISO timestamp]
   CURRENT_ITERATION: 1
   MAX_ITERATIONS: 1
   GIT_ROLLBACK_BASE: [git rev-parse HEAD]

   ## Acceptance Criteria 1
   - change-validator reports no convention violations
   - All existing tests still pass

   ## Build Task 1
   [For each violation from the report:]
   - File: [file path]
   - Line: [line number]
   - Violation: [convention text]
   - Fix: [what to change]

   ## Dead Ends
   (none)
   ```
3. Then spawn the builder pointing at this plan:
   ```
   Agent(subagent_type="builder", name="convention-fixer", maxTurns=15,
     prompt="Read /tmp/caf_fix_plan.md. Execute 'Build Task 1'. Write output to /tmp/caf_fix_build_1.md.")
   ```
4. After builder completes, re-run the validator to confirm violations are cleared.
