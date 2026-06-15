---
name: test-generator
version: 0.1.0
description: "This skill should be used when the user asks for tests, test generation, test coverage, TDD, or writing unit/integration/e2e tests. It generates comprehensive test suites for any codebase."
---

# Test Generator Skill

Generate thorough test suites following testing best practices. Supports unit, integration, and end-to-end testing patterns.

## When to Use

- User asks: "write tests", "generate tests", "add test coverage", "TDD"
- After implementing a new feature
- When test coverage is low
- Before refactoring (safety net)

## Workflow

### Detect Testing Framework
```bash
# Check for existing test configuration
find . -maxdepth 3 -name "*.test.*" -o -name "*.spec.*" -o -name "test_*.py" -o -name "*_test.go" | head -5
# Check package.json or pyproject.toml for test runner
```

### Analyze Code Under Test

For each function/class to test:
1. Identify inputs, outputs, and side effects
2. Map happy paths and edge cases
3. Find dependencies to mock
4. Determine test boundaries (unit vs integration)

### Generate Tests

**Unit Test Pattern (AAA)**:
```
Arrange: Set up test data and mocks
Act: Call the function under test
Assert: Verify the expected outcome
```

**Test Categories to Generate**:
1. **Happy path**: Normal expected behavior
2. **Edge cases**: Empty inputs, nulls, boundaries, max values
3. **Error cases**: Invalid inputs, network failures, timeouts
4. **State transitions**: Before/after state changes
5. **Concurrency**: Race conditions (if applicable)

See [references/test-patterns.md](references/test-patterns.md) for ready-to-adapt pytest/Jest/Go test scaffolds.

### Apply Quality Checklist

- Each test has a descriptive name explaining what it tests
- Tests are independent (no shared mutable state)
- Tests are deterministic (no flaky tests)
- Assertions are specific (not just "no error")
- Mocks are minimal (only mock external dependencies)
- Tests follow project conventions

## TDD Mode

When user asks for TDD:
1. Write failing test FIRST
2. Implement minimum code to pass
3. Refactor while tests stay green
4. Repeat

## Examples

### Example 1: Generate Tests for a Module
User: "Generate tests for src/auth.py"

1. Read src/auth.py to understand functions
2. Identify test-worthy functions
3. Generate test file test_auth.py with comprehensive tests
4. Run tests to verify they pass

### Example 2: Add Missing Coverage
User: "Increase test coverage for the API routes"

1. Run coverage report to identify gaps
2. Generate tests for uncovered paths
3. Focus on error handling and edge cases
