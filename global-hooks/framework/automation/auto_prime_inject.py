#!/usr/bin/env python3
"""
Auto-Prime Inject - UserPromptSubmit Hook

Fires before every user message. If the project has no prime cache,
injects a mandatory instruction to run /prime FIRST before responding.

Once .claude/PROJECT_CONTEXT.md exists, this is a no-op (fast file check).

Exit codes:
    0: Always (never blocks)
"""

import json
import sys
from pathlib import Path


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
        cwd = hook_input.get("cwd", ".")
        cache_file = Path(cwd) / ".claude" / "PROJECT_CONTEXT.md"

        if not cache_file.exists():
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": (
                        "[MANDATORY STARTUP ACTION] No project context cache found at "
                        "`.claude/PROJECT_CONTEXT.md`. You MUST invoke the `/prime` skill "
                        "as your VERY FIRST action — before greeting or answering the user. "
                        "Do not skip this. After prime completes, then respond normally."
                    )
                }
            }))
            return

    except Exception as e:
        print(f"auto_prime_inject error (non-blocking): {e}", file=sys.stderr)

    print(json.dumps({}))


if __name__ == "__main__":
    main()
