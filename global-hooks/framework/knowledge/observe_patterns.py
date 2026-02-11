#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""
OBSERVE stage of the Knowledge Pipeline.

Hook: PostToolUse
Tracks tool usage patterns, errors, decisions, and performance
to ~/.claude/observations.jsonl (append-only JSONL).

Each observation is a single JSON line with:
  - timestamp, session_id, type, tool, pattern, context
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONFIG_PATH = Path.home() / ".claude" / "knowledge_pipeline.yaml"
OBSERVATIONS_DEFAULT = Path.home() / ".claude" / "observations.jsonl"


def load_config():
    """Load pipeline config with safe defaults."""
    defaults = {
        "observe": {
            "enabled": True,
            "track_tool_usage": True,
            "track_errors": True,
            "track_decisions": True,
            "track_performance": True,
            "max_observations_per_session": 1000,
            "observations_file": str(OBSERVATIONS_DEFAULT),
        }
    }
    if CONFIG_PATH.exists():
        try:
            import yaml
            with open(CONFIG_PATH, "r") as f:
                cfg = yaml.safe_load(f) or {}
            # Merge observe section
            obs = cfg.get("observe", {})
            for k, v in obs.items():
                defaults["observe"][k] = v
        except Exception:
            pass
    return defaults["observe"]


# ---------------------------------------------------------------------------
# Pattern classification
# ---------------------------------------------------------------------------

def classify_tool_pattern(tool_name, tool_input):
    """Classify the tool usage into a named pattern."""
    if tool_name == "Edit":
        old_str = tool_input.get("old_string", "")
        new_str = tool_input.get("new_string", "")
        old_lines = old_str.count("\n") + 1 if old_str else 0
        new_lines = new_str.count("\n") + 1 if new_str else 0
        if old_lines <= 3 and new_lines <= 3:
            return "small_modification"
        elif new_lines > old_lines * 2:
            return "expansion"
        elif old_lines > new_lines * 2:
            return "reduction"
        else:
            return "refactor"

    elif tool_name == "Write":
        content = tool_input.get("content", "")
        lines = content.count("\n") + 1 if content else 0
        if lines > 100:
            return "large_file_write"
        elif lines > 30:
            return "medium_file_write"
        else:
            return "small_file_write"

    elif tool_name == "Read":
        return "file_read"

    elif tool_name == "Bash":
        cmd = tool_input.get("command", "")
        if cmd.startswith("git "):
            return "git_operation"
        elif "test" in cmd or "pytest" in cmd or "jest" in cmd:
            return "test_execution"
        elif "npm" in cmd or "pip" in cmd or "uv" in cmd:
            return "package_management"
        elif "ls" in cmd or "find" in cmd:
            return "file_discovery"
        else:
            return "shell_command"

    elif tool_name == "Grep":
        return "code_search"

    elif tool_name == "Glob":
        return "file_search"

    elif tool_name in ("TaskCreate", "TaskUpdate", "TaskGet", "TaskList"):
        return "task_management"

    elif tool_name == "WebSearch" or tool_name == "WebFetch":
        return "web_lookup"

    else:
        return "other"


