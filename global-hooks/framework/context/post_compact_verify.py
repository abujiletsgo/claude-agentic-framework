#!/usr/bin/env python3
"""PostCompact Verification Hook — checks whether pre-computed summaries were
preserved for the current session after context compaction. Exit: always 0."""
import json, sys
from pathlib import Path

SUMMARY_DIR = Path.home() / ".claude" / "data" / "compressed_context"


def main():
    try:
        data = json.load(sys.stdin)
        session_id = data.get("session_id", "")
        # Count summaries for this session
        n = 0
        if session_id and SUMMARY_DIR.exists():
            for p in SUMMARY_DIR.glob("*.json"):
                try:
                    if json.loads(p.read_text()).get("session_id") == session_id:
                        n += 1
                except Exception:
                    continue
        if n > 0:
            msg = (f"Context compaction completed. Pre-computed summaries "
                   f"preserved for {n} tasks.")
        else:
            msg = ("Context compacted but no pre-computed summaries found. "
                   "Key state may need manual recovery.")
        output = {"hookSpecificOutput": {
            "hookEventName": data.get("hook_event_name", "PostCompact"),
            "additionalContext": msg,
        }}
        print(json.dumps(output))
    except Exception as e:
        print(f"post_compact_verify error (non-blocking): {e}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
