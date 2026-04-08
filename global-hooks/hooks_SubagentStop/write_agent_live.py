#!/usr/bin/env python3
"""SubagentStop hook: mark agent done in /tmp/caf_live_agents.json."""
import fcntl
import json
import sys
import time
from pathlib import Path

LIVE_FILE = Path("/tmp/caf_live_agents.json")


def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        hook_input = {}

    try:
        tool_input = hook_input.get("tool_input", {})
        description = tool_input.get("description", "")
        prompt = tool_input.get("prompt", "")
        name = description[:40] if description else prompt[:40]

        if not LIVE_FILE.exists():
            print(json.dumps({}))
            return

        now = time.time()

        with open(LIVE_FILE, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                data = json.load(f)
            except Exception:
                data = {"agents": []}

            # Find the most recent running entry matching this name
            matched = False
            for entry in reversed(data.get("agents", [])):
                if entry.get("name") == name and entry.get("status") == "running":
                    entry["status"] = "done"
                    entry["ended"] = now
                    started = entry.get("started", now)
                    entry["duration_s"] = round(now - started, 1)
                    matched = True
                    break

            # Fallback: mark oldest running agent done if name didn't match
            if not matched:
                for entry in reversed(data.get("agents", [])):
                    if entry.get("status") == "running":
                        entry["status"] = "done"
                        entry["ended"] = now
                        started = entry.get("started", now)
                        entry["duration_s"] = round(now - started, 1)
                        break

            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)
            fcntl.flock(f, fcntl.LOCK_UN)

    except Exception as e:
        print(f"write_agent_live stop error: {e}", file=sys.stderr)

    print(json.dumps({}))


if __name__ == "__main__":
    main()
