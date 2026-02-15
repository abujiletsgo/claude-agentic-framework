#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""
Auto Review Team - Pre-Tool-Use Hook
=====================================

Automatically detects PR creation commands and offers to spawn a review team.

Detects:
  - gh pr create
  - git push with branch containing "pr/" or "pull/"
  - gh pr ready (converting draft to ready)

Triggered: Before Bash tool executes
Action: Prompts user to spawn review team if issues found
Exit: Always 0 (allows command to proceed)

The review team performs parallel analysis:
  - Security reviewer (Opus) - vulnerabilities, auth issues
  - Performance reviewer (Sonnet) - bottlenecks, complexity
  - Architecture reviewer (Opus) - design patterns, maintainability

Usage:
    # From Claude Code pre-tool-use hook:
    cat hook_input.json | uv run auto_review_team.py

Input JSON format:
    {
        "tool_name": "Bash",
        "tool_input": {
            "command": "gh pr create --title \"...\""
        }
    }
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml


def is_pr_command(command: str) -> bool:
    """
    Check if command is PR-related.

    Args:
        command: Bash command to check

    Returns:
        True if command creates/updates a PR
    """
    pr_patterns = [
        r"\bgh\s+pr\s+create\b",
        r"\bgh\s+pr\s+ready\b",
        r"\bgit\s+push\b.*\b(pr|pull)/",
    ]

    for pattern in pr_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return True

    return False


def get_current_branch() -> str:
    """
    Get current git branch name.

    Returns:
        Branch name or empty string
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        pass

    return ""


def count_review_findings() -> int:
    """
    Quick count of existing review findings.

    Returns:
        Number of unresolved findings
    """
    # Check for review findings store
    home = Path.home()
    findings_file = home / ".claude" / "review_findings.json"

    if not findings_file.exists():
        return 0

    try:
        with open(findings_file) as f:
            data = json.load(f)

        # Handle both dict and list formats
        if isinstance(data, dict):
            findings = data.get("findings", [])
        elif isinstance(data, list):
            findings = data
        else:
            return 0

        # Count unresolved findings
        unresolved = [
            f for f in findings
            if isinstance(f, dict) and f.get("status") in ("new", "open")
        ]
        return len(unresolved)

    except (json.JSONDecodeError, OSError):
        return 0


def load_team_template() -> dict | None:
    """
    Load the review team template.

    Returns:
        Team template dict or None if not found
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    template_path = Path(project_dir) / "data" / "team_templates" / "review_team.yaml"

    if not template_path.exists():
        return None

    try:
        with open(template_path) as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, OSError):
        return None


def prompt_user_for_review(findings_count: int) -> dict:
    """
    Generate permission request for spawning review team.

    Args:
        findings_count: Number of existing review findings

    Returns:
        Hook output dict with permission decision
    """
    if findings_count > 0:
        reason = (
            f"Found {findings_count} existing review finding(s). "
            "Spawn review team to analyze changes before creating PR? [Y/n]"
        )
    else:
        reason = (
            "No recent review findings. "
            "Spawn review team to analyze changes before creating PR? [Y/n]"
        )

    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }


def spawn_review_team() -> None:
    """
    Spawn the review team (placeholder).

    In production, this would:
    1. Load team template from data/team_templates/review_team.yaml
    2. Spawn teammate agents (security, performance, architecture)
    3. Coordinate parallel review
    4. Synthesize findings
    """
    print("[Auto Review Team] Spawning review team...", file=sys.stderr)

    template = load_team_template()
    if not template:
        print("[Auto Review Team] Error: review_team.yaml not found", file=sys.stderr)
        return

    team_name = template.get("name", "Code Review Team")
    teammates = template.get("teammates", [])

    print(f"[Auto Review Team] Team: {team_name}", file=sys.stderr)
    print(f"[Auto Review Team] Members:", file=sys.stderr)
    for teammate in teammates:
        name = teammate.get("name", "unknown")
        model = teammate.get("model", "unknown")
        focus = teammate.get("focus_area", "unknown")
        print(f"  - {name} ({model}): {focus}", file=sys.stderr)

    # Placeholder for actual team spawning
    # In production, this would use Claude Code's team system:
    # 1. TeamCreate with review_team template
    # 2. Spawn teammates in parallel
    # 3. Each teammate analyzes their domain
    # 4. Architecture reviewer synthesizes results
    # 5. Present consolidated findings to user


def main():
    """Main entry point for pre-tool-use hook."""
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only process Bash tool
    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")
    if not command:
        sys.exit(0)

    # Check if command is PR-related
    if not is_pr_command(command):
        sys.exit(0)

    # Additional check for push commands with pr/pull branches
    if "git push" in command.lower():
        branch = get_current_branch()
        if not ("pr/" in branch.lower() or "pull/" in branch.lower()):
            sys.exit(0)

    # Count existing review findings
    findings_count = count_review_findings()

    # Prompt user for review team spawn
    output = prompt_user_for_review(findings_count)
    print(json.dumps(output))

    # Exit 0 to allow command to proceed
    # User can choose to spawn team or proceed without review
    sys.exit(0)


if __name__ == "__main__":
    main()
