---
name: Verification Checklist
version: 0.1.0
description: "This skill should be used when finishing a feature, closing a bug fix, completing a PR, or when the user asks to 'verify', 'check everything', or 'make sure it works'. It runs a comprehensive verification checklist before marking any task as complete, preventing premature completion claims."
---

# Verification Checklist Skill

Systematic verification that work is genuinely complete before declaring it done. Each item must be actively verified (not assumed), with evidence recorded. Prevents the common failure mode of claiming completion when tests have not been run, code has not been executed, or bugs have not been reproduced.

## When to Use

- Before marking any task as completed
- Before submitting or approving a pull request
- After fixing a bug (verify the fix actually works)
- User asks: "verify this", "check everything", "is this done?", "make sure it works"
- At the Stop hook (automatic verification before session end)
- Before any deployment or release

## The Verification Checklist

Every item must be checked and evidenced. Do not skip items.

### 1. Tests Actually Pass

**Not just written -- actually executed and green.**

```bash
# Run the full test suite
pytest --tb=short -q 2>&1 | tail -20
# or
npm test 2>&1 | tail -30
# or
go test ./... 2>&1 | tail -20
```

| Check | Evidence Required |
|-------|------------------|
| All existing tests pass | Test runner output showing 0 failures |
| New tests were added for new functionality | List of new test files/functions |
| New tests actually test the right thing | Each test has a meaningful assertion |
| Edge cases are covered | Tests for null, empty, boundary, error conditions |
| No tests were skipped or disabled | Grep for `@skip`, `xit`, `test.skip`, `pytest.mark.skip` |

**Failure mode this prevents**: "I wrote the tests" (but never ran them, and they actually fail).

### 2. Code Actually Runs

**Not just compiles -- actually executes the intended behavior.**

```bash
# Build the project
npm run build 2>&1 | tail -10
# or
cargo build 2>&1 | tail -10
# or
python -c "from module import function; print(function('test'))"
```

| Check | Evidence Required |
|-------|------------------|
| Code compiles without errors | Build output showing success |
| Code runs without runtime errors | Execution output or log |
| Feature works as intended | Manual test output or screenshot |
| No new warnings introduced | Build output with zero new warnings |

**Failure mode this prevents**: "It compiles" (but crashes at runtime with an import error).

### 3. Issue Actually Fixed

**For bug fixes only: the original bug is no longer reproducible.**

| Check | Evidence Required |
|-------|------------------|
| Bug was reproduced before the fix | Description of reproduction steps and observed failure |
| Bug no longer reproduces after the fix | Same reproduction steps showing correct behavior |
| Regression test added | Test that would fail if the bug returned |
| Related edge cases checked | Similar inputs tested to verify no adjacent bugs |

**Failure mode this prevents**: "I fixed the function" (but tested with different inputs than the ones that triggered the bug).

### 4. Build Actually Succeeds

**Full build pipeline, not just the code you changed.**

```bash
# Full build
npm run build && npm run lint && npm run typecheck
# or
make all
# or
cargo build && cargo clippy && cargo fmt --check
```

| Check | Evidence Required |
|-------|------------------|
| Full build succeeds | Build command output with exit code 0 |
| Linting passes | Linter output with zero errors |
| Type checking passes | Type checker output with zero errors |
| No new deprecation warnings | Diff of warnings before/after |

**Failure mode this prevents**: "My file works" (but it broke the import chain in another module).

### 5. Reviews Actually Addressed

**For PR reviews: all comments are resolved with real changes, not just dismissed.**

| Check | Evidence Required |
|-------|------------------|
| All review comments have responses | Comment thread status |
| Requested changes are implemented | Diff showing the changes |
| Reviewer's concern is addressed (not just acknowledged) | Explanation of how the concern was resolved |
| No comments marked "resolved" without actual changes | Audit of resolved vs changed |

**Failure mode this prevents**: "All comments addressed" (but half were just marked as resolved without changes).

## Workflow

### Step 1: Collect Checklist Items

Determine which checks apply:

| Situation | Checks to Run |
|-----------|--------------|
| New feature | 1, 2, 4 |
| Bug fix | 1, 2, 3, 4 |
| Refactoring | 1, 2, 4 |
| Pull request | 1, 2, 4, 5 |
| Pre-deployment | 1, 2, 3, 4, 5 |

### Step 2: Execute Each Check

Run each applicable check and collect evidence:

```bash
# 1. Tests pass
TEST_OUTPUT=$(pytest --tb=short -q 2>&1)
echo "$TEST_OUTPUT" | tail -5

# 2. Code runs
BUILD_OUTPUT=$(npm run build 2>&1)
echo "$BUILD_OUTPUT" | tail -5

# 4. Full build
LINT_OUTPUT=$(npm run lint 2>&1)
echo "$LINT_OUTPUT" | tail -5
```

### Step 3: Generate Verification Report

