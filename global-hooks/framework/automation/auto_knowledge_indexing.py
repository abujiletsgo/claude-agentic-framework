#!/usr/bin/env python3
"""
Auto Knowledge DB Indexing - PostCommit Hook

Extracts commit context and indexes it into the knowledge database
for cross-session learning. Runs asynchronously after commits.

Usage:
    Called automatically after git commits by Claude Code.
    Extracts commit message, changed files, and patterns.
    Indexes to ~/.claude/knowledge.db using knowledge_db.py.

What it indexes:
- Commit messages as DECISION or LEARNED
- Error resolutions as FACT
- Code patterns as PATTERN

Exit codes:
    0: Always (never block commits)
"""

import json
import sys
import re
import subprocess
from pathlib import Path
from datetime import datetime, timezone


def run_git_command(args, cwd="."):
    """Run a git command and return output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, OSError):
        return None


def get_commit_info(commit_hash=None):
    """Extract commit message and files changed."""
    if not commit_hash:
        commit_hash = "HEAD"

    # Get commit message
    message = run_git_command(["log", "-1", "--pretty=%B", commit_hash])
    if not message:
        return None

    # Get files changed
    files_output = run_git_command([
        "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash
    ])
    files = files_output.split("\n") if files_output else []

    # Get commit author and timestamp
    author = run_git_command(["log", "-1", "--pretty=%an", commit_hash])
    timestamp = run_git_command(["log", "-1", "--pretty=%cI", commit_hash])

    return {
        "hash": commit_hash,
        "message": message,
        "files": [f for f in files if f],
        "author": author,
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
    }


def extract_error_resolutions(commit_message):
    """
    Extract error resolutions from commit message.

    Looks for patterns like:
    - "Fix: <description>"
    - "Resolve: <description>"
    - "Error: <description> -> Solution: <description>"
    - "Bug fix: <description>"
    """
    resolutions = []

    # Fix pattern
    fix_match = re.search(r'(?:fix|fixes|fixed):\s*(.+?)(?:\n|$)', commit_message, re.IGNORECASE)
    if fix_match:
        resolutions.append(f"Fix: {fix_match.group(1).strip()}")

    # Resolve pattern
    resolve_match = re.search(r'(?:resolve|resolves|resolved):\s*(.+?)(?:\n|$)', commit_message, re.IGNORECASE)
    if resolve_match:
        resolutions.append(f"Resolve: {resolve_match.group(1).strip()}")

    # Bug fix pattern
    bug_match = re.search(r'bug\s+fix:\s*(.+?)(?:\n|$)', commit_message, re.IGNORECASE)
    if bug_match:
        resolutions.append(f"Bug fix: {bug_match.group(1).strip()}")

    return resolutions


def extract_patterns(commit_message, files):
    """
    Extract learned patterns from commit context.

    Examples:
    - Refactoring patterns
    - Architecture decisions
    - Performance improvements
    """
    patterns = []

    message_lower = commit_message.lower()

    # Refactoring
    if any(word in message_lower for word in ["refactor", "restructure", "reorganize"]):
        patterns.append(f"Refactoring: {commit_message.split('\n')[0][:100]}")

    # Performance
    if any(word in message_lower for word in ["perf", "performance", "optimize", "speed"]):
        patterns.append(f"Performance: {commit_message.split('\n')[0][:100]}")

    # Architecture
    if any(word in message_lower for word in ["architecture", "design", "pattern"]):
        patterns.append(f"Architecture: {commit_message.split('\n')[0][:100]}")

    # File-based patterns
    if files:
        extensions = {Path(f).suffix for f in files if Path(f).suffix}
        if extensions:
            patterns.append(f"Modified {', '.join(extensions)} files")

    return patterns


def index_to_knowledge_db(commit_info):
    """
    Index commit information to knowledge database.

    Uses the knowledge_db.py module from framework/knowledge/.
    """
    # Import knowledge_db module
    framework_dir = Path(__file__).parent.parent / "knowledge"
    sys.path.insert(0, str(framework_dir))

    try:
        from knowledge_db import add_knowledge

        # Add commit message as DECISION or LEARNED
        tag = "DECISION" if any(
            word in commit_info["message"].lower()
            for word in ["decide", "decision", "choose", "architecture"]
        ) else "LEARNED"

        content = f"Commit: {commit_info['message'][:200]}"
        metadata = {
            "commit_hash": commit_info["hash"][:8],
            "files_changed": len(commit_info["files"]),
            "timestamp": commit_info["timestamp"],
        }

        add_knowledge(
            content=content,
            tag=tag,
            context="git-commit",
            metadata=metadata,
        )

        # Add error resolutions as FACT
        import re
        resolutions = extract_error_resolutions(commit_info["message"])
        for resolution in resolutions:
            add_knowledge(
                content=resolution,
                tag="FACT",
                context="error-resolution",
                metadata={"commit_hash": commit_info["hash"][:8]},
            )

        # Add patterns as PATTERN
        patterns = extract_patterns(commit_info["message"], commit_info["files"])
        for pattern in patterns:
            add_knowledge(
                content=pattern,
                tag="PATTERN",
                context="commit-pattern",
                metadata={"commit_hash": commit_info["hash"][:8]},
            )

        return True

    except ImportError:
        # knowledge_db module not available, skip silently
        return False
    except Exception as e:
        # Log error to stderr but don't fail the commit
        print(f"Knowledge indexing error: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point for auto knowledge indexing hook."""
    try:
        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        # Get commit info from the latest commit
        commit_hash = "HEAD"
        commit_info = get_commit_info(commit_hash)

        if not commit_info:
            # Unable to get commit info, continue silently
            sys.exit(0)

        # Index to knowledge DB (silent operation)
        success = index_to_knowledge_db(commit_info)

        if success:
            # Optionally log success to stderr in verbose mode
            # print(f"✓ Indexed commit {commit_info['hash'][:8]} to knowledge DB", file=sys.stderr)
            pass

    except Exception as e:
        # Never fail the commit, just log to stderr
        print(f"Auto knowledge indexing error (non-blocking): {e}", file=sys.stderr)

    # Always exit 0 (never block commits)
    sys.exit(0)


if __name__ == "__main__":
    main()
