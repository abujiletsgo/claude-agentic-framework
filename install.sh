#!/bin/bash
set -e

# Claude Agentic Framework — Consolidated Installer
# One repo, one install, one source of truth.
#
# What it does:
#   1. Backs up existing ~/.claude/ files
#   2. Symlinks commands, agents, skills, guides, output-styles, scripts, templates
#   3. Generates settings.json from template (hooks + status line referenced by absolute path)
#   4. Creates runtime dirs, sets permissions
#   5. Validates the result

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLAUDE_DIR="$HOME/.claude"
BACKUP_DIR="$CLAUDE_DIR/backups/$(date +%Y%m%d_%H%M%S)"

echo "=== Claude Agentic Framework Installer ==="
echo "Repo: $REPO_DIR"
echo ""

# ─── Helpers ──────────────────────────────────────────────

create_symlink() {
    local target="$1"   # Source path in repo
    local link="$2"     # Destination path in ~/.claude/

    mkdir -p "$(dirname "$link")"

    # Already correct symlink?
    if [ -L "$link" ]; then
        local current_target
        current_target=$(readlink "$link")
        if [ "$current_target" = "$target" ]; then
            return 0
        fi
    fi

    # Backup existing regular file/dir
    if [ -e "$link" ] && [ ! -L "$link" ]; then
        mkdir -p "$BACKUP_DIR"
        echo "  Backing up: $link"
        cp -a "$link" "$BACKUP_DIR/$(basename "$link").$(date +%s)"
        rm -rf "$link"
    fi

    # Remove existing symlink or broken link
    [ -L "$link" ] && rm "$link"

    # -n prevents following existing dir targets, -f forces overwrite
    ln -sfn "$target" "$link"
}

symlink_dir_contents() {
    local src_dir="$1"
    local dest_dir="$2"
    local pattern="${3:-*.md}"

    mkdir -p "$dest_dir"
    for f in "$src_dir"/$pattern; do
        [ -f "$f" ] || continue
        create_symlink "$f" "$dest_dir/$(basename "$f")"
    done
}

symlink_subdir() {
    local src_dir="$1"
    local dest_dir="$2"

    if [ -d "$src_dir" ]; then
        # Symlink the entire subdir as one link
        create_symlink "$src_dir" "$dest_dir"
    fi
}

# ─── Step 1: Commands ────────────────────────────────────

echo "[1/8] Commands..."
symlink_dir_contents "$REPO_DIR/global-commands" "$CLAUDE_DIR/commands" "*.md"
# Subdirectories
symlink_subdir "$REPO_DIR/global-commands/agent_prompts" "$CLAUDE_DIR/commands/agent_prompts"
symlink_subdir "$REPO_DIR/global-commands/bench" "$CLAUDE_DIR/commands/bench"

# ─── Step 2: Agents ──────────────────────────────────────

echo "[2/8] Agents..."
symlink_dir_contents "$REPO_DIR/global-agents" "$CLAUDE_DIR/agents" "*.md"
# Subdirectories
symlink_subdir "$REPO_DIR/global-agents/team" "$CLAUDE_DIR/agents/team"
symlink_subdir "$REPO_DIR/global-agents/crypto" "$CLAUDE_DIR/agents/crypto"

# ─── Step 3: Skills ──────────────────────────────────────

echo "[3/8] Skills..."
for skill_dir in "$REPO_DIR/global-skills"/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name=$(basename "$skill_dir")
    create_symlink "$skill_dir" "$CLAUDE_DIR/skills/$skill_name"
done

# ─── Step 4: Guides ──────────────────────────────────────

echo "[4/8] Guides..."
for f in "$REPO_DIR/guides"/*.md; do
    [ -f "$f" ] || continue
    create_symlink "$f" "$CLAUDE_DIR/$(basename "$f")"
done

# ─── Step 5: Output Styles ───────────────────────────────

echo "[5/8] Output styles..."
symlink_dir_contents "$REPO_DIR/global-output-styles" "$CLAUDE_DIR/output-styles" "*.md"

# ─── Step 6: Scripts + Templates ─────────────────────────

echo "[6/8] Scripts & templates..."
mkdir -p "$CLAUDE_DIR/scripts" "$CLAUDE_DIR/templates"
for f in "$REPO_DIR/scripts"/*.sh; do
    [ -f "$f" ] || continue
    create_symlink "$f" "$CLAUDE_DIR/scripts/$(basename "$f")"
done
for f in "$REPO_DIR/templates"/*.md; do
    [ -f "$f" ] || continue
    create_symlink "$f" "$CLAUDE_DIR/templates/$(basename "$f")"
done

# ─── Step 7: Generate settings.json ──────────────────────

echo "[7/8] Generating settings.json..."
TEMPLATE="$REPO_DIR/templates/settings.json.template"
SETTINGS="$CLAUDE_DIR/settings.json"

if [ -f "$SETTINGS" ]; then
    mkdir -p "$BACKUP_DIR"
    cp "$SETTINGS" "$BACKUP_DIR/settings.json"
    echo "  Backed up existing settings.json"
fi

sed "s|__REPO_DIR__|$REPO_DIR|g" "$TEMPLATE" > "$SETTINGS"

# Validate JSON
if python3 -m json.tool "$SETTINGS" > /dev/null 2>&1; then
    echo "  settings.json is valid JSON"
else
    echo "  WARNING: settings.json has JSON errors!"
    exit 1
fi

# ─── Step 8: Runtime dirs & permissions ───────────────────

echo "[8/8] Runtime setup..."
mkdir -p "$REPO_DIR/data/logs" "$REPO_DIR/data/tts_queue"

# Make all hook scripts executable
find "$REPO_DIR/global-hooks" -name "*.py" -exec chmod +x {} \;
# Make all status line scripts executable
find "$REPO_DIR/global-status-lines" -name "*.py" -exec chmod +x {} \;
# Make shell scripts executable
find "$REPO_DIR/scripts" -name "*.sh" -exec chmod +x {} \;

# ─── Done ─────────────────────────────────────────────────

echo ""
echo "=== Installation Complete ==="
echo ""

# Summary
CMD_COUNT=$(find "$CLAUDE_DIR/commands" -name "*.md" -not -path "*/agent_prompts/*" -not -path "*/bench/*" 2>/dev/null | wc -l | tr -d ' ')
AGENT_COUNT=$(find "$CLAUDE_DIR/agents" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
SKILL_COUNT=$(find "$CLAUDE_DIR/skills" -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
GUIDE_COUNT=$(ls "$CLAUDE_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')
STYLE_COUNT=$(find "$CLAUDE_DIR/output-styles" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')

echo "  Commands:      $CMD_COUNT"
echo "  Agents:        $AGENT_COUNT"
echo "  Skills:        $SKILL_COUNT"
echo "  Guides:        $GUIDE_COUNT"
echo "  Output styles: $STYLE_COUNT"
echo "  Hooks:         4 namespaces (mastery, observability, damage-control, framework)"
echo ""

if [ -d "$BACKUP_DIR" ] && [ "$(ls -A "$BACKUP_DIR" 2>/dev/null)" ]; then
    echo "Backups saved to: $BACKUP_DIR"
fi

echo ""
echo "Verify: python3 -m json.tool ~/.claude/settings.json"
echo "Test:   ls -la ~/.claude/commands/ ~/.claude/agents/"
