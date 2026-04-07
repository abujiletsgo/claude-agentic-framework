#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

echo "=== Claude Agentic Framework Install ==="
echo "Repo: $REPO_DIR"
echo ""

# 0. Ensure prerequisites are installed
echo "[0/9] Checking prerequisites..."

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
# Try common Homebrew paths first (macOS often has old system python3)
for _p in /opt/homebrew/bin /usr/local/bin; do
  if [ -x "$_p/python3" ]; then
    _ver=$("$_p/python3" -c "import sys; print(sys.version_info.minor)" 2>/dev/null)
    if [ -n "$_ver" ] && [ "$_ver" -ge 10 ]; then
      export PATH="$_p:$PATH"
      break
    fi
  fi
done

_install_python() {
  echo "  Python 3.10+ not found. Installing via uv..."
  uv python install 3.13 2>/dev/null
  # uv installs to ~/.local/share/uv/python — find it
  local uv_py
  uv_py=$(uv python find 3.13 2>/dev/null)
  if [ -n "$uv_py" ] && [ -x "$uv_py" ]; then
    # Symlink into a PATH location so the rest of the script sees it
    mkdir -p "$HOME/.local/bin"
    ln -sf "$uv_py" "$HOME/.local/bin/python3"
    export PATH="$HOME/.local/bin:$PATH"
  fi
}

if ! command -v python3 >/dev/null 2>&1; then
  _install_python
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "  ERROR: python3 not found and auto-install failed."
  echo "         Install Python 3.10+ manually and re-run."
  exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
  echo "  System python3 is $PY_VERSION (too old). Installing via uv..."
  _install_python
  # Re-check after install
  PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
  PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
  PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
  if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo "  ERROR: Python 3.10+ required (found $PY_VERSION). Auto-install failed."
    echo "         Install Python 3.10+ manually and re-run."
    exit 1
  fi
fi
echo "  python3: OK ($PY_VERSION)"

# git — required for hook validation and pre-push hook
if ! command -v git >/dev/null 2>&1; then
  echo "  git not found. Installing..."
  if command -v brew >/dev/null 2>&1; then
    brew install git
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update && sudo apt-get install -y git
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y git
  else
    echo "  ERROR: git not found and no supported package manager detected."
    echo "         Install git manually and re-run."
    exit 1
  fi
fi
if ! command -v git >/dev/null 2>&1; then
  echo "  ERROR: git install failed. Install manually and re-run."
  exit 1
fi
echo "  git: OK"

# officecli — required for /docs skill (Word/Excel/PowerPoint operations)
if ! command -v officecli >/dev/null 2>&1; then
  echo "  officecli not found. Installing..."
  if curl -fsSL https://raw.githubusercontent.com/iOfficeAI/OfficeCLI/main/install.sh | bash 2>/dev/null; then
    # Re-source PATH in case install.sh added to .local/bin
    export PATH="$HOME/.local/bin:$PATH"
    if command -v officecli >/dev/null 2>&1; then
      echo "  officecli: installed ($(officecli --version 2>/dev/null || echo OK))"
    else
      echo "  WARNING: officecli install ran but binary not found in PATH."
      echo "           Restart your shell or run: export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
  else
    echo "  WARNING: officecli install failed. /docs skill will not work."
    echo "           Install manually: curl -fsSL https://raw.githubusercontent.com/iOfficeAI/OfficeCLI/main/install.sh | bash"
  fi
else
  echo "  officecli: OK ($(officecli --version 2>/dev/null || echo found))"
fi

# claude — auto-install Claude Code CLI if not found
if ! command -v claude >/dev/null 2>&1; then
  echo "  Claude Code CLI not found. Installing via npm..."
  if command -v npm >/dev/null 2>&1; then
    npm install -g @anthropic-ai/claude-code 2>/dev/null && echo "  claude: installed" || \
      echo "  WARNING: Claude Code CLI install failed. Install manually: npm install -g @anthropic-ai/claude-code"
  elif command -v brew >/dev/null 2>&1; then
    brew install claude-code 2>/dev/null && echo "  claude: installed" || \
      echo "  WARNING: Claude Code CLI install failed. Install manually: https://docs.anthropic.com/en/docs/claude-code"
  else
    echo "  WARNING: Claude Code CLI not found and no npm/brew available."
    echo "           Install it to use the framework: https://docs.anthropic.com/en/docs/claude-code"
  fi
fi

echo ""

# 0b. Create required directories
echo "[0b/11] Creating required directories..."
mkdir -p "$CLAUDE_DIR/data/compressed_context"
mkdir -p "$CLAUDE_DIR/data/knowledge-db"
mkdir -p "$CLAUDE_DIR/circuit_breakers"
mkdir -p "$CLAUDE_DIR/skills/auto-generated"
mkdir -p "/tmp/claude"
echo "  -> ~/.claude/data/, circuit_breakers/, skills/auto-generated/, /tmp/claude/"

