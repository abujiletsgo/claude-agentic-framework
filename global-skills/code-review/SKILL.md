---
name: Code Review
version: 0.1.0
description: "This skill should be used when the user asks for a code review, quality check, or PR review. It performs thorough code reviews checking for bugs, security issues, performance problems, and style violations."
---

# Code Review Skill

Systematic code review following industry best practices. Checks for correctness, security, performance, maintainability, and style.

## When to Use

- User asks: "review this code", "check this PR", "code review", "quality check"
- Before merging significant changes
- When debugging complex issues
- After major refactoring

## Workflow

### Step 1: Scope Assessment
Identify all files changed:
```bash
# For git changes
git diff --name-only HEAD~1
# Or for PR
git diff --name-only main...HEAD
```

### Step 2: Review Checklist

For each file, check:

**Correctness**
- Logic errors
- Edge cases (null, empty, boundary values)
- Error handling (missing try/catch, unhandled promises)
- Race conditions (concurrent access)
- Resource leaks (unclosed files, connections)

**Security**
- Input validation (SQL injection, XSS, path traversal)
- Authentication/authorization gaps
- Secrets in code (API keys, passwords)
- Unsafe deserialization
- Insecure random number generation

**Performance**
- N+1 queries
- Unbounded collections
- Missing indexes
- Unnecessary re-renders
- Memory leaks
- Synchronous I/O in async contexts

**Maintainability**
- Function length (>50 lines = warning)
- Cyclomatic complexity (>10 = warning)
- Magic numbers/strings
- Code duplication
- Missing documentation for public APIs
- Unclear naming

**Style**
- Consistent formatting
- Language-specific conventions (PEP 8, ESLint rules)
- Import organization
- Comment quality (why, not what)

### Step 3: Generate Review Report

Format findings as:

```markdown
## Code Review Report

### Summary
- Files reviewed: N
- Issues found: N (X critical, Y warnings, Z suggestions)

### Critical Issues
1. **[File:Line]** Description of issue
   - Impact: What could go wrong
   - Fix: Suggested correction

### Warnings
1. **[File:Line]** Description
   - Suggestion: How to improve

### Suggestions
1. **[File:Line]** Nice-to-have improvement

### Positive Observations
- Things done well worth noting
```

## Examples

### Example 1: Review a Single File
User: "Review api/routes.py for issues"

1. Read the file
2. Apply all checklist items
3. Report findings with specific line references

### Example 2: Review a Git Diff
User: "Review my last commit"

1. Run `git diff HEAD~1` to see changes
2. Focus review on changed lines (context-aware)
3. Report issues in changed code specifically
