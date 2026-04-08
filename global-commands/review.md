# /review - Code Review

Run automated code review on the working tree or specific files.

## Usage
```
/review                     # Review all changed files
/review "src/module.py"     # Review a specific file
/review --staged            # Review only staged changes
/review --analyzer security # Run only the security analyzer
```

## Implementation

When the user runs `/review`:

1. **Determine scope**:
   - If no argument: review all files changed since last commit (`git diff --name-only HEAD`)
   - If file path given: review that specific file
   - If `--staged`: review only staged files (`git diff --cached --name-only`)

2. **Run analyzers** on each file:
   - **Complexity**: Functions with cyclomatic complexity > 10, deeply nested code
   - **Security**: Hardcoded secrets, SQL injection, command injection, path traversal
   - **Duplication**: Copy-paste blocks > 6 lines with > 80% similarity
   - **Dead code**: Unused imports, unreachable code, empty except blocks
   - **Architecture**: God classes (> 500 lines), circular imports, missing error handling

3. **Report findings** grouped by severity:
   ```
   CRITICAL  Hardcoded API key in config.py:42
   ERROR     Cyclomatic complexity 18 in process_data() - pipeline.py:89
   WARNING   Unused import os - utils.py:3
   INFO      Missing docstring - api.py:15
   ```

4. **Save findings** to `~/.claude/review_findings.json` for `/refine` to consume

5. **Suggest next steps**:
   - If critical/error findings: "Run `/refine` to auto-fix these issues"
   - If only warnings/info: "All clear for commit. Run `/commit` when ready."

## Analyzer Details

The review system uses analyzers in `global-hooks/framework/review/analyzers/`:
- `complexity.py` - Cyclomatic complexity and nesting depth
- `dead_code.py` - Unused imports, functions, variables
- `duplication.py` - Copy-paste detection
- `architecture.py` - Structural anti-patterns
- `test_coverage.py` - Missing test files for source modules

## Notes
- Review is read-only; it never modifies files
- Use `/refine` after `/review` to auto-fix findings
- Findings persist across sessions in the findings store
