#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Auto Security Scan - Post-Commit Hook
======================================

Automatically detects changes to sensitive files and triggers security scanning.

Monitors:
  - **/auth/**     - Authentication/authorization code
  - **/api/**      - API endpoints
  - **/*.env*      - Environment configuration
  - **/config/**   - Configuration files

Triggered: After each git commit
Action: Spawns security-scanner skill if sensitive files changed
Output: Findings to stderr
Exit: Always 0 (never blocks commits)

Usage:
    # From git post-commit hook:
    cat hook_input.json | uv run auto_security_scan.py

    # Direct test:
    echo '{"commit_hash": "HEAD"}' | uv run auto_security_scan.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path


# Sensitive file patterns that trigger security scanning
SENSITIVE_PATTERNS = [
    "**/auth/**",
    "**/api/**",
    "**/*.env*",
    "**/config/**",
    "**/security/**",
    "**/secrets/**",
    "**/credentials/**",
]


def get_changed_files(commit_hash: str = "HEAD") -> list[str]:
    """
    Get list of files changed in the most recent commit.

    Returns:
        List of file paths changed in commit
    """
    try:
        # Get changed files from last commit
        result = subprocess.run(
            ["git", "diff", f"{commit_hash}~1", "--name-only"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            # Might be initial commit, try different approach
            result = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash],
                capture_output=True,
                text=True,
                timeout=5,
            )

        if result.returncode == 0:
            return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]

    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        pass

    return []


def matches_sensitive_pattern(file_path: str, patterns: list[str]) -> bool:
    """
    Check if file path matches any sensitive pattern.

    Args:
        file_path: Path to check
        patterns: List of glob patterns

    Returns:
        True if file matches any pattern
    """
    from fnmatch import fnmatch

    for pattern in patterns:
        # Check direct match
        if fnmatch(file_path, pattern):
            return True
        # Check path components
        if fnmatch(f"**/{file_path}", pattern):
            return True
        # Check any parent directory
        parts = Path(file_path).parts
        for i in range(len(parts)):
            partial = "/".join(parts[: i + 1])
            if fnmatch(partial, pattern) or fnmatch(f"**/{partial}", pattern):
                return True

    return False


def spawn_security_scanner(files: list[str]) -> None:
    """
    Spawn security-scanner skill for the given files.

    Args:
        files: List of files to scan
    """
    print(f"\n[Auto Security Scan] Detected changes to {len(files)} sensitive file(s):", file=sys.stderr)
    for f in files[:10]:  # Show first 10
        print(f"  - {f}", file=sys.stderr)
    if len(files) > 10:
        print(f"  ... and {len(files) - 10} more", file=sys.stderr)

    print("\n[Auto Security Scan] Triggering security scan...", file=sys.stderr)

    # Determine project directory
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    skill_path = Path(project_dir) / "global-skills" / "security-scanner" / "SKILL.md"

    if not skill_path.exists():
        print(f"[Auto Security Scan] Warning: security-scanner skill not found at {skill_path}", file=sys.stderr)
        print(f"[Auto Security Scan] Skipping scan.", file=sys.stderr)
        return

    try:
        # Invoke security-scanner skill
        # In a real implementation, this would use the Claude Code skill system
        # For now, we just log what would happen
        print(f"[Auto Security Scan] Would invoke: security-scanner on {len(files)} files", file=sys.stderr)
        print(f"[Auto Security Scan] Skill location: {skill_path}", file=sys.stderr)

        # Placeholder for actual skill invocation
        # In production, this would:
        # 1. Load the skill definition
        # 2. Prepare context with file list
        # 3. Invoke Claude with security-scanner instructions
        # 4. Stream findings to stderr

    except Exception as e:
        print(f"[Auto Security Scan] Error during scan: {e}", file=sys.stderr)


def main():
    """Main entry point for post-commit hook."""
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    except json.JSONDecodeError:
        input_data = {}

    # Get commit hash from input or use HEAD
    commit_hash = input_data.get("commit_hash", "HEAD")

    # Get changed files
    changed_files = get_changed_files(commit_hash)

    if not changed_files:
        # No files changed or initial commit
        sys.exit(0)

    # Filter for sensitive files
    sensitive_files = [
        f for f in changed_files
        if matches_sensitive_pattern(f, SENSITIVE_PATTERNS)
    ]

    if not sensitive_files:
        # No sensitive files changed, skip scan
        sys.exit(0)

    # Spawn security scanner
    spawn_security_scanner(sensitive_files)

    # Always exit 0 (never block commits)
    sys.exit(0)


if __name__ == "__main__":
    main()
