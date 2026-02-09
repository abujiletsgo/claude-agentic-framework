#!/bin/bash
set -e

# Elite Agentic Engineering System Uninstaller
# Removes only symlinks pointing to this repo (safe, leaves other files alone)

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLAUDE_DIR="$HOME/.claude"

echo "🗑️  Uninstalling Elite Agentic Engineering System"
echo "Repo: $REPO_DIR"
echo ""

# Function to remove symlink if it points to our repo
remove_symlink() {
    local link="$1"

    if [ -L "$link" ]; then
        local target=$(readlink "$link")
        if [[ "$target" == "$REPO_DIR"* ]]; then
            rm "$link"
            echo "✅ Removed: $link"
            return 0
        else
            echo "⏭️  Skipped (points elsewhere): $link"
            return 1
        fi
    elif [ -e "$link" ]; then
        echo "⏭️  Skipped (not a symlink): $link"
        return 1
    else
        echo "⏭️  Not found: $link"
        return 1
    fi
}

echo "📚 Removing guide links..."
remove_symlink "$CLAUDE_DIR/MASTER_SUMMARY.md"
remove_symlink "$CLAUDE_DIR/L_THREADS.md"
remove_symlink "$CLAUDE_DIR/F_THREADS.md"
remove_symlink "$CLAUDE_DIR/RLM_ARCHITECTURE.md"
remove_symlink "$CLAUDE_DIR/RALPH_LOOPS.md"
remove_symlink "$CLAUDE_DIR/CONTEXT_ENGINEERING.md"
remove_symlink "$CLAUDE_DIR/GENERATIVE_UI.md"
remove_symlink "$CLAUDE_DIR/MISSION_CONTROL.md"
remove_symlink "$CLAUDE_DIR/AGENT_TEAMS.md"
remove_symlink "$CLAUDE_DIR/AGENT_TEAMS_SETUP.md"
remove_symlink "$CLAUDE_DIR/MULTI_AGENT_ORCHESTRATION.md"
remove_symlink "$CLAUDE_DIR/SELF_CORRECTING_AGENTS.md"
remove_symlink "$CLAUDE_DIR/Z_THREADS_AND_PLUGINS.md"
remove_symlink "$CLAUDE_DIR/AGENTIC_DROP_ZONES.md"
remove_symlink "$CLAUDE_DIR/AGENTIC_LAYER.md"

echo ""
echo "⚡ Removing command links..."
remove_symlink "$CLAUDE_DIR/commands/analyze.md"
remove_symlink "$CLAUDE_DIR/commands/fusion.md"
remove_symlink "$CLAUDE_DIR/commands/loadbundle.md"
remove_symlink "$CLAUDE_DIR/commands/orchestrate.md"
remove_symlink "$CLAUDE_DIR/commands/prime.md"
remove_symlink "$CLAUDE_DIR/commands/research.md"
remove_symlink "$CLAUDE_DIR/commands/rlm.md"
remove_symlink "$CLAUDE_DIR/commands/search.md"

echo ""
echo "🤖 Removing agent links..."
remove_symlink "$CLAUDE_DIR/agents/orchestrator.md"
remove_symlink "$CLAUDE_DIR/agents/researcher.md"
remove_symlink "$CLAUDE_DIR/agents/rlm-root.md"

echo ""
echo "🎯 Removing skill links..."
remove_symlink "$CLAUDE_DIR/skills/prime/SKILL.md"

echo ""
echo "🪝 Removing hook links..."
remove_symlink "$CLAUDE_DIR/hooks/context-bundle-logger.py"
remove_symlink "$CLAUDE_DIR/hooks/validators/check_lthread_progress.py"
remove_symlink "$CLAUDE_DIR/hooks/validators/run_tests.py"

echo ""
echo "📜 Removing script links..."
remove_symlink "$CLAUDE_DIR/scripts/ralph-harness.sh"

echo ""
echo "📋 Removing template links..."
remove_symlink "$CLAUDE_DIR/templates/long-migration.md"

echo ""
echo "⚠️  Note: settings.json hook paths were NOT reverted automatically."
echo "    If you want to restore hook paths, manually edit: $CLAUDE_DIR/settings.json"
echo "    Or restore from backup in: $CLAUDE_DIR/backups/"

echo ""
echo "✨ Uninstall complete!"
echo ""
echo "The repo files remain at: $REPO_DIR"
echo "You can still use them by re-running install.sh"
