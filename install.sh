#!/bin/bash
set -e

# Elite Agentic Engineering System Installer
# Creates symlinks from ~/.claude/ to this repo for all global components

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLAUDE_DIR="$HOME/.claude"
BACKUP_DIR="$CLAUDE_DIR/backups/$(date +%Y%m%d_%H%M%S)"

echo "🚀 Installing Elite Agentic Engineering System"
echo "Repo: $REPO_DIR"
echo ""

# Create backup directory if needed
mkdir -p "$BACKUP_DIR"

# Function to create symlink with backup
create_symlink() {
    local target="$1"  # Path in repo
    local link="$2"    # Path in ~/.claude/

    # Create parent directory if needed
    mkdir -p "$(dirname "$link")"

    # Check if already a symlink to our repo
    if [ -L "$link" ]; then
        local current_target=$(readlink "$link")
        if [[ "$current_target" == "$REPO_DIR"* ]]; then
            echo "✓ Already linked: $link"
            return 0
        fi
    fi

    # Backup existing regular file
    if [ -f "$link" ] && [ ! -L "$link" ]; then
        echo "📦 Backing up: $link"
        cp "$link" "$BACKUP_DIR/$(basename "$link")"
        rm "$link"
    fi

    # Remove broken symlink
    if [ -L "$link" ] && [ ! -e "$link" ]; then
        echo "🗑️  Removing broken symlink: $link"
        rm "$link"
    fi

    # Create symlink
    ln -sf "$target" "$link"
    echo "✅ Linked: $link -> $target"
}

echo "📚 Installing guides..."
create_symlink "$REPO_DIR/guides/MASTER_SUMMARY.md" "$CLAUDE_DIR/MASTER_SUMMARY.md"
create_symlink "$REPO_DIR/guides/L_THREADS.md" "$CLAUDE_DIR/L_THREADS.md"
create_symlink "$REPO_DIR/guides/F_THREADS.md" "$CLAUDE_DIR/F_THREADS.md"
create_symlink "$REPO_DIR/guides/RLM_ARCHITECTURE.md" "$CLAUDE_DIR/RLM_ARCHITECTURE.md"
create_symlink "$REPO_DIR/guides/RALPH_LOOPS.md" "$CLAUDE_DIR/RALPH_LOOPS.md"
create_symlink "$REPO_DIR/guides/CONTEXT_ENGINEERING.md" "$CLAUDE_DIR/CONTEXT_ENGINEERING.md"
create_symlink "$REPO_DIR/guides/GENERATIVE_UI.md" "$CLAUDE_DIR/GENERATIVE_UI.md"
create_symlink "$REPO_DIR/guides/MISSION_CONTROL.md" "$CLAUDE_DIR/MISSION_CONTROL.md"
create_symlink "$REPO_DIR/guides/AGENT_TEAMS.md" "$CLAUDE_DIR/AGENT_TEAMS.md"
create_symlink "$REPO_DIR/guides/AGENT_TEAMS_SETUP.md" "$CLAUDE_DIR/AGENT_TEAMS_SETUP.md"
create_symlink "$REPO_DIR/guides/MULTI_AGENT_ORCHESTRATION.md" "$CLAUDE_DIR/MULTI_AGENT_ORCHESTRATION.md"
create_symlink "$REPO_DIR/guides/SELF_CORRECTING_AGENTS.md" "$CLAUDE_DIR/SELF_CORRECTING_AGENTS.md"
create_symlink "$REPO_DIR/guides/Z_THREADS_AND_PLUGINS.md" "$CLAUDE_DIR/Z_THREADS_AND_PLUGINS.md"
create_symlink "$REPO_DIR/guides/AGENTIC_DROP_ZONES.md" "$CLAUDE_DIR/AGENTIC_DROP_ZONES.md"
create_symlink "$REPO_DIR/guides/AGENTIC_LAYER.md" "$CLAUDE_DIR/AGENTIC_LAYER.md"

