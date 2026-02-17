#!/usr/bin/env python3
"""
Auto Prime - SessionStart Hook

Automatically loads cached project context if valid, skips if stale/missing.
User can manually run /prime if context is missing or stale.

Usage:
    Called automatically at session start by Claude Code.
    Checks .claude/PROJECT_CONTEXT.md for cached context.
    Validates git hash matches current HEAD.

Behavior:
    - Valid cache: Load silently (no output)
    - Stale/missing: Skip silently (user can manually /prime)

Exit codes:
    0: Always (never block session start)
"""

import json
import subprocess
import sys
from pathlib import Path


def get_git_hash(repo_root):
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def get_cached_hash(cache_file):
    """Extract git hash from cached context file."""
    try:
        if not cache_file.exists():
            return None

        # Read first line which should contain: <!-- GIT_HASH: abc123 -->
        with open(cache_file, "r") as f:
            first_line = f.readline().strip()

        # Extract hash (40 character hex string)
        import re
        match = re.search(r'[a-f0-9]{40}', first_line)
        if match:
            return match.group(0)
    except Exception:
        pass
    return None


def load_cached_context(cache_file):
    """Load cached context and return content if valid."""
    try:
        if not cache_file.exists():
            return None

        # Read and validate content
        with open(cache_file, "r") as f:
            content = f.read()

        # Basic validation: should have git hash comment and content
        if "GIT_HASH:" in content and len(content) > 500:
            return content
    except Exception:
        pass
    return None


def emit_and_exit(message=None):
    """Output valid JSON and exit 0."""
    result = {"result": "continue"}
    if message:
        result["message"] = message
    print(json.dumps(result))
    sys.exit(0)


def main():
    """Main entry point for auto prime hook."""
    try:
        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        # Get current working directory from hook input or use cwd
        cwd = hook_input.get("cwd", ".")
        repo_root = Path(cwd).resolve()

        # Path to cached context
        cache_file = repo_root / ".claude" / "PROJECT_CONTEXT.md"

        # Check if cache exists
        if not cache_file.exists():
            emit_and_exit()

        # Load cached content regardless of staleness
        cached_content = load_cached_context(cache_file)
        if cached_content:
            # Check if stale (inform Claude but still load)
            current_hash = get_git_hash(repo_root)
            cached_hash = get_cached_hash(cache_file)
            stale = current_hash and cached_hash and current_hash != cached_hash

            if stale:
                cached_content += "\n\n> **Note:** Project context cache may be slightly stale (new commits since last /prime). Run /prime to refresh."

            emit_and_exit(message=cached_content)

    except Exception as e:
        print(f"Auto prime error (non-blocking): {e}", file=sys.stderr)

    emit_and_exit()


if __name__ == "__main__":
    main()
