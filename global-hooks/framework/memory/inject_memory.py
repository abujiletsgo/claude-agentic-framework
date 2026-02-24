#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
inject_memory.py - SessionStart Hook (Layer 2: Project Mid-Term Memory)
========================================================================

Injects .claude/MEMORY.md — the project's rolling session history.

Captures what changed/was learned/was fixed across past sessions.
This is the mid-term layer that bridges FACTS.md (verified truths) and
PROJECT_CONTEXT.md (static architecture) — it records the *history of change*.

Injects only the last N sessions (default 5) to stay token-efficient.
Budget: ~1000 tokens.

Exit: always 0 (never blocks)
"""

import json
import os
import re
import sys
from pathlib import Path

MAX_SESSIONS = 5       # How many past session entries to inject
MAX_CHARS = 2000       # Token budget (~500 tokens)


def memory_path(cwd: str) -> Path:
    return Path(cwd).resolve() / ".claude" / "MEMORY.md"


def get_recent_sessions(content: str, max_sessions: int) -> str:
    """Extract the last N session entries from MEMORY.md."""
    # Sessions are delimited by "## YYYY-MM-DD" headers
    parts = re.split(r"(## \d{4}-\d{2}-\d{2})", content)

    if len(parts) <= 1:
        return content  # No session entries yet

    # Reconstruct session blocks: [header, body, header, body, ...]
    sessions = []
    i = 1
    while i < len(parts) - 1:
        header = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        sessions.append(header + body)
        i += 2

    # Take the most recent N
    recent = sessions[-max_sessions:]

    # Get the file header (everything before first ## date)
    file_header = parts[0]

    return file_header + "".join(recent)


def main():
    try:
        data = json.loads(sys.stdin.read())
        cwd = data.get("cwd", os.getcwd())
        path = memory_path(cwd)

        if not path.exists():
            print(json.dumps({}))
            sys.exit(0)

        content = path.read_text().strip()
        if not content:
            print(json.dumps({}))
            sys.exit(0)

        # Check if there are any actual session entries
        if "## 20" not in content:
            print(json.dumps({}))
            sys.exit(0)

        recent = get_recent_sessions(content, MAX_SESSIONS)

        # Trim to budget
        if len(recent) > MAX_CHARS:
            recent = recent[:MAX_CHARS] + "\n_[... older entries truncated]_"

        header = (
            "**PROJECT MEMORY** (recent session history) — "
            "what changed, was fixed, or was decided in past sessions.\n\n"
        )

        out = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": header + recent,
            }
        }
        print(json.dumps(out))

    except Exception as e:
        print(f"inject_memory error: {e}", file=sys.stderr)
        print(json.dumps({}))

    sys.exit(0)


if __name__ == "__main__":
    main()
