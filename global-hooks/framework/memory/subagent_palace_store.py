#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
subagent_palace_store.py — SubagentStop hook that stores agent output in project-local mempalace.

Reads tool_output from hook input and stores it as a drawer in the project mempalace.
Also extracts decision statements and writes them as KG triples.
Fail-open: always prints {} and exits 0.
"""

import json
import os
import sys
from datetime import date

# Add the hook's own directory to path so palace_init can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


DECISION_SIGNALS = ["decided", "chose", "will use", "approach:", "going with"]
MAX_KG_WRITES = 5
MIN_CONTENT_LENGTH = 50


def _extract_agent_type(tool_input: dict) -> str:
    """Extract agent type from tool_input if available."""
    if not tool_input:
        return "unknown"
    prompt = tool_input.get("prompt", "")
    if prompt:
        # Use first 60 chars of prompt as agent identifier
        return prompt[:60].strip().replace("\n", " ")
    return "unknown"


def _extract_decisions(text: str) -> list[str]:
    """Scan text for decision statements using signal words."""
    decisions = []
    for line in text.splitlines():
        line_lower = line.lower()
        if any(signal in line_lower for signal in DECISION_SIGNALS):
            decisions.append(line.strip())
    return decisions


def main():
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}
    except Exception:
        print("{}")
        sys.exit(0)

    try:
        tool_output = hook_input.get("tool_output", "") or ""
        content = tool_output.strip()

        # Exit silently if content is too short
        if len(content) < MIN_CONTENT_LENGTH:
            print("{}")
            sys.exit(0)

        cwd = hook_input.get("cwd") or os.getcwd()
        tool_input = hook_input.get("tool_input", {}) or {}
        project = os.path.basename(os.path.abspath(cwd))
        agent_type = _extract_agent_type(tool_input)

        from palace_init import store_drawer, get_project_kg

        # Store the agent output as a mempalace drawer
        store_drawer(
            content=content,
            cwd=cwd,
            wing=project,
            room="agent_results",
            source_file=f"agent:{agent_type}",
        )

        print(f"[Palace] Stored agent result for {project} ({len(content)} chars)", file=sys.stderr)

        # Extract decisions and write as KG triples
        decisions = _extract_decisions(content)
        if decisions:
            kg = get_project_kg(cwd=cwd)
            if kg is not None:
                today = date.today().isoformat()
                writes = 0
                for decision in decisions:
                    if writes >= MAX_KG_WRITES:
                        break
                    try:
                        kg.add_triple(
                            subject=project,
                            predicate="decided",
                            obj=decision[:200],
                            valid_from=today,
                            source_file="subagent_palace_store",
                        )
                        writes += 1
                    except Exception:
                        pass

    except Exception:
        pass

    print("{}")
    sys.exit(0)


if __name__ == "__main__":
    main()
