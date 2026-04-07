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
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Output below this character count is considered suspiciously empty
MINIMUM_MEANINGFUL_OUTPUT = 50

# Patterns that signal a failed/errored agent response
ERROR_PATTERNS = [
    "traceback", "exception:", "error:", "internal error",
    "rate_limit", "authentication_failed", "tool_call_error",
    "context_length_exceeded", "max_tokens", "500 ", " 500\n",
    "i cannot", "i'm unable", "i am unable",
]

# CAF role agent name prefixes — these have expected output files we can verify
CAF_ROLE_AGENTS = {"builder", "validator", "debugger"}


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

        # ── Anomaly Detection ─────────────────────────────────────────────
        output_text = tool_output if isinstance(tool_output, str) else json.dumps(tool_output)

        is_empty_output = output_length < MINIMUM_MEANINGFUL_OUTPUT

        has_error_signal = any(p in output_text.lower() for p in ERROR_PATTERNS)

        # Check if this is a CAF role agent with an expected output file
        output_file_missing = False
        expected_file = None
        match = re.search(r'(builder|validator|debugger)-(\d+)', agent_name.lower())
        if match:
            role, iteration = match.group(1), match.group(2)
            expected_file = f"/tmp/caf_{role}_{iteration}.md"
            output_file_missing = not Path(expected_file).exists()

        anomaly_types = []
        if is_empty_output:
            anomaly_types.append("empty_output")
        if has_error_signal:
            anomaly_types.append("error_signal")
        if output_file_missing:
            anomaly_types.append("missing_output_file")

        # ── Build tracking record ─────────────────────────────────────────
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": agent_name,
            "tool_name": tool_name,
            "output_length": output_length,
            "input_keys": list(tool_input.keys()) if isinstance(tool_input, dict) else [],
            "anomalies": anomaly_types,
        }

        # Append to tracking file
        tracking_path = get_tracking_path()
        with open(tracking_path, "a") as f:
            f.write(json.dumps(record) + "\n")

        # ── Surface anomalies to watchdog and alert log ───────────────────
        if anomaly_types:
            ts = record["timestamp"]

            # Write to watchdog state file so agent-watchdog detects it
            # without requiring the failing agent to self-report
            watchdog_path = Path("/tmp/caf_watchdog.md")
            error_detail = "+".join(anomaly_types)
            if has_error_signal:
                error_detail += f":{output_text[:120].replace(chr(10), ' ')}"
            watchdog_line = (
                f"[{ts}] AGENT:{agent_name} STATUS:FAILED "
                f"TASK:hook_detected ERROR:{error_detail}\n"
            )
            try:
                with open(watchdog_path, "a") as f:
                    f.write(watchdog_line)
            except Exception:
                pass  # Never fail the hook

            # Write to persistent alert log for post-session review
            alert_path = Path.home() / ".claude" / "data" / "subagent_alerts.jsonl"
            alert = {
                "timestamp": ts,
                "agent_name": agent_name,
                "anomaly_types": anomaly_types,
                "output_length": output_length,
                "expected_file": expected_file,
                "error_excerpt": output_text[:200] if has_error_signal else None,
            }
            try:
                with open(alert_path, "a") as f:
                    f.write(json.dumps(alert) + "\n")
            except Exception:
                pass  # Never fail the hook

    except Exception:
        # Never fail, never block
        pass

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
