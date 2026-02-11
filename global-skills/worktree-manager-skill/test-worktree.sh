#!/bin/bash
# test-worktree.sh - End-to-end test for worktree management
#
# This script tests the full worktree lifecycle:
#   0. Validates input security (feature name, path traversal, port offset)
#   1. Creates a test git repo
#   2. Sets up .claude/settings.json in main repo
#   3. Creates a worktree with isolated config
#   4. Verifies isolation (settings.json, ports, .env)
#   5. Makes changes and commits in worktree
#   6. Merges back to main
#   7. Removes worktree and cleans up
#
# Usage: bash test-worktree.sh [--keep]
#   --keep: Do not clean up the test directory after success

set -e

# --- Configuration ---
KEEP_ON_SUCCESS=false
if [ "$1" = "--keep" ]; then
    KEEP_ON_SUCCESS=true
fi

TEST_DIR="/tmp/worktree-test-$$"
PROJECT_NAME="test-project"
PROJECT_DIR="$TEST_DIR/$PROJECT_NAME"
FEATURE_NAME="test-feature"
WORKTREE_DIR="$TEST_DIR/${PROJECT_NAME}-${FEATURE_NAME}"

PASS_COUNT=0
FAIL_COUNT=0

# --- Helpers ---
pass() {
    PASS_COUNT=$((PASS_COUNT + 1))
    echo "  PASS: $1"
}

fail() {
    FAIL_COUNT=$((FAIL_COUNT + 1))
    echo "  FAIL: $1"
}

check() {
    local description="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        pass "$description"
    else
        fail "$description"
    fi
}

check_file_exists() {
    if [ -f "$1" ]; then
        pass "File exists: $1"
    else
        fail "File missing: $1"
    fi
}

check_file_contains() {
    local file="$1"
    local pattern="$2"
    local desc="$3"
    if grep -q "$pattern" "$file" 2>/dev/null; then
        pass "$desc"
    else
        fail "$desc (pattern '$pattern' not found in $file)"
    fi
}

check_file_not_contains() {
    local file="$1"
    local pattern="$2"
    local desc="$3"
    if ! grep -q "$pattern" "$file" 2>/dev/null; then
        pass "$desc"
    else
        fail "$desc (pattern '$pattern' found in $file but should not be)"
    fi
}

# Check that a command is rejected (exits non-zero)
check_rejects() {
    local desc="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        fail "$desc (should have been rejected but was accepted)"
    else
        pass "$desc"
    fi
}

# Check that a command is accepted (exits zero)
check_accepts() {
    local desc="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        pass "$desc"
    else
        fail "$desc (should have been accepted but was rejected)"
    fi
}

cleanup() {
    echo ""
    echo "--- Cleanup ---"
    if [ -d "$PROJECT_DIR" ]; then
        cd "$PROJECT_DIR"
        # Remove worktree if it exists
        git worktree remove "$WORKTREE_DIR" --force 2>/dev/null || true
        git worktree prune 2>/dev/null || true
    fi
    if [ "$KEEP_ON_SUCCESS" = "false" ] || [ "$FAIL_COUNT" -gt 0 ]; then
        rm -rf "$TEST_DIR"
        echo "Cleaned up test directory: $TEST_DIR"
    else
        echo "Kept test directory: $TEST_DIR"
    fi
}

trap cleanup EXIT

# --- Test Execution ---
echo "=== Worktree Manager Test Suite ==="
echo "Test directory: $TEST_DIR"
echo ""

# ============================================================
echo "--- Phase 1: Set up test repository ---"
# ============================================================

mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

git init
git checkout -b main

# Create a minimal project structure
mkdir -p apps/server apps/client .claude

# Create a settings.json with port references
cat > .claude/settings.json << 'SETTINGS'
{
  "permissions": {
    "allow": ["*"]
  },
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo 'hook running'",
            "timeout": 5,
            "env": {
              "AGENT_SERVER_URL": "http://localhost:4000"
            }
          }
        ]
      }
    ]
  }
}
SETTINGS

# Create root .env with API keys
cat > .env << 'ENV'
ANTHROPIC_API_KEY=test-key-12345
OPENAI_API_KEY=test-openai-key
ENV

# Create server and client files
cat > apps/server/index.js << 'JS'
const port = process.env.SERVER_PORT || 4000;
console.log(`Server running on port ${port}`);
JS

