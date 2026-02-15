# /debug - Diagnose and Fix Errors

Analyze errors, trace root causes, and apply fixes.

## Usage
```
/debug                       # Analyze the last error in terminal
/debug "error message"       # Diagnose a specific error
/debug "file.py:42"          # Debug a specific location
/debug --trace               # Full stack trace analysis
```

## Implementation

When the user runs `/debug`:

1. **Gather error context**:
   - If no argument: look at the last command output for error messages
   - If error message given: use it directly
   - If file:line given: read that location and surrounding context

2. **Classify the error**:
   - **Syntax**: Missing brackets, invalid tokens, indentation
   - **Import**: Module not found, circular import, wrong path
   - **Runtime**: TypeError, ValueError, AttributeError, NoneType
   - **Environment**: Missing dependency, wrong Python version, path issues
   - **Logic**: Wrong output, off-by-one, race condition

3. **Trace root cause**:
   - Read the stack trace bottom-up
   - Identify the originating file and line
   - Read surrounding code (50 lines context)
   - Check for common patterns matching the error type

4. **Propose fix**:
   - Show the root cause explanation
   - Show the proposed code change
   - Ask for confirmation before applying

5. **Apply and verify**:
   - Make the minimal fix
   - Re-run the failing command to verify
   - If still failing, iterate (max 3 attempts)

## Error Analysis Patterns

| Error Type | Common Causes | Fix Strategy |
|-----------|--------------|-------------|
| ImportError | Missing package, wrong path | `uv add <pkg>` or fix import path |
| TypeError | Wrong arg count, None passed | Add type checks, fix call site |
| FileNotFoundError | Wrong path, missing file | Verify path, create if needed |
| KeyError | Missing dict key | Add `.get()` with default |
| PermissionError | File permissions, sandbox | Check permissions, use allowed paths |

## Notes
- Uses the `error-analyzer` skill for deep analysis when available
- Never applies fixes without showing them first
- Keeps a log of errors and fixes for the knowledge pipeline
