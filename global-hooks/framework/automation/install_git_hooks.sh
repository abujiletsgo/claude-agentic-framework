#!/bin/bash
# Install git hooks for auto code review
# Usage: bash install_git_hooks.sh [repo_path]
#
# Installs post-commit hook that runs auto_code_review.py

set -e

REPO_PATH="${1:-.}"
HOOK_DIR="$REPO_PATH/.git/hooks"
POST_COMMIT_HOOK="$HOOK_DIR/post-commit"

# Get absolute path to auto_code_review.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTO_REVIEW_SCRIPT="$SCRIPT_DIR/auto_code_review.py"

# Check if repo exists
if [ ! -d "$REPO_PATH/.git" ]; then
    echo "Error: $REPO_PATH is not a git repository"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p "$HOOK_DIR"

# Create post-commit hook
cat > "$POST_COMMIT_HOOK" << 'EOF'
#!/bin/bash
# Auto Code Review - Post-Commit Hook
# Installed by: claude-agentic-framework/global-hooks/framework/automation/install_git_hooks.sh
# Runs review asynchronously after each commit

COMMIT_HASH=$(git rev-parse HEAD)
REPO_ROOT=$(git rev-parse --show-toplevel)

# Check if review is enabled
REVIEW_CONFIG="$HOME/.claude/review_config.yaml"
if [ -f "$REVIEW_CONFIG" ]; then
    # Quick check: if config says enabled: false, skip
    if grep -q "^enabled: false" "$REVIEW_CONFIG" 2>/dev/null; then
        exit 0
    fi
fi

# Run review in background (non-blocking)
# Use the framework's review system
FRAMEWORK_ROOT="$(dirname "$(dirname "$(dirname "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")")")")"
REVIEW_ENGINE="$FRAMEWORK_ROOT/global-hooks/framework/review/review_engine.py"

if [ -f "$REVIEW_ENGINE" ]; then
    nohup uv run python3 "$REVIEW_ENGINE" \
        --commit "$COMMIT_HASH" \
        --repo-root "$REPO_ROOT" \
        >> "$HOME/.claude/logs/review.log" 2>&1 &
fi

exit 0
EOF

# Make hook executable
chmod +x "$POST_COMMIT_HOOK"

echo "✅ Installed post-commit hook to: $POST_COMMIT_HOOK"
echo "   Auto code review will run in background after each commit"
echo ""
echo "To disable: Set 'enabled: false' in ~/.claude/review_config.yaml"
echo "To uninstall: rm $POST_COMMIT_HOOK"
