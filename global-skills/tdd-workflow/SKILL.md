---
name: TDD Workflow
version: 0.1.0
description: "This skill should be used when the user asks for TDD, test-first development, or when implementing features where correctness is critical. It enforces Test-Driven Development (RED-GREEN-REFACTOR) discipline and prevents writing production code before tests exist."
---

# TDD Workflow Skill

Enforce strict RED-GREEN-REFACTOR test-driven development cycles. Every feature starts with a failing test, gets minimal implementation to pass, then gets refactored. No production code is written without a corresponding test first.

## When to Use

- User asks: "use TDD", "test-first", "RED-GREEN-REFACTOR", "write tests first"
- Implementing critical business logic where correctness matters
- Building functions with well-defined inputs and outputs
- When the user wants disciplined, incremental development
- Fixing bugs (write a test that reproduces the bug first)

## Workflow

### Phase 1: RED -- Write a Failing Test

**Goal**: Define the desired behavior before writing any implementation.

1. **Identify the behavior** to implement (one small unit at a time)
2. **Write a test** that describes the expected behavior
3. **Run the test** and confirm it FAILS

```bash
# Run the specific test file to confirm failure
# Python
pytest path/to/test_file.py -v --tb=short 2>&1 | tail -20

# JavaScript/TypeScript
npx jest path/to/test.spec.ts --verbose 2>&1 | tail -20

# Go
go test ./path/to/... -run TestFunctionName -v 2>&1 | tail -20
```

**Critical Rule**: If the test passes immediately, either:
- The behavior already exists (skip to next behavior)
- The test is wrong (fix the test so it actually tests new behavior)

**What makes a good RED test**:
- Tests ONE specific behavior
- Has a descriptive name explaining what it verifies
- Uses the AAA pattern (Arrange, Act, Assert)
- Fails for the RIGHT reason (not a syntax error or import error)

### Phase 2: GREEN -- Write Minimal Code to Pass

**Goal**: Make the failing test pass with the simplest possible implementation.

1. **Write only enough code** to make the test pass
2. **Do not optimize** or generalize yet
3. **Run the test** and confirm it PASSES
4. **Run the full test suite** to ensure no regressions

```bash
# Run the specific test
pytest path/to/test_file.py -v --tb=short

# Then run the full suite
pytest --tb=short -q
```

**Rules for GREEN phase**:
- Write the MINIMUM code needed -- no more
- Hard-coded values are acceptable if they make the test pass
- Do not add error handling unless a test requires it
- Do not add features the test does not verify
- If you feel tempted to write more, write another test first (go back to RED)

### Phase 3: REFACTOR -- Clean Up While Green

**Goal**: Improve code quality without changing behavior.

1. **Identify code smells**: duplication, magic numbers, unclear naming, long functions
2. **Refactor in small steps** (one change at a time)
3. **Run tests after each change** to confirm nothing broke
4. **Apply DRY, SOLID, and clean code** principles

```bash
# After each refactoring step, verify tests still pass
pytest path/to/test_file.py -v --tb=short
```

**What to refactor**:
- Extract duplicated code into helper functions
- Rename variables and functions for clarity
- Simplify conditional logic
- Extract magic numbers into named constants
- Improve function signatures
- Add type annotations if missing

**What NOT to do in REFACTOR**:
- Add new features (that requires a new RED phase)
- Change test assertions
- Skip running tests between changes

### Phase 4: COMMIT -- Lock in the Cycle

After completing a full RED-GREEN-REFACTOR cycle:

1. Stage the test file and implementation file
2. Commit with a descriptive message referencing the TDD cycle

```bash
git add path/to/test_file.py path/to/implementation.py
git commit -m "feat: add [behavior] (TDD cycle)

- RED: test_[behavior_name] added
- GREEN: [brief implementation description]
- REFACTOR: [what was cleaned up, if anything]"
```

3. Repeat from Phase 1 for the next behavior

## Hook Integration

### PreToolUse Hook: Test-Before-Code Guard

When TDD mode is active, before writing to a non-test file, verify:
- A corresponding test file exists
- The test file was modified MORE RECENTLY than the implementation file
- If not, warn: "TDD violation: write or update the test first"

