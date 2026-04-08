# /test - Run or Generate Tests

Run existing tests or generate new test suites for uncovered code.

## Usage
```
/test                        # Run all tests in the project
/test "src/module.py"        # Run tests for a specific module
/test --generate "module.py" # Generate tests for a module
/test --coverage             # Run with coverage report
```

## Implementation

When the user runs `/test`:

1. **Detect test framework**:
   - Look for `pytest.ini`, `pyproject.toml [tool.pytest]`, `setup.cfg` -> pytest
   - Look for `jest.config.*`, `package.json.jest` -> jest
   - Look for `vitest.config.*` -> vitest
   - Look for `Cargo.toml` -> cargo test
   - Look for `go.mod` -> go test
   - Fallback: ask user

2. **Find tests**:
   - If argument given: find matching test file (`test_<module>.py` or `<module>.test.ts`)
   - If no argument: run full test suite

3. **Run tests**:
   ```bash
   # Python
   uv run pytest <path> -v --tb=short

   # JavaScript/TypeScript
   npx jest <path> --verbose
   # or: npx vitest run <path>

   # Rust
   cargo test <path>

   # Go
   go test ./... -v
   ```

4. **Report results**:
   - Show pass/fail count
   - Show failed test details with file:line references
   - If `--coverage`: show coverage percentage per file

5. **If `--generate`**:
   - Read the source module
   - Identify all public functions/methods/classes
   - Generate test file with one test per public function
   - Use appropriate assertions and edge cases
   - Save to the conventional test location

## Notes
- Always use `uv run` for Python test execution
- Generated tests are starting points -- they need manual refinement
- Use the `test-generator` skill for more sophisticated test generation
