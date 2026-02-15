---
description: List all git worktrees with their configuration, ports, and status
allowed-tools: Bash, Read, Glob, Grep
---

# List Worktrees

Show all git worktrees for the current repository with comprehensive status information.

## Workflow

### 1. Get Project Info

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel)
PROJECT_NAME=$(basename "$PROJECT_ROOT")
CURRENT_BRANCH=$(git branch --show-current)
```

### 2. List All Worktrees

```bash
git worktree list
```

Parse each line to extract:
- Path
- Commit hash
- Branch name

### 3. Gather Details for Each Worktree

For each worktree path:

**Configuration:**
- Check if `.claude/settings.json` exists (isolated config)
- Check if `.env` exists at root
- If `apps/server/.env` exists, read SERVER_PORT
- If `apps/client/.env` exists, read CLIENT_PORT (VITE_PORT)

**Service Status:**
- If SERVER_PORT known: `lsof -i :$SERVER_PORT` to check if running, extract PID
- If CLIENT_PORT known: `lsof -i :$CLIENT_PORT` to check if running, extract PID

**Dependencies:**
- Check for `node_modules/` at root, `apps/server/node_modules/`, `apps/client/node_modules/`

### 4. Calculate Summary Stats

- Total worktree count (excluding main)
- Running vs stopped count
- Next available port offset
- Any configuration warnings

### 5. Report

```
Worktree Overview for PROJECT_NAME

Main Repository
  Path:   PROJECT_ROOT
  Branch: CURRENT_BRANCH
  Ports:  4000 (server), 5173 (client)
  Config: .claude/settings.json [present/missing]
  Status: [Running (PIDs) / Stopped]

---

Worktree: FEATURE_NAME
  Path:   WORKTREE_DIR
  Branch: BRANCH_NAME
  Ports:  SERVER_PORT (server), CLIENT_PORT (client)
  Config: .claude/settings.json [present (isolated) / missing]
  Status: [Running (PIDs) / Stopped]
  Deps:   [Installed / Missing]

[Repeat for each worktree]

---

Summary:
  Total worktrees: N
  Running: N | Stopped: N
  Next available offset: N

Quick Commands:
  Create:  /create-worktree <feature-name>
  Remove:  /remove-worktree <feature-name>
  Refresh: /list-worktrees
```

If no worktrees exist (only main):
```
Worktree Overview for PROJECT_NAME

Main Repository
  Path:   PROJECT_ROOT
  Branch: CURRENT_BRANCH

No worktrees found.

Create your first worktree:
  /create-worktree <feature-name>
```