def extract_context(tool_name, tool_input, tool_output):
    """Extract relevant context from tool usage for the observation."""
    ctx = {}

    if tool_name == "Edit":
        old_str = tool_input.get("old_string", "")
        new_str = tool_input.get("new_string", "")
        ctx["file_path"] = tool_input.get("file_path", "")
        ctx["old_lines"] = old_str.count("\n") + 1 if old_str else 0
        ctx["new_lines"] = new_str.count("\n") + 1 if new_str else 0
        ctx["replace_all"] = tool_input.get("replace_all", False)

    elif tool_name == "Write":
        content = tool_input.get("content", "")
        ctx["file_path"] = tool_input.get("file_path", "")
        ctx["content_lines"] = content.count("\n") + 1 if content else 0
        ctx["content_bytes"] = len(content.encode("utf-8")) if content else 0

    elif tool_name == "Read":
        ctx["file_path"] = tool_input.get("file_path", "")
        ctx["offset"] = tool_input.get("offset")
        ctx["limit"] = tool_input.get("limit")

    elif tool_name == "Bash":
        cmd = tool_input.get("command", "")
        # Truncate long commands
        ctx["command"] = cmd[:200] if len(cmd) > 200 else cmd
        ctx["timeout"] = tool_input.get("timeout")
        ctx["background"] = tool_input.get("run_in_background", False)

    elif tool_name == "Grep":
        ctx["pattern"] = tool_input.get("pattern", "")
        ctx["path"] = tool_input.get("path", "")
        ctx["output_mode"] = tool_input.get("output_mode", "files_with_matches")

    elif tool_name == "Glob":
        ctx["pattern"] = tool_input.get("pattern", "")
        ctx["path"] = tool_input.get("path", "")

    # Truncate file paths to just filename for privacy
    if "file_path" in ctx and ctx["file_path"]:
        ctx["file_ext"] = Path(ctx["file_path"]).suffix
        ctx["file_name"] = Path(ctx["file_path"]).name

    return ctx


# ---------------------------------------------------------------------------
# Session counting (to enforce max_observations_per_session)
# ---------------------------------------------------------------------------

SESSION_COUNT_FILE = Path.home() / ".claude" / ".obs_session_count"


def get_session_count(session_id):
    """Get the current observation count for this session."""
    try:
        if SESSION_COUNT_FILE.exists():
            data = json.loads(SESSION_COUNT_FILE.read_text())
            if data.get("session_id") == session_id:
                return data.get("count", 0)
    except Exception:
        pass
    return 0


def increment_session_count(session_id):
    """Increment and persist the session observation count."""
    count = get_session_count(session_id) + 1
    try:
        SESSION_COUNT_FILE.write_text(json.dumps({
            "session_id": session_id,
            "count": count
        }))
    except Exception:
        pass
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    config = load_config()

    if not config.get("enabled", True):
        sys.exit(0)

    # Extract hook fields
    session_id = input_data.get("session_id", "unknown")
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    tool_output = input_data.get("tool_output", "")

    if not tool_name:
        sys.exit(0)

    # Check session limit
    max_obs = config.get("max_observations_per_session", 1000)
    current_count = get_session_count(session_id)
    if current_count >= max_obs:
        sys.exit(0)

    # Build observation record
    obs_type = "tool_usage"
    pattern = classify_tool_pattern(tool_name, tool_input)
    context = extract_context(tool_name, tool_input, tool_output)

    # Check if this was an error (tool_output often contains error info)
    is_error = False
    if isinstance(tool_output, str) and ("error" in tool_output.lower() or "Error" in tool_output):
        is_error = True
        obs_type = "error"
        # Capture first 300 chars of error
        context["error_snippet"] = tool_output[:300]

    # Skip if tracking is disabled for this type
    if obs_type == "tool_usage" and not config.get("track_tool_usage", True):
        sys.exit(0)
    if obs_type == "error" and not config.get("track_errors", True):
        sys.exit(0)

    observation = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": obs_type,
        "tool": tool_name,
        "pattern": pattern,
        "context": context,
        "session_id": session_id,
        "processed": False,
    }

    # Resolve observations file path
    obs_file_str = config.get("observations_file", str(OBSERVATIONS_DEFAULT))
    obs_file = Path(os.path.expanduser(obs_file_str))

    # Ensure parent directory exists
    obs_file.parent.mkdir(parents=True, exist_ok=True)

    # Append as JSONL (one JSON object per line)
    try:
        with open(obs_file, "a") as f:
            f.write(json.dumps(observation) + "\n")
    except Exception:
        # Never block the tool on observation failure
        sys.exit(0)

    # Update session counter
    increment_session_count(session_id)

    sys.exit(0)


if __name__ == "__main__":
    main()