```markdown
## Verification Report

### Task: [Task name/description]
### Date: [YYYY-MM-DD]
### Status: [PASS / FAIL]

### Checklist Results

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Tests actually pass | PASS | 47 tests passed, 0 failed, 0 skipped |
| 2 | Code actually runs | PASS | Build succeeded, feature manually verified |
| 3 | Issue actually fixed | N/A | Not a bug fix |
| 4 | Build actually succeeds | PASS | Build + lint + typecheck all clean |
| 5 | Reviews addressed | N/A | No PR review |

### New Tests Added
- `test_user_creation_with_valid_data`
- `test_user_creation_rejects_empty_name`
- `test_user_creation_hashes_password`

### Notes
[Any additional observations or caveats]

### Verdict: READY FOR COMPLETION
```

### Step 4: Decision Gate

| Result | Action |
|--------|--------|
| All checks PASS | Mark task as completed |
| Any check FAIL | Fix the failure, re-run the failed check, do NOT mark complete |
| Check cannot be run | Document why and get explicit approval to skip |

**Critical rule**: NEVER mark a task as completed if any check fails. Fix first, verify again, then complete.

## Hook Integration

### Stop Hook: Automatic Verification

When the Stop hook fires (session ending or task completion):

1. Detect if there are in-progress tasks
2. For each in-progress task, run applicable checks
3. If any check fails, inject a warning message:
   ```
   WARNING: Verification failed before completion.
   - Tests: [PASS/FAIL]
   - Build: [PASS/FAIL]
   - Details: [failure information]

   Please fix the failures before marking this task as complete.
   ```
4. Only allow task completion if all checks pass

### PreToolUse Hook: Premature Completion Guard

When TaskUpdate is called with `status: completed`:
- Check that verification was run in this session
- If not, warn: "Task marked complete without verification. Run /verify first."

## Quick Verification (For Small Tasks)

For atomic tasks (< 5 minutes), a condensed verification is acceptable:

```bash
# Quick verify: tests pass + code builds
pytest --tb=line -q && npm run build 2>&1 | tail -3
# If both succeed: task is verified
```

## Examples

### Example 1: Feature Complete Verification

Task: "Add user profile endpoint"

```
Verification Report:
1. Tests: PASS (12 new tests, all passing, 0 skipped)
2. Runs: PASS (curl localhost:3000/api/profile returns 200 with correct data)
3. Fixed: N/A
4. Build: PASS (tsc --noEmit clean, eslint clean)
5. Reviews: N/A

Verdict: READY FOR COMPLETION
```

### Example 2: Bug Fix Verification

Task: "Fix date parsing for single-digit months"

```
Verification Report:
1. Tests: PASS (2 new regression tests + 45 existing, all passing)
2. Runs: PASS (parse_date("2024-1-15") returns correct datetime)
3. Fixed: PASS
   - Reproduced: parse_date("2024-1-15") raised ValueError before fix
   - Verified: parse_date("2024-1-15") returns datetime(2024, 1, 15) after fix
   - Edge cases: Also tested "2024-1-1", "2024-12-1", "2024-1-31"
4. Build: PASS (pytest + mypy + ruff all clean)
5. Reviews: N/A

Verdict: READY FOR COMPLETION
```

### Example 3: Failed Verification

Task: "Refactor authentication module"

```
Verification Report:
1. Tests: FAIL -- 3 tests failing in test_auth_middleware.py
   - test_expired_token_returns_401: AssertionError (returns 500)
   - test_missing_header_returns_401: AssertionError (returns 500)
   - test_invalid_token_format: KeyError in jwt.decode
2. Runs: FAIL -- Server crashes on invalid auth tokens
3. Fixed: N/A
4. Build: PASS (compiles clean)
5. Reviews: N/A

Verdict: NOT READY -- Fix test failures before completion
Action: Debug error handling in auth middleware, re-run verification
```

## Anti-Patterns

### What to Avoid

1. **Verification theater** -- Running checks but ignoring failures. Every failure must be addressed.

2. **Partial verification** -- Only running the tests you wrote, not the full suite. Regressions hide in other tests.

3. **Mental verification** -- "I think it works" without actually running the code. Trust evidence, not intuition.

4. **Skipping checks for "small" changes** -- Small changes can cause big failures. At minimum, run tests and build.

5. **Verifying only the happy path** -- If you only test the normal case, edge cases and error paths remain unverified.

6. **Marking complete then verifying** -- Verify FIRST, complete SECOND. Never reverse this order.

7. **Optimistic test interpretation** -- "3 tests failed but they're probably flaky" is not verification. Investigate every failure.

## Integration with Other Skills

- **TDD Workflow**: TDD naturally provides test verification; this skill adds build and runtime checks
- **Task Decomposition**: Add verification as the final task in every decomposition
- **Downstream Correction**: If verification reveals the approach is fundamentally wrong, trigger a correction
- **Feasibility Analysis**: Post-implementation verification can validate or invalidate feasibility assumptions
