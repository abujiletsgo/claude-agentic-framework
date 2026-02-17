#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

echo "=== Claude Agentic Framework Install ==="
echo "Repo: $REPO_DIR"
echo ""

# 1. Validate all hook files exist before generating config
echo "[1/7] Validating hook files..."
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
echo "[2/7] Generating settings.json..."
mkdir -p "$CLAUDE_DIR"
echo "$SETTINGS_CONTENT" > "$CLAUDE_DIR/settings.json"
echo "  -> $CLAUDE_DIR/settings.json"

# 3. Symlink commands (clean stale links first)
echo "[3/7] Linking commands..."
mkdir -p "$CLAUDE_DIR/commands"
find "$CLAUDE_DIR/commands" -maxdepth 1 -type l ! -exec test -e {} \; -delete 2>/dev/null || true
for f in "$REPO_DIR"/global-commands/*.md; do
  [ -f "$f" ] || continue
  ln -sf "$f" "$CLAUDE_DIR/commands/$(basename "$f")"
done
echo "  -> $(ls "$REPO_DIR"/global-commands/*.md 2>/dev/null | wc -l | tr -d ' ') commands"

# 4. Symlink skills (clean stale links first)
echo "[4/7] Linking skills..."
mkdir -p "$CLAUDE_DIR/skills"
find "$CLAUDE_DIR/skills" -maxdepth 1 -type l ! -exec test -e {} \; -delete 2>/dev/null || true
for skill_dir in "$REPO_DIR"/global-skills/*/; do
  [ -d "$skill_dir" ] || continue
  skill_name=$(basename "$skill_dir")
  ln -sf "$skill_dir" "$CLAUDE_DIR/skills/$skill_name"
done
echo "  -> $(ls -d "$REPO_DIR"/global-skills/*/ 2>/dev/null | wc -l | tr -d ' ') skills"

# 5. Symlink agents (clean stale links first)
echo "[5/7] Linking agents..."
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
echo "[6/7] Generating docs..."
if command -v uv >/dev/null 2>&1; then
  uv run "$REPO_DIR/scripts/generate_docs.py"
else
  python3 "$REPO_DIR/scripts/generate_docs.py"
fi

# 7. Install git hooks (auto-doc before push)
echo "[7/8] Installing git hooks..."
if [ -d "$REPO_DIR/.git" ]; then
  cp "$REPO_DIR/scripts/pre-push-hook.sh" "$REPO_DIR/.git/hooks/pre-push"
  chmod +x "$REPO_DIR/.git/hooks/pre-push"
  echo "  -> .git/hooks/pre-push (auto-regenerates docs before every push)"
else
  echo "  Skipped: not a git repository"
fi

# 8. Verify dependencies
echo "[8/8] Checking dependencies..."
command -v uv >/dev/null 2>&1 && echo "  uv: OK" || echo "  uv: MISSING (curl -LsSf https://astral.sh/uv/install.sh | sh)"
command -v python3 >/dev/null 2>&1 && echo "  python3: OK" || echo "  python3: MISSING"
command -v git >/dev/null 2>&1 && echo "  git: OK" || echo "  git: MISSING"

echo ""
echo "Done. Start a new Claude Code session to use the framework."
echo "Git pre-push hook installed: docs auto-regenerate before every push."
