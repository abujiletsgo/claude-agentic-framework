#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///
"""
Context Bundle Logger - PostToolUse Hook
========================================

Logs every Read, Edit, Write, and NotebookEdit operation to a session-specific
bundle file. This creates a "save game" of the agent's knowledge that can be
restored in a new session with zero token waste.

Exit: Always 0 (never blocks)
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def get_bundle_path(session_id):
    """Get path to bundle file for this session."""
    bundle_dir = Path.home() / ".claude" / "bundles"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    return bundle_dir / f"{session_id}.json"


def load_bundle(bundle_path):
    """Load existing bundle or create new one."""
    if bundle_path.exists():
        try:
            with open(bundle_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    # Create new bundle
    return {
        "session_id": None,
        "created_at": datetime.now().isoformat(),
        "last_updated": None,
        "operations": [],
        "files_read": [],
        "files_modified": [],
        "summary": {
            "read_count": 0,
            "edit_count": 0,
            "write_count": 0,
            "total_operations": 0
        }
    }


def save_bundle(bundle_path, bundle_data):
    """Save bundle to disk."""
    bundle_data["last_updated"] = datetime.now().isoformat()
    with open(bundle_path, 'w') as f:
        json.dump(bundle_data, f, indent=2)


def extract_file_path(tool_input):
    """Extract file path from tool input."""
    if isinstance(tool_input, dict):
        return (
            tool_input.get('file_path') or
            tool_input.get('notebook_path') or
            tool_input.get('path')
        )
    return None


def log_operation(bundle, tool_name, tool_input, timestamp):
    """Log a tool operation to the bundle."""
    file_path = extract_file_path(tool_input)

    if not file_path:
        return  # Skip if no file path

    operation = {
        "timestamp": timestamp,
        "tool": tool_name,
        "file": file_path,
        "action": None
    }

    # Determine action and track files
    if tool_name == "Read":
        operation["action"] = "read"
        if file_path not in bundle["files_read"]:
            bundle["files_read"].append(file_path)
        bundle["summary"]["read_count"] += 1

    elif tool_name == "Edit":
        operation["action"] = "edit"
        operation["old_string"] = tool_input.get("old_string", "")[:100]  # Truncate
        operation["new_string"] = tool_input.get("new_string", "")[:100]
        if file_path not in bundle["files_modified"]:
            bundle["files_modified"].append(file_path)
        bundle["summary"]["edit_count"] += 1

    elif tool_name == "Write":
        operation["action"] = "write"
        # Don't store content, just track that file was written
        if file_path not in bundle["files_modified"]:
            bundle["files_modified"].append(file_path)
        bundle["summary"]["write_count"] += 1

    elif tool_name == "NotebookEdit":
        operation["action"] = "notebook_edit"
        operation["cell_id"] = tool_input.get("cell_id")
        if file_path not in bundle["files_modified"]:
            bundle["files_modified"].append(file_path)
        bundle["summary"]["edit_count"] += 1

    bundle["operations"].append(operation)
    bundle["summary"]["total_operations"] += 1


def main():
    try:
        # Read hook input
        input_data = json.load(sys.stdin)

        # Extract key fields
        session_id = input_data.get("session_id", "unknown")
        tool_name = input_data.get("tool_name")
        tool_input = input_data.get("tool_input", {})
        timestamp = input_data.get("timestamp", datetime.now().isoformat())

        # Only log Read, Edit, Write, NotebookEdit
        if tool_name not in ["Read", "Edit", "Write", "NotebookEdit"]:
            sys.exit(0)

        # Load bundle
        bundle_path = get_bundle_path(session_id)
        bundle = load_bundle(bundle_path)

        # Initialize session_id if first operation
        if bundle["session_id"] is None:
            bundle["session_id"] = session_id

        # Log operation
        log_operation(bundle, tool_name, tool_input, timestamp)

        # Save bundle
        save_bundle(bundle_path, bundle)

        sys.exit(0)

    except Exception:
        # Never block - exit cleanly
        sys.exit(0)


if __name__ == '__main__':
    main()
