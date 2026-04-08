#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
subagent_kg_inject.py — SubagentStart hook: inject project-local KG context into spawned agents.

Queries the project-local knowledge graph for recent decisions and confirmed facts,
then emits them as additionalContext so spawned subagents start with relevant project history.

Fail-open: if mempalace is unavailable or KG is empty, emits {} and exits 0.
Target latency: <10ms (KG is SQLite, sub-ms queries).
"""

import json
import os
import sys
from datetime import date

# Add the directory containing palace_init to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    # Read hook input from stdin
    try:
        raw = sys.stdin.read() or "{}"
        hook_input = json.loads(raw)
    except Exception:
        hook_input = {}

    try:
        from palace_init import get_project_kg, has_mempalace

        # Get agent name for logging
        tool_input = hook_input.get("tool_input", {})
        agent_name = tool_input.get("name", "unknown")

        # Get CWD from hook input, fallback to os.getcwd()
        cwd = hook_input.get("cwd") or os.getcwd()

        # If mempalace not available, emit empty and exit
        if not has_mempalace():
            print(json.dumps({}))
            sys.exit(0)

        kg = get_project_kg(cwd)
        if kg is None:
            print(json.dumps({}))
            sys.exit(0)

        today = date.today().isoformat()

        # Query for "decided" relationship type
        decisions = []
        try:
            decisions = kg.query_relationship("decided", as_of=today) or []
        except Exception:
            decisions = []

        # Query for "confirmed" relationship type
        confirmed = []
        try:
            confirmed = kg.query_relationship("confirmed", as_of=today) or []
        except Exception:
            confirmed = []

        # If nothing to inject, emit empty and exit
        if not decisions and not confirmed:
            print(json.dumps({}))
            sys.exit(0)

        # Format as compact markdown
        lines = []

        if decisions:
            lines.append("## Prior Decisions (from project knowledge graph)")
            # Cap at 10 most recent
            for triple in decisions[:10]:
                obj = triple.get("object", triple.get("subject", "?"))
                valid_from = triple.get("valid_from", "")
                since_str = f" (since {valid_from})" if valid_from else ""
                lines.append(f"- {obj}{since_str}")

        if confirmed:
            lines.append("\n## Confirmed Facts (from project knowledge graph)")
            for triple in confirmed[:10]:
                obj = triple.get("object", triple.get("subject", "?"))
                valid_from = triple.get("valid_from", "")
                since_str = f" (since {valid_from})" if valid_from else ""
                lines.append(f"- {obj}{since_str}")

        context_text = "\n".join(lines)

        # Cap total output at 1500 chars (~375 tokens) — KG-only fast path
        if len(context_text) > 1500:
            context_text = context_text[:1470] + "\n\n*[truncated]*"

        n_injected = len(decisions[:10]) + len(confirmed[:10])
        print(f"[Palace] Injected {n_injected} decisions for agent {agent_name}", file=sys.stderr)

        output = {
            "hookSpecificOutput": {
                "additionalContext": context_text
            }
        }
        print(json.dumps(output))

    except Exception as e:
        print(f"[Palace] subagent_kg_inject error (non-blocking): {e}", file=sys.stderr)
        print(json.dumps({}))

    sys.exit(0)


if __name__ == "__main__":
    main()