# 0c. Pre-warm uv dependency cache (prevents first-run hook timeouts)
echo "[0c/11] Pre-warming hook dependencies..."
UV_WARMUP=$(cat <<'PYEOF'
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pyyaml>=6.0.0",
#   "pydantic>=2.0.0",
# ]
# ///
"""Pre-warm: download all hook dependencies into uv cache."""
import yaml, pydantic  # noqa: F401, E401
print("  Core deps (pyyaml, pydantic): cached")
PYEOF
)

WARMUP_FILE=$(mktemp /tmp/caf_warmup_XXXX.py)
echo "$UV_WARMUP" > "$WARMUP_FILE"
if uv run --no-project "$WARMUP_FILE" 2>/dev/null; then
  : # success message already printed by script
else
  echo "  WARNING: Failed to pre-warm core deps. Hooks may timeout on first run."
  echo "           Try: uv pip install pyyaml pydantic"
fi

# Optional deps (don't fail install if these can't be cached)
UV_WARMUP_OPT=$(cat <<'PYEOF'
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "anthropic>=0.40.0",
# ]
# ///
"""Pre-warm: cache anthropic SDK for kr_mode and caddy hooks."""
import anthropic  # noqa: F401
print("  Optional deps (anthropic): cached")
PYEOF
)

OPT_FILE=$(mktemp /tmp/caf_warmup_opt_XXXX.py)
echo "$UV_WARMUP_OPT" > "$OPT_FILE"
uv run --no-project "$OPT_FILE" 2>/dev/null || echo "  Optional deps (anthropic): skipped (install later if needed)"
rm -f "$WARMUP_FILE" "$OPT_FILE"

echo ""

# 1. Validate all hook files exist before generating config
echo "[1/11] Validating hook files..."
ERRORS=0
SETTINGS_CONTENT=$(sed "s|__REPO_DIR__|$REPO_DIR|g" "$REPO_DIR/templates/settings.json.template" | sed "s|__HOME__|$HOME|g")
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

# 2. Generate settings.json from template (with dynamic PATH for uv)
echo "[2/11] Generating settings.json..."
mkdir -p "$CLAUDE_DIR"

# Build a PATH that guarantees hooks can find uv, python3, and git.
# Claude Code hooks run in a minimal shell env that may not inherit the user's
# full PATH (especially on macOS where ~/.local/bin is not in default PATH).
UV_BIN_DIR=$(dirname "$(command -v uv)")
PYTHON_BIN_DIR=$(dirname "$(command -v python3)")
GIT_BIN_DIR=$(dirname "$(command -v git)")

# Collect unique directories, preserving order
HOOK_PATH=""
for _dir in "$UV_BIN_DIR" "$PYTHON_BIN_DIR" "$GIT_BIN_DIR" \
            "$HOME/.local/bin" "$HOME/.cargo/bin" \
            "/opt/homebrew/bin" "/usr/local/bin" "/usr/bin" "/bin"; do
  case ":$HOOK_PATH:" in
    *":$_dir:"*) ;;  # already present
    *) HOOK_PATH="${HOOK_PATH:+$HOOK_PATH:}$_dir" ;;
  esac
done

