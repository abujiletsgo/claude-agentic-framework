#!/bin/bash
# pre-push-hook.sh — Auto-regenerate docs before every git push.
#
# Installed by: bash install.sh  (writes to .git/hooks/pre-push)
# To skip:      git push --no-verify
#
# What it does:
#   1. Regenerates README.md and CLAUDE.md from repo state
#   2. If they changed, stages + commits them automatically
#   3. Allows the push to proceed (including the auto-doc commit)

set -e

REPO_DIR="$(git rev-parse --show-toplevel)"

echo "[pre-push] Regenerating docs..."

if command -v uv >/dev/null 2>&1; then
    uv run "$REPO_DIR/scripts/generate_docs.py"
else
    python3 "$REPO_DIR/scripts/generate_docs.py"
fi

# Check if tracked docs changed
CHANGED=$(git diff --name-only README.md CLAUDE.md 2>/dev/null)

if [ -n "$CHANGED" ]; then
    git add README.md CLAUDE.md
    git commit -m "docs: auto-regenerate from repo state

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
    echo "[pre-push] Docs updated and committed. Push will include this commit."
else
    echo "[pre-push] Docs are current. No changes."
fi

exit 0
