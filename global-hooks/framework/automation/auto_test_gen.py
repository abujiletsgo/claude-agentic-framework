#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Auto Test Generation - Post-Commit Hook
========================================

Automatically detects new source files without corresponding test coverage
and triggers test generation.

Pattern:
  - src/**/*.py  requires  tests/**/*_test.py
  - src/**/*.js  requires  tests/**/*.test.js
  - src/**/*.ts  requires  tests/**/*.test.ts

Triggered: After each git commit
Action: Spawns test-generator skill for uncovered files
Output: Test skeleton location
Exit: Always 0 (never blocks commits)

Usage:
    # From git post-commit hook:
    cat hook_input.json | uv run auto_test_gen.py

    # Direct test:
    echo '{"commit_hash": "HEAD"}' | uv run auto_test_gen.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path


# Source -> Test path mappings
TEST_PATTERNS = {
    ".py": {
        "source_dirs": ["src", "lib", "app"],
        "test_dir": "tests",
        "test_suffix": "_test.py",
    },
    ".js": {
        "source_dirs": ["src", "lib"],
        "test_dir": "tests",
        "test_suffix": ".test.js",
    },
    ".ts": {
        "source_dirs": ["src", "lib"],
        "test_dir": "tests",
        "test_suffix": ".test.ts",
    },
}


def get_new_files(commit_hash: str = "HEAD") -> list[str]:
    """
    Get list of newly added files in the most recent commit.

    Returns:
        List of newly added file paths
    """
    try:
        # Get added files from last commit
        result = subprocess.run(
            ["git", "diff", f"{commit_hash}~1", "--name-status", "--diff-filter=A"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            # Might be initial commit, try different approach
            result = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-status", "--diff-filter=A", "-r", commit_hash],
                capture_output=True,
                text=True,
                timeout=5,
            )

        if result.returncode == 0:
            files = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    parts = line.split("\t", 1)
                    if len(parts) == 2 and parts[0] == "A":
                        files.append(parts[1].strip())
            return files

    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        pass

    return []


def is_source_file(file_path: str) -> bool:
    """
    Check if file is a source file that needs tests.

    Args:
        file_path: Path to check

    Returns:
        True if file is a source file in a tracked directory
    """
    path = Path(file_path)
    ext = path.suffix

    if ext not in TEST_PATTERNS:
        return False

    # Check if in source directory
    pattern = TEST_PATTERNS[ext]
    for source_dir in pattern["source_dirs"]:
        if source_dir in path.parts:
            return True

    return False


def get_expected_test_path(source_path: str) -> str:
    """
    Get the expected test file path for a source file.

    Args:
        source_path: Path to source file

    Returns:
        Expected test file path
    """
    path = Path(source_path)
    ext = path.suffix

    if ext not in TEST_PATTERNS:
        return ""

    pattern = TEST_PATTERNS[ext]

    # Replace source dir with test dir
    parts = list(path.parts)
    for i, part in enumerate(parts):
        if part in pattern["source_dirs"]:
            parts[i] = pattern["test_dir"]
            break

    # Change suffix
    stem = path.stem
    new_name = stem + pattern["test_suffix"]
    parts[-1] = new_name

    return str(Path(*parts))


def test_file_exists(test_path: str) -> bool:
    """
    Check if test file exists.

    Args:
        test_path: Path to test file

    Returns:
        True if test file exists
    """
    return Path(test_path).exists()


def spawn_test_generator(uncovered_files: list[tuple[str, str]]) -> None:
    """
    Spawn test-generator skill for uncovered files.

    Args:
        uncovered_files: List of (source_path, test_path) tuples
    """
    print(f"\n[Auto Test Gen] Detected {len(uncovered_files)} new source file(s) without tests:", file=sys.stderr)
    for source, test in uncovered_files[:10]:  # Show first 10
        print(f"  - {source} -> {test}", file=sys.stderr)
    if len(uncovered_files) > 10:
        print(f"  ... and {len(uncovered_files) - 10} more", file=sys.stderr)

    print("\n[Auto Test Gen] Triggering test generation...", file=sys.stderr)

    # Determine project directory
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    skill_path = Path(project_dir) / "global-skills" / "test-generator" / "SKILL.md"

    if not skill_path.exists():
        print(f"[Auto Test Gen] Warning: test-generator skill not found at {skill_path}", file=sys.stderr)
        print(f"[Auto Test Gen] Skipping test generation.", file=sys.stderr)
        return

    try:
        # Invoke test-generator skill
        # In a real implementation, this would use the Claude Code skill system
        # For now, we just log what would happen
        print(f"[Auto Test Gen] Would invoke: test-generator for {len(uncovered_files)} files", file=sys.stderr)
        print(f"[Auto Test Gen] Skill location: {skill_path}", file=sys.stderr)

        # Show where tests would be created
        print(f"\n[Auto Test Gen] Test skeletons would be created at:", file=sys.stderr)
        for source, test in uncovered_files:
            print(f"  {test}", file=sys.stderr)

        # Placeholder for actual skill invocation
        # In production, this would:
        # 1. Load the skill definition
        # 2. For each source file, analyze structure
        # 3. Generate test skeleton with Claude
        # 4. Write test files to expected locations
        # 5. Report results

    except Exception as e:
        print(f"[Auto Test Gen] Error during generation: {e}", file=sys.stderr)


def main():
    """Main entry point for post-commit hook."""
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    except json.JSONDecodeError:
        input_data = {}

    # Get commit hash from input or use HEAD
    commit_hash = input_data.get("commit_hash", "HEAD")

    # Get newly added files
    new_files = get_new_files(commit_hash)

    if not new_files:
        # No new files
        sys.exit(0)

    # Filter for source files
    source_files = [f for f in new_files if is_source_file(f)]

    if not source_files:
        # No new source files
        sys.exit(0)

    # Check for missing tests
    uncovered = []
    for source in source_files:
        test_path = get_expected_test_path(source)
        if test_path and not test_file_exists(test_path):
            uncovered.append((source, test_path))

    if not uncovered:
        # All source files have tests
        sys.exit(0)

    # Spawn test generator
    spawn_test_generator(uncovered)

    # Always exit 0 (never block commits)
    sys.exit(0)


if __name__ == "__main__":
    main()
