#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""Task Quality Gate - TaskCompleted hook. Logs completion metrics and nudges
the agent to verify tests when the task description mentions test requirements.
Always exits 0 (observability + gentle nudge, never blocks)."""

import json, sys
from datetime import datetime, timezone
from pathlib import Path

TEST_KEYWORDS = {"test", "verify", "validate", "check"}


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}
    if not data:
        sys.exit(0)

    task_id = data.get("task_id", "unknown")
    task_subject = data.get("task_subject", "")
    task_desc = data.get("task_description", "")
    teammate = data.get("teammate_name", "")

    # Log completion to JSONL
    log_path = Path.home() / ".claude" / "data" / "task_completions.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "task_subject": task_subject,
        "teammate_name": teammate,
    }
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass

    # Session completion count (all entries in the log)
    count = 0
    try:
        with open(log_path) as f:
            count = sum(1 for _ in f)
    except OSError:
        pass

    # Check for test requirements in description
    desc_lower = task_desc.lower()
    has_test_req = any(kw in desc_lower for kw in TEST_KEYWORDS)

    output = {}
    if has_test_req:
        output = {"hookSpecificOutput": {
            "hookEventName": "TaskCompleted",
            "additionalContext": (
                f"[Quality Gate] Task '{task_subject}' mentions testing requirements. "
                "Please confirm that all relevant tests pass before considering this done."
            )
        }}
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