# Inject PATH into env block of settings.json
export HOOK_PATH
SETTINGS_CONTENT=$(echo "$SETTINGS_CONTENT" | python3 -c "
import json, sys, os
data = json.load(sys.stdin)
hook_path = os.environ['HOOK_PATH']
data.setdefault('env', {})['PATH'] = hook_path
json.dump(data, sys.stdout, indent=2)
")

echo "$SETTINGS_CONTENT" > "$CLAUDE_DIR/settings.json"
echo "  -> $CLAUDE_DIR/settings.json"
echo "  -> Hook PATH: $HOOK_PATH"

# 3. Symlink commands (remove ALL existing symlinks first for clean install)
echo "[3/11] Linking commands..."
mkdir -p "$CLAUDE_DIR/commands"
find "$CLAUDE_DIR/commands" -maxdepth 1 -type l -delete 2>/dev/null || true
for f in "$REPO_DIR"/global-commands/*.md; do
  [ -f "$f" ] || continue
  ln -sf "$f" "$CLAUDE_DIR/commands/$(basename "$f")"
done
echo "  -> $(ls "$REPO_DIR"/global-commands/*.md 2>/dev/null | wc -l | tr -d ' ') commands"

# 4. Symlink skills (remove ALL existing symlinks first for clean install)
echo "[4/11] Linking skills..."
mkdir -p "$CLAUDE_DIR/skills"
find "$CLAUDE_DIR/skills" -maxdepth 1 -type l -delete 2>/dev/null || true
for skill_dir in "$REPO_DIR"/global-skills/*/; do
  [ -d "$skill_dir" ] || continue
  skill_name=$(basename "$skill_dir")
  ln -sf "$skill_dir" "$CLAUDE_DIR/skills/$skill_name"
done
echo "  -> $(ls -d "$REPO_DIR"/global-skills/*/ 2>/dev/null | wc -l | tr -d ' ') skills"
# Ensure auto-generated skills directory exists (used by auto_skill_generator hook)
mkdir -p "$CLAUDE_DIR/skills/auto-generated"
mkdir -p "$CLAUDE_DIR/data"

# 5. Symlink agents (remove ALL existing symlinks first for clean install)
echo "[5/11] Linking agents..."
mkdir -p "$CLAUDE_DIR/agents"
# Only create team subdir if source exists
if [ -d "$REPO_DIR/global-agents/team" ]; then
  mkdir -p "$CLAUDE_DIR/agents/team"
fi
find "$CLAUDE_DIR/agents" -maxdepth 2 -type l -delete 2>/dev/null || true
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
echo "[6/11] Generating docs..."
uv run "$REPO_DIR/scripts/generate_docs.py"

# 7. Write global CLAUDE.md with full-autonomy instructions
echo "[7/11] Writing global CLAUDE.md..."
GLOBAL_CLAUDE="$CLAUDE_DIR/CLAUDE.md"
YOLO_MARKER="# Autonomy: Yolo"
if [ -f "$GLOBAL_CLAUDE" ] && grep -q "$YOLO_MARKER" "$GLOBAL_CLAUDE"; then
  echo "  -> Already present, skipping."
else
  cat >> "$GLOBAL_CLAUDE" <<'YOLO'

# Autonomy: Yolo

Full autonomy mode. Execute all actions immediately without asking for confirmation:
- Read, write, edit any file
- Run any bash command
- Git operations including push, force-push, hard-reset, branch deletion
- Install packages, modify configs, delete files

Do NOT say "let me read X", "shall I proceed", or ask permission before any tool use. Just do it.
YOLO
  echo "  -> $GLOBAL_CLAUDE (appended yolo instructions)"
fi

# 8. Install git hooks (auto-doc before push)
echo "[8/11] Installing git hooks..."
if [ -d "$REPO_DIR/.git" ]; then
  cp "$REPO_DIR/scripts/pre-push-hook.sh" "$REPO_DIR/.git/hooks/pre-push"
  chmod +x "$REPO_DIR/.git/hooks/pre-push"
  echo "  -> .git/hooks/pre-push (auto-regenerates docs before every push)"
else
  echo "  Skipped: not a git repository"
fi

# 9. Final summary
echo "[9/11] Initializing memory files..."
# Create FACTS.md and MEMORY.md if they don't exist (hooks append to these)
for memfile in ".claude/FACTS.md" ".claude/MEMORY.md"; do
  target="$HOME/$memfile"
  if [ ! -f "$target" ]; then
    mkdir -p "$(dirname "$target")"
    touch "$target"
    echo "  -> Created ~/$memfile"
  fi
done

# Create project-level memory index if missing
if [ -d "$REPO_DIR/.claude" ] && [ ! -f "$REPO_DIR/.claude/MEMORY.md" ]; then
  touch "$REPO_DIR/.claude/MEMORY.md"
  echo "  -> Created .claude/MEMORY.md (project)"
fi
if [ -d "$REPO_DIR/.claude" ] && [ ! -f "$REPO_DIR/.claude/FACTS.md" ]; then
  touch "$REPO_DIR/.claude/FACTS.md"
  echo "  -> Created .claude/FACTS.md (project)"
fi

echo "[10/11] Verifying hook execution..."
# Quick smoke test: run a lightweight hook to verify uv + deps work
SMOKE_TEST=$(cat <<'PYEOF'
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pyyaml>=6.0.0",
#   "pydantic>=2.0.0",
# ]
# ///
import yaml, pydantic, json, sys  # noqa
# Simulate hook: read stdin (empty), output valid hook JSON
print(json.dumps({"result": "pass"}))
PYEOF
)
SMOKE_FILE=$(mktemp /tmp/caf_smoke_XXXX.py)
echo "$SMOKE_TEST" > "$SMOKE_FILE"
if echo '{}' | uv run --no-project "$SMOKE_FILE" >/dev/null 2>&1; then
  echo "  Hook smoke test: PASS"
else
  echo "  WARNING: Hook smoke test FAILED. Hooks may error at runtime."
  echo "           Check: uv --version, python3 --version"
  echo "           Try:   uv cache clean && bash install.sh"
fi
rm -f "$SMOKE_FILE"

echo "[11/11] Installation complete."
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
