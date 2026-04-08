#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Findings Notifier - SessionStart context injection.

On session start, checks for unresolved review findings and
formats them as context for the agent. After injection, marks
findings as "notified" to avoid repeated notifications.

Usage as a SessionStart hook:
    In settings.json hooks.SessionStart:
    {
        "type": "command",
        "command": "uv run .../findings_notifier.py",
        "timeout": 5
    }

Or called programmatically:
    from findings_notifier import get_notification_context
    context = get_notification_context()
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from findings_store import (
    get_unresolved_findings,
    mark_as_notified,
    get_findings_summary,
)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

SEVERITY_ICONS = {
    "critical": "CRITICAL",
    "error": "ERROR",
    "warning": "WARN",
    "info": "INFO",
}

MAX_FINDINGS_IN_CONTEXT = 10  # Don't overwhelm the agent


def format_finding_for_context(finding: dict) -> str:
    """Format a single finding for agent context injection."""
    severity = SEVERITY_ICONS.get(finding.get("severity", ""), "?")
    title = finding.get("title", "Unknown finding")
    file_path = finding.get("file_path", "?")
    line_start = finding.get("line_start")
    suggestion = finding.get("suggestion", "")
    commit = finding.get("commit_hash", "?")[:8]

    location = file_path
    if line_start:
        location += f":{line_start}"

    lines = [
        f"  [{severity}] {title}",
        f"    Location: {location} (commit {commit})",
    ]
    if suggestion:
        lines.append(f"    Suggestion: {suggestion[:200]}")

    return "\n".join(lines)


def get_notification_context() -> str:
    """
    Build context string for unresolved findings.

    Returns empty string if no findings to report.
    """
    unresolved = get_unresolved_findings(limit=MAX_FINDINGS_IN_CONTEXT + 5)

    # Filter to only "open" (not yet notified) findings first
    open_findings = [f for f in unresolved if f.get("status") == "open"]

    # If no new findings, check if there are previously notified but unresolved
    if not open_findings:
        # Only re-notify if there are critical/error findings still unresolved
        critical = [
            f for f in unresolved
            if f.get("severity") in ("critical", "error")
            and f.get("status") == "notified"
        ]
        if not critical:
            return ""
        open_findings = critical[:3]  # Limit re-notifications

    # Cap the number of findings
    findings_to_show = open_findings[:MAX_FINDINGS_IN_CONTEXT]
    remaining = len(open_findings) - len(findings_to_show)

    # Build context
    parts = [
        "## Code Review Findings (Unresolved)",
        "",
        f"The continuous review system found {len(open_findings)} unresolved issue(s):",
        "",
    ]

    for finding in findings_to_show:
        parts.append(format_finding_for_context(finding))
        parts.append("")

    if remaining > 0:
        parts.append(f"  ... and {remaining} more findings.")
        parts.append("")

    parts.extend([
        "To resolve: fix the issues and commit, or mark as wontfix.",
        "To see all findings: check ~/.claude/review_findings.json",
    ])

    # Mark shown findings as notified
    finding_ids = [f.get("id") for f in findings_to_show if f.get("id")]
    if finding_ids:
        mark_as_notified(finding_ids)

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Hook entry point
# ---------------------------------------------------------------------------


def main():
    """
    SessionStart hook entry point.

    Reads hook input from stdin, outputs additionalContext if there
    are unresolved findings.
    """
    try:
        # Read stdin (hook input)
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, Exception):
        input_data = {}

    context = get_notification_context()

    if context:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            }
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
