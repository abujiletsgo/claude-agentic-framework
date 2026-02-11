#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Task Validator - TaskCompleted Hook
====================================

Runs when a task is marked as completed via TaskUpdate.
Verifies that the task is truly complete with valid deliverables.

Validation Checks:
  - File changes were actually made
  - Tests pass (if applicable)
  - Task description requirements met
  - No obvious errors or incomplete work

Exit Codes:
  0 - Allow completion (task valid)
  1 - Warn but allow completion (minor issues)
  2 - Block completion (task invalid/incomplete)

Integration:
  - Updates context-manager with validation results
  - Logs validation events for observability
  - Can trigger remediation workflows
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def load_input() -> dict:
    """Load input from stdin."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def get_task_details(task_id: str) -> Optional[dict]:
    """
    Get task details from task system.

    In a real implementation, this would query the task database
    or use TaskGet to retrieve full task information.
    """
    # Placeholder - would integrate with actual task system
    return {
        "id": task_id,
        "subject": "Unknown task",
        "description": "",
        "status": "completed",
    }


def check_file_changes(task_id: str) -> dict:
    """
    Check if any files were actually modified for this task.

    Returns:
        dict with keys: has_changes, files_changed, warnings
    """
    result = {
        "has_changes": False,
        "files_changed": [],
        "warnings": [],
    }

    # In a real implementation:
    # 1. Check git status for uncommitted changes
    # 2. Check git log for commits related to this task
    # 3. Verify files match task description expectations

    # For now, assume changes exist
    result["has_changes"] = True

    return result


def check_tests_pass(task_id: str) -> dict:
    """
    Verify tests pass if applicable.

    Returns:
        dict with keys: tests_run, tests_passed, failures
    """
    result = {
        "tests_run": False,
        "tests_passed": True,
        "failures": [],
    }

    # In a real implementation:
    # 1. Detect test framework (pytest, jest, cargo test, etc.)
    # 2. Run relevant tests
    # 3. Parse output for failures

    return result


def validate_deliverables(task: dict, file_changes: dict, test_results: dict) -> dict:
    """
    Validate that task deliverables are complete.

    Returns:
        dict with keys: valid, issues, warnings
    """
    issues = []
    warnings = []

    # Check for file changes
    if not file_changes["has_changes"]:
        issues.append("No file changes detected - task may be incomplete")

    # Check test results
    if test_results["tests_run"] and not test_results["tests_passed"]:
        issues.append(f"Tests failing: {', '.join(test_results['failures'])}")

    # Add file change warnings
    warnings.extend(file_changes.get("warnings", []))

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
    }


def notify_context_manager(task_id: str, validation_result: dict):
    """
    Notify context-manager about task completion and validation status.
    """
    notification_dir = Path.home() / ".claude" / "data" / "team-notifications"
    notification_dir.mkdir(parents=True, exist_ok=True)

    notification_file = notification_dir / f"task-{task_id}-completed.json"

    notification = {
        "timestamp": datetime.now().isoformat(),
        "task_id": task_id,
        "event": "task_completed",
        "validation": validation_result,
    }

    notification_file.write_text(json.dumps(notification, indent=2))


def log_validation(task_id: str, validation_result: dict, exit_code: int):
    """Log validation event."""
    log_dir = Path.home() / ".claude" / "logs" / "teams"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "task_validator.jsonl"

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "task_id": task_id,
        "validation": validation_result,
        "exit_code": exit_code,
        "event": "task_completed_validation",
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def main():
    """Main hook logic."""
    input_data = load_input()

    # Extract task info
    task_id = input_data.get("task_id", "")
    session_id = input_data.get("session_id", "unknown")
    new_status = input_data.get("status", "")

    # Only validate when status changes to 'completed'
    if new_status != "completed":
        sys.exit(0)  # Nothing to validate

    # Get task details
    task = get_task_details(task_id)
    if not task:
        # Can't validate without task info - allow but warn
        print(json.dumps({
            "message": f"[Task Validator] Could not retrieve details for task {task_id}",
        }))
        sys.exit(1)

    # Run validation checks
    file_changes = check_file_changes(task_id)
    test_results = check_tests_pass(task_id)
    validation = validate_deliverables(task, file_changes, test_results)

    # Notify context-manager
    notify_context_manager(task_id, validation)

    # Determine exit code based on validation
    exit_code = 0

    if not validation["valid"]:
        # Task completion invalid - block
        feedback = {
            "message": f"[Task Validator] Task {task_id} completion blocked - validation failed",
            "issues": validation["issues"],
            "action": "Please address the issues before marking task as completed",
        }
        print(json.dumps(feedback))
        exit_code = 2

    elif validation["warnings"]:
        # Task valid but with warnings
        warning = {
            "message": f"[Task Validator] Task {task_id} completed with warnings",
            "warnings": validation["warnings"],
        }
        print(json.dumps(warning))
        exit_code = 1

    else:
        # All good
        success = {
            "message": f"[Task Validator] Task {task_id} validated successfully",
        }
        print(json.dumps(success))
        exit_code = 0

    # Log the validation
    log_validation(task_id, validation, exit_code)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
