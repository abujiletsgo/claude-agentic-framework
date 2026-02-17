#!/usr/bin/env python3
"""
Auto Escalation - PostToolUse Hook
====================================

Detects mid-task complexity growth and injects a directive to switch
to orchestration mode before the work spirals out of control.

Fires after every tool use. Tracks per-session complexity signals:
  - task_count     : TaskCreate calls (multi-task work in progress)
  - error_count    : Bash exits with non-zero code (repeated failures)
  - files_modified : unique files edited/written (wide-spread changes)
  - tool_use_count : total tool uses (long-running session)

Escalation fires when 2+ signals exceed their thresholds:
  - task_count     >= 4
  - error_count    >= 3
  - files_modified >= 8
  - tool_use_count >= 25

One escalation per session (won't spam). State stored in:
  ~/.claude/auto_escalate_state.json

Exit codes: always 0 (never blocks).
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime


# ── Thresholds ────────────────────────────────────────────────────────────────

THRESHOLDS = {
    "task_count":     4,   # 4+ tasks created → complex multi-task
    "error_count":    3,   # 3+ bash errors   → repeated failures
    "files_modified": 8,   # 8+ unique files   → wide-spread changes
    "tool_use_count": 25,  # 25+ tool uses     → long-running session
}
MIN_SIGNALS_TO_ESCALATE = 2   # Need 2+ signals to fire


# ── State management ─────────────────────────────────────────────────────────

def get_state_path() -> Path:
    return Path.home() / ".claude" / "auto_escalate_state.json"


def load_state(session_id: str) -> dict:
    state_path = get_state_path()
    if state_path.exists():
        try:
            with open(state_path) as f:
                state = json.load(f)
            if state.get("session_id") == session_id:
                return state
        except (json.JSONDecodeError, OSError):
            pass
    # Fresh state for this session
    return {
        "session_id": session_id,
        "task_count": 0,
        "error_count": 0,
        "files_modified": [],
        "tool_use_count": 0,
        "escalated": False,
        "escalation_turn": None,
        "created_at": datetime.now().isoformat(),
    }


def save_state(state: dict) -> None:
    state_path = get_state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)
    except OSError:
        pass


# ── Signal counting ───────────────────────────────────────────────────────────

def update_signals(state: dict, hook_input: dict) -> dict:
    """Update complexity signals based on the current tool use."""
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except (json.JSONDecodeError, ValueError):
            tool_input = {}

    state["tool_use_count"] += 1

    # TaskCreate → multi-task indicator
    if tool_name == "TaskCreate":
        state["task_count"] += 1

    # Bash failure → error indicator
    if tool_name == "Bash":
        tool_response = hook_input.get("tool_response", "")
        if isinstance(tool_response, str):
            try:
                resp = json.loads(tool_response)
            except (json.JSONDecodeError, ValueError):
                resp = {}
        elif isinstance(tool_response, dict):
            resp = tool_response
        else:
            resp = {}
        if resp.get("exit_code", 0) != 0:
            state["error_count"] += 1

    # Edit/Write → file modification indicator
    if tool_name in ("Edit", "Write", "MultiEdit"):
        file_path = tool_input.get("file_path", "")
        if file_path and file_path not in state["files_modified"]:
            state["files_modified"].append(file_path)

    return state


# ── Escalation check ─────────────────────────────────────────────────────────

def check_escalation(state: dict) -> tuple:
    """
    Returns (should_escalate: bool, triggered_signals: list[str]).

    Escalation fires when >= MIN_SIGNALS_TO_ESCALATE thresholds are crossed
    AND the session hasn't already escalated.
    """
    if state.get("escalated"):
        return False, []

    triggered = []
    if state["task_count"] >= THRESHOLDS["task_count"]:
        triggered.append(f"{state['task_count']} tasks created")
    if state["error_count"] >= THRESHOLDS["error_count"]:
        triggered.append(f"{state['error_count']} errors encountered")
    if len(state["files_modified"]) >= THRESHOLDS["files_modified"]:
        triggered.append(f"{len(state['files_modified'])} files modified")
    if state["tool_use_count"] >= THRESHOLDS["tool_use_count"]:
        triggered.append(f"{state['tool_use_count']} tool uses")

    should_escalate = len(triggered) >= MIN_SIGNALS_TO_ESCALATE
    return should_escalate, triggered


# ── Escalation output ─────────────────────────────────────────────────────────

ESCALATION_MESSAGE = """\
╔══════════════════════════════════════════════════════════════════╗
║  🤖 AUTO-ESCALATION: Mid-task complexity threshold exceeded      ║
╠══════════════════════════════════════════════════════════════════╣
║  Signals detected: {signals}
║                                                                  ║
║  MANDATORY: Spawn the orchestrator to coordinate remaining work. ║
║                                                                  ║
║  Use the Task tool NOW:                                          ║
║    Task(                                                         ║
║      subagent_type="orchestrator",                               ║
║      description="Coordinate remaining work",                    ║
║      prompt="<summarize what's been done and what remains>"      ║
║    )                                                             ║
║                                                                  ║
║  The orchestrator will distribute remaining work to specialists  ║
║  and synthesize results. Do NOT continue direct execution.       ║
╚══════════════════════════════════════════════════════════════════╝"""


def emit_escalation(triggered_signals: list) -> None:
    """Write the escalation directive to stderr (injected into Claude's context)."""
    signals_str = ", ".join(triggered_signals)
    # Pad to fit in the box
    padded = signals_str[:60].ljust(60)
    msg = ESCALATION_MESSAGE.format(signals=padded)
    print(msg, file=sys.stderr)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    session_id = hook_input.get("session_id", os.environ.get("CLAUDE_SESSION_ID", "unknown"))

    state = load_state(session_id)
    state = update_signals(state, hook_input)

    should_escalate, triggered = check_escalation(state)

    if should_escalate:
        state["escalated"] = True
        state["escalation_turn"] = state["tool_use_count"]
        emit_escalation(triggered)

    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
