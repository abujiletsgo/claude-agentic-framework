#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

echo "=== Claude Agentic Framework Install ==="
echo "Repo: $REPO_DIR"
echo ""

# 1. Validate all hook files exist before generating config
echo "[1/5] Validating hook files..."
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
echo "[2/5] Generating settings.json..."
mkdir -p "$CLAUDE_DIR"
echo "$SETTINGS_CONTENT" > "$CLAUDE_DIR/settings.json"
echo "  -> $CLAUDE_DIR/settings.json"

# 3. Symlink commands (clean stale links first)
echo "[3/5] Linking commands..."
mkdir -p "$CLAUDE_DIR/commands"
find "$CLAUDE_DIR/commands" -maxdepth 1 -type l ! -exec test -e {} \; -delete 2>/dev/null || true
for f in "$REPO_DIR"/global-commands/*.md; do
  [ -f "$f" ] || continue
  ln -sf "$f" "$CLAUDE_DIR/commands/$(basename "$f")"
done
echo "  -> $(ls "$REPO_DIR"/global-commands/*.md 2>/dev/null | wc -l | tr -d ' ') commands"

# 4. Symlink agents (clean stale links first)
echo "[4/5] Linking agents..."
mkdir -p "$CLAUDE_DIR/agents" "$CLAUDE_DIR/agents/team"
find "$CLAUDE_DIR/agents" -maxdepth 2 -type l ! -exec test -e {} \; -delete 2>/dev/null || true
for f in "$REPO_DIR"/global-agents/*.md; do
  [ -f "$f" ] || continue
  ln -sf "$f" "$CLAUDE_DIR/agents/$(basename "$f")"
done
for f in "$REPO_DIR"/global-agents/team/*.md; do
  [ -f "$f" ] || continue
  ln -sf "$f" "$CLAUDE_DIR/agents/team/$(basename "$f")"
done
echo "  -> $(ls "$REPO_DIR"/global-agents/*.md "$REPO_DIR"/global-agents/team/*.md 2>/dev/null | wc -l | tr -d ' ') agents"

# 5. Verify dependencies
echo "[5/5] Checking dependencies..."
command -v uv >/dev/null 2>&1 && echo "  uv: OK" || echo "  uv: MISSING (curl -LsSf https://astral.sh/uv/install.sh | sh)"
command -v python3 >/dev/null 2>&1 && echo "  python3: OK" || echo "  python3: MISSING"
command -v git >/dev/null 2>&1 && echo "  git: OK" || echo "  git: MISSING"

echo ""
echo "Done. Start a new Claude Code session to use the framework."
