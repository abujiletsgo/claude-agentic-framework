---
name: health
description: "Check CAF framework infrastructure health: git cleanliness, hook wiring in settings.json, and MCP server registration. Triggers: 'check my hooks', 'are CAF hooks working', 'MCP server status', 'CAF infra health', '/health'."
when_to_use: "Use specifically for CAF framework/infra diagnostics (hooks, MCP, git state). For code-quality health — typecheck, lint, tests, dead-code score — that is the gstack health skill; this skill does not run those."
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

Run these checks directly (Bash + Read) — no dedicated agent needed for a check this mechanical.

### Step 1 — Git status

```bash
git status --porcelain
```
- Empty output → Status: `✓ clean`, Notes: `0 dirty files`
- Non-empty → Status: `✗ dirty`, Notes: `N dirty files` (count the lines)

### Step 2 — Hooks

Read `~/.claude/settings.json`. Extract every value in the `hooks` section that looks like a file path (starts with `/` or contains `/`). For each path:

```bash
test -f "/path/to/file" && echo EXISTS || echo MISSING
```
- All exist → Status: `✓ N/N present`, Notes: (empty)
- Any missing → Status: `✗ N/M present`, Notes: list missing file names (basename only)

### Step 3 — MCP servers

Read `~/.claude/settings.json`. Extract all keys from the `mcpServers` object; report them as a comma-separated list in Notes. Note: `context7` is registered as a plugin under `enabledPlugins`, not `mcpServers` — if present there, include it in Notes labeled `(plugin)`.

### Step 4 — Format and present results

Produce the table below and print it — no interpretation or diagnosis, raw results only:

```markdown
| Component | Status | Latency | Notes |
|-----------|--------|---------|-------|
| git | ✓ clean | N/A | 0 dirty files |
| hooks | ✓ 45/45 present | N/A | |
| MCP servers | ✓ configured | N/A | officecli, papers, github, papersflow, sourcegraph |
```

If reading `~/.claude/settings.json` fails, mark the hooks and MCP servers rows `✗ cannot read settings.json`. Never abort early — all three rows must always appear.

## Expected Output

```markdown
| Component | Status | Latency | Notes |
|-----------|--------|---------|-------|
| git        | ✓ clean | N/A | 0 dirty files |
| hooks      | ✓ 45/45 present | N/A | |
| MCP servers | ✓ configured | N/A | officecli, papers, github, papersflow, sourcegraph |
```

If any component is unhealthy, that row shows ✗ with a brief error note. Other rows are unaffected.
