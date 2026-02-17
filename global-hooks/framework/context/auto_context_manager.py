#!/usr/bin/env python3
"""
Auto Context Manager - Incremental Compaction Signal

Monitors the conversation transcript every CHECK_FREQUENCY turns.
When context usage exceeds CONTEXT_THRESHOLD and cold segments exist,
injects an additionalContext message asking Claude to summarize proactively.

Cold segment = completed topic not referenced in 20+ turns.

Exit codes:
  0 = Always (non-blocking hook)
"""

import json
import re
import sys
import os
from pathlib import Path
from datetime import datetime

# ─── Configuration ───────────────────────────────────────────────────

TURNS_UNTIL_COLD = 20      # Not mentioned in 20+ turns = cold
CONTEXT_THRESHOLD = 60     # Start signaling at 60% context usage
CHECK_FREQUENCY = 10       # Check every 10 assistant turns

# Token estimation (rough: Claude transcripts average ~0.25 tokens/char)
AVG_TOKENS_PER_CHAR = 0.25
MAX_CONTEXT_TOKENS = 200_000

# ─── Transcript parsing ───────────────────────────────────────────────

def parse_transcript(transcript_path: str) -> list[dict]:
    """Read JSONL transcript — same format as pre_compact_preserve.py."""
    messages = []
    try:
        path = Path(transcript_path)
        if not path.exists():
            return []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return messages


# ─── Analysis ────────────────────────────────────────────────────────

def estimate_context_pct(messages: list[dict]) -> float:
    """Estimate context usage % from transcript character count."""
    total_chars = sum(len(json.dumps(m)) for m in messages)
    estimated_tokens = total_chars * AVG_TOKENS_PER_CHAR
    return (estimated_tokens / MAX_CONTEXT_TOKENS) * 100


def count_assistant_turns(messages: list[dict]) -> int:
    return sum(1 for m in messages if m.get("role") == "assistant")


def find_cold_completed_topics(messages: list[dict], current_turn: int) -> list[str]:
    """
    Identify topics from completed tasks that haven't been referenced recently.

    Scans TaskCreate/TaskUpdate tool calls to find completed subjects,
    then checks whether they appear in the last TURNS_UNTIL_COLD turns.
    """
    # Collect all completed task subjects with the turn they completed
    completed: dict[str, int] = {}  # subject -> turn number
    turn = 0

    for msg in messages:
        if msg.get("role") == "assistant":
            turn += 1

        # Look for tool calls in content blocks
        content = msg.get("content", "")
        if not isinstance(content, list):
            content_str = str(content)
            # Parse TaskUpdate completed from raw JSON text
            for m in re.finditer(
                r'"tool_name"\s*:\s*"TaskUpdate".*?"status"\s*:\s*"completed".*?"subject"\s*:\s*"([^"]+)"',
                content_str,
                re.DOTALL,
            ):
                completed[m.group(1)] = turn
            continue

        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_use":
                continue
            name = block.get("name", "")
            inp = block.get("input", {})
            if name == "TaskUpdate" and inp.get("status") == "completed":
                subject = inp.get("subject", "")
                if subject:
                    completed[subject] = turn

    if not completed:
        return []

    # Collect text from the last TURNS_UNTIL_COLD assistant turns
    recent_turns_text = []
    recent_turn = 0
    cutoff = max(0, current_turn - TURNS_UNTIL_COLD)
    for msg in messages:
        if msg.get("role") == "assistant":
            recent_turn += 1
        if recent_turn > cutoff:
            recent_turns_text.append(json.dumps(msg).lower())
    recent_text = " ".join(recent_turns_text)

    # A topic is cold if it completed before the cutoff and isn't in recent text
    cold = []
    for subject, completed_at_turn in completed.items():
        if completed_at_turn <= cutoff:
            if subject.lower() not in recent_text:
                cold.append(subject)

    return cold[:5]  # Cap at 5 to keep the message concise


# ─── State file (track last check turn) ──────────────────────────────

def get_state_path(session_id: str) -> Path:
    state_dir = Path.home() / ".claude" / "data" / "context_queue"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / f"{session_id}_state.json"


def load_state(session_id: str) -> dict:
    p = get_state_path(session_id)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {"last_check_turn": 0}


def save_state(session_id: str, state: dict):
    try:
        get_state_path(session_id).write_text(json.dumps(state))
    except Exception:
        pass


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    try:
        input_data = json.load(sys.stdin)

        transcript_path = input_data.get("transcript_path", "")
        session_id = input_data.get("session_id", os.environ.get("CLAUDE_SESSION_ID", "unknown"))

        if not transcript_path:
            sys.exit(0)

        messages = parse_transcript(transcript_path)
        if not messages:
            sys.exit(0)

        current_turn = count_assistant_turns(messages)

        # Only check every CHECK_FREQUENCY turns
        state = load_state(session_id)
        last_check = state.get("last_check_turn", 0)
        if current_turn - last_check < CHECK_FREQUENCY:
            sys.exit(0)

        # Update check turn before analysis (avoid hammering on every call)
        state["last_check_turn"] = current_turn
        save_state(session_id, state)

        # Estimate context usage
        context_pct = estimate_context_pct(messages)
        if context_pct < CONTEXT_THRESHOLD:
            sys.exit(0)

        # Find cold completed topics
        cold_topics = find_cold_completed_topics(messages, current_turn)
        if not cold_topics:
            sys.exit(0)

        # Write flag for status line
        flag_dir = Path("/tmp/claude")
        flag_dir.mkdir(parents=True, exist_ok=True)
        (flag_dir / "compacting_custom").write_text(json.dumps({
            "queued": len(cold_topics),
            "context_pct": round(context_pct),
            "timestamp": datetime.now().isoformat(),
        }))

        topic_list = ", ".join(f'"{t}"' for t in cold_topics)

        result = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": (
                    f"INCREMENTAL COMPACTION: Context at {context_pct:.0f}%. "
                    f"These completed topics are taking up space and haven't been referenced in {TURNS_UNTIL_COLD}+ turns: "
                    f"{topic_list}. "
                    f"Summarize each into 1-2 sentences, then continue. "
                    f"Do NOT wait for the context limit — compact now."
                ),
            }
        }
        print(json.dumps(result))

    except Exception as e:
        print(f"[auto_context_manager] error (non-blocking): {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
