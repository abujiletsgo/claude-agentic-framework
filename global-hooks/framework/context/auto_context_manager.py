#!/usr/bin/env python3
"""
Auto Context Manager - Proactive Segment Pre-compression

Runs every CHECK_FREQUENCY assistant turns via PostToolUse.
At CONTEXT_THRESHOLD%+, finds cold completed tasks and writes
structured summaries to disk. These summaries are then injected
by pre_compact_preserve.py when Claude Code's compaction fires,
giving the compaction model pre-computed, high-quality summaries
instead of asking it to reconstruct 50-turn-old history cold.

Pipeline:
  [PostToolUse @ 70%] → detect cold tasks → write summaries to disk
  [PreCompact @ 95%]  → pre_compact_preserve reads summaries → injects verbatim

Cold segment = completed task not referenced in 20+ assistant turns.
Summaries are written once and never overwritten.

Exit: Always 0 (non-blocking)
"""

import json
import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────

TURNS_UNTIL_COLD = 20      # Not mentioned in N+ turns = cold
CONTEXT_THRESHOLD = 70     # Start pre-compressing at 70% context usage
CHECK_FREQUENCY = 10       # Check every N assistant turns

AVG_TOKENS_PER_CHAR = 0.25
MAX_CONTEXT_TOKENS = 200_000

SUMMARY_DIR = Path.home() / ".claude" / "data" / "compressed_context"

# ─── Transcript parsing ───────────────────────────────────────────────

def parse_transcript(transcript_path: str) -> list[dict]:
    """Read JSONL transcript. Each line is a message dict."""
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


def msg_role(msg: dict) -> str:
    """Extract role from a transcript message (handles message wrapper)."""
    return msg.get("message", {}).get("role", "")


def msg_content(msg: dict) -> list:
    """Extract content list from a transcript message."""
    content = msg.get("message", {}).get("content", [])
    return content if isinstance(content, list) else []


# ─── Context estimation ───────────────────────────────────────────────

def estimate_context_pct(messages: list[dict]) -> float:
    total_chars = sum(len(json.dumps(m)) for m in messages)
    estimated_tokens = total_chars * AVG_TOKENS_PER_CHAR
    return (estimated_tokens / MAX_CONTEXT_TOKENS) * 100


def count_assistant_turns(messages: list[dict]) -> int:
    return sum(1 for m in messages if msg_role(m) == "assistant")


# ─── Task registry (same approach as pre_compact_preserve.py) ────────

def build_task_registry(messages: list[dict]) -> dict:
    """
    Returns:
      registry[task_id] = {
        "subject": str,
        "start_turn": int,   # assistant turn when TaskCreate fired
        "end_turn": int,     # assistant turn when TaskUpdate completed fired
        "status": "pending"|"in_progress"|"completed"
      }
    Correlates TaskCreate tool_use blocks with their tool_result responses
    to get the real task_id → subject mapping.
    """
    pending_creates = {}   # tool_use_id -> {"subject": str, "turn": int}
    registry = {}          # task_id -> task info

    turn = 0
    for msg in messages:
        role = msg_role(msg)
        if role == "assistant":
            turn += 1

        for block in msg_content(msg):
            if not isinstance(block, dict):
                continue

            btype = block.get("type", "")

            # TaskCreate call: remember tool_use_id + subject + turn
            if btype == "tool_use" and block.get("name") == "TaskCreate":
                tool_use_id = block.get("id", "")
                subject = block.get("input", {}).get("subject", "")
                if tool_use_id and subject:
                    pending_creates[tool_use_id] = {"subject": subject, "turn": turn}

            # Tool result: match back to TaskCreate to get real task_id
            elif btype == "tool_result":
                tool_use_id = block.get("tool_use_id", "")
                if tool_use_id in pending_creates:
                    info = pending_creates.pop(tool_use_id)
                    # Parse task_id from result JSON
                    content = block.get("content", "")
                    if isinstance(content, list):
                        content = " ".join(
                            b.get("text", "") for b in content
                            if isinstance(b, dict) and b.get("type") == "text"
                        )
                    try:
                        data = json.loads(content)
                        task_id = str(data.get("taskId") or data.get("id") or "")
                    except (json.JSONDecodeError, AttributeError):
                        task_id = tool_use_id  # fallback

                    if task_id:
                        registry[task_id] = {
                            "subject": info["subject"],
                            "start_turn": info["turn"],
                            "end_turn": None,
                            "status": "pending",
                        }

            # TaskUpdate: track status and completion turn
            elif btype == "tool_use" and block.get("name") == "TaskUpdate":
                task_id = str(block.get("input", {}).get("taskId", ""))
                status = block.get("input", {}).get("status", "")
                if task_id and task_id in registry:
                    registry[task_id]["status"] = status
                    if status == "completed":
                        registry[task_id]["end_turn"] = turn

    return registry


# ─── Cold topic detection ─────────────────────────────────────────────

