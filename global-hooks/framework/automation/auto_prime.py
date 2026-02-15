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


def load_context_silently(cache_file):
    """Load cached context into internal understanding (no output).

    This function would be called by Claude Code to inject the cached
    context into the conversation context. For now, we just validate
    the cache exists and is loadable.
    """
    try:
        if not cache_file.exists():
            return False

        # Validate file is readable and has content
        with open(cache_file, "r") as f:
            content = f.read()

        # Basic validation: should have git hash comment and content
        if "GIT_HASH:" in content and len(content) > 500:
            return True
    except Exception:
        pass
    return False


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
            # No cache - user can manually run /prime if needed
            sys.exit(0)

        # Get current git hash
        current_hash = get_git_hash(repo_root)
        if not current_hash:
            # Not a git repo or git unavailable - skip
            sys.exit(0)

        # Get cached hash
        cached_hash = get_cached_hash(cache_file)
        if not cached_hash:
            # Cache missing hash metadata - treat as stale
            sys.exit(0)

        # Compare hashes
        if current_hash != cached_hash:
            # Cache is stale - user can manually run /prime
            sys.exit(0)

        # Cache is valid - load silently
        if load_context_silently(cache_file):
            # Successfully loaded - no output (silent load)
            # In a full implementation, this would inject context into
            # the conversation via Claude Code's context system
            pass

    except Exception as e:
        # Fail silently - auto prime should never block session start
        print(f"Auto prime error (non-blocking): {e}", file=sys.stderr)

    # Always exit 0 (never block session start)
    sys.exit(0)


if __name__ == "__main__":
    main()
