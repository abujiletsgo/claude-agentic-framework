#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Auto Refine After Review
========================

PostToolUse hook that detects `/review` command completion,
parses review output for findings with severity >= WARNING,
and prompts to run `/refine` to auto-fix issues.

Hook event: PostToolUse
Exit codes:
  0 = Continue (always allows, may show prompt)
"""

import json
import sys
import re


def count_findings(tool_result):
    """
    Count findings with severity >= WARNING from review output.

    Looks for patterns like:
    - [WARNING], [ERROR], [CRITICAL], [!!], [!!!]
    - severity: warning, severity: error, severity: critical
    """
    if not tool_result:
        return 0

    text = str(tool_result).lower()

    # Count severity markers
    warning_count = len(re.findall(r'\[(warning|error|critical|!!+)\]', text, re.IGNORECASE))
    severity_count = len(re.findall(r'severity[:\s]+(warning|error|critical)', text, re.IGNORECASE))

    # Use the higher count
    return max(warning_count, severity_count)


def is_review_command(tool_name, tool_input):
    """Check if this is a review command execution."""
    if tool_name == "Skill":
        skill = tool_input.get("skill", "")
        return skill.lower() in ["review", "code-review"]

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        # Check for direct review script invocation
        return "review" in command.lower() and any(
            pattern in command.lower()
            for pattern in ["review.py", "review_engine", "/review"]
        )

    return False


def post_tool_use_handler():
    """PostToolUse hook - detect review completion and prompt for refine."""
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        return

    # Flat snake_case keys per Claude Code docs
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except json.JSONDecodeError:
            tool_input = {}

    tool_output = hook_input.get("tool_response", "")

    # Check if this is a review command
    if not is_review_command(tool_name, tool_input):
        return

    # Count findings
    issue_count = count_findings(tool_output)

    if issue_count == 0:
        # No issues found, continue silently
        return

    # Found issues - output to stderr (never block)
    print("\n" + "="*60, file=sys.stderr)
    print("🔍 CODE REVIEW COMPLETED", file=sys.stderr)
    print("="*60, file=sys.stderr)
    print(f"Found {issue_count} issue(s) with severity >= WARNING", file=sys.stderr)
    print(f"\nℹ️  Run /refine to auto-fix these issues", file=sys.stderr)
    print("="*60 + "\n", file=sys.stderr)


def main():
    """Main entry point."""
    try:
        post_tool_use_handler()
    except Exception as e:
        # Fail silently - should never block operations
        print(f"Auto refine error (non-blocking): {e}", file=sys.stderr)

    # Always exit 0 (never block workflow)
    sys.exit(0)


if __name__ == "__main__":
    main()