cat > apps/client/index.html << 'HTML'
<html><body>Client</body></html>
HTML

echo '{"name": "test-server", "version": "1.0.0"}' > apps/server/package.json
echo '{"name": "test-client", "version": "1.0.0"}' > apps/client/package.json

# Initial commit
git add -A
git commit -m "Initial commit"

check "Git repo initialized" test -d .git
check "Main branch exists" git branch --list main
check_file_exists "$PROJECT_DIR/.claude/settings.json"
check_file_exists "$PROJECT_DIR/.env"

echo ""

# ============================================================
echo "--- Phase 1b: Input validation tests ---"
# ============================================================

# Resolve path to validation script
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
VALIDATE_SCRIPT="$SKILL_DIR/scripts/validate_name.sh"

if [ ! -f "$VALIDATE_SCRIPT" ]; then
    fail "Validation script not found at $VALIDATE_SCRIPT"
else
    pass "Validation script exists"

    # Source the validation functions
    source "$VALIDATE_SCRIPT"

    # --- Valid names (should be accepted) ---
    check_accepts "Accept: my-feature" validate_feature_name "my-feature"
    check_accepts "Accept: fix-bug" validate_feature_name "fix-bug"
    check_accepts "Accept: add_auth" validate_feature_name "add_auth"
    check_accepts "Accept: v1.2.3" validate_feature_name "v1.2.3"
    check_accepts "Accept: feature.test_name-123" validate_feature_name "feature.test_name-123"
    check_accepts "Accept: AB" validate_feature_name "AB"

    # --- Invalid names (should be rejected) ---
    check_rejects "Reject: empty string" validate_feature_name ""
    check_rejects "Reject: single char 'a'" validate_feature_name "a"
    check_rejects "Reject: space in name" validate_feature_name "bad name"
    check_rejects "Reject: slash in name" validate_feature_name "feat/auth"
    check_rejects "Reject: semicolon" validate_feature_name "feat;cmd"
    check_rejects "Reject: ampersand" validate_feature_name "feat&cmd"
    check_rejects "Reject: pipe" validate_feature_name "feat|cmd"
    check_rejects "Reject: dollar sign" validate_feature_name 'feat$var'
    check_rejects "Reject: backtick" validate_feature_name 'feat`cmd`'
    check_rejects "Reject: parentheses" validate_feature_name "feat(1)"
    check_rejects "Reject: leading dot" validate_feature_name ".hidden"
    check_rejects "Reject: path traversal (..)" validate_feature_name "a..b"

    # --- Long name (over 50 chars) ---
    LONG_NAME="abcdefghijklmnopqrstuvwxyz-abcdefghijklmnopqrstuvwxyz"
    check_rejects "Reject: name over 50 chars" validate_feature_name "$LONG_NAME"

    # --- Port offset validation ---
    check_accepts "Accept: port offset 0" validate_port_offset "0"
    check_accepts "Accept: port offset 5" validate_port_offset "5"
    check_accepts "Accept: port offset 99" validate_port_offset "99"
    check_rejects "Reject: port offset negative" validate_port_offset "-1"
    check_rejects "Reject: port offset non-numeric" validate_port_offset "abc"
    check_rejects "Reject: port offset too large" validate_port_offset "100"

    # --- Path validation ---
    # Create a temporary parent to test path validation
    TEMP_PARENT="$TEST_DIR/path-test-parent"
    mkdir -p "$TEMP_PARENT"
    check_accepts "Accept: path within parent" validate_worktree_path "$TEMP_PARENT/child" "$TEMP_PARENT"
    check_rejects "Reject: path outside parent" validate_worktree_path "/tmp/elsewhere" "$TEMP_PARENT"
    rmdir "$TEMP_PARENT"
fi

echo ""

# ============================================================
echo "--- Phase 2: Create worktree with isolated config ---"
# ============================================================

# Calculate ports (offset 1)
PORT_OFFSET=1
SERVER_PORT=$((4000 + PORT_OFFSET * 10))
CLIENT_PORT=$((5173 + PORT_OFFSET * 10))

echo "  Port offset: $PORT_OFFSET"
echo "  Server port: $SERVER_PORT"
echo "  Client port: $CLIENT_PORT"
echo "  Worktree dir: $WORKTREE_DIR"

