#!/usr/bin/env python3
"""
Enforce /orchestrate Skill Invocation - UserPromptSubmit Hook
=============================================================

Detects when the user types /orchestrate (or asks to orchestrate) and injects
a BLOCKING system reminder that forces the Skill tool to be invoked before
any other action. This prevents Claude from ignoring /orchestrate and doing
work single-threaded in the main agent.

Trigger: UserPromptSubmit
Exit: Always 0 (never blocks)
Output: additionalContext with mandatory Skill invocation reminder
"""

import json
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# Direct slash command
SLASH_ORCHESTRATE = re.compile(r"(?:^|\s)/orchestrate\b", re.IGNORECASE)

# Natural language requests that should also trigger orchestration
ORCHESTRATE_INTENT = re.compile(
    r"\b(?:orchestrate\b|run orchestrat\w*|use orchestrat\w*|spawn orchestrat\w*|"
    r"parallel agents?\b|multi.?agent\b|spawn.*team\b)",
    re.IGNORECASE,
)


def needs_orchestrate_enforcement(prompt: str) -> bool:
    """Return True if the prompt contains /orchestrate or orchestration intent."""
    stripped = prompt.strip()
    if not stripped:
        return False

    # Direct slash command — always enforce
    if SLASH_ORCHESTRATE.search(stripped):
        return True

    # Natural language — only if clearly requesting orchestration
    if ORCHESTRATE_INTENT.search(stripped):
        return True

    return False


# ---------------------------------------------------------------------------
# Enforcement reminder
# ---------------------------------------------------------------------------

ORCHESTRATE_ENFORCEMENT = """\
[ORCHESTRATE ENFORCEMENT — BLOCKING REQUIREMENT]
The user has requested /orchestrate. You MUST:

1. IMMEDIATELY call: Skill(skill="orchestrate", args="<user's full message>")
2. Do NOT read files, do NOT write code, do NOT research — the Skill tool FIRST
3. Do NOT treat /orchestrate as decorative text — it is a COMMAND
4. The skill will load the orchestrator protocol — YOU are the orchestrator
5. You coordinate by spawning parallel Agent() calls — never do work yourself

SEQUENCE: Skill("orchestrate") → protocol loads → YOU spawn parallel agents (researchers, builders, validators)
VIOLATION: Any Read/Edit/Bash call instead of spawning agents = failure"""

# Marker file for orchestrator_tool_guard.py
ORCH_GUARD_MARKER = "/tmp/caf_orch_guard.marker"
ORCH_DEPTH_FILE = "/tmp/caf_orch_depth"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        # CAF_MODE check
        _framework_dir = Path(__file__).parent.parent
        if str(_framework_dir) not in sys.path:
            sys.path.insert(0, str(_framework_dir))
        try:
            from caf_mode import should_run
            if not should_run("enforce_orchestrate"):
                sys.exit(0)
        except ImportError:
            pass

        # Dry-run mode: print to stderr instead of stdout so enforcement
        # is visible in logs but does NOT inject into Claude's context.
        dry_run = os.environ.get("CAF_DRY_RUN") == "1"

        input_data = json.load(sys.stdin)
        prompt = input_data.get("prompt", "")

        if needs_orchestrate_enforcement(prompt):
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": ORCHESTRATE_ENFORCEMENT,
                }
            }
            if dry_run:
                print(
                    f"[DRY-RUN] enforce_orchestrate would inject:\n{json.dumps(output, indent=2)}",
                    file=sys.stderr,
                )
            else:
                print(json.dumps(output))

            # Note: marker/depth files are managed by orch_depth_tracker.py
            # The guard hook blocks orchestrator SUBAGENTS from using
            # Read/Grep/Glob/Edit (forces delegation). The root agent
            # is NOT blocked — it coordinates by spawning agents directly.

        sys.exit(0)

    except Exception:
        # Never block
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
