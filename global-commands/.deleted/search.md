---
description: Delegate heavy codebase searches to sub-agents
---

# Search & Report

**Purpose:** Offload expensive codebase searches to sub-agents. Find patterns, implementations, or references without bloating primary context.

## When to Use

✅ Use `/search` when:
- Looking for pattern across many files
- Finding all usages of a function/class
- Searching for similar implementations
- Need exhaustive search results

❌ Don't use when:
- Simple grep in 1-2 files (use Grep tool directly)
- Already know exact file location

## Usage Pattern

```
/search "Find all API endpoints that use authentication"
/search "Where is the database connection configured"
/search "Find all files that import React hooks"
```

## Delegation Strategy

Spawn Explore sub-agent with focused search instructions:

```
Task tool (subagent_type="Explore"):
"Search the codebase for [pattern]. Use Grep to find matches, then Read relevant files to understand context. Report findings in structured format with file references."
```

## Report Format Expected

```markdown
### Search Results: [Query]

**Matches Found**: [count]

**Key Locations**:
1. [file:line] - [brief description]
2. [file:line] - [brief description]

**Patterns Identified**:
- [Common pattern across results]

**Notable Files**:
- [file] - [why it's important]
```

## Token Efficiency

- Sub-agent searches: 20k+ tokens (in isolation)
- Report back: 1-2k tokens
- Primary context: Clean ✅
