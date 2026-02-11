#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "pydantic"]
# ///
"""
Post-Commit Review Hook
========================

Entry point for the continuous background review system.
Triggered by a git post-commit hook, runs analysis in the background,
and stores findings for later agent consumption.

Usage:
    # Direct invocation (foreground):
    uv run post_commit_review.py [--commit HASH] [--repo-root PATH] [--foreground]

    # From git hook (background):
    nohup uv run post_commit_review.py --commit "$1" &

    # Install git hook:
    uv run post_commit_review.py --install-hook [--repo-root PATH]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def get_latest_commit(repo_root: str = ".") -> str:
    """Get the hash of the latest commit."""
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
    return ""


def install_hook(repo_root: str) -> bool:
    """
    Install the post-commit git hook.

    Creates or appends to .git/hooks/post-commit to trigger
    background review on every commit.
    """
    git_dir = Path(repo_root) / ".git"
    if not git_dir.is_dir():
        print(f"Error: {repo_root} is not a git repository", file=sys.stderr)
        return False

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    hook_path = hooks_dir / "post-commit"
    script_path = Path(__file__).resolve()

    hook_content = f"""#!/bin/bash
# Continuous background review (roborev-style)
# Installed by: {script_path}
# Runs review asynchronously after each commit

COMMIT_HASH=$(git rev-parse HEAD)
REPO_ROOT=$(git rev-parse --show-toplevel)

# Check if review is enabled
REVIEW_CONFIG="$HOME/.claude/review_config.yaml"
if [ -f "$REVIEW_CONFIG" ]; then
    # Quick check: if config says enabled: false, skip
    if grep -q "^enabled: false" "$REVIEW_CONFIG" 2>/dev/null; then
        exit 0
    fi
fi

# Run review in background (non-blocking)
nohup uv run "{script_path}" \\
    --commit "$COMMIT_HASH" \\
    --repo-root "$REPO_ROOT" \\
    > /dev/null 2>&1 &

# Always exit successfully (never block commits)
exit 0
"""

    # Check if hook already exists
    if hook_path.exists():
        existing = hook_path.read_text()
        if "post_commit_review.py" in existing:
            print(f"Review hook already installed in {hook_path}")
            return True

        # Append to existing hook
        print(f"Appending review hook to existing {hook_path}")
        with open(hook_path, "a") as f:
            f.write("\n" + hook_content.split("#!/bin/bash\n", 1)[1])
    else:
        hook_path.write_text(hook_content)

    # Make executable
    hook_path.chmod(0o755)
    print(f"Installed review hook: {hook_path}")
    return True


def uninstall_hook(repo_root: str) -> bool:
    """Remove the review hook from post-commit."""
    git_dir = Path(repo_root) / ".git"
    hook_path = git_dir / "hooks" / "post-commit"

    if not hook_path.exists():
        print("No post-commit hook found")
        return True

    content = hook_path.read_text()
    if "post_commit_review.py" not in content:
        print("Review hook not found in post-commit")
        return True

    # Remove the review section
    lines = content.split("\n")
    new_lines = []
    skip = False
    for line in lines:
        if "Continuous background review" in line:
            skip = True
            continue
        if skip and line.strip() == "exit 0":
            skip = False
            continue
        if skip:
            continue
        new_lines.append(line)

    new_content = "\n".join(new_lines).strip()
    if new_content == "#!/bin/bash" or not new_content:
        hook_path.unlink()
        print(f"Removed review hook: {hook_path}")
    else:
        hook_path.write_text(new_content + "\n")
        print(f"Removed review section from: {hook_path}")

    return True


def run_review(commit_hash: str, repo_root: str, foreground: bool = False) -> int:
    """
    Run the review for a specific commit.

    Returns exit code (0 for success, 1 for failure).
    """
    from review_engine import ReviewEngine, load_review_config

    config = load_review_config()
    if not config.enabled:
        return 0

    engine = ReviewEngine(
        commit_hash=commit_hash,
        repo_root=repo_root,
        config=config,
    )

    result = engine.run()

    if foreground:
        # Print results to stdout when running in foreground
        print(f"\nReview Results for {commit_hash[:8]}")
        print(f"{'=' * 50}")
        print(f"Duration: {result.duration_seconds:.1f}s")
        print(f"Analyzers: {', '.join(result.analyzers_run)}")
        print(f"Findings: {len(result.findings)} ({result.findings_added} new)")

        if result.errors:
            print(f"\nErrors:")
            for err in result.errors:
                print(f"  - {err}")

        if result.findings:
            print(f"\nFindings:")
            for finding in result.findings:
                severity_icon = {
                    "critical": "[!!!]",
                    "error": "[!!]",
                    "warning": "[!]",
                    "info": "[i]",
                }.get(finding.severity, "[?]")
                print(f"  {severity_icon} {finding.title}")
                print(f"       {finding.file_path}:{finding.line_start or '?'}")
                if finding.suggestion:
                    print(f"       Fix: {finding.suggestion[:100]}")
                print()

    return 0 if result.success else 1


def show_status() -> None:
    """Show current review system status."""
    from findings_store import get_findings_summary, get_unresolved_findings
    from review_engine import load_review_config

    config = load_review_config()
    summary = get_findings_summary()
    unresolved = get_unresolved_findings(limit=5)

    print(f"\nReview System Status")
    print(f"{'=' * 40}")
    print(f"Enabled: {config.enabled}")
    print(f"Background: {config.background}")
    print(f"Analyzers: {', '.join(config.analysis_types)}")
    print(f"\nFindings Summary:")
    print(f"  Total: {summary['total']}")
    for status, count in summary.get("by_status", {}).items():
        print(f"  {status}: {count}")
    print(f"\nBy Severity:")
    for severity, count in summary.get("by_severity", {}).items():
        print(f"  {severity}: {count}")

    if unresolved:
        print(f"\nLatest Unresolved ({len(unresolved)}):")
        for f in unresolved[:5]:
            print(f"  [{f.get('severity', '?')}] {f.get('title', '?')}")
            print(f"    {f.get('file_path', '?')}:{f.get('line_start', '?')}")


def main():
    parser = argparse.ArgumentParser(
        description="Continuous background review system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--commit",
        help="Commit hash to review (default: HEAD)",
    )
    parser.add_argument(
        "--repo-root",
        help="Repository root path (default: auto-detect)",
    )
    parser.add_argument(
        "--foreground",
        action="store_true",
        help="Run in foreground with output (default: background/silent)",
    )
    parser.add_argument(
        "--install-hook",
        action="store_true",
        help="Install git post-commit hook",
    )
    parser.add_argument(
        "--uninstall-hook",
        action="store_true",
        help="Remove git post-commit hook",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show review system status",
    )

    args = parser.parse_args()

    # Determine repo root
    repo_root = args.repo_root
    if not repo_root:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            repo_root = result.stdout.strip() if result.returncode == 0 else "."
        except Exception:
            repo_root = "."

    if args.install_hook:
        sys.exit(0 if install_hook(repo_root) else 1)

    if args.uninstall_hook:
        sys.exit(0 if uninstall_hook(repo_root) else 1)

    if args.status:
        show_status()
        sys.exit(0)

    # Get commit hash
    commit_hash = args.commit or get_latest_commit(repo_root)
    if not commit_hash:
        print("Error: Could not determine commit hash", file=sys.stderr)
        sys.exit(1)

    sys.exit(run_review(commit_hash, repo_root, foreground=args.foreground))


if __name__ == "__main__":
    main()
