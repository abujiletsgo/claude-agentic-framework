#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
inject_facts.py - SessionStart Hook (Layer 2: Episodic Memory Injection)
=========================================================================

Injects FACTS.md at session start as authoritative project ground truth.

This is the "recall" phase of the episodic memory layer. It fires after
auto_prime.py (architecture overview) and before inject_relevant.py
(cross-project knowledge), ensuring the session starts with verified facts.

Injection budget: ~2000 tokens (3000 chars), prioritized by confidence.
If no FACTS.md exists: creates it and injects an initialization notice.

Exit: always 0 (never blocks session start)
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fact_manager import facts_path, get_for_injection, init, count_facts


def get_project_name(cwd: str) -> str:
    return Path(cwd).resolve().name


def main():
    try:
        data = json.loads(sys.stdin.read())
        cwd = data.get("cwd", os.getcwd())
        project = get_project_name(cwd)
        path = facts_path(cwd)

        if not path.exists():
            # Initialize and inform Claude to populate it
            init(path, project)
            out = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": (
                        f"**FACTS.md initialized** at `.claude/FACTS.md` for `{project}`.\n"
                        "This is the project's episodic memory layer — it will auto-populate as you work.\n"
                        "Facts verified by execution will be saved here and injected at every session start.\n"
                        "You can add facts manually: `/facts add CONFIRMED \"fact text\"`"
                    ),
                }
            }
            print(json.dumps(out))
            return

        block = get_for_injection(path)
        counts = count_facts(path)
        total = sum(counts.values())

        if not block or total == 0:
            print(json.dumps({}))
            return

        # Build injection with authoritative prefix
        count_summary = " | ".join(
            f"{v} {k.lower()}" for k, v in counts.items() if v > 0 and k != "STALE"
        )
        header = (
            f"**PROJECT FACTS** ({count_summary}) — episodic memory layer, verified ground truth.\n"
            "Trust CONFIRMED entries fully. GOTCHAS override assumptions. "
            "Use PATHS before reading files to check if you already know the location.\n\n"
        )

        out = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": header + block,
            }
        }
        print(json.dumps(out))

    except Exception as e:
        print(f"inject_facts error: {e}", file=sys.stderr)
        print(json.dumps({}))

    sys.exit(0)


if __name__ == "__main__":
    main()
