#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Auto Team Review - PostToolUse Hook

Automatically runs quality checks when team work completes.

Logic:
  - Simple tasks (no team) → manual skills (save tokens)
  - Complex tasks (team spawned) → auto-review stack (worth the cost)

Triggers:
  1. TeamCreate detected → mark session as "team mode"
  2. Team completion detected → run review stack:
     - code-review skill (Sonnet)
     - security-scanner skill (Opus)
     - test-generator skill (Sonnet)

Cost: ~$2-4 per team completion (justified for complex work)

Exit codes:
  0: Always (non-blocking)
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# ─── Configuration ───────────────────────────────────────────────────

# Team mode tracking
def get_team_mode_file():
    """Get path to team mode tracking file."""
    session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")
    team_dir = Path.home() / ".claude" / "data" / "team_mode"
    team_dir.mkdir(parents=True, exist_ok=True)
    return team_dir / f"{session_id}.json"

# ─── Team Detection ──────────────────────────────────────────────────

def detect_team_create(hook_input):
    """Detect if TeamCreate was called."""
    tool = hook_input.get("tool", {})
    tool_name = tool.get("name", "")

    if tool_name == "TeamCreate":
        tool_input = tool.get("input", {})
        team_name = tool_input.get("team_name", "unknown")
        return True, team_name

    return False, None

def detect_team_completion(hook_input):
    """
    Detect if team work has completed.

    Signals:
    - TeamDelete called
    - Multiple SendMessage with type="shutdown_response" approve=true
    - Task tool spawns multiple agents then all go idle
    """
    tool = hook_input.get("tool", {})
    tool_name = tool.get("name", "")

    # Direct signal: TeamDelete
    if tool_name == "TeamDelete":
        return True, "TeamDelete"

    # Shutdown responses (team winding down)
    if tool_name == "SendMessage":
        tool_input = tool.get("input", {})
        msg_type = tool_input.get("type", "")

        if msg_type == "shutdown_response":
            approve = tool_input.get("approve", False)
            if approve:
                return True, "shutdown_approved"

    return False, None

# ─── Team Mode State Management ──────────────────────────────────────

def load_team_mode():
    """Load team mode state."""
    team_file = get_team_mode_file()

    if not team_file.exists():
        return None

    try:
        with open(team_file, 'r') as f:
            return json.load(f)
    except Exception:
        return None

def save_team_mode(team_name):
    """Save team mode state."""
    team_file = get_team_mode_file()

    state = {
        "team_name": team_name,
        "created_at": datetime.now().isoformat(),
        "review_pending": False
    }

    with open(team_file, 'w') as f:
        json.dump(state, f, indent=2)

def mark_review_pending():
    """Mark that review should run."""
    team_file = get_team_mode_file()
    state = load_team_mode()

    if state:
        state["review_pending"] = True
        state["completed_at"] = datetime.now().isoformat()

        with open(team_file, 'w') as f:
            json.dump(state, f, indent=2)

def clear_team_mode():
    """Clear team mode (review completed or team deleted)."""
    team_file = get_team_mode_file()

    if team_file.exists():
        team_file.unlink()

# ─── Review Stack ────────────────────────────────────────────────────

def trigger_review_stack():
    """
    Output suggestion to run review stack.

    Note: This outputs a message to stderr. Claude sees it and can choose
    to run the skills. We don't auto-spawn skills from hooks (that would
    require subprocess spawning which is fragile).

    Instead, we output a clear prompt that Claude should see and act on.
    """

    review_message = """
┌─────────────────────────────────────────────────────────────┐
│ 🎯 TEAM WORK COMPLETED - AUTO QUALITY REVIEW                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Complex team task finished. Running quality checks:        │
│                                                             │
│ 1. 👀 Code Review (Sonnet)                                 │
│    /review                                                  │
│                                                             │
│ 2. 🔒 Security Scan (Opus)                                 │
│    /security-scanner                                        │
│                                                             │
│ 3. 🧪 Test Coverage (Sonnet)                               │
│    /test-generator                                          │
│                                                             │
│ Estimated cost: ~$2-4 (justified for complex work)         │
│                                                             │
└─────────────────────────────────────────────────────────────┘

RECOMMENDED: Run these skills now to ensure quality.
"""

    print(review_message, file=sys.stderr)

# ─── Main Hook Logic ─────────────────────────────────────────────────

def main():
    try:
        # Read hook input
        hook_input = json.load(sys.stdin)

        # Check for TeamCreate
        is_team_create, team_name = detect_team_create(hook_input)

        if is_team_create:
            save_team_mode(team_name)
            print(f"\n🎯 [Team Mode] Activated for team: {team_name}", file=sys.stderr)
            print(f"    Auto-review will run when team completes.\n", file=sys.stderr)

        # Check for team completion
        is_complete, signal = detect_team_completion(hook_input)

        if is_complete:
            team_state = load_team_mode()

            if team_state and not team_state.get("review_pending", False):
                # Team completed, trigger review
                mark_review_pending()

                print(f"\n🎯 [Team Mode] Team completed (signal: {signal})", file=sys.stderr)
                trigger_review_stack()

                # Don't clear team mode yet - let it persist until review runs
                # This prevents duplicate review triggers

    except Exception as e:
        # Non-blocking: log error but don't fail
        print(f"[Auto Team Review] Error (non-blocking): {e}", file=sys.stderr)

    # Always exit 0 (non-blocking)
    sys.exit(0)

if __name__ == "__main__":
    main()
