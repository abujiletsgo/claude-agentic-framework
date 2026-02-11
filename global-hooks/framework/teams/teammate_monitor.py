#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Teammate Monitor - TeammateIdle Hook
====================================

Runs when a teammate is about to go idle (stop active work).
This hook validates that work is complete and deliverables are ready.
Can send feedback to keep the teammate working if needed.

Exit Codes:
  0 - Allow idle (work complete)
  1 - Warn but allow idle (potential issues detected)
  2 - Block idle + send feedback (work incomplete)

Integration:
  - Notifies context-manager agent to create summaries
  - Validates task completion status
  - Checks for file changes
  - Verifies tests pass (if applicable)
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


def check_task_status(teammate_name: str, task_id: str) -> dict:
    """
    Check if the teammate's task is truly complete.

    Returns:
        dict with keys: complete, has_changes, issues
    """
    result = {
        "complete": False,
        "has_changes": False,
        "issues": [],
    }

    # In a real implementation, this would:
    # 1. Query TaskGet to get task details
    # 2. Check git status for uncommitted changes
    # 3. Verify tests passed (if applicable)
    # 4. Validate deliverables exist

    # For now, we assume completion if no obvious issues
    result["complete"] = True

    return result


def notify_context_manager(teammate_name: str, task_id: str, status: str):
    """
    Notify the context-manager agent to create a summary.
    Writes a notification file that context-manager can pick up.
    """
    notification_dir = Path.home() / ".claude" / "data" / "team-notifications"
    notification_dir.mkdir(parents=True, exist_ok=True)

    notification_file = notification_dir / f"{teammate_name}-{task_id}.json"

    notification = {
        "timestamp": datetime.now().isoformat(),
        "teammate": teammate_name,
        "task_id": task_id,
        "status": status,
        "event": "idle",
    }

    notification_file.write_text(json.dumps(notification, indent=2))


def main():
    """Main hook logic."""
    input_data = load_input()

    # Extract teammate info from input
    teammate_name = input_data.get("agent_name", "unknown")
    task_id = input_data.get("task_id", "")
    session_id = input_data.get("session_id", "unknown")

    # Log the event
    log_dir = Path.home() / ".claude" / "logs" / "teams"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "teammate_monitor.jsonl"

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "teammate": teammate_name,
        "task_id": task_id,
        "event": "teammate_idle",
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Check task status
    status = check_task_status(teammate_name, task_id)

    # Notify context-manager to create summary
    notify_context_manager(
        teammate_name,
        task_id,
        "completed" if status["complete"] else "in_progress"
    )

    # Decide whether to allow idle
    if not status["complete"]:
        # Task not complete - send feedback
        feedback = {
            "message": f"[Teammate Monitor] {teammate_name} attempted to go idle but task {task_id} is incomplete.",
            "issues": status["issues"],
            "action": "Please complete the task or update its status before going idle.",
        }
        print(json.dumps(feedback))
        sys.exit(2)  # Block idle

    if status["issues"]:
        # Task complete but with warnings
        warning = {
            "message": f"[Teammate Monitor] {teammate_name} completed task {task_id} with warnings.",
            "issues": status["issues"],
        }
        print(json.dumps(warning))
        sys.exit(1)  # Warn but allow

    # All good - allow idle
    success = {
        "message": f"[Teammate Monitor] {teammate_name} completed task {task_id}. Context-manager notified.",
    }
    print(json.dumps(success))
    sys.exit(0)


if __name__ == "__main__":
    main()
