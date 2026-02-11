# Worktree Operations Guide

Detailed step-by-step instructions for each worktree operation.

**Security**: All operations MUST validate input before executing any shell commands. See the [Security](#security-validation) section below.

---

## Security Validation

Every operation that accepts user input MUST run validation **before** any git or shell commands.

### Input Validation (Required First Step)

```bash
# Source the validation library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/scripts/validate_name.sh"

# Validate feature name BEFORE any other operation
validate_feature_name "$FEATURE_NAME" || {
    echo "Aborting: invalid feature name"
    exit 1
}

# Validate port offset if provided
if [ -n "$PORT_OFFSET" ]; then
    validate_port_offset "$PORT_OFFSET" || {
        echo "Aborting: invalid port offset"
        exit 1
    }
fi
```

### Feature Name Rules

- **Allowed characters**: `a-z A-Z 0-9 . _ -`
- **Rejected**: `/`, `..`, spaces, shell metacharacters (`;`, `&`, `|`, `$`, backticks, etc.)
- **Length**: 2-50 characters
- **No leading dot**: prevents hidden directory creation

### Path Validation

After computing the worktree directory path, validate it stays within the expected parent:

```bash
# Compute worktree path
WORKTREE_DIR="$(dirname "$PROJECT_ROOT")/${PROJECT_NAME}-${FEATURE_NAME}"

# Validate path does not escape parent directory
validate_worktree_path "$WORKTREE_DIR" "$(dirname "$PROJECT_ROOT")" || {
    echo "Aborting: path traversal detected"
    exit 1
}
```

---

## CREATE Operation

**Command:** `/create-worktree <feature-name> [port-offset]`

### Step 1: Validate input and detect project

```bash
# Required
FEATURE_NAME="$1"

# SECURITY: Validate feature name before ANY shell command
source scripts/validate_name.sh
validate_feature_name "$FEATURE_NAME" || exit 1

# Optional (auto-calculated if not provided)
PORT_OFFSET="$2"
if [ -n "$PORT_OFFSET" ]; then
    validate_port_offset "$PORT_OFFSET" || exit 1
fi

# Detect project root and name
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"

# Worktree location: sibling directory
WORKTREE_DIR="$(dirname "$PROJECT_ROOT")/${PROJECT_NAME}-${FEATURE_NAME}"

# SECURITY: Validate the computed path stays within parent directory
validate_worktree_path "$WORKTREE_DIR" "$(dirname "$PROJECT_ROOT")" || exit 1
```

### Step 2: Calculate port offset (if not provided)

```bash
# Count existing worktrees to auto-calculate offset
EXISTING_COUNT=$(git worktree list | grep -v "$(pwd)" | wc -l | tr -d ' ')
PORT_OFFSET=$((EXISTING_COUNT + 1))

# Validate auto-calculated offset
validate_port_offset "$PORT_OFFSET" || exit 1

# Calculate ports
SERVER_PORT=$((4000 + PORT_OFFSET * 10))
CLIENT_PORT=$((5173 + PORT_OFFSET * 10))
```

### Step 3: Create git branch and worktree

```bash
# Create branch if it doesn't exist
git branch "$FEATURE_NAME" 2>/dev/null || true

# Create worktree as sibling directory
git worktree add "$WORKTREE_DIR" "$FEATURE_NAME"

# Verify
git worktree list
```

### Step 4: Set up isolated .claude/settings.json

This is the critical isolation step. Each worktree gets its own `.claude/settings.json`.

```bash
# Create .claude directory in worktree
mkdir -p "$WORKTREE_DIR/.claude"

# Copy settings.json from parent
cp "$PROJECT_ROOT/.claude/settings.json" "$WORKTREE_DIR/.claude/settings.json"
```

Then update port references in the copied settings.json:
- Replace `localhost:4000` with `localhost:$SERVER_PORT` in hook URLs
- Replace `localhost:5173` with `localhost:$CLIENT_PORT` in any client references
- Keep all `__REPO_DIR__` paths unchanged (they are absolute and still valid)

**Important**: Use `sed` or programmatic replacement to update ports. The hooks themselves reference `__REPO_DIR__` which points to the framework repo (not the project), so they work across all worktrees without modification.

### Step 5: Set up environment files

```bash
# Root .env (copy from parent if exists)
if [ -f "$PROJECT_ROOT/.env" ]; then
    cp "$PROJECT_ROOT/.env" "$WORKTREE_DIR/.env"
fi

# Server .env (if project has apps/server structure)
if [ -d "$WORKTREE_DIR/apps/server" ]; then
    cat > "$WORKTREE_DIR/apps/server/.env" << EOF
SERVER_PORT=$SERVER_PORT
DB_PATH=events.db
EOF
fi

# Client .env (if project has apps/client structure)
if [ -d "$WORKTREE_DIR/apps/client" ]; then
    cat > "$WORKTREE_DIR/apps/client/.env" << EOF
VITE_PORT=$CLIENT_PORT
VITE_API_URL=http://localhost:$SERVER_PORT
VITE_WS_URL=ws://localhost:$SERVER_PORT/stream
EOF
fi
```

### Step 6: Create PID tracking directory

```bash
# Create a directory to track processes we start in this worktree
mkdir -p "$WORKTREE_DIR/.worktree-pids"
```

### Step 7: Install dependencies

```bash
# Detect package manager and install
if [ -f "$WORKTREE_DIR/package.json" ]; then
    cd "$WORKTREE_DIR" && npm install
fi

# If monorepo with apps/
if [ -d "$WORKTREE_DIR/apps/server" ]; then
    cd "$WORKTREE_DIR/apps/server" && npm install
fi
if [ -d "$WORKTREE_DIR/apps/client" ]; then
    cd "$WORKTREE_DIR/apps/client" && npm install
fi
```

### Step 8: Report results

Provide the user with:
- Worktree location
- Branch name
- Port configuration
- Access URLs
- How to start/stop services
- How to remove the worktree

---

## LIST Operation

**Command:** `/list-worktrees`

### Step 1: Get all worktrees

```bash
git worktree list
```

### Step 2: For each worktree, gather information

- Path and branch name
- Check for `.claude/settings.json` (isolated config present?)
- Read `.env` files for port configuration
- Check if services are running on configured ports: `lsof -i :PORT`
- Check for PID files in `.worktree-pids/` directory
- Extract PIDs of running processes

### Step 3: Report

For each worktree, show:
- Location and branch
- Port configuration (server + client)
- Service status (running/stopped)
- Whether `.claude/settings.json` is isolated
- Access URLs if running
- Quick commands for management

---

## REMOVE Operation

**Command:** `/remove-worktree <feature-name>`

### Step 1: Validate input and identify the worktree

```bash
# SECURITY: Validate feature name before ANY shell command
source scripts/validate_name.sh
validate_feature_name "$FEATURE_NAME" || exit 1

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"
WORKTREE_DIR="$(dirname "$PROJECT_ROOT")/${PROJECT_NAME}-${FEATURE_NAME}"

# SECURITY: Validate path stays within parent
validate_worktree_path "$WORKTREE_DIR" "$(dirname "$PROJECT_ROOT")" || exit 1
```

Also check the legacy `trees/` location:
```bash
LEGACY_DIR="$PROJECT_ROOT/trees/$FEATURE_NAME"
```

### Step 2: Read port configuration

```bash
# Try to read ports from worktree env files
if [ -f "$WORKTREE_DIR/apps/server/.env" ]; then
    SERVER_PORT=$(grep SERVER_PORT "$WORKTREE_DIR/apps/server/.env" | cut -d= -f2)
fi
if [ -f "$WORKTREE_DIR/apps/client/.env" ]; then
    CLIENT_PORT=$(grep VITE_PORT "$WORKTREE_DIR/apps/client/.env" | cut -d= -f2)
fi
```

### Step 3: Stop running services (safe process management)

**SECURITY**: Do NOT use blind `kill -9` on arbitrary PIDs from `lsof`. Instead, use PID file-based process management to only kill processes we started.

```bash
# --- Safe Process Shutdown ---

# Method 1: PID file-based shutdown (preferred)
# Only kills processes we explicitly started and tracked
PID_DIR="$WORKTREE_DIR/.worktree-pids"
if [ -d "$PID_DIR" ]; then
    for pid_file in "$PID_DIR"/*.pid; do
        [ -f "$pid_file" ] || continue
        PID=$(cat "$pid_file")
        SERVICE_NAME=$(basename "$pid_file" .pid)

        # Verify PID is numeric
        if ! [[ "$PID" =~ ^[0-9]+$ ]]; then
            echo "WARNING: Invalid PID in $pid_file, skipping"
            continue
        fi

        # Verify process exists and belongs to current user
        if kill -0 "$PID" 2>/dev/null; then
            PROC_USER=$(ps -o user= -p "$PID" 2>/dev/null | tr -d ' ')
            CURRENT_USER=$(whoami)
            if [ "$PROC_USER" = "$CURRENT_USER" ]; then
                echo "Stopping $SERVICE_NAME (PID $PID)..."
                # Graceful shutdown first (SIGTERM)
                kill "$PID" 2>/dev/null
                # Wait up to 5 seconds for graceful shutdown
                for i in 1 2 3 4 5; do
                    kill -0 "$PID" 2>/dev/null || break
                    sleep 1
                done
                # Force kill only if still running after graceful attempt
                if kill -0 "$PID" 2>/dev/null; then
                    echo "WARNING: Process $PID did not stop gracefully, sending SIGKILL"
                    kill -9 "$PID" 2>/dev/null || true
                fi
            else
                echo "WARNING: PID $PID belongs to user '$PROC_USER', not '$CURRENT_USER'. Skipping."
            fi
        else
            echo "Process $SERVICE_NAME (PID $PID) already stopped"
        fi
        rm -f "$pid_file"
    done
fi

# Method 2: Port-based shutdown (fallback, with safety checks)
# Only used if no PID files exist, and with ownership verification
if [ ! -d "$PID_DIR" ] || [ -z "$(ls -A "$PID_DIR" 2>/dev/null)" ]; then
    for PORT in $SERVER_PORT $CLIENT_PORT; do
        [ -n "$PORT" ] || continue
        # Validate port is numeric
        if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
            echo "WARNING: Invalid port '$PORT', skipping"
            continue
        fi
        PID=$(lsof -ti :"$PORT" 2>/dev/null | head -1)
        if [ -n "$PID" ]; then
            # Verify process belongs to current user
            PROC_USER=$(ps -o user= -p "$PID" 2>/dev/null | tr -d ' ')
            CURRENT_USER=$(whoami)
            if [ "$PROC_USER" = "$CURRENT_USER" ]; then
                echo "Stopping process on port $PORT (PID $PID)..."
                # Graceful first
                kill "$PID" 2>/dev/null
                sleep 2
                # Force only if needed
                if kill -0 "$PID" 2>/dev/null; then
                    echo "WARNING: Process $PID did not stop gracefully, sending SIGKILL"
                    kill -9 "$PID" 2>/dev/null || true
                fi
            else
                echo "WARNING: Port $PORT is used by user '$PROC_USER', not '$CURRENT_USER'. Skipping."
            fi
        fi
    done
fi

# Wait for processes to terminate
sleep 2
```

### Step 4: Check for uncommitted changes

```bash
# SECURITY: Check for uncommitted changes BEFORE removing
if [ -d "$WORKTREE_DIR" ]; then
    cd "$WORKTREE_DIR"
    UNCOMMITTED=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    cd "$PROJECT_ROOT"

    if [ "$UNCOMMITTED" -gt 0 ]; then
        echo "WARNING: Worktree has $UNCOMMITTED uncommitted change(s)."
        echo "  To preserve changes, commit or stash them first."
        echo "  To force removal, use: /remove-worktree $FEATURE_NAME --force"

        # Default: do NOT force remove
        if [ "$FORCE_REMOVE" != "true" ]; then
            echo "Aborting removal. Use --force to override."
            exit 1
        else
            echo "FORCE mode: Proceeding despite uncommitted changes."
        fi
    fi
fi
```

### Step 5: Remove git worktree

```bash
# Default: graceful removal only (no --force)
if git worktree remove "$WORKTREE_DIR" 2>/dev/null; then
    echo "Worktree removed successfully"
else
    # If graceful removal fails, explain why and offer force option
    echo "ERROR: Could not remove worktree gracefully."
    echo "  This usually means there are uncommitted changes."
    echo "  Options:"
    echo "    1. Commit or stash changes, then try again"
    echo "    2. Use --force flag: /remove-worktree $FEATURE_NAME --force"

    if [ "$FORCE_REMOVE" = "true" ]; then
        echo "FORCE mode: Removing with --force..."
        git worktree remove "$WORKTREE_DIR" --force
    else
        exit 1
    fi
fi

# Prune stale worktree metadata
git worktree prune
```

### Step 6: Optionally delete the branch

```bash
# Safe delete (fails if unmerged)
git branch -d "$FEATURE_NAME" 2>/dev/null || \
    echo "Branch $FEATURE_NAME has unmerged changes. Use 'git branch -D $FEATURE_NAME' to force delete."
```

### Step 7: Verify cleanup

```bash
# Confirm worktree removed
git worktree list | grep "$FEATURE_NAME" && echo "WARNING: Worktree still listed" || echo "Worktree removed"

# Confirm directory removed
[ -d "$WORKTREE_DIR" ] && echo "WARNING: Directory still exists" || echo "Directory cleaned up"

# Confirm ports are free
if [ -n "$SERVER_PORT" ]; then
    lsof -i :"$SERVER_PORT" 2>/dev/null && echo "WARNING: Server port still in use" || echo "Server port free"
fi
if [ -n "$CLIENT_PORT" ]; then
    lsof -i :"$CLIENT_PORT" 2>/dev/null && echo "WARNING: Client port still in use" || echo "Client port free"
fi
```

### Step 8: Report

Confirm what was removed:
- Services stopped (ports freed)
- Worktree removed
- Branch status (deleted or kept)
- Any warnings

---

## PID File Management

When starting services in a worktree, record the PID for safe shutdown later.

### Recording PIDs when starting services

```bash
PID_DIR="$WORKTREE_DIR/.worktree-pids"
mkdir -p "$PID_DIR"

# Start server and record PID
cd "$WORKTREE_DIR/apps/server"
node index.js &
echo $! > "$PID_DIR/server.pid"

# Start client and record PID
cd "$WORKTREE_DIR/apps/client"
npx vite --port "$CLIENT_PORT" &
echo $! > "$PID_DIR/client.pid"
```

### Checking service status

```bash
PID_DIR="$WORKTREE_DIR/.worktree-pids"
for pid_file in "$PID_DIR"/*.pid; do
    [ -f "$pid_file" ] || continue
    PID=$(cat "$pid_file")
    SERVICE=$(basename "$pid_file" .pid)
    if kill -0 "$PID" 2>/dev/null; then
        echo "$SERVICE: Running (PID $PID)"
    else
        echo "$SERVICE: Stopped (stale PID file)"
        rm -f "$pid_file"
    fi
done
```