def find_cold_tasks(
    messages: list[dict],
    registry: dict,
    current_turn: int,
) -> list[dict]:
    """
    Returns tasks that are:
    - Completed
    - Not mentioned in the last TURNS_UNTIL_COLD assistant turns
    """
    # Collect text from recent turns for mention check
    recent_text_parts = []
    seen_turn = 0
    cutoff = max(0, current_turn - TURNS_UNTIL_COLD)
    for msg in messages:
        if msg_role(msg) == "assistant":
            seen_turn += 1
        if seen_turn > cutoff:
            recent_text_parts.append(json.dumps(msg).lower())
    recent_text = " ".join(recent_text_parts)

    cold = []
    for task_id, info in registry.items():
        if info["status"] != "completed":
            continue
        end_turn = info.get("end_turn") or 0
        if end_turn > cutoff:
            continue  # Completed too recently to be cold
        subject = info["subject"]
        if subject.lower() in recent_text:
            continue  # Still being referenced
        cold.append({"task_id": task_id, **info})

    return cold


# ─── Segment content extraction ───────────────────────────────────────

def extract_segment_content(
    messages: list[dict],
    start_turn: int,
    end_turn: int,
) -> dict:
    """
    Extract key content from a task's turn range without API calls.
    Returns structured summary data.
    """
    files_modified = []
    commands_run = []
    key_outcomes = []
    errors_seen = []
    seen_files = set()
    seen_cmds = set()

    turn = 0
    for msg in messages:
        if msg_role(msg) == "assistant":
            turn += 1

        if turn < start_turn:
            continue
        if end_turn and turn > end_turn:
            break

        for block in msg_content(msg):
            if not isinstance(block, dict):
                continue

            btype = block.get("type", "")

            if btype == "tool_use":
                name = block.get("name", "")
                inp = block.get("input", {})

                if name in ("Edit", "Write"):
                    fp = inp.get("file_path", "")
                    if fp and fp not in seen_files:
                        seen_files.add(fp)
                        files_modified.append(fp)

                elif name == "Bash":
                    cmd = inp.get("command", "")[:100]
                    if cmd and cmd not in seen_cmds:
                        seen_cmds.add(cmd)
                        commands_run.append(cmd)

            elif btype == "text" and msg_role(msg) == "assistant":
                text = block.get("text", "").strip()
                # Short focused messages are likely decision/outcome summaries
                if text and len(text) < 300 and "\n\n" not in text:
                    key_outcomes.append(text[:250])
                # Capture error mentions
                text_lower = text.lower()
                if any(s in text_lower for s in ["error:", "failed:", "fixed:", "resolved:"]):
                    errors_seen.append(text[:200])

    return {
        "files_modified": files_modified[:15],
        "commands_run": commands_run[:8],
        "key_outcomes": key_outcomes[:6],
        "errors_resolved": errors_seen[:4],
    }


# ─── Summary persistence ──────────────────────────────────────────────

def summary_path(session_id: str, task_id: str) -> Path:
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    safe_id = hashlib.md5(f"{session_id}:{task_id}".encode()).hexdigest()[:12]
    return SUMMARY_DIR / f"{safe_id}.json"


def summary_exists(session_id: str, task_id: str) -> bool:
    return summary_path(session_id, task_id).exists()


def write_summary(session_id: str, task: dict, content: dict):
    path = summary_path(session_id, task["task_id"])
    data = {
        "session_id": session_id,
        "task_id": task["task_id"],
        "subject": task["subject"],
        "start_turn": task.get("start_turn"),
        "end_turn": task.get("end_turn"),
        "compressed_at": datetime.now().isoformat(),
        **content,
    }
    path.write_text(json.dumps(data, indent=2))


def load_session_summaries(session_id: str) -> list[dict]:
    """Load all pre-computed summaries for a session."""
    summaries = []
    if not SUMMARY_DIR.exists():
        return summaries
    for p in SUMMARY_DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text())
            if data.get("session_id") == session_id:
                summaries.append(data)
        except Exception:
            pass
    return summaries


# ─── State file ───────────────────────────────────────────────────────

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
        session_id = input_data.get("session_id") or os.environ.get("CLAUDE_SESSION_ID", "unknown")

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

        state["last_check_turn"] = current_turn
        save_state(session_id, state)

        # Check context usage
        context_pct = estimate_context_pct(messages)
        if context_pct < CONTEXT_THRESHOLD:
            sys.exit(0)

        # Build task registry and find cold tasks
        registry = build_task_registry(messages)
        cold_tasks = find_cold_tasks(messages, registry, current_turn)
        if not cold_tasks:
            sys.exit(0)

        # Write pre-computed summaries for cold tasks (skip if already done)
        newly_written = []
        for task in cold_tasks:
            task_id = task["task_id"]
            if summary_exists(session_id, task_id):
                continue
            content = extract_segment_content(
                messages,
                task.get("start_turn", 0),
                task.get("end_turn"),
            )
            write_summary(session_id, task, content)
            newly_written.append(task["subject"])

        if not newly_written:
            sys.exit(0)

        # Write status flag for observability/status line
        flag_dir = Path("/tmp/claude")
        flag_dir.mkdir(parents=True, exist_ok=True)
        (flag_dir / "compacting_custom").write_text(json.dumps({
            "compressed": len(newly_written),
            "context_pct": round(context_pct),
            "timestamp": datetime.now().isoformat(),
        }))

        # Minimal signal — actual payoff is when pre_compact_preserve reads summaries
        topics = ", ".join(f'"{t}"' for t in newly_written[:3])
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": (
                    f"[context-manager] Pre-compressed {len(newly_written)} cold task(s) to disk "
                    f"at {context_pct:.0f}% context: {topics}. "
                    f"Summaries will be injected automatically if compaction fires."
                ),
            }
        }
        print(json.dumps(result))

    except Exception as e:
        print(f"[auto_context_manager] error (non-blocking): {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
