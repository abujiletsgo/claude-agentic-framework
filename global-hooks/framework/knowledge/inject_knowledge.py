#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Inject Knowledge - PreToolUse Hook (or SessionStart alternative)
================================================================

At the start of a session or before key tool uses, injects relevant
knowledge from the persistent database into the assistant's context.

Uses BM25 search to find entries relevant to the current working
directory, project name, or recent tool activity.

Exit: Always 0 (never blocks)
Output: JSON with optional "message" field to inject into context
"""

import json
import os
import sys
from pathlib import Path

# Import knowledge_db from same directory
sys.path.insert(0, str(Path(__file__).parent))


def get_project_context() -> str:
    """Infer project context from the current working directory."""
    cwd = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    cwd_lower = cwd.lower()

    # Match known project patterns
    if "vaultmind" in cwd_lower:
        return "vaultmind"
    if "claude-agentic" in cwd_lower:
        return "claude-agentic-framework"
    if "obsidian" in cwd_lower:
        return "obsidian"

    # Use the last directory component as context
    return Path(cwd).name


def format_knowledge_block(entries: list[dict]) -> str:
    """Format knowledge entries into a readable context block."""
    if not entries:
        return ""

    lines = ["## Relevant Knowledge from Previous Sessions", ""]

    for entry in entries:
        tag = entry.get("tag", "?")
        content = entry.get("content", "")
        context = entry.get("context", "")
        ts = entry.get("timestamp", "")[:10]  # Just the date

        prefix = f"[{tag}]"
        if context:
            prefix += f" ({context})"
        prefix += f" {ts}"

        lines.append(f"- **{prefix}**: {content}")

    lines.append("")
    return "\n".join(lines)


def main():
    """Hook entry point."""
    try:
        input_data = json.load(sys.stdin)
        session_id = input_data.get("session_id", "unknown")

        # Import knowledge_db
        try:
            from knowledge_db import get_recent, search_knowledge, count_entries
        except ImportError:
            sys.exit(0)

        # Check if we have any knowledge at all
        stats = count_entries()
        if stats["total"] == 0:
            sys.exit(0)

        project_context = get_project_context()

        # Gather relevant knowledge: recent entries + context-specific
        entries = []

        # Get recent decisions and learnings (most valuable for new sessions)
        recent = get_recent(
            limit=5,
            tags=["LEARNED", "DECISION"],
        )
        entries.extend(recent)

        # Get context-specific entries
        if project_context:
            try:
                context_results = search_knowledge(
                    query=project_context,
                    limit=5,
                )
                # Deduplicate by id
                existing_ids = {e["id"] for e in entries}
                for r in context_results:
                    if r["id"] not in existing_ids:
                        entries.append(r)
            except Exception:
                pass

        # Get recent patterns and facts
        recent_facts = get_recent(limit=3, tags=["FACT", "PATTERN"])
        existing_ids = {e["id"] for e in entries}
        for f in recent_facts:
            if f["id"] not in existing_ids:
                entries.append(f)

        # Cap at 10 entries total to avoid context bloat
        entries = entries[:10]

        if entries:
            message = format_knowledge_block(entries)
            # Output as a system message injection
            result = {
                "result": "continue",
                "message": message,
            }
            print(json.dumps(result))
        else:
            print(json.dumps({"result": "continue"}))

    except Exception:
        # Never block
        print(json.dumps({"result": "continue"}))

    sys.exit(0)


if __name__ == "__main__":
    main()
