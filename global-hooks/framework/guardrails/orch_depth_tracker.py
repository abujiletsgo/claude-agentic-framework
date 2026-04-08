#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Orchestrator Depth Tracker - SubagentStart + SubagentStop Hook
===============================================================

Tracks nesting depth during orchestration to enable the orchestrator_tool_guard
to distinguish between the orchestrator (depth 1, should be blocked) and its
subagents (depth 2+, should be allowed).

On SubagentStart: increment depth counter in /tmp/caf_orch_depth
On SubagentStop:  decrement depth counter; if depth reaches 0 and the stopping
                  agent is the orchestrator, remove the guard marker file

Activates in two ways:
  1. enforce_orchestrate.py (UserPromptSubmit) pre-creates the marker when /orchestrate is typed
  2. This hook auto-creates the marker when it detects an orchestrator agent starting
     (covers direct Agent(subagent_type="orchestrator") spawns without /orchestrate)

Hook events: SubagentStart, SubagentStop
Exit codes:
  0 = Always (never blocks, tracking only)
"""

import json
import os
import sys
from pathlib import Path

MARKER_FILE = Path("/tmp/caf_orch_guard.marker")
DEPTH_FILE = Path("/tmp/caf_orch_depth")
VERBOSE = os.environ.get("CAF_VERBOSE") == "1"


def _verbose(msg: str) -> None:
    """Print to stderr when CAF_VERBOSE=1."""
    if VERBOSE:
        print(msg, file=sys.stderr)


def get_depth() -> int:
    """Read current depth from file."""
    try:
        if DEPTH_FILE.exists():
            return int(DEPTH_FILE.read_text().strip())
    except (ValueError, OSError):
        pass
    return 0


def set_depth(depth: int) -> None:
    """Write depth to file."""
    try:
        DEPTH_FILE.write_text(str(max(0, depth)))
    except OSError:
        pass


def cleanup_marker() -> None:
    """Remove marker and depth files when orchestration completes."""
    try:
        MARKER_FILE.unlink(missing_ok=True)
        DEPTH_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def is_orchestrator_agent(hook_input: dict) -> bool:
    """Check if the agent being started/stopped is an orchestrator."""
    # Check agent_type (set by subagent_type in Agent() call)
    agent_type = hook_input.get("agent_type", "")
    if agent_type and "orchestrator" in agent_type.lower():
        return True

    # Check agent_id / agent_name
    for field in ("agent_id", "agent_name"):
        val = hook_input.get(field, "")
        if val and "orchestrator" in val.lower():
            return True

    # Check tool_input for name field
    tool_input = hook_input.get("tool_input", {})
    if isinstance(tool_input, dict):
        for field in ("name", "agent_name", "subagent_type"):
            val = tool_input.get(field, "")
            if val and "orchestrator" in val.lower():
                return True

    return False


def main():
    try:
        # CAF_MODE check
        _framework_dir = Path(__file__).parent.parent
        if str(_framework_dir) not in sys.path:
            sys.path.insert(0, str(_framework_dir))
        try:
            from caf_mode import should_run
            if not should_run("orch_depth_tracker"):
                sys.exit(0)
        except ImportError:
            pass

        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)

        hook_input = json.loads(raw)

        # Determine if this is a start or stop event by checking for
        # fields unique to each event type
        has_transcript = "agent_transcript_path" in hook_input
        has_tool_output = "tool_output" in hook_input

        if has_transcript or has_tool_output:
            # SubagentStop event: decrement depth (only if marker active)
            if not MARKER_FILE.exists():
                sys.exit(0)

            depth = get_depth()
            new_depth = max(0, depth - 1)
            set_depth(new_depth)
            _verbose(f"depth: {depth} -> {new_depth}")

            # If orchestrator finished (back to depth 0), clean up
            if new_depth == 0 and is_orchestrator_agent(hook_input):
                cleanup_marker()
        else:
            # SubagentStart event
            # Auto-create marker if an orchestrator agent is starting
            # This ensures the guard activates even when orchestrator is
            # spawned directly (not via /orchestrate skill flow)
            if not MARKER_FILE.exists():
                if is_orchestrator_agent(hook_input):
                    MARKER_FILE.touch()
                    set_depth(0)
                    _verbose("orchestrator detected — marker created, depth=0")
                else:
                    sys.exit(0)

            depth = get_depth()
            new_depth = depth + 1
            set_depth(new_depth)
            _verbose(f"depth: {depth} -> {new_depth}")

    except Exception:
        pass  # Never fail, never block

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