# Clean any stale worktree directory from a previous run
[ -d "$WORKTREE_DIR" ] && rm -rf "$WORKTREE_DIR"

# Create the worktree
git worktree add "$WORKTREE_DIR" -b "$FEATURE_NAME"
check "Worktree created" test -d "$WORKTREE_DIR"
check "Worktree in git list" git worktree list

# Verify worktree is listed
LISTED=$(git worktree list | grep "$FEATURE_NAME" | wc -l | tr -d ' ')
if [ "$LISTED" -ge 1 ]; then
    pass "Worktree appears in git worktree list"
else
    fail "Worktree not found in git worktree list"
fi

echo ""

# ============================================================
echo "--- Phase 3: Set up isolated .claude/settings.json ---"
# ============================================================

# Create .claude directory in worktree
mkdir -p "$WORKTREE_DIR/.claude"

# Copy settings.json and adjust ports
cp "$PROJECT_DIR/.claude/settings.json" "$WORKTREE_DIR/.claude/settings.json"

# Replace port references
sed -i.bak "s/localhost:4000/localhost:${SERVER_PORT}/g" "$WORKTREE_DIR/.claude/settings.json"
sed -i.bak "s/localhost:5173/localhost:${CLIENT_PORT}/g" "$WORKTREE_DIR/.claude/settings.json"
rm -f "$WORKTREE_DIR/.claude/settings.json.bak"

check_file_exists "$WORKTREE_DIR/.claude/settings.json"
check_file_contains "$WORKTREE_DIR/.claude/settings.json" "localhost:${SERVER_PORT}" \
    "settings.json has worktree server port ($SERVER_PORT)"
check_file_not_contains "$WORKTREE_DIR/.claude/settings.json" "localhost:4000" \
    "settings.json does NOT have main server port (4000)"

# Verify main project settings.json is unchanged
check_file_contains "$PROJECT_DIR/.claude/settings.json" "localhost:4000" \
    "Main settings.json still has original port (4000)"

echo ""

# ============================================================
echo "--- Phase 4: Set up environment files ---"
# ============================================================

# Copy root .env
cp "$PROJECT_DIR/.env" "$WORKTREE_DIR/.env"

# Create server .env
cat > "$WORKTREE_DIR/apps/server/.env" << EOF
SERVER_PORT=$SERVER_PORT
DB_PATH=events.db
EOF

# Create client .env
cat > "$WORKTREE_DIR/apps/client/.env" << EOF
VITE_PORT=$CLIENT_PORT
VITE_API_URL=http://localhost:$SERVER_PORT
VITE_WS_URL=ws://localhost:$SERVER_PORT/stream
EOF

check_file_exists "$WORKTREE_DIR/.env"
check_file_contains "$WORKTREE_DIR/.env" "ANTHROPIC_API_KEY" \
    "Root .env has API keys"
check_file_exists "$WORKTREE_DIR/apps/server/.env"
check_file_contains "$WORKTREE_DIR/apps/server/.env" "SERVER_PORT=$SERVER_PORT" \
    "Server .env has correct port ($SERVER_PORT)"
check_file_exists "$WORKTREE_DIR/apps/client/.env"
check_file_contains "$WORKTREE_DIR/apps/client/.env" "VITE_PORT=$CLIENT_PORT" \
    "Client .env has correct port ($CLIENT_PORT)"

# Create PID tracking directory
mkdir -p "$WORKTREE_DIR/.worktree-pids"
check "PID tracking directory created" test -d "$WORKTREE_DIR/.worktree-pids"

echo ""

# ============================================================
echo "--- Phase 5: Verify complete isolation ---"
# ============================================================

# Settings files are different
MAIN_SETTINGS=$(cat "$PROJECT_DIR/.claude/settings.json")
WT_SETTINGS=$(cat "$WORKTREE_DIR/.claude/settings.json")
if [ "$MAIN_SETTINGS" != "$WT_SETTINGS" ]; then
    pass "settings.json files are different (ports isolated)"
else
    fail "settings.json files are identical (ports NOT isolated)"
fi

# Worktree has its own .git file (not directory)
if [ -f "$WORKTREE_DIR/.git" ]; then
    pass "Worktree has .git file (not directory) - correct worktree setup"
else
    fail "Worktree missing .git file"
fi