**Detection heuristic**: If the Write/Edit target path does NOT contain `test_`, `.test.`, `.spec.`, or reside in a `tests/` or `__tests__/` directory, check that a corresponding test file exists and has been recently modified in this session.

### Stop Hook: Test Verification

Before completing any TDD session:
1. Run the full test suite
2. Verify all tests pass (zero failures)
3. Check that new tests were actually written (not just implementation)
4. Report test count delta (tests added in this session)

## Cycle Size Guidelines

Each TDD cycle should be small enough to complete in 2-10 minutes:

| Cycle Size | Example | Tests Per Cycle |
|-----------|---------|----------------|
| **Nano** | Return a constant, validate one input | 1 |
| **Micro** | Implement a pure function, handle one edge case | 1-2 |
| **Small** | Implement a method with branching logic | 2-3 |
| **Medium** | Implement a class with multiple methods | 3-5 (split into multiple cycles) |

If a cycle feels too large, split it into smaller behaviors.

## Examples

### Example 1: TDD for a Utility Function

**RED**: Write failing test
```python
# test_validator.py
def test_validate_email_accepts_valid_email():
    assert validate_email("user@example.com") is True

def test_validate_email_rejects_missing_at():
    assert validate_email("userexample.com") is False
```

Run: both tests fail (validate_email does not exist).

**GREEN**: Minimal implementation
```python
# validator.py
import re

def validate_email(email: str) -> bool:
    return "@" in email
```

Run: first test passes, second test passes. Both green.

**REFACTOR**: Improve the implementation
```python
# validator.py
import re

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

def validate_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.match(email))
```

Run: all tests still pass. Commit.

### Example 2: TDD for Bug Fix

**Step 1**: Write a test that reproduces the bug
```python
def test_parse_date_handles_single_digit_month():
    # Bug: parse_date("2024-1-15") raises ValueError
    result = parse_date("2024-1-15")
    assert result.month == 1
    assert result.day == 15
```

**Step 2**: Confirm the test fails (reproduces the bug)

**Step 3**: Fix the bug with minimal code change

**Step 4**: Confirm the test passes AND all existing tests still pass

**Step 5**: Commit: `fix: handle single-digit months in parse_date (TDD)`

### Example 3: TDD Cycle Log

Track progress across multiple cycles:

```
Cycle 1: RED test_create_user_with_valid_data -> GREEN (User model) -> REFACTOR (extract validation)
Cycle 2: RED test_create_user_rejects_empty_name -> GREEN (add name check) -> REFACTOR (none needed)
Cycle 3: RED test_create_user_rejects_duplicate_email -> GREEN (add uniqueness) -> REFACTOR (extract db query)
Cycle 4: RED test_create_user_hashes_password -> GREEN (add bcrypt) -> REFACTOR (extract hasher)
```

## Anti-Patterns

### What to Avoid

1. **Writing implementation first, then tests** -- This is backward. Tests become rubber-stamp confirmations instead of specifications. The test does not drive the design.

2. **Writing too many tests at once** -- Write ONE test, make it pass, then write the next. Multiple failing tests create confusion about what needs to be implemented.

3. **Gold-plating in GREEN phase** -- Do not add error handling, logging, or features that no test requires. If you want it, write a test for it first.

4. **Skipping REFACTOR** -- Technical debt accumulates if you never clean up. After each GREEN, ask: "Is this code clear and simple?"

5. **Huge cycles** -- If a single RED-GREEN cycle takes more than 10 minutes, the step is too large. Break it down.

6. **Testing implementation details** -- Test behavior (what), not implementation (how). Tests that break when you refactor internals are brittle.

7. **Ignoring test failures during REFACTOR** -- Every refactoring step must leave all tests green. If a test breaks, undo the refactoring step and try a smaller change.

## Integration with Other Skills

- **Task Decomposition**: Break features into TDD-sized cycles before starting
- **Verification Checklist**: TDD naturally satisfies "tests actually pass" and "code actually runs"
- **Code Review**: TDD code tends to be more modular and testable, making reviews easier
