---
description: Remove a git worktree, stop its services, and optionally delete the branch
argument-hint: <feature-name>
allowed-tools: Bash, Read, Glob, Grep
---

# Remove Worktree

Safely remove a git worktree, stop any running services on its ports, clean up the directory, and optionally delete the git branch.

## Arguments

- `$1` = feature-name (required) - Name of the worktree/branch to remove

## Workflow

### 1. Locate the Worktree

```bash
FEATURE_NAME="$1"
PROJECT_ROOT=$(git rev-parse --show-toplevel)
PROJECT_NAME=$(basename "$PROJECT_ROOT")
PARENT_DIR=$(dirname "$PROJECT_ROOT")

# Check sibling directory (new convention)
WORKTREE_DIR="$PARENT_DIR/${PROJECT_NAME}-${FEATURE_NAME}"

# Also check legacy trees/ location
LEGACY_DIR="$PROJECT_ROOT/trees/$FEATURE_NAME"
```

Determine which location exists:
- If WORKTREE_DIR exists, use it
- Else if LEGACY_DIR exists, use it
- Else check `git worktree list` for any path containing FEATURE_NAME
- If none found, error with message

### 2. Read Port Configuration

```bash
# Try server .env
SERVER_PORT=""
if [ -f "$WORKTREE_DIR/apps/server/.env" ]; then
    SERVER_PORT=$(grep -E '^SERVER_PORT=' "$WORKTREE_DIR/apps/server/.env" | cut -d= -f2)
fi

# Try client .env
CLIENT_PORT=""
if [ -f "$WORKTREE_DIR/apps/client/.env" ]; then
    CLIENT_PORT=$(grep -E '^VITE_PORT=' "$WORKTREE_DIR/apps/client/.env" | cut -d= -f2)
fi
```

### 3. Stop Running Services

```bash
# Stop server
if [ -n "$SERVER_PORT" ]; then
    lsof -ti :$SERVER_PORT | xargs kill -9 2>/dev/null || true
fi

# Stop client
if [ -n "$CLIENT_PORT" ]; then
    lsof -ti :$CLIENT_PORT | xargs kill -9 2>/dev/null || true
fi

# Wait for cleanup
sleep 2
```

### 4. Remove Git Worktree

```bash
# Graceful removal
git worktree remove "$WORKTREE_DIR" 2>/dev/null || \
    git worktree remove "$WORKTREE_DIR" --force 2>/dev/null || true

# Prune stale entries
git worktree prune
```

If directory still exists after git worktree remove, note it as a warning but do NOT automatically `rm -rf` it. Provide the manual command to the user.

### 5. Delete Git Branch (with confirmation)

```bash
# Try safe delete first
git branch -d "$FEATURE_NAME" 2>/dev/null
```

If safe delete fails (unmerged changes), inform the user:
```
Branch FEATURE_NAME has unmerged changes.
To force delete: git branch -D FEATURE_NAME
```

Do NOT force-delete without telling the user.

### 6. Verify Cleanup

```bash
# Worktree removed from git
git worktree list  # should not contain FEATURE_NAME

# Directory removed
ls -d "$WORKTREE_DIR" 2>/dev/null  # should fail

# Ports freed
lsof -i :$SERVER_PORT 2>/dev/null  # should return nothing
lsof -i :$CLIENT_PORT 2>/dev/null  # should return nothing
```

### 7. Report

```
Worktree Removed: FEATURE_NAME

Services:
  Server (port SERVER_PORT): [Stopped / Was not running]
  Client (port CLIENT_PORT): [Stopped / Was not running]

Cleanup:
  Git worktree: Removed
  Directory:    Removed [or: WARNING - still exists, manual removal needed]
  Git branch:   [Deleted / Kept (unmerged) / Not found]

Ports SERVER_PORT and CLIENT_PORT are now free.

Verify: git worktree list
```
