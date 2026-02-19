#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

echo "=== Claude Agentic Framework Install ==="
echo "Repo: $REPO_DIR"
echo ""

# 0. Ensure prerequisites are installed
echo "[0/8] Checking prerequisites..."

# uv — required for all hook execution (hooks use `uv run --script`)
if ! command -v uv >/dev/null 2>&1; then
  echo "  uv not found. Installing via official installer..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Add to PATH for the rest of this script
  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
  if ! command -v uv >/dev/null 2>&1; then
    echo "  ERROR: uv install failed. Install manually: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "         Then re-run: bash install.sh"
    exit 1
  fi
  echo "  uv installed: $(uv --version)"
else
  echo "  uv: OK ($(uv --version))"
fi

# python3 3.10+ — required for settings.json generation during install
if ! command -v python3 >/dev/null 2>&1; then
  echo "  ERROR: python3 not found. Install Python 3.10+ and re-run."
  exit 1
fi
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
  echo "  ERROR: Python 3.10+ required (found $PY_VERSION). Upgrade Python and re-run."
  exit 1
fi
echo "  python3: OK ($PY_VERSION)"

# git — required for hook validation and pre-push hook
if ! command -v git >/dev/null 2>&1; then
  echo "  ERROR: git not found. Install git and re-run."
  exit 1
fi
echo "  git: OK"

# claude — warn if Claude Code CLI is not installed (required to use the framework)
if ! command -v claude >/dev/null 2>&1; then
  echo "  WARNING: Claude Code CLI not found. Install it to use the framework:"
  echo "           https://docs.anthropic.com/en/docs/claude-code"
fi

echo ""

# 1. Validate all hook files exist before generating config
echo "[1/8] Validating hook files..."
ERRORS=0
SETTINGS_CONTENT=$(sed "s|__REPO_DIR__|$REPO_DIR|g" "$REPO_DIR/templates/settings.json.template")
HOOK_PATHS=$(echo "$SETTINGS_CONTENT" | python3 -c "
import json, sys, re
data = json.load(sys.stdin)
for event, matchers in data.get('hooks', {}).items():
    for matcher in matchers:
        for hook in matcher.get('hooks', []):
            cmd = hook.get('command', '')
            # extract the python file path from 'uv run /path/to/file.py [args]'
            parts = cmd.split()
            for p in parts:
                if p.endswith('.py'):
                    print(p)
                    break
# status line
sl = data.get('statusLine', {})
cmd = sl.get('command', '')
for p in cmd.split():
    if p.endswith('.py'):
        print(p)
        break
")
while IFS= read -r path; do
  if [ ! -f "$path" ]; then
    echo "  MISSING: $path"
    ERRORS=$((ERRORS + 1))
  fi
done <<< "$HOOK_PATHS"
if [ "$ERRORS" -gt 0 ]; then
  echo "  ABORT: $ERRORS hook file(s) missing. Fix before installing."
  exit 1
fi
echo "  All hook files verified."

# 2. Generate settings.json from template
echo "[2/8] Generating settings.json..."
mkdir -p "$CLAUDE_DIR"
echo "$SETTINGS_CONTENT" > "$CLAUDE_DIR/settings.json"
echo "  -> $CLAUDE_DIR/settings.json"

# 3. Symlink commands (clean stale links first)
echo "[3/8] Linking commands..."
mkdir -p "$CLAUDE_DIR/commands"
find "$CLAUDE_DIR/commands" -maxdepth 1 -type l ! -exec test -e {} \; -delete 2>/dev/null || true
for f in "$REPO_DIR"/global-commands/*.md; do
  [ -f "$f" ] || continue
  ln -sf "$f" "$CLAUDE_DIR/commands/$(basename "$f")"
done
echo "  -> $(ls "$REPO_DIR"/global-commands/*.md 2>/dev/null | wc -l | tr -d ' ') commands"

# 4. Symlink skills (clean stale links first)
echo "[4/8] Linking skills..."
mkdir -p "$CLAUDE_DIR/skills"
find "$CLAUDE_DIR/skills" -maxdepth 1 -type l ! -exec test -e {} \; -delete 2>/dev/null || true
for skill_dir in "$REPO_DIR"/global-skills/*/; do
  [ -d "$skill_dir" ] || continue
  skill_name=$(basename "$skill_dir")
  ln -sf "$skill_dir" "$CLAUDE_DIR/skills/$skill_name"
done
echo "  -> $(ls -d "$REPO_DIR"/global-skills/*/ 2>/dev/null | wc -l | tr -d ' ') skills"

# 5. Symlink agents (clean stale links first)
echo "[5/8] Linking agents..."
mkdir -p "$CLAUDE_DIR/agents"
# Only create team subdir if source exists
if [ -d "$REPO_DIR/global-agents/team" ]; then
  mkdir -p "$CLAUDE_DIR/agents/team"
fi
find "$CLAUDE_DIR/agents" -maxdepth 2 -type l ! -exec test -e {} \; -delete 2>/dev/null || true
for f in "$REPO_DIR"/global-agents/*.md; do
  [ -f "$f" ] || continue
  ln -sf "$f" "$CLAUDE_DIR/agents/$(basename "$f")"
done
if [ -d "$REPO_DIR/global-agents/team" ]; then
  for f in "$REPO_DIR"/global-agents/team/*.md; do
    [ -f "$f" ] || continue
    ln -sf "$f" "$CLAUDE_DIR/agents/team/$(basename "$f")"
  done
fi
echo "  -> $(ls "$REPO_DIR"/global-agents/*.md 2>/dev/null | wc -l | tr -d ' ') agents"

# 6. Generate documentation from repo state
echo "[6/8] Generating docs..."
uv run "$REPO_DIR/scripts/generate_docs.py"

# 7. Install git hooks (auto-doc before push)
echo "[7/8] Installing git hooks..."
if [ -d "$REPO_DIR/.git" ]; then
  cp "$REPO_DIR/scripts/pre-push-hook.sh" "$REPO_DIR/.git/hooks/pre-push"
  chmod +x "$REPO_DIR/.git/hooks/pre-push"
  echo "  -> .git/hooks/pre-push (auto-regenerates docs before every push)"
else
  echo "  Skipped: not a git repository"
fi

# 8. Final summary
echo "[8/8] Installation complete."
echo "  uv:      $(uv --version)"
echo "  python3: $(python3 --version)"
echo "  git:     $(git --version)"
if command -v claude >/dev/null 2>&1; then
  echo "  claude:  $(claude --version 2>/dev/null || echo OK)"
else
  echo "  claude:  NOT FOUND — install Claude Code CLI to use the framework"
  echo "           https://docs.anthropic.com/en/docs/claude-code"
fi

echo ""
echo "Done. Start a new Claude Code session to use the framework."
if [ -d "$REPO_DIR/.git" ]; then
  echo "Git pre-push hook installed: docs auto-regenerate before every push."
fi
if ! command -v claude >/dev/null 2>&1; then
  echo ""
  echo "ACTION REQUIRED: Claude Code CLI is not installed."
  echo "  Install: https://docs.anthropic.com/en/docs/claude-code"
fi
