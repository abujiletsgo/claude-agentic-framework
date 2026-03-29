#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Subagent Tracker - SubagentStop Hook

Lightweight tracker that logs subagent execution metadata (agent name,
duration, output length) to ~/.claude/data/agent_tracking.jsonl for
observability and quality analysis.

Hook event: SubagentStop
Exit codes:
  0 = Always (never blocks, tracking only)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_tracking_path():
    """Return path to agent tracking JSONL file, creating dirs if needed."""
    tracking_path = Path.home() / ".claude" / "data" / "agent_tracking.jsonl"
    tracking_path.parent.mkdir(parents=True, exist_ok=True)
    return tracking_path


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)

        hook_input = json.loads(raw)

        # Extract subagent metadata from hook payload
        tool_name = hook_input.get("tool_name", "unknown")
        tool_input = hook_input.get("tool_input", {})
        tool_output = hook_input.get("tool_output", "")

        # Compute output length
        if isinstance(tool_output, str):
            output_length = len(tool_output)
        elif isinstance(tool_output, dict):
            output_length = len(json.dumps(tool_output))
        else:
            output_length = 0

        # Extract agent name from tool input if available
        agent_name = "unknown"
        if isinstance(tool_input, dict):
            agent_name = (
                tool_input.get("agent_name")
                or tool_input.get("name")
                or tool_input.get("task_description", "unknown")[:80]
            )
        elif isinstance(tool_input, str):
            agent_name = tool_input[:80]

        # Build tracking record
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": agent_name,
            "tool_name": tool_name,
            "output_length": output_length,
            "input_keys": list(tool_input.keys()) if isinstance(tool_input, dict) else [],
        }

        # Append to tracking file
        tracking_path = get_tracking_path()
        with open(tracking_path, "a") as f:
            f.write(json.dumps(record) + "\n")

    except Exception:
        # Never fail, never block
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
