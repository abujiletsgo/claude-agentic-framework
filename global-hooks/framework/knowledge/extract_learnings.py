#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Extract Learnings - PostToolUse Hook
=====================================

Monitors tool outputs for knowledge-worthy content and automatically
stores it in the knowledge database. Looks for patterns like:

- Error corrections (LEARNED)
- Architecture decisions (DECISION)
- Project facts discovered (FACT)
- Recurring patterns (PATTERN)
- Open questions (INVESTIGATION)

This hook reads from stdin (Claude hook protocol) and never blocks.
Exit: Always 0 (never blocks the tool pipeline)
"""

import json
import re
import sys
from pathlib import Path

# Import knowledge_db from same directory
sys.path.insert(0, str(Path(__file__).parent))


def extract_from_tool_output(tool_name: str, tool_input: dict, tool_output: str, session_id: str) -> list[dict]:
    """
    Analyze tool output and extract knowledge entries.

    Returns a list of dicts with keys: content, tag, context
    """
    entries = []

    # Skip tools that are unlikely to produce learnings
    if tool_name in ("Read", "Glob", "WebSearch"):
        return entries

    output_lower = (tool_output or "").lower()

    # Pattern: Error messages that were resolved
    # When Bash returns an error followed by a fix, that is a LEARNED
    if tool_name == "Bash" and tool_input:
        command = tool_input.get("command", "")

        # Detect test failures or compilation errors
        if any(kw in output_lower for kw in ("error:", "failed", "traceback", "exception")):
            # Only record if the output is short enough to be meaningful
            if len(tool_output or "") < 2000:
                content = f"Command `{command[:100]}` produced error. Output: {(tool_output or '')[:500]}"
                entries.append({
                    "content": content,
                    "tag": "INVESTIGATION",
                    "context": _infer_context(command),
                })

    # Pattern: File Write/Edit that creates configuration or architecture
    if tool_name in ("Write", "Edit") and tool_input:
        file_path = tool_input.get("file_path", "")

        # Architecture-related files
        if any(name in file_path.lower() for name in (
            "architecture", "config", "schema", "migration",
            ".env", "dockerfile", "docker-compose", "makefile",
            "justfile", "pyproject.toml", "package.json",
        )):
            entries.append({
                "content": f"Modified architecture/config file: {file_path}",
                "tag": "DECISION",
                "context": _infer_context(file_path),
            })

    return entries


def _infer_context(text: str) -> str:
    """Infer a context label from a file path or command."""
    text = text.lower()

    # Match known project patterns
    patterns = {
        "vaultmind": "vaultmind",
        "claude-agentic": "claude-agentic-framework",
        "obsidian": "obsidian",
        "knowledge": "knowledge-system",
        "hook": "hooks",
        "agent": "agents",
        "test": "testing",
        "docker": "infrastructure",
        "deploy": "deployment",
    }

    for keyword, ctx in patterns.items():
        if keyword in text:
            return ctx

    return "general"


def main():
    """Hook entry point - reads from stdin, never blocks."""
    try:
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        tool_output = str(input_data.get("tool_output", ""))
        session_id = input_data.get("session_id", "unknown")

        entries = extract_from_tool_output(tool_name, tool_input, tool_output, session_id)

        if entries:
            # Import here to avoid import errors if DB is not initialized
            try:
                from knowledge_db import add_knowledge
                for entry in entries:
                    add_knowledge(
                        content=entry["content"],
                        tag=entry["tag"],
                        context=entry.get("context"),
                        session_id=session_id,
                    )
            except Exception:
                # Never block on DB errors
                pass

    except Exception:
        # Never block the pipeline
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
