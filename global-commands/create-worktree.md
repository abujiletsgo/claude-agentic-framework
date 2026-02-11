---
description: Create a git worktree with isolated .claude/settings.json for parallel development
argument-hint: <feature-name> [port-offset]
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Create Worktree

Create a fully isolated git worktree for parallel development. Each worktree gets its own `.claude/settings.json` with adjusted ports, its own `.env` files, and its own dependencies.

## Arguments

- `$1` = feature-name (required) - Name for the branch and worktree
- `$2` = port-offset (optional) - Explicit port offset; auto-calculated if omitted

## Workflow

### 1. Parse Arguments and Detect Project

```
FEATURE_NAME = $1 (required, error if missing)
PORT_OFFSET  = $2 (optional)
PROJECT_ROOT = output of: git rev-parse --show-toplevel
PROJECT_NAME = basename of PROJECT_ROOT
PARENT_DIR   = dirname of PROJECT_ROOT
WORKTREE_DIR = PARENT_DIR/PROJECT_NAME-FEATURE_NAME
```

Validate:
- FEATURE_NAME is provided and is a valid git branch name (no spaces, no special chars)
- PROJECT_ROOT is a git repository
- WORKTREE_DIR does not already exist

### 2. Calculate Port Offset

If PORT_OFFSET not provided:
```bash
# Count existing worktrees (excluding main)
WORKTREE_COUNT=$(git worktree list | grep -cv "$(git rev-parse --show-toplevel) ")
PORT_OFFSET=$((WORKTREE_COUNT + 1))
```

Calculate ports:
```
SERVER_PORT = 4000 + (PORT_OFFSET * 10)
CLIENT_PORT = 5173 + (PORT_OFFSET * 10)
```

Verify ports are available:
```bash
lsof -i :$SERVER_PORT  # should return nothing
lsof -i :$CLIENT_PORT  # should return nothing
```

### 3. Create Git Worktree

```bash
# Create branch + worktree in one step
git worktree add "$WORKTREE_DIR" -b "$FEATURE_NAME" 2>/dev/null || \
    git worktree add "$WORKTREE_DIR" "$FEATURE_NAME"

# Verify creation
git worktree list
```

### 4. Set Up Isolated .claude/settings.json

This is the critical step for Claude Code isolation.

```bash
mkdir -p "$WORKTREE_DIR/.claude"
```

If PROJECT_ROOT/.claude/settings.json exists:
1. Copy it to WORKTREE_DIR/.claude/settings.json
2. In the copied file, replace all occurrences of `localhost:4000` with `localhost:SERVER_PORT`
3. In the copied file, replace all occurrences of `localhost:5173` with `localhost:CLIENT_PORT`
4. Keep all absolute paths (hook script paths) unchanged -- they point to the framework repo and work from any directory

If PROJECT_ROOT/.claude/settings.json does not exist, skip this step and note in the report.

Also copy any other .claude/ contents that exist:
- .claude/commands/ (symlink or copy)
- .claude/skills/ (symlink or copy)
- .claude/agents/ (symlink or copy)

### 5. Set Up Environment Files

Copy root .env if it exists:
```bash
[ -f "$PROJECT_ROOT/.env" ] && cp "$PROJECT_ROOT/.env" "$WORKTREE_DIR/.env"
```

Create server .env (if apps/server/ exists in worktree):
```
SERVER_PORT=<calculated>
DB_PATH=events.db
```

Create client .env (if apps/client/ exists in worktree):
```
VITE_PORT=<calculated CLIENT_PORT>
VITE_API_URL=http://localhost:<calculated SERVER_PORT>
VITE_WS_URL=ws://localhost:<calculated SERVER_PORT>/stream
VITE_MAX_EVENTS_TO_DISPLAY=100
OBSERVABILITY_SERVER_URL=http://localhost:<calculated SERVER_PORT>/events
```

### 6. Install Dependencies

Detect and install:
```bash
# Root package.json
[ -f "$WORKTREE_DIR/package.json" ] && (cd "$WORKTREE_DIR" && npm install)

# Monorepo: apps/server
[ -f "$WORKTREE_DIR/apps/server/package.json" ] && (cd "$WORKTREE_DIR/apps/server" && npm install)

# Monorepo: apps/client
[ -f "$WORKTREE_DIR/apps/client/package.json" ] && (cd "$WORKTREE_DIR/apps/client" && npm install)
```

Use bun if bun.lockb exists, otherwise npm, otherwise yarn.

### 7. Validate

Verify:
- WORKTREE_DIR exists
- WORKTREE_DIR/.claude/settings.json exists (if parent had one)
- .env files created where needed
- git worktree list shows the new worktree
- Ports are not yet in use (services not started -- user starts manually)

### 8. Report

```
Worktree Created Successfully

Location:    WORKTREE_DIR
Branch:      FEATURE_NAME
Server Port: SERVER_PORT
Client Port: CLIENT_PORT
Port Offset: PORT_OFFSET

Isolated Config:
  .claude/settings.json: [Yes/No] (ports adjusted to SERVER_PORT/CLIENT_PORT)
  Root .env:             [Copied/Not found]
  Server .env:           [Created/N/A]
  Client .env:           [Created/N/A]

Dependencies:
  Root:   [Installed/N/A]
  Server: [Installed/N/A]
  Client: [Installed/N/A]

Next Steps:
  1. Open a new terminal
  2. cd WORKTREE_DIR
  3. Start Claude Code: claude
  4. The isolated .claude/settings.json will be used automatically

To start services (if applicable):
  cd WORKTREE_DIR
  SERVER_PORT=SERVER_PORT CLIENT_PORT=CLIENT_PORT sh scripts/start-system.sh

To remove later:
  /remove-worktree FEATURE_NAME
```
