#!/usr/bin/env python3
"""Inject ~/.claude/lessons.md into session context at startup."""
import json
import sys
from pathlib import Path


def main():
    lessons_file = Path.home() / '.claude' / 'lessons.md'

    if not lessons_file.exists():
        print(json.dumps({}))
        return

    content = lessons_file.read_text().strip()
    if len(content) < 10:
        print(json.dumps({}))
        return

    message = (
        "**LESSONS** — self-improvement log, apply these rules this session:\n\n"
        + content
    )
    print(json.dumps({"message": message}))


if __name__ == "__main__":
    try:
        sys.stdin.read()
        main()
    except Exception:
        print(json.dumps({}))
    sys.exit(0)
