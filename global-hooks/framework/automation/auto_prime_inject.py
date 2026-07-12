#!/usr/bin/env python3
"""
Auto-Prime Inject - UserPromptSubmit Hook

Fires before every user message. PROJECT_CONTEXT.md is normally generated
automatically by the auto_prime.py SessionStart hook. If it's still missing
mid-session (e.g. SessionStart hook failed, or the file was deleted), this
injects a fallback instruction to regenerate it directly instead of relying
on a slash command.

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
                        "`.claude/PROJECT_CONTEXT.md`. The SessionStart hook (auto_prime.py) "
                        "should have generated it — it did not run or was skipped. Generate it "
                        "yourself now, as your VERY FIRST action, before greeting or answering "
                        "the user: read CLAUDE.md, detect the stack, and write a project context "
                        "summary to `.claude/PROJECT_CONTEXT.md`. Do not skip this. Then respond "
                        "normally."
                    )
                }
            }))
            return

    except Exception as e:
        print(f"auto_prime_inject error (non-blocking): {e}", file=sys.stderr)

    print(json.dumps({}))


if __name__ == "__main__":
    main()
