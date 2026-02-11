---
name: Error Analyzer
version: 0.1.0
description: "This skill should be used when the user encounters an error, exception, crash, stack trace, or needs help debugging failures. It analyzes errors, stack traces, and exceptions to identify root causes and suggest fixes."
---

# Error Analyzer Skill

Systematic error analysis: parse stack traces, identify root causes, correlate with known patterns, and suggest targeted fixes.

## When to Use

- User pastes a stack trace or error message
- Build/compile failures
- Runtime exceptions or crashes
- Test failures with unclear causes
- Hook or script errors in the Claude Code framework

## Workflow

### Step 1: Classify the Error

Determine the error category:

| Category | Indicators | Priority |
|----------|-----------|----------|
| **Syntax** | SyntaxError, parse error, unexpected token | High (quick fix) |
| **Type** | TypeError, type mismatch, undefined is not | High |
| **Runtime** | NullPointerException, segfault, SIGABRT | Critical |
| **Import/Module** | ModuleNotFoundError, Cannot find module | Medium |
| **Network** | ECONNREFUSED, timeout, 404/500 | Medium |
| **Permission** | EACCES, PermissionError, 403 | Medium |
| **Configuration** | Missing env var, invalid config, YAML parse | Medium |
| **Resource** | OOM, disk full, too many open files | Critical |

### Step 2: Parse the Stack Trace

Extract key information:
1. **Error type and message** (the actual exception)
2. **Origin frame** (where the error was thrown)
3. **Call chain** (how execution reached the error point)
4. **Context variables** (any values shown in the trace)
5. **File and line numbers** (for targeted investigation)

### Step 3: Investigate Root Cause

Read the file at the error location using the Read tool with the file path and line number from the stack trace. Use Grep to search for similar patterns or usages. Check recent git changes that might have caused the issue.

### Step 4: Correlate with Known Patterns

Check the knowledge database for previously seen errors:
```bash
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py search "<error-type>" --category error
```

### Step 5: Generate Analysis Report

Format as:
```markdown
## Error Analysis

### Error
- **Type**: [ErrorType]
- **Message**: [error message]
- **Location**: [file:line]

### Root Cause
[Clear explanation of why this error occurred]

### Fix
[Specific code change or configuration fix needed]

### Prevention
[How to prevent this error from recurring]
```

### Step 6: Store for Future Reference

If this is a novel error pattern, store it in the knowledge database:
```bash
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py store \
  --category error \
  --title "<ErrorType>: <brief description>" \
  --content "<root cause and fix>" \
  --tags "<language>,<framework>,<error-type>"
```

## Common Error Patterns

### Python
- `ModuleNotFoundError`: Check virtualenv activation, pip install
- `AttributeError: NoneType`: Trace back None propagation
- `KeyError`: Check dict key existence, use `.get()` with default
- `IndentationError`: Mixed tabs/spaces, copy-paste issues

### JavaScript/TypeScript
- `TypeError: Cannot read properties of undefined`: Optional chaining missing
- `ReferenceError`: Variable scoping, hoisting, import issues
- `SyntaxError: Unexpected token`: JSON parse failure, template literal issues
- `ENOENT`: File path issues, missing build artifacts

### Shell/Hooks
- Exit code 2: Hook blocked the operation (check patterns.yaml)
- `uv run` failures: Missing pyproject.toml, dependency issues
- JSON parse errors: Invalid stdin to hook scripts
- Permission denied: Missing chmod +x on scripts

## Examples

### Example 1: Python Stack Trace
User pastes a KeyError traceback at main.py:42.

1. Read main.py around line 42 for context
2. Identify the missing key in the dict access
3. Suggest safe access with `.get()` or existence check
4. Store the pattern in knowledge DB if novel

### Example 2: Node.js TypeError
User sees "Cannot read properties of null (reading 'map')" in UserList.tsx:15.

1. Read the component file
2. Identify that data is null before async load completes
3. Suggest optional chaining or loading state guard
4. Check if similar issues exist elsewhere with Grep
