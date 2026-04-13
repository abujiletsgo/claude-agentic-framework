#!/usr/bin/env -S uv run --script
"""
lead_memory_writer.py — SubagentStop hook
Detects lead/PO agents and writes domain-scoped memory to .claude/lead-memories/
"""
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

import json
import sys
import os
import re
from datetime import datetime
from pathlib import Path

def main():
    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    # Only act on SubagentStop events
    hook_event = event.get("hook_event_name", "")
    if hook_event != "SubagentStop":
        sys.exit(0)

    # Get agent identity from the event
    agent_name = event.get("agent_name", "") or event.get("name", "")
    subagent_type = event.get("subagent_type", "") or event.get("agent_type", "")

    # Detect if this is a lead or PO
    is_po = "po" in agent_name.lower() or subagent_type == "po"
    is_lead = (
        agent_name.endswith("-lead") or
        subagent_type.endswith("-lead") or
        any(x in agent_name.lower() for x in [
            "backend-lead", "frontend-lead", "architecture-lead",
            "debugging-lead", "refactoring-lead", "performance-lead",
            "docs-lead", "release-lead"
        ])
    )

    if not is_po and not is_lead:
        sys.exit(0)

    # Find project root (look for .claude/ directory)
    cwd = Path(event.get("cwd", os.getcwd()))
    project_root = cwd
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".claude").exists():
            project_root = parent
            break

    lead_memories_dir = project_root / ".claude" / "lead-memories"
    lead_memories_dir.mkdir(parents=True, exist_ok=True)

    # Determine memory file
    if is_po:
        memory_file = lead_memories_dir / "PO.md"
        memory_header = "PO"
    else:
        # Normalize lead name
        lead_name = agent_name if agent_name.endswith("-lead") else subagent_type
        lead_name = lead_name.replace("_", "-").lower()
        memory_file = lead_memories_dir / f"{lead_name}.md"
        memory_header = lead_name

    # Get session summary from event
    # The hook receives the agent's final output/transcript summary
    session_output = event.get("output", "") or event.get("result", "") or ""
    orch_id = event.get("orch_id", "") or ""

    # Try to extract orch_id from cwd or environment
    if not orch_id:
        orch_id = os.environ.get("ORCH_ID", "")

    date_str = datetime.now().strftime("%Y-%m-%d")

    # Write memory entry
    # PO memory: brief index pointing to lead memories
    # Lead memory: domain-scoped detail

    if is_po:
        # PO writes a brief summary - will be populated by PO itself at session end
        # This hook just ensures the file exists and adds a timestamp marker
        if not memory_file.exists():
            memory_file.write_text(
                "# PO Memory\n"
                "<!-- Index of what each lead did per job. Details live in lead memory files. -->\n\n"
            )
    else:
        # Lead memory - initialize if needed
        if not memory_file.exists():
            memory_file.write_text(
                f"# {memory_header} Memory\n"
                f"<!-- Domain-scoped episodic memory for {memory_header}. -->\n"
                f"<!-- Loaded at session start. Written at session end. -->\n\n"
            )

        # Append a placeholder entry that the lead should have filled in
        # (The actual content is written by the lead itself at session end per its instructions)
        # This hook just ensures the file exists and is reachable

    sys.exit(0)

if __name__ == "__main__":
    main()
