---
name: health
description: "Check CAF system health — git status, MCP servers, hooks"
user-invocable: true
---

# /health — CAF System Health Check

Run a point-in-time diagnostic of the CAF framework and report results as a markdown table.

## What Gets Checked

| Component | Check |
|-----------|-------|
| **git** | `git status --porcelain` — clean working tree vs. dirty file count |
| **hooks** | All file paths referenced in `~/.claude/settings.json` hooks section exist |
| **MCP servers** | All `mcpServers` keys present in `~/.claude/settings.json` |

## When to Use

- Before starting a sprint or complex task — confirm environment is healthy
- After framework changes — verify hooks and MCP config are intact
- Debugging unexplained agent failures — rule out infra issues first

## Workflow

### Step 1 — Spawn health-checker

Spawn the `health-checker` agent to run all checks and format the results:

```python
Agent(
    name="health-checker",
    subagent_type="health-checker",
    prompt="Run all CAF health checks from the project root at $(pwd). Output a markdown table."
)
```

### Step 2 — Present results

Print the markdown table returned by health-checker verbatim. No interpretation or diagnosis — raw results only.

## Expected Output

```markdown
| Component | Status | Latency | Notes |
|-----------|--------|---------|-------|
| git        | ✓ clean | N/A | 0 dirty files |
| hooks      | ✓ 45/45 present | N/A | |
| MCP servers | ✓ configured | N/A | officecli, papers, github, papersflow, sourcegraph |
```

If any component is unhealthy, that row shows ✗ with a brief error note. Other rows are unaffected.
