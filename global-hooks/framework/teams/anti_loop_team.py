#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Anti-Loop Team - PreToolUse:Task Hook
======================================

Prevents teammates from spawning their own teams (recursive team creation).
Also limits team size to prevent resource exhaustion.

Prevents:
  - Teammates spawning sub-teams (only lead can delegate)
  - Recursive team creation (teams within teams)
  - Team size exceeding configured limits
  - Infinite delegation loops

Exit Codes:
  0 - Allow (safe delegation)
  1 - Warn (approaching team size limit)
  2 - Block (unsafe delegation pattern detected)

Integration:
  - Monitors team hierarchy depth
  - Tracks total active agents
  - Enforces delegation rules
  - Prevents resource exhaustion
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def load_input() -> dict:
    """Load input from stdin."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def is_teammate_agent(agent_name: str) -> bool:
    """
    Check if the current agent is a teammate.

    Teammates should NOT spawn their own teams.
    """
    teammate_names = [
        "builder",
        "validator",
        "researcher",
        "context-manager",
        "project-skill-generator",
    ]

    return agent_name.lower() in teammate_names


def get_team_hierarchy_depth(session_id: str) -> int:
    """
    Calculate current team hierarchy depth.

    Returns:
        Depth level (0 = main agent, 1 = first-level team, etc.)
    """
    # Check session hierarchy in session tracking
    session_dir = Path.home() / ".claude" / "data" / "session-hierarchy"
    if not session_dir.exists():
        return 0

    session_file = session_dir / f"{session_id}.json"
    if not session_file.exists():
        return 0

    try:
        session_data = json.loads(session_file.read_text())
        return session_data.get("depth", 0)
    except (json.JSONDecodeError, KeyError):
        return 0


def count_active_agents() -> int:
    """
    Count currently active agent sessions.

    Returns:
        Number of active agent sessions
    """
    session_dir = Path.home() / ".claude" / "data" / "team-sessions"
    if not session_dir.exists():
        return 0

    current_time = datetime.now()
    active_count = 0

    # Count sessions active within last 5 minutes
    for session_file in session_dir.glob("*.json"):
        try:
            session_data = json.loads(session_file.read_text())
            started_at = datetime.fromisoformat(session_data.get("started_at", ""))
            age_minutes = (current_time - started_at).total_seconds() / 60

            if age_minutes < 5:
                active_count += 1
        except (json.JSONDecodeError, ValueError, KeyError):
            continue

    return active_count


def is_safe_delegation(
    agent_name: str,
    target_agent: str,
    hierarchy_depth: int,
    active_agents: int,
) -> dict:
    """
    Check if delegation is safe and within limits.

    Returns:
        dict with keys: safe, reason, warnings
    """
    result = {
        "safe": True,
        "reason": "",
        "warnings": [],
    }

    # Configuration limits
    MAX_HIERARCHY_DEPTH = 2  # Main -> Team -> (no more)
    MAX_ACTIVE_AGENTS = 8    # Total concurrent agents
    WARN_THRESHOLD = 6       # Warn when approaching limit

    # Rule 1: Teammates cannot spawn teams
    if is_teammate_agent(agent_name):
        result["safe"] = False
        result["reason"] = (
            f"Teammate agent '{agent_name}' cannot spawn sub-teams. "
            "Only the lead agent can delegate to teammates."
        )
        return result

    # Rule 2: Check hierarchy depth
    if hierarchy_depth >= MAX_HIERARCHY_DEPTH:
        result["safe"] = False
        result["reason"] = (
            f"Team hierarchy depth limit ({MAX_HIERARCHY_DEPTH}) reached. "
            "Cannot create teams within teams."
        )
        return result

    # Rule 3: Check active agent count
    if active_agents >= MAX_ACTIVE_AGENTS:
        result["safe"] = False
        result["reason"] = (
            f"Active agent limit ({MAX_ACTIVE_AGENTS}) reached. "
            "Wait for current agents to complete before spawning more."
        )
        return result

    # Warning: Approaching limits
    if active_agents >= WARN_THRESHOLD:
        result["warnings"].append(
            f"Approaching active agent limit ({active_agents}/{MAX_ACTIVE_AGENTS}). "
            "Consider completing existing tasks before spawning more agents."
        )

    if hierarchy_depth >= MAX_HIERARCHY_DEPTH - 1:
        result["warnings"].append(
            f"Approaching hierarchy depth limit ({hierarchy_depth + 1}/{MAX_HIERARCHY_DEPTH}). "
            "This delegation level cannot spawn further sub-teams."
        )

    return result


def log_delegation_check(
    agent_name: str,
    target_agent: str,
    safety_check: dict,
    action: str,
):
    """Log delegation safety check for audit."""
    log_dir = Path.home() / ".claude" / "logs" / "teams"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "anti_loop_team.jsonl"

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent_name,
        "target": target_agent,
        "safety_check": safety_check,
        "action": action,
        "event": "delegation_safety_check",
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def extract_target_agent(tool_args: dict) -> Optional[str]:
    """
    Extract target agent name from Task tool arguments.

    Returns:
        Agent name if found, None otherwise
    """
    # Task tool might specify agent in different ways
    agent = tool_args.get("agent")
    agent_type = tool_args.get("agent_type")
    description = tool_args.get("description", "")

    if agent:
        return agent
    if agent_type:
        return agent_type

    # Try to detect agent names in description
    known_agents = [
        "builder", "validator", "researcher", "context-manager",
        "project-skill-generator", "orchestrator", "rlm-root",
    ]

    for known_agent in known_agents:
        if known_agent in description.lower():
            return known_agent

    return None


def main():
    """Main hook logic."""
    input_data = load_input()

    # Extract info
    tool_name = input_data.get("tool_name", "")
    agent_name = input_data.get("agent_name", "main")
    session_id = input_data.get("session_id", "unknown")
    tool_args = input_data.get("tool_arguments", {})

    # Only check Task tool invocations
    if tool_name != "Task":
        sys.exit(0)

    # Extract target agent
    target_agent = extract_target_agent(tool_args)
    if not target_agent:
        # Can't determine target - allow but log
        sys.exit(0)

    # Get current state
    hierarchy_depth = get_team_hierarchy_depth(session_id)
    active_agents = count_active_agents()

    # Check if delegation is safe
    safety_check = is_safe_delegation(
        agent_name, target_agent, hierarchy_depth, active_agents
    )

    # Log the check
    log_delegation_check(agent_name, target_agent, safety_check, "checked")

    # Decide action based on safety check
    if not safety_check["safe"]:
        # Unsafe delegation - block
        feedback = {
            "message": "[Anti-Loop Team] Delegation blocked - safety limit reached",
            "reason": safety_check["reason"],
            "current_state": {
                "hierarchy_depth": hierarchy_depth,
                "active_agents": active_agents,
            },
            "action": (
                "Consider waiting for existing agents to complete, "
                "or restructure your approach to avoid deep delegation."
            ),
        }
        print(json.dumps(feedback))
        log_delegation_check(agent_name, target_agent, safety_check, "blocked")
        sys.exit(2)

    elif safety_check["warnings"]:
        # Safe but with warnings
        warning = {
            "message": "[Anti-Loop Team] Delegation allowed with warnings",
            "warnings": safety_check["warnings"],
            "current_state": {
                "hierarchy_depth": hierarchy_depth,
                "active_agents": active_agents,
            },
        }
        print(json.dumps(warning))
        log_delegation_check(agent_name, target_agent, safety_check, "warned")
        sys.exit(1)

    else:
        # All good
        log_delegation_check(agent_name, target_agent, safety_check, "allowed")
        sys.exit(0)


if __name__ == "__main__":
    main()
