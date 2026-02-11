#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""
Caddy Progress Monitor - PostToolUse Hook
==========================================

Tracks sub-agent progress, task completion, blockers, and resource usage
when the Caddy meta-orchestrator is active.

Monitors:
- Task tool calls (sub-agent spawning and completion)
- File operations (tracks scope of changes)
- Bash tool calls (tracks commands executed)
- Error patterns (detects repeated failures)

Writes progress state to ~/.claude/logs/caddy/progress.json for the
Caddy agent to read and react to.

Exit: Always 0 (never blocks)
"""

import json
import sys
from pathlib import Path
from datetime import datetime


PROGRESS_DIR = Path.home() / ".claude" / "logs" / "caddy"
PROGRESS_FILE = PROGRESS_DIR / "progress.json"
MAX_EVENTS = 500  # Cap stored events to prevent unbounded growth
MAX_ERRORS = 50   # Cap stored errors


def load_progress() -> dict:
    """Load or initialize progress state."""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE) as f:
                data = json.load(f)
            # Validate structure
            if isinstance(data, dict) and "sessions" in data:
                return data
        except (json.JSONDecodeError, KeyError):
            pass

    return {
        "last_updated": None,
        "sessions": {},
    }


def save_progress(state: dict) -> None:
    """Persist progress state to disk."""
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_session(state: dict, session_id: str) -> dict:
    """Get or create session tracking data."""
    if session_id not in state["sessions"]:
        state["sessions"][session_id] = {
            "started_at": datetime.now().isoformat(),
            "subagents": {
                "spawned": 0,
                "completed": 0,
                "failed": 0,
                "active": [],
            },
            "tools_used": {
                "total_calls": 0,
                "by_tool": {},
            },
            "files": {
                "read": [],
                "modified": [],
            },
            "errors": [],
            "events": [],
        }
    return state["sessions"][session_id]


def track_task_tool(session: dict, tool_input: dict, tool_output: str) -> None:
    """Track Task tool usage (sub-agent spawning)."""
    subagent_type = tool_input.get("subagent_type", "unknown")
    description = tool_input.get("description", "")[:200]

    session["subagents"]["spawned"] += 1
    session["subagents"]["active"].append({
        "type": subagent_type,
        "description": description,
        "spawned_at": datetime.now().isoformat(),
    })

    # Cap active list
    if len(session["subagents"]["active"]) > 20:
        session["subagents"]["active"] = session["subagents"]["active"][-20:]

    add_event(session, "subagent_spawned", {
        "type": subagent_type,
        "description": description,
    })


def track_file_operation(
    session: dict,
    tool_name: str,
    tool_input: dict,
) -> None:
    """Track file read/write/edit operations."""
    file_path = (
        tool_input.get("file_path")
        or tool_input.get("notebook_path")
        or tool_input.get("path")
    )
    if not file_path:
        return

    if tool_name == "Read":
        if file_path not in session["files"]["read"]:
            session["files"]["read"].append(file_path)
            # Cap list
            if len(session["files"]["read"]) > 200:
                session["files"]["read"] = session["files"]["read"][-200:]
    elif tool_name in ("Edit", "Write", "NotebookEdit"):
        if file_path not in session["files"]["modified"]:
            session["files"]["modified"].append(file_path)
            if len(session["files"]["modified"]) > 200:
                session["files"]["modified"] = (
                    session["files"]["modified"][-200:]
                )


def track_bash_tool(session: dict, tool_input: dict) -> None:
    """Track bash command execution."""
    command = tool_input.get("command", "")[:300]
    add_event(session, "bash_executed", {"command": command})


def track_error(
    session: dict,
    tool_name: str,
    tool_input: dict,
    error: str,
) -> None:
    """Track tool errors for failure detection."""
    if len(session["errors"]) >= MAX_ERRORS:
        session["errors"] = session["errors"][-(MAX_ERRORS - 1):]

    session["errors"].append({
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "error": error[:500],
    })

    # Detect repeated failures (3+ errors from same tool in last 10 events)
    recent_errors = session["errors"][-10:]
    tool_errors = [e for e in recent_errors if e["tool"] == tool_name]
    if len(tool_errors) >= 3:
        add_event(session, "repeated_failure_detected", {
            "tool": tool_name,
            "count": len(tool_errors),
            "suggestion": (
                f"Tool '{tool_name}' has failed {len(tool_errors)} times "
                f"recently. Consider a different approach or debugging."
            ),
        })


def add_event(session: dict, event_type: str, data: dict) -> None:
    """Add a timestamped event to the session log."""
    if len(session["events"]) >= MAX_EVENTS:
        session["events"] = session["events"][-(MAX_EVENTS - 1):]

    session["events"].append({
        "timestamp": datetime.now().isoformat(),
        "type": event_type,
        "data": data,
    })


def compute_summary(session: dict) -> dict:
    """Compute a summary of session progress for quick reading."""
    subagents = session["subagents"]
    tools = session["tools_used"]
    files = session["files"]
    errors = session["errors"]

    return {
        "subagents_spawned": subagents["spawned"],
        "subagents_completed": subagents["completed"],
        "subagents_failed": subagents["failed"],
        "subagents_active": len(subagents["active"]),
        "total_tool_calls": tools["total_calls"],
        "files_read": len(files["read"]),
        "files_modified": len(files["modified"]),
        "total_errors": len(errors),
        "recent_errors": len([
            e for e in errors[-10:]
            if e.get("timestamp", "") > ""
        ]),
        "health": (
            "healthy" if len(errors) < 5
            else "degraded" if len(errors) < 15
            else "unhealthy"
        ),
    }


def main():
    try:
        input_data = json.load(sys.stdin)

        session_id = input_data.get("session_id", "unknown")
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        tool_output = input_data.get("tool_output", "")

        # Load progress state
        state = load_progress()
        session = get_session(state, session_id)

        # Track tool usage count
        session["tools_used"]["total_calls"] += 1
        by_tool = session["tools_used"]["by_tool"]
        by_tool[tool_name] = by_tool.get(tool_name, 0) + 1

        # Check for errors in output
        output_str = str(tool_output)[:2000] if tool_output else ""
        is_error = any(
            indicator in output_str.lower()
            for indicator in [
                "error:", "traceback", "exception", "failed",
                "permission denied", "not found",
            ]
        )

        if is_error and tool_name != "Read":
            # Read tool "errors" are often just file-not-found which is normal
            track_error(session, tool_name, tool_input, output_str[:500])

        # Tool-specific tracking
        if tool_name == "Task":
            track_task_tool(session, tool_input, output_str)

        elif tool_name in ("Read", "Edit", "Write", "NotebookEdit"):
            track_file_operation(session, tool_name, tool_input)

        elif tool_name == "Bash":
            track_bash_tool(session, tool_input)

        # Update summary
        session["summary"] = compute_summary(session)

        # Save state
        save_progress(state)

        # Output nothing (this hook is purely observational)
        sys.exit(0)

    except Exception:
        # Never block
        sys.exit(0)


if __name__ == "__main__":
    main()
