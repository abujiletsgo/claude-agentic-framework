# /refine - Auto-fix Review Findings

Apply continuous review findings and iterate until passing.

## Usage
```
/refine                    # Fix all open findings for latest commit
/refine --commit <hash>    # Fix findings for a specific commit
/refine --analyzer <name>  # Only fix findings from one analyzer
/refine --max-iterations 3 # Limit fix iterations (default: 5)
```

## Workflow

1. **Read findings** from `~/.claude/review_findings.json`
2. **Group by file** and prioritize by severity (critical > error > warning > info)
3. **For each finding**:
   - Read the affected file and understand the issue
   - Apply the suggested fix
   - Mark the finding as resolved
4. **Re-run review** on the working tree to check for new issues
5. **Repeat** until all findings are resolved or max iterations reached
6. **Commit** all fixes with a descriptive message

## Finding Types

| Analyzer | What it finds | How to fix |
|----------|--------------|------------|
| duplication | Copy-paste code blocks | Extract shared functions |
| complexity | Functions with high cyclomatic complexity | Split into smaller functions, use early returns |
| dead_code | Unused imports, functions, classes | Remove or add to __all__ |
| architecture | Security anti-patterns, god modules, debt markers | Restructure, use proper patterns |
| test_coverage | Missing test files or uncovered definitions | Add tests |

## Implementation

When the user runs `/refine`:

1. Read `~/.claude/review_findings.json`
2. Filter to open/notified findings (not resolved/wontfix)
3. If `--commit` specified, filter to that commit only
4. If `--analyzer` specified, filter to that analyzer only
5. Sort by severity (critical first)
6. For each finding:
   - Read the file at `finding.file_path`
   - Understand the issue from `finding.description` and `finding.suggestion`
   - Make the minimal fix needed
   - Update `finding.status` to "resolved" in the findings store
7. After fixing all findings, run the review again:
   ```bash
   uv run ~/Documents/claude-agentic-framework/global-hooks/framework/review/post_commit_review.py --foreground
   ```
8. If new findings appear, repeat (up to max iterations)
9. Stage and commit all changes:
   ```
   git add -A && git commit -m "refine: auto-fix review findings

   Resolved findings:
   - [list of resolved finding titles]

   Co-Authored-By: Claude Code <noreply@anthropic.com>"
   ```

## Example

```
> /refine

Reading review findings...
Found 4 unresolved findings:
  [ERROR] Code duplication detected (85% similar) - src/utils.py
  [WARN]  High complexity in process_data() (score: 15) - src/pipeline.py
  [INFO]  Unused import: requests - src/api.py
  [INFO]  No test file for utils.py

Fixing finding 1/4: Code duplication in src/utils.py...
  Extracted shared function `validate_input()` to src/common.py
  Updated both call sites

Fixing finding 2/4: High complexity in process_data()...
  Split into 3 helper functions: _parse_input, _transform, _validate_output
  Complexity reduced from 15 to 4

Fixing finding 3/4: Unused import in src/api.py...
  Removed unused `import requests`

Fixing finding 4/4: Missing tests for utils.py...
  Created tests/test_utils.py with 5 test cases

Re-running review... 0 new findings.

All findings resolved. Committing fixes.
```

## Notes

- The `/refine` command never introduces breaking changes intentionally
- Dead code removal is conservative (only removes what is clearly unused)
- Complexity fixes preserve existing behavior through refactoring only
- Test generation creates skeleton tests that may need manual refinement
- Always review the commit after `/refine` completes