echo ""
echo "⚡ Installing commands..."
create_symlink "$REPO_DIR/global-commands/analyze.md" "$CLAUDE_DIR/commands/analyze.md"
create_symlink "$REPO_DIR/global-commands/fusion.md" "$CLAUDE_DIR/commands/fusion.md"
create_symlink "$REPO_DIR/global-commands/loadbundle.md" "$CLAUDE_DIR/commands/loadbundle.md"
create_symlink "$REPO_DIR/global-commands/orchestrate.md" "$CLAUDE_DIR/commands/orchestrate.md"
create_symlink "$REPO_DIR/global-commands/prime.md" "$CLAUDE_DIR/commands/prime.md"
create_symlink "$REPO_DIR/global-commands/research.md" "$CLAUDE_DIR/commands/research.md"
create_symlink "$REPO_DIR/global-commands/rlm.md" "$CLAUDE_DIR/commands/rlm.md"
create_symlink "$REPO_DIR/global-commands/search.md" "$CLAUDE_DIR/commands/search.md"

echo ""
echo "🤖 Installing agents..."
create_symlink "$REPO_DIR/global-agents/orchestrator.md" "$CLAUDE_DIR/agents/orchestrator.md"
create_symlink "$REPO_DIR/global-agents/researcher.md" "$CLAUDE_DIR/agents/researcher.md"
create_symlink "$REPO_DIR/global-agents/rlm-root.md" "$CLAUDE_DIR/agents/rlm-root.md"

echo ""
echo "🎯 Installing skills..."
create_symlink "$REPO_DIR/global-skills/prime/SKILL.md" "$CLAUDE_DIR/skills/prime/SKILL.md"

echo ""
echo "🪝 Installing hooks..."
create_symlink "$REPO_DIR/global-hooks/context-bundle-logger.py" "$CLAUDE_DIR/hooks/context-bundle-logger.py"
create_symlink "$REPO_DIR/global-hooks/validators/check_lthread_progress.py" "$CLAUDE_DIR/hooks/validators/check_lthread_progress.py"
create_symlink "$REPO_DIR/global-hooks/validators/run_tests.py" "$CLAUDE_DIR/hooks/validators/run_tests.py"

echo ""
echo "📜 Installing scripts..."
create_symlink "$REPO_DIR/scripts/ralph-harness.sh" "$CLAUDE_DIR/scripts/ralph-harness.sh"
chmod +x "$CLAUDE_DIR/scripts/ralph-harness.sh"

echo ""
echo "📋 Installing templates..."
create_symlink "$REPO_DIR/templates/long-migration.md" "$CLAUDE_DIR/templates/long-migration.md"

echo ""
echo "⚙️  Updating settings.json hook paths..."
SETTINGS_FILE="$CLAUDE_DIR/settings.json"
if [ -f "$SETTINGS_FILE" ]; then
    # Create backup of settings.json
    cp "$SETTINGS_FILE" "$BACKUP_DIR/settings.json"

    # Update hook paths using sed (macOS compatible)
    sed -i '' "s|$HOME/.claude/hooks/context-bundle-logger.py|$REPO_DIR/global-hooks/context-bundle-logger.py|g" "$SETTINGS_FILE"
    sed -i '' "s|$HOME/.claude/hooks/validators/run_tests.py|$REPO_DIR/global-hooks/validators/run_tests.py|g" "$SETTINGS_FILE"
    sed -i '' "s|$HOME/.claude/hooks/validators/check_lthread_progress.py|$REPO_DIR/global-hooks/validators/check_lthread_progress.py|g" "$SETTINGS_FILE"

    echo "✅ Updated settings.json hook paths"

    # Validate JSON
    if command -v python3 &> /dev/null; then
        python3 -m json.tool "$SETTINGS_FILE" > /dev/null && echo "✅ settings.json is valid JSON" || echo "⚠️  settings.json may have JSON errors"
    fi
else
    echo "⚠️  settings.json not found at $SETTINGS_FILE"
fi

echo ""
echo "✨ Installation complete!"
echo ""
if [ "$(ls -A "$BACKUP_DIR" 2>/dev/null)" ]; then
    echo "📦 Backups saved to: $BACKUP_DIR"
fi
echo ""
echo "Next steps:"
echo "  1. Verify symlinks: ls -la ~/.claude/commands/"
echo "  2. Test system: cd apps/test_app && ./run_system_test.sh"
echo "  3. Try commands: /fusion, /rlm, /analyze"
