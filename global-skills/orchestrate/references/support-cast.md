# Support-Cast Reference

Consolidated reference for the three orchestration support agents: change-validator, issue-scoper, test-scout. These are only meaningful inside an orchestration run — they read/write the shared `/tmp/caf_*.md` state files that orchestrate produces and consumes. Previously three separate user-invocable skills; folded here since they're always used in service of an orchestrate run rather than standalone.

---

## change-validator

Before committing or handing off: verifies that changes match the plan, no unintended blast radius, tests pass, and conventions are followed. Project-aware — uses `/tmp/caf_project_context.md` and `/tmp/caf_plan.md`. Outputs a go/no-go decision.

Flags: `--staged` (validate only staged changes), `--fix` (auto-fix convention violations found).

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

---

## issue-scoper

Narrows context to a specific issue or task. Finds relevant files, related tests, blast radius, and similar past fixes. Writes `/tmp/caf_issue_context.md`. Agents read this to start with laser focus instead of searching the whole codebase.

**Skip condition**: If the issue description already contains a specific `file:line` reference AND a clear description of what to change (e.g., "fix the null check at auth.py:42"), skip the scoper entirely — the issue is already scoped. Just confirm: "Issue is already specific — skipping scope analysis."

Otherwise, proceed:

First, ensure `/tmp/caf_project_context.md` exists. If not, run the `project-adapter` skill first:
```
Agent(name="project-adapter", model="haiku", maxTurns=10, prompt="[project-adapter full prompt]")
```

Then spawn a Sonnet agent to scope the issue (needs search + reasoning):

```
Agent(
    name="issue-scoper",
    model="sonnet",
    maxTurns=15,
    prompt="""You are an issue context builder. Your job: given an issue description, find everything relevant to solving it and write a focused context file.

Read /tmp/caf_project_context.md first — it has the project structure, test commands, and known paths.

Issue/task to scope: [USER'S ISSUE DESCRIPTION]

## What to find

### 1. Relevant source files
Search for files directly related to the issue:
- Grep for key terms from the issue description
- Grep for function/class names mentioned
- Check files in the path the error trace mentions (if any)
- Limit to top 5 most relevant files. More is noise.

For each file found, note: why it's relevant (one sentence, cite the grep match).

### 2. Related tests
Find tests that cover the affected code:
- Grep for the affected function/class names in the test directory (from project context)
- List test files with the specific test names that are relevant
- Note which test command runs them (from project context)

### 3. Similar past fixes
Check .claude/solve-history/ for similar problems:
- List files in .claude/solve-history/ if the directory exists
- For each, check the frontmatter: does `problem:` match the current issue?
- If yes, extract: root_cause + files_changed from that history entry
- Limit to top 3 matches

### 4. Blast radius
For each relevant source file found:
- Grep for its imports in the rest of the codebase
- Count how many files depend on it
- Flag files with 5+ dependents as "high blast radius"

### 5. Error pattern (if issue has an error message)
If the issue description contains an error or exception:
- Grep for the exact error string in the codebase
- Find where it's thrown/generated
- Note the file:line

## Write output

Write to /tmp/caf_issue_context.md:

```markdown
# Issue Context
GENERATED: [ISO timestamp]
ISSUE: [issue description, one line]
COMPLEXITY_ESTIMATE: simple | medium | hard
(simple = 1 file, obvious fix; medium = 2-5 files; hard = cross-cutting or unclear)

## Relevant Files (top 5)
| File | Why Relevant | Blast Radius |
|------|-------------|--------------|
| /path/to/file | [grep match or reason] | [N dependents] |

## Related Tests
| Test File | Test Name/Function | Run With |
|-----------|-------------------|----------|
| /path/to/test | [test function name] | [exact command] |

## Similar Past Fixes
[If any found in .claude/solve-history/]
- [date] [problem] → [approach that worked] (files: [list])
[If none: "No similar fixes found in solve-history"]

## Error Origin (if applicable)
- Error: [exact error text]
- Thrown at: [file:line]
- Caught/handled at: [file:line if found]

## Blast Radius Warning
[List any files with 5+ dependents that would be affected]
[Or: "No high blast-radius files identified"]

## Suggested Approach (one sentence)
[Based on complexity and blast radius — builder should start here]
```

Exit immediately after writing the file.
"""
)
```

After completion, show the user the issue context and confirm the complexity estimate.

Pass the user's full message (the issue description) as the issue to scope.

---

## test-scout

Runs the project's test suite and categorizes failures with project-aware context. Uses `/tmp/caf_project_context.md` for the right command. Writes a structured failure report to `/tmp/caf_test_report.md`. Use before and after a build step to detect regressions.

Flags: `--baseline` (delete existing baseline and re-establish it), `--compare` (show diff from last baseline).

Check if `/tmp/caf_project_context.md` exists. If not, run project-adapter first.

Spawn a Haiku agent to run tests and report:

```
Agent(
    name="test-scout",
    model="haiku",
    maxTurns=8,
    prompt="""You are a test runner and failure reporter. Run the project's test suite and write a structured report.

Read /tmp/caf_project_context.md — find the `test:` command under ## Commands.

## Step 1: Record baseline (if /tmp/caf_test_baseline.md exists)
Read /tmp/caf_test_baseline.md to get the previous pass count.
If it doesn't exist, this is the baseline run — note it.

## Step 2: Run tests
Run the test command from project context.
Capture full output. Note:
- Total tests run
- Tests passed
- Tests failed
- Tests skipped

## Step 3: Categorize failures (if any)
For each failing test:
- Test name
- File:line where it fails
- Exact error message (first 3 lines only)
- Is this a NEW failure (not in baseline) or pre-existing?

## Step 4: Write report

Write to /tmp/caf_test_report.md:

```markdown
# Test Report
GENERATED: [ISO timestamp]
COMMAND: [exact command run]
STATUS: PASS | FAIL | PARTIAL

## Summary
- Passed: X / Y
- Failed: Z
- Skipped: N
- Regression from baseline: [+N new failures | no change | N fixed]

## Failures
### [test name]
- File: [file:line]
- Error: [first 3 lines of error]
- New failure: YES | NO (was failing in baseline too)

## Passed (count only, no list)
[X tests passed]
```

Also write /tmp/caf_test_baseline.md if this is a baseline run:
```markdown
BASELINE_PASS_COUNT: X
BASELINE_FAIL_COUNT: Z
TIMESTAMP: [ISO]
COMMAND: [command]
```

Exit immediately after writing.
"""
)
```

If args include `--baseline`, delete existing baseline and re-establish it.
If args include `--compare`, show diff from last baseline.

Show the user the STATUS line and failure count after the agent completes.
