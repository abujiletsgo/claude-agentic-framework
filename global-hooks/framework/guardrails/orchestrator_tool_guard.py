#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Orchestrator Tool Guard - PreToolUse Hook
==========================================

Prevents the orchestrator agent from directly using Read, Grep, Glob, Edit,
or Bash tools. The orchestrator's role is to delegate ALL file operations
to subagents (researchers, builders, validators).

Detection mechanism:
  - enforce_orchestrate.py (UserPromptSubmit) writes a marker file when
    /orchestrate is detected: /tmp/caf_orch_guard.marker
  - This hook checks for the marker AND whether the current call is at
    the orchestrator depth (depth 1 = orchestrator, depth 2+ = subagents)
  - SubagentStart hook increments depth, SubagentStop decrements it
  - Only blocks at depth 1 (orchestrator itself). Depth 0 (main session)
    and depth 2+ (subagents) are always allowed.

Trigger: PreToolUse (matcher: Read|Grep|Glob|Edit|Bash)
Exit codes:
  0 = Allow (not in orchestration mode, or subagent at depth 2+)
  2 = Block (orchestrator attempting forbidden tool)
"""

import json
import os
import sys
from pathlib import Path

# Marker file written by enforce_orchestrate.py
MARKER_FILE = Path("/tmp/caf_orch_guard.marker")

# Depth tracker: incremented by SubagentStart, decremented by SubagentStop
DEPTH_FILE = Path("/tmp/caf_orch_depth")

# Tools the orchestrator must never call directly
FORBIDDEN_TOOLS = {"Read", "Grep", "Glob", "Edit"}

# Bash is partially restricted — only cat/grep/find/head/tail/sed/awk
BASH_RESEARCH_PATTERNS = [
    "cat ", "grep ", "rg ", "find ", "head ", "tail ", "sed ", "awk ",
    "less ", "more ", "wc ", "sort ", "uniq ", "xargs ",
    "ls ", "tree ", "file ", "stat ",
]

# Block message injected via JSON output (additionalContext)
BLOCK_REMINDER = (
    "[ORCHESTRATOR GUARD] You are the orchestrator. You MUST NOT use "
    "file-reading or code-searching tools directly. Spawn a subagent instead:\n"
    "  - Need to read a file? → Agent(name='researcher-N', model='haiku', ...)\n"
    "  - Need to search code? → Agent(name='researcher-N', model='sonnet', ...)\n"
    "  - Need to edit code? → Agent(name='builder-N', model='sonnet', ...)\n"
    "  - Need to run tests? → Agent(name='validator-N', model='haiku', ...)\n\n"
    "This tool call has been BLOCKED. Delegate this work to a subagent."
)


def get_depth() -> int:
    """Read the current orchestration depth from the depth file."""
    try:
        if DEPTH_FILE.exists():
            return int(DEPTH_FILE.read_text().strip())
    except (ValueError, OSError):
        pass
    return 0


def is_bash_research(command: str) -> bool:
    """Check if a bash command is doing file research (cat, grep, etc.)."""
    cmd = command.strip().lstrip("'\"")
    return any(cmd.startswith(p) for p in BASH_RESEARCH_PATTERNS)


def main():
    try:
        # ── CAF_MODE check ────────────────────────────────────────────
        _framework_dir = Path(__file__).parent.parent
        if str(_framework_dir) not in sys.path:
            sys.path.insert(0, str(_framework_dir))
        try:
            from caf_mode import should_run
            if not should_run("orchestrator_tool_guard"):
                sys.exit(0)
        except ImportError:
            pass

        # ── Quick exit: no orchestration active ───────────────────────
        if not MARKER_FILE.exists():
            sys.exit(0)

        # ── Check depth: only block at depth 1 (orchestrator itself)
        depth = get_depth()
        if depth == 0:
            # This is the main session — never block it
            sys.exit(0)
        if depth >= 2:
            # This is a subagent's subagent (researcher, builder, etc.)
            # They SHOULD use Read/Grep/Glob/Edit — allow
            sys.exit(0)

        # ── Read hook input ───────────────────────────────────────────
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # ── Check if tool is forbidden ────────────────────────────────
        should_block = False

        if tool_name in FORBIDDEN_TOOLS:
            should_block = True
        elif tool_name == "Bash":
            command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
            if is_bash_research(command):
                should_block = True

        if should_block:
            # Output block decision + reminder context
            print(BLOCK_REMINDER, file=sys.stderr)
            sys.exit(2)

        # Allow all other tools (Agent, Task, Write, SendMessage, etc.)
        sys.exit(0)

    except Exception:
        # Never crash, never block on error — fail open
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
