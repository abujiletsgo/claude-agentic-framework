#!/usr/bin/env python3
"""SubagentStart hook: write agent status to /tmp/caf_live_agents.json for dashboard visibility."""
import fcntl
import json
import os
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
        model = tool_input.get("model", "")

        # Derive name: description → first 40 chars, fallback to prompt snippet
        name = description[:40] if description else prompt[:40]
        if not name:
            name = f"agent-{int(time.time()) % 10000}"

        # Prompt snippet for display (first 80 chars, single line)
        snippet = prompt.replace("\n", " ")[:80] if prompt else description

        # Short model name
        if "opus" in model:
            model_short = "opus"
        elif "haiku" in model:
            model_short = "haiku"
        elif "sonnet" in model:
            model_short = "sonnet"
        else:
            model_short = model.split("-")[0] if model else "?"

        entry = {
            "name": name,
            "status": "running",
            "started": time.time(),
            "model": model_short,
            "snippet": snippet,
        }

        # Atomic read-modify-write with file lock
        LIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LIVE_FILE, "a+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            try:
                data = json.load(f)
            except Exception:
                data = {"agents": [], "session_start": time.time()}
            # Append new agent (keep last 50)
            data.setdefault("agents", [])
            data["agents"].append(entry)
            data["agents"] = data["agents"][-50:]
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)
            fcntl.flock(f, fcntl.LOCK_UN)

    except Exception as e:
        print(f"write_agent_live start error: {e}", file=sys.stderr)

    print(json.dumps({}))


if __name__ == "__main__":
    main()
