#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
kg_session_context.py — Query mempalace KG for current facts at session start.

Fail-open: if mempalace is unavailable or KG is empty, emits no message.
Runs as a sub-hook in session_startup.py chain.
"""

import json
import os
import sys
from datetime import date


def _get_kg(cwd=None):
    """Import and return a project-local KnowledgeGraph. Returns None if unavailable."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from palace_init import get_project_kg
        return get_project_kg(cwd)
    except Exception:
        return None


def main():
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
    except Exception:
        hook_input = {}

    cwd = hook_input.get("cwd", os.getcwd())

    try:
        kg = _get_kg(cwd)
        if kg is None:
            print(json.dumps({}))
            sys.exit(0)

        stats = kg.stats()
        if stats.get("current_facts", 0) == 0:
            print(json.dumps({}))
            sys.exit(0)

        today = date.today().isoformat()

        # Get all current facts, grouped by predicate type
        facts_by_type = {}
        for rel_type in stats.get("relationship_types", []):
            triples = kg.query_relationship(rel_type, as_of=today)
            if triples:
                facts_by_type[rel_type] = triples

        if not facts_by_type:
            print(json.dumps({}))
            sys.exit(0)

        # Format as readable context
        lines = ["## Knowledge Graph: Current Facts"]
        lines.append(f"*{stats.get('current_facts', 0)} active facts as of {today}*\n")

        for rel_type, triples in sorted(facts_by_type.items()):
            lines.append(f"**{rel_type.upper()}** ({len(triples)} facts)")
            for t in triples[:15]:  # Cap per category to avoid bloat
                subj = t.get("subject", "?")
                obj = t.get("object", "?")
                since = t.get("valid_from", "")
                since_str = f" (since {since})" if since else ""
                lines.append(f"- {subj} → {obj}{since_str}")
            if len(triples) > 15:
                lines.append(f"- ... and {len(triples) - 15} more")
            lines.append("")

        message = "\n".join(lines)

        # Cap total size to avoid context bloat (max ~2000 chars)
        if len(message) > 2000:
            message = message[:1950] + "\n\n*[truncated — query mempalace for full KG]*"

        print(json.dumps({"message": message}))

    except Exception as e:
        print(f"KG session context error (non-blocking): {e}", file=sys.stderr)
        print(json.dumps({}))

    sys.exit(0)


if __name__ == "__main__":
    main()
