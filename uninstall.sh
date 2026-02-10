#!/bin/bash
set -e

# Claude Agentic Framework — Uninstaller
# Removes only symlinks pointing to this repo. Leaves everything else untouched.

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLAUDE_DIR="$HOME/.claude"

echo "=== Claude Agentic Framework Uninstaller ==="
echo "Repo: $REPO_DIR"
echo ""

removed=0
skipped=0

remove_symlink() {
    local link="$1"

    if [ -L "$link" ]; then
        local target
        target=$(readlink "$link")
        if [[ "$target" == "$REPO_DIR"* ]]; then
            rm "$link"
            removed=$((removed + 1))
            return 0
        fi
    fi
    skipped=$((skipped + 1))
    return 0
}

remove_dir_symlinks() {
    local dir="$1"
    [ -d "$dir" ] || return 0
    for f in "$dir"/*; do
        [ -L "$f" ] && remove_symlink "$f"
    done
}

# ─── Commands ────────────────────────────────────────────

echo "[1/6] Commands..."
remove_dir_symlinks "$CLAUDE_DIR/commands"
remove_symlink "$CLAUDE_DIR/commands/agent_prompts" 2>/dev/null || true
remove_symlink "$CLAUDE_DIR/commands/bench" 2>/dev/null || true

# ─── Agents ──────────────────────────────────────────────

echo "[2/6] Agents..."
remove_dir_symlinks "$CLAUDE_DIR/agents"
remove_symlink "$CLAUDE_DIR/agents/team" 2>/dev/null || true
remove_symlink "$CLAUDE_DIR/agents/crypto" 2>/dev/null || true

# ─── Skills ──────────────────────────────────────────────

echo "[3/6] Skills..."
for d in "$CLAUDE_DIR/skills"/*/; do
    [ -L "${d%/}" ] && remove_symlink "${d%/}"
done

# ─── Guides ──────────────────────────────────────────────

echo "[4/6] Guides..."
for f in "$CLAUDE_DIR"/*.md; do
    [ -L "$f" ] && remove_symlink "$f"
done

# ─── Output Styles ───────────────────────────────────────

echo "[5/6] Output styles..."
remove_dir_symlinks "$CLAUDE_DIR/output-styles"

# ─── Scripts & Templates ────────────────────────────────

echo "[6/6] Scripts & templates..."
remove_dir_symlinks "$CLAUDE_DIR/scripts"
remove_dir_symlinks "$CLAUDE_DIR/templates"

# ─── Done ─────────────────────────────────────────────────

echo ""
echo "=== Uninstall Complete ==="
echo ""
echo "  Removed: $removed symlinks"
echo "  Skipped: $skipped (not pointing to this repo)"
echo ""
echo "NOTE: settings.json was NOT reverted automatically."
echo "  To restore: cp ~/.claude/backups/*/settings.json ~/.claude/settings.json"
echo "  Or re-run:  $REPO_DIR/install.sh"
echo ""
echo "Repo files remain at: $REPO_DIR"
