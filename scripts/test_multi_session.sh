#!/bin/bash
# Multi-Session Conflict Detection Test Script
#
# This script helps you test the session lock manager by simulating
# two concurrent Claude Code sessions working on the same files.
#
# Usage: bash scripts/test_multi_session.sh

set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOCK_DIR="$HOME/.claude/file-locks"
SESSION_DIR="$HOME/.claude/session-locks"

echo "=== Multi-Session Conflict Detection Test ==="
echo ""

# Clean up any existing locks
echo "[1/4] Cleaning up existing locks..."
rm -rf "$LOCK_DIR"/* 2>/dev/null || true
rm -rf "$SESSION_DIR"/* 2>/dev/null || true
echo "✅ Locks cleared"
echo ""

# Simulate Session A creating a lock
echo "[2/4] Simulating Session A editing README.md..."
mkdir -p "$LOCK_DIR"
mkdir -p "$SESSION_DIR"

SESSION_A_ID="test-session-a-$(date +%s)"
SESSION_B_ID="test-session-b-$(date +%s)"

# Create Session A lock
cat > "$SESSION_DIR/$SESSION_A_ID.json" <<EOF
{
  "session_id": "$SESSION_A_ID",
  "started_at": "$(date -u +"%Y-%m-%dT%H:%M:%S")",
  "cwd": "$REPO_DIR",
  "files": ["README.md"]
}
EOF

# Create file lock for README.md
README_HASH=$(echo -n "$REPO_DIR/README.md" | md5)
cat > "$LOCK_DIR/${README_HASH}.lock" <<EOF
{
  "session_id": "$SESSION_A_ID",
  "file": "$REPO_DIR/README.md",
  "operation": "editing",
  "locked_at": "$(date -u +"%Y-%m-%dT%H:%M:%S")"
}
EOF

echo "✅ Session A lock created for README.md"
echo ""

# Test Session B trying to edit the same file
echo "[3/4] Testing Session B conflict detection..."
cat > /tmp/test_hook_input.json <<EOF
{
  "session_id": "$SESSION_B_ID",
  "tool": {
    "name": "Edit",
    "input": {
      "file_path": "$REPO_DIR/README.md"
    }
  }
}
EOF

export HOOK_EVENT="PreToolUse"
export CLAUDE_SESSION_ID="$SESSION_B_ID"

RESULT=$(cat /tmp/test_hook_input.json | uv run "$REPO_DIR/global-hooks/framework/session/session_lock_manager.py" 2>/dev/null)

if echo "$RESULT" | grep -q "CONFLICT"; then
  echo "✅ Conflict detected correctly!"
  echo ""
  echo "Hook output:"
  echo "$RESULT" | python3 -m json.tool
else
  echo "❌ No conflict detected (expected warning)"
  echo "Output: $RESULT"
fi
echo ""

# Show lock files
echo "[4/4] Current lock state:"
echo ""
echo "Session locks:"
ls -la "$SESSION_DIR/" 2>/dev/null || echo "  (none)"
echo ""
echo "File locks:"
ls -la "$LOCK_DIR/" 2>/dev/null || echo "  (none)"
echo ""

# Cleanup test locks
echo "Cleaning up test locks..."
rm -f "$SESSION_DIR/$SESSION_A_ID.json"
rm -f "$LOCK_DIR/${README_HASH}.lock"
rm -f /tmp/test_hook_input.json

echo ""
echo "=== Test Complete ==="
echo ""
echo "To test with real Claude Code sessions:"
echo "1. Terminal 1: cd $REPO_DIR && claude"
echo "2. Terminal 2: cd $REPO_DIR && claude"
echo "3. Session 1: Edit README.md"
echo "4. Session 2: Edit README.md (should see conflict warning)"
