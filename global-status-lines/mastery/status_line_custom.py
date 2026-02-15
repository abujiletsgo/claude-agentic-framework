#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""
Custom Status Line - Minimal + Action Emojis + Loading Animation

Display: Opus  main  ~/project  42%  ⚡🔬🌐

Features:
- Minimal info (model, branch, directory, context %)
- Animated loading indicator when working
- Action emojis for active agents (what they're doing, not animals)
- Clean, cute aesthetic
"""

import json
import sys
import os
import subprocess
from pathlib import Path

# ─── Action Emoji Assignments ────────────────────────────────────────

# No spinner - static display only (Claude Code refreshes too slowly for animation)

# Agent action emojis (what they're doing)
AGENT_ACTIONS = {
    "orchestrator": "🎯",      # Coordinating/targeting
    "builder": "🔨",           # Building/constructing
    "validator": "✅",         # Checking/validating
    "researcher": "🔬",        # Researching/analyzing
    "project-architect": "📐", # Designing/architecting
    "critical-analyst": "🔍",  # Deep analysis/investigating
    "rlm-root": "🔄",          # Recursing/iterating
    "meta-agent": "⚙️",        # Generating/configuring
    "scout-report-suggest": "🗺️", # Exploring/mapping
    "docs-scraper": "📄",      # Fetching documents
    "error-analyzer": "🐛",    # Debugging
    "test-generator": "🧪",    # Testing
    "code-review": "👀",       # Reviewing
    "security-scanner": "🔒",  # Security checking
    "refactoring-assistant": "♻️", # Refactoring
    "knowledge-db": "💾",      # Database operations

    # Fallback for unknown agents
    "unknown": "⚡"
}

# ─── Utility Functions ───────────────────────────────────────────────

def get_git_branch():
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=1
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            if branch:
                return branch[:15]  # Limit length
    except Exception:
        pass
    return None

def get_project_dir():
    """Get current project directory name."""
    cwd = Path.cwd()
    return f"~/{cwd.name}" if cwd.name else "~"

def get_context_percentage(hook_input):
    """Estimate context usage percentage."""
    # Claude Code sends context_window dict with used_percentage
    context_data = hook_input.get("context_window", {})
    if isinstance(context_data, dict):
        pct = context_data.get("used_percentage", 0) or 0
        return min(pct, 99)

    return 0

def get_model_tier(hook_input):
    """Get model tier (Opus/Sonnet/Haiku)."""
    # Claude Code sends model as dict with display_name
    model_info = hook_input.get("model", {})
    if isinstance(model_info, dict):
        model = model_info.get("display_name", "")
    elif isinstance(model_info, str):
        model = model_info
    else:
        model = ""

    model_lower = model.lower()
    if "opus" in model_lower:
        return "Opus"
    elif "sonnet" in model_lower:
        return "Sonnet"
    elif "haiku" in model_lower:
        return "Haiku"

    return model[:10] if model else "Claude"

def get_active_team_members():
    """
    Detect active team members from team config or task list.

    Returns: list of agent names currently working
    """
    team_members = []

    # Check for team config
    session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")

    # Try to find team config
    team_config_paths = [
        Path.home() / ".claude" / "teams",
        Path.cwd() / ".claude" / "teams"
    ]

    for teams_dir in team_config_paths:
        if not teams_dir.exists():
            continue

        # Find team configs
        for team_file in teams_dir.glob("*/config.json"):
            try:
                with open(team_file, 'r') as f:
                    team_data = json.load(f)
                    members = team_data.get("members", [])

                    # Extract agent types
                    for member in members:
                        agent_type = member.get("agentType", "unknown")
                        if agent_type and agent_type not in team_members:
                            team_members.append(agent_type)
            except Exception:
                continue

    return team_members[:5]  # Limit to 5 activities max

def check_compaction_active():
    """Check if auto context compaction is active (flag written by auto_context_manager)."""
    flag_file = Path("/tmp/claude/compacting_custom")
    if not flag_file.exists():
        return False
    try:
        import time
        # Flag is active if written within last 60 seconds
        age = time.time() - flag_file.stat().st_mtime
        if age < 60:
            return True
        # Stale flag — clean it up
        flag_file.unlink(missing_ok=True)
    except Exception:
        pass
    return False


# ─── ANSI Colors ─────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Foreground colors
FG_CYAN = "\033[36m"
FG_GREEN = "\033[32m"
FG_YELLOW = "\033[33m"
FG_MAGENTA = "\033[35m"
FG_BLUE = "\033[34m"
FG_WHITE = "\033[97m"
FG_GRAY = "\033[90m"

# ─── Status Line Builder ─────────────────────────────────────────────

def build_status_line(hook_input):
    """Build the status line output."""

    # Get info
    model_tier = get_model_tier(hook_input)
    branch = get_git_branch()
    project = get_project_dir()
    context_pct = get_context_percentage(hook_input)

    # Get activity indicators
    team_members = get_active_team_members()
    action_emojis = "".join(AGENT_ACTIONS.get(agent, AGENT_ACTIONS["unknown"]) for agent in team_members)

    # Build segments
    segments = []

    # Model tier
    if model_tier == "Opus":
        color = FG_MAGENTA
    elif model_tier == "Sonnet":
        color = FG_CYAN
    elif model_tier == "Haiku":
        color = FG_GREEN
    else:
        color = FG_WHITE

    segments.append(f"{color}{BOLD}{model_tier}{RESET}")

    # Git branch (if available)
    if branch:
        segments.append(f"{FG_GRAY}│{RESET} {FG_BLUE}{branch}{RESET}")

    # Project directory
    segments.append(f"{FG_GRAY}│{RESET} {DIM}{project}{RESET}")

    # Context percentage
    if context_pct > 0:
        if context_pct > 80:
            ctx_color = FG_YELLOW
        elif context_pct > 60:
            ctx_color = FG_GREEN
        else:
            ctx_color = FG_GRAY

        segments.append(f"{FG_GRAY}│{RESET} {ctx_color}{context_pct:.0f}%{RESET}")

    # Compaction indicator
    if check_compaction_active():
        segments.append(f"{FG_GRAY}│{RESET} {FG_YELLOW}COMPACTING{RESET}")

    # Activity indicators (action emojis only)
    if action_emojis:
        segments.append(f"{FG_GRAY}│{RESET} {action_emojis}")

    # Join and return
    return " ".join(segments)

# ─── Main ────────────────────────────────────────────────────────────

def main():
    """Main entry point."""
    try:
        # Read hook input from stdin
        hook_input = {}
        if not sys.stdin.isatty():
            try:
                input_data = sys.stdin.read().strip()
                if input_data:
                    hook_input = json.loads(input_data)
            except json.JSONDecodeError:
                pass

        # Build and print status line
        status_line = build_status_line(hook_input)
        print(status_line, flush=True)

    except Exception as e:
        # Fallback: minimal status
        print(f"Claude", flush=True)

if __name__ == "__main__":
    main()