# Both point to same repo
# Note: on macOS, /tmp is a symlink to /private/tmp, so resolve real paths
WT_TOPLEVEL=$(cd "$WORKTREE_DIR" && git rev-parse --show-toplevel)
RESOLVED_WORKTREE_DIR=$(cd "$WORKTREE_DIR" && pwd -P)
RESOLVED_WT_TOPLEVEL=$(cd "$WT_TOPLEVEL" && pwd -P)
# Note: worktree's --show-toplevel returns its own path
if [ "$RESOLVED_WT_TOPLEVEL" = "$RESOLVED_WORKTREE_DIR" ]; then
    pass "Worktree has its own toplevel path"
else
    fail "Worktree toplevel mismatch: expected $RESOLVED_WORKTREE_DIR, got $RESOLVED_WT_TOPLEVEL"
fi

# Both share same git objects
MAIN_GIT_DIR=$(cd "$PROJECT_DIR" && git rev-parse --git-dir)
WT_GIT_DIR=$(cd "$WORKTREE_DIR" && git rev-parse --git-dir)
if [ "$MAIN_GIT_DIR" = ".git" ] && echo "$WT_GIT_DIR" | grep -q "worktrees"; then
    pass "Git objects are shared (worktree links to main .git)"
else
    fail "Git object sharing unclear: main=$MAIN_GIT_DIR, wt=$WT_GIT_DIR"
fi

echo ""

# ============================================================
echo "--- Phase 6: Make changes in worktree and commit ---"
# ============================================================

cd "$WORKTREE_DIR"

# Create a new file in the worktree
cat > apps/server/auth.js << 'JS'
module.exports = function authenticate(req, res, next) {
    console.log('Auth middleware');
    next();
};
JS

git add apps/server/auth.js
git commit -m "Add authentication middleware"

# Verify commit exists in worktree branch
COMMIT_MSG=$(git log -1 --format=%s)
if [ "$COMMIT_MSG" = "Add authentication middleware" ]; then
    pass "Commit created in worktree branch"
else
    fail "Commit message mismatch: $COMMIT_MSG"
fi

# Verify main branch does NOT have the file yet
cd "$PROJECT_DIR"
if [ ! -f "apps/server/auth.js" ]; then
    pass "Main branch does not have worktree changes (isolated)"
else
    fail "Main branch has worktree changes (NOT isolated)"
fi

echo ""

# ============================================================
echo "--- Phase 7: Merge worktree branch back to main ---"
# ============================================================

cd "$PROJECT_DIR"

git merge "$FEATURE_NAME" --no-edit
MERGE_RESULT=$?

if [ $MERGE_RESULT -eq 0 ]; then
    pass "Merge completed successfully"
else
    fail "Merge failed with exit code $MERGE_RESULT"
fi

if [ -f "apps/server/auth.js" ]; then
    pass "Merged file exists in main branch"
else
    fail "Merged file missing from main branch"
fi

echo ""

# ============================================================
echo "--- Phase 8: Remove worktree and clean up ---"
# ============================================================

cd "$PROJECT_DIR"

# Remove the worktree (--force needed because we added untracked .claude/ and .env files)
git worktree remove "$WORKTREE_DIR" --force
check "Worktree removed via git" test ! -d "$WORKTREE_DIR"

# Prune
git worktree prune

# Verify no longer listed
STILL_LISTED=$(git worktree list | grep "$FEATURE_NAME" | wc -l | tr -d ' ')
if [ "$STILL_LISTED" -eq 0 ]; then
    pass "Worktree no longer in git worktree list"
else
    fail "Worktree still appears in git worktree list"
fi

# Delete the branch
git branch -d "$FEATURE_NAME"
BRANCH_EXISTS=$(git branch --list "$FEATURE_NAME" | wc -l | tr -d ' ')
if [ "$BRANCH_EXISTS" -eq 0 ]; then
    pass "Branch deleted successfully"
else
    fail "Branch still exists after deletion"
fi

echo ""

# ============================================================
echo "=== Test Results ==="
# ============================================================

TOTAL=$((PASS_COUNT + FAIL_COUNT))
echo ""
echo "  Total:  $TOTAL"
echo "  Passed: $PASS_COUNT"
echo "  Failed: $FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "  ALL TESTS PASSED"
    exit 0
else
    echo "  SOME TESTS FAILED"
    exit 1
fi
