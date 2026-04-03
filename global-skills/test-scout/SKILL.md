---
name: test-scout
description: Runs the project's test suite and categorizes failures with project-aware context. Uses /tmp/caf_project_context.md for the right command. Writes a structured failure report to /tmp/caf_test_report.md. Use before and after a build step to detect regressions.
user-invocable: true
---

Run tests and write a structured failure report. Uses project context for the right command.

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
