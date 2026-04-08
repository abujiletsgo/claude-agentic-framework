#!/usr/bin/env python3
"""
Auto Code Review - Post-Commit Git Hook

Runs code review asynchronously after each commit. Calls review_engine.py
in background and stores findings in knowledge DB.

Usage:
    Install to .git/hooks/post-commit in the repository.
    Runs in background (non-blocking).
    Uses review_engine.py for analysis.

Installation:
    This script is typically installed by the framework's setup process.
    Manual installation:
        cp auto_code_review.py /path/to/repo/.git/hooks/post-commit
        chmod +x /path/to/repo/.git/hooks/post-commit

Exit codes:
    0: Always (never block commits)
"""

import subprocess
import sys
from pathlib import Path


def get_repo_root():
    """Get git repository root."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def get_commit_hash():
    """Get current commit hash (HEAD)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def check_review_enabled():
    """Check if review is enabled in config."""
    config_path = Path.home() / ".claude" / "review_config.yaml"
    if not config_path.exists():
        return True  # Default: enabled

    try:
        with open(config_path, "r") as f:
            content = f.read()
        # Simple check: if config says enabled: false, skip
        if "enabled: false" in content or "enabled:false" in content:
            return False
    except Exception:
        pass

    return True


def run_review_background(commit_hash, repo_root):
    """Run review in background (non-blocking).

    Uses nohup to detach from git process and run asynchronously.
    """
    # Path to review engine
    review_engine = Path(__file__).parent.parent / "review" / "review_engine.py"

    if not review_engine.exists():
        return

    # Path to Python wrapper script (post_commit_review.py)
    wrapper_script = Path(__file__).parent.parent / "review" / "post_commit_review.py"

    if wrapper_script.exists():
        # Use the wrapper script if available
        try:
            # Run in background with nohup
            subprocess.Popen(
                ["nohup", "uv", "run", str(wrapper_script), "--commit", commit_hash],
                cwd=repo_root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,  # Detach from parent process
            )
        except Exception:
            pass
    else:
        # Fallback: run review engine directly
        try:
            subprocess.Popen(
                [
                    "nohup", "uv", "run", "python3", str(review_engine),
                    "--commit", commit_hash,
                    "--repo-root", repo_root,
                ],
                cwd=repo_root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception:
            pass


def main():
    """Main entry point for auto code review hook."""
    try:
        # Check if review is enabled
        if not check_review_enabled():
            sys.exit(0)

        # Get commit hash
        commit_hash = get_commit_hash()
        if not commit_hash:
            sys.exit(0)

        # Get repo root
        repo_root = get_repo_root()
        if not repo_root:
            sys.exit(0)

        # Run review in background
        run_review_background(commit_hash, repo_root)

    except Exception as e:
        # Fail silently - review should never block commits
        pass

    # Always exit 0 (never block commits)
    sys.exit(0)


if __name__ == "__main__":
    main()
