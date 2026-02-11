#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Delegate Mode Enforcer - PreToolUse:Write/Edit Hook
====================================================

Prevents the lead agent from implementing when teammates are active.
Forces the lead into coordination-only mode, allowing only delegation
and communication with teammates, not direct code editing.

Purpose:
  - Enforces clean separation of concerns
  - Lead agent coordinates, teammates implement
  - Prevents context conflicts and duplicated work
  - Maintains clear audit trail of who did what

Exit Codes:
  0 - Allow (no active teammates, or agent IS a teammate)
  1 - Warn (edge case detected)
  2 - Block (lead attempting to implement with active teammates)

Integration:
  - Monitors active teammate sessions
  - Allows Task tool for delegation
  - Blocks Write/Edit tools when teammates working
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def load_input() -> dict:
    """Load input from stdin."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def is_teammate_agent(agent_name: str) -> bool:
    """
    Check if the current agent is a teammate (not the lead).

    Teammates are allowed to write/edit.
    Lead agent is NOT allowed when teammates are active.
    """
    teammate_names = [
        "builder",
        "validator",
        "researcher",
        "context-manager",
        "project-skill-generator",
    ]

    return agent_name.lower() in teammate_names


def get_active_teammates() -> list[dict]:
    """
    Get list of currently active teammates.

    Returns:
        List of dicts with teammate info: name, task_id, started_at
    """
    # Check for active teammate sessions
    session_dir = Path.home() / ".claude" / "data" / "team-sessions"
    if not session_dir.exists():
        return []

    active_teammates = []
    current_time = datetime.now()

    # Read session files to find active teammates
    for session_file in session_dir.glob("*.json"):
        try:
            session_data = json.loads(session_file.read_text())

            # Check if session is still active (within last 5 minutes)
            started_at = datetime.fromisoformat(session_data.get("started_at", ""))
            age_minutes = (current_time - started_at).total_seconds() / 60

            if age_minutes < 5:  # Session active if < 5 minutes old
                active_teammates.append({
                    "name": session_data.get("teammate", "unknown"),
                    "task_id": session_data.get("task_id", ""),
                    "started_at": session_data.get("started_at", ""),
                })
        except (json.JSONDecodeError, ValueError, KeyError):
            continue

    return active_teammates


def is_coordination_only_file(file_path: str) -> bool:
    """
    Check if file is coordination-only (allowed even with active teammates).

    Coordination files:
      - Task definitions/updates
      - Team communication logs
      - Planning documents
      - Context summaries

    Not allowed:
      - Source code
      - Configuration files
      - Tests
    """
    coordination_patterns = [
        "data/team-context/",
        "data/team-sessions/",
        "data/team-communications/",
        ".claude/plans/",
        ".claude/team/",
    ]

    return any(pattern in file_path for pattern in coordination_patterns)


def log_enforcement_action(
    agent_name: str,
    tool_name: str,
    file_path: str,
    active_teammates: list[dict],
    action: str,
):
    """Log enforcement action for audit trail."""
    log_dir = Path.home() / ".claude" / "logs" / "teams"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "delegate_mode_enforcer.jsonl"

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent_name,
        "tool": tool_name,
        "file": file_path,
        "active_teammates": [t["name"] for t in active_teammates],
        "action": action,
        "event": "delegate_mode_enforcement",
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def main():
    """Main hook logic."""
    input_data = load_input()

    # Extract info from input
    tool_name = input_data.get("tool_name", "")
    agent_name = input_data.get("agent_name", "main")
    session_id = input_data.get("session_id", "unknown")

    # Get file path from tool arguments
    tool_args = input_data.get("tool_arguments", {})
    file_path = tool_args.get("file_path", "")

    # If this is a teammate agent, always allow (teammates should implement)
    if is_teammate_agent(agent_name):
        log_enforcement_action(
            agent_name, tool_name, file_path, [], "allow_teammate"
        )
        sys.exit(0)

    # Check for active teammates
    active_teammates = get_active_teammates()

    # If no active teammates, lead can implement directly
    if not active_teammates:
        log_enforcement_action(
            agent_name, tool_name, file_path, [], "allow_no_teammates"
        )
        sys.exit(0)

    # Active teammates exist - check if this is coordination-only file
    if is_coordination_only_file(file_path):
        log_enforcement_action(
            agent_name, tool_name, file_path, active_teammates, "allow_coordination"
        )
        sys.exit(0)

    # Lead agent attempting to implement while teammates are active - BLOCK
    teammate_names = ", ".join(t["name"] for t in active_teammates)

    feedback = {
        "message": f"[Delegate Mode Enforcer] Lead agent cannot implement while teammates are active",
        "active_teammates": teammate_names,
        "blocked_tool": tool_name,
        "blocked_file": file_path,
        "action": (
            "You are in coordination mode. Please use Task tools to delegate "
            f"to active teammates ({teammate_names}) instead of implementing directly."
        ),
        "allowed_actions": [
            "Use TaskCreate to create new tasks",
            "Use TaskUpdate to update task status",
            "Use Task tool to communicate with teammates",
            "Write to coordination files (data/team-context/)",
            "Wait for teammates to complete their work",
        ],
    }

    print(json.dumps(feedback))

    log_enforcement_action(
        agent_name, tool_name, file_path, active_teammates, "block_lead_implementing"
    )

    sys.exit(2)  # Block the write/edit


if __name__ == "__main__":
    main()
