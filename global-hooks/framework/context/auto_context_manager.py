#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = ["anthropic"]
# ///
"""
Auto Context Manager - Rolling Window Compaction

Monitors conversation every ~10 turns and proactively compresses "cold" segments
before hitting context limits. Uses current Claude instance for compression.

Triggers:
  - Context > 60% + cold segments exist → Queue for compression
  - Context > 80% + very old segments → Archive to L3

Exit codes:
  0 = Always (non-blocking hook)
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# ─── Configuration ───────────────────────────────────────────────────

# Cold segment thresholds
TURNS_UNTIL_COLD = 20  # Not mentioned in 20+ turns = cold
CONTEXT_THRESHOLD = 60  # Start compressing at 60% context usage
CHECK_FREQUENCY = 10    # Check every 10 turns

# Archive thresholds
ARCHIVE_THRESHOLD = 80  # Archive to L3 at 80% context
ARCHIVE_AGE_DAYS = 30   # Prune archives older than 30 days

# Token estimation (rough)
AVG_TOKENS_PER_CHAR = 0.25
MAX_CONTEXT_TOKENS = 200000

# Paths
def get_context_queue_path():
    """Get path to compression queue file"""
    session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")
    queue_dir = Path.home() / ".claude" / "data" / "context_queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    return queue_dir / f"{session_id}_pending.json"

def get_archive_dir():
    """Get path to L3 archive directory"""
    session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")
    archive_dir = Path.home() / ".claude" / "data" / "sessions" / session_id / "archived_context"
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir

# ─── Conversation Analysis ───────────────────────────────────────────

def estimate_context_usage(messages: List[Dict]) -> float:
    """Estimate current context usage as percentage"""
    total_chars = sum(
        len(str(msg.get("content", "")))
        for msg in messages
    )
    estimated_tokens = total_chars * AVG_TOKENS_PER_CHAR
    return (estimated_tokens / MAX_CONTEXT_TOKENS) * 100

def count_turns(messages: List[Dict]) -> int:
    """Count conversation turns (user + assistant pairs)"""
    return sum(1 for msg in messages if msg.get("role") == "assistant")

def extract_segments(messages: List[Dict]) -> List[Dict[str, Any]]:
    """
    Extract conversation segments based on task boundaries.

    A segment is a group of messages around a specific topic/task.
    Boundaries detected by:
    - Task completion markers
    - Topic shift indicators
    - Tool usage patterns
    """
    segments = []
    current_segment = {
        "messages": [],
        "topic": None,
        "start_turn": 0,
        "end_turn": 0,
        "completed": False,
        "last_mentioned_turn": 0
    }

    turn_count = 0

    for i, msg in enumerate(messages):
        if msg.get("role") == "assistant":
            turn_count += 1

        content = str(msg.get("content", ""))

        # Detect segment boundaries
        is_boundary = (
            "TaskUpdate" in content and "completed" in content or
            re.search(r"(done|completed|finished|ready)", content, re.I) and "✅" in content or
            i > 0 and len(current_segment["messages"]) > 5 and
            re.search(r"(next|now let's|moving on)", content, re.I)
        )

        if is_boundary and current_segment["messages"]:
            # Finalize current segment
            current_segment["end_turn"] = turn_count
            current_segment["last_mentioned_turn"] = turn_count
            segments.append(current_segment.copy())

            # Start new segment
            current_segment = {
                "messages": [msg],
                "topic": extract_topic(msg),
                "start_turn": turn_count,
                "end_turn": turn_count,
                "completed": "completed" in content.lower(),
                "last_mentioned_turn": turn_count
            }
        else:
            current_segment["messages"].append(msg)
            if not current_segment["topic"]:
                current_segment["topic"] = extract_topic(msg)

    # Add final segment
    if current_segment["messages"]:
        current_segment["end_turn"] = turn_count
        segments.append(current_segment)

    return segments

def extract_topic(msg: Dict) -> Optional[str]:
    """Extract topic from message (simplified)"""
    content = str(msg.get("content", ""))

    # Look for task subjects
    task_match = re.search(r'"subject":\s*"([^"]+)"', content)
    if task_match:
        return task_match.group(1)

    # Look for headings
    heading_match = re.search(r'^#{1,3}\s+(.+)$', content, re.M)
    if heading_match:
        return heading_match.group(1).strip()

    # Extract first sentence
    sentences = re.split(r'[.!?]\s+', content)
    if sentences:
        first = sentences[0].strip()
        if len(first) < 100:
            return first

    return None

def identify_cold_segments(segments: List[Dict], current_turn: int) -> List[Dict]:
    """Identify segments that are cold (not mentioned recently)"""
    cold = []
    for segment in segments:
        turns_since = current_turn - segment["last_mentioned_turn"]

        # Segment is cold if:
        # 1. Not mentioned in 20+ turns
        # 2. Marked as completed
        # 3. Has at least 5 messages (substantial content)
        if (turns_since >= TURNS_UNTIL_COLD and
            segment.get("completed", False) and
            len(segment["messages"]) >= 5):
            segment["turns_since_mention"] = turns_since
            cold.append(segment)

    return cold

# ─── Queue Management ────────────────────────────────────────────────

def load_queue() -> Dict:
    """Load pending compression queue"""
    queue_path = get_context_queue_path()
    if queue_path.exists():
        with open(queue_path, 'r') as f:
            return json.load(f)
    return {"pending": [], "compressed": [], "last_check_turn": 0}

def save_queue(queue: Dict):
    """Save pending compression queue"""
    queue_path = get_context_queue_path()
    with open(queue_path, 'w') as f:
        json.dump(queue, f, indent=2)

def queue_segments_for_compression(segments: List[Dict], current_turn: int):
    """Add cold segments to compression queue"""
    queue = load_queue()

    # Filter out already queued/compressed segments
    existing_topics = {s["topic"] for s in queue["pending"]} | {s["topic"] for s in queue["compressed"]}

    new_segments = [
        {
            "segment_id": f"seg_{current_turn}_{i}",
            "topic": seg["topic"],
            "start_turn": seg["start_turn"],
            "end_turn": seg["end_turn"],
            "message_count": len(seg["messages"]),
            "turns_since_mention": seg["turns_since_mention"],
            "queued_at_turn": current_turn,
            "timestamp": datetime.now().isoformat()
        }
        for i, seg in enumerate(segments)
        if seg["topic"] not in existing_topics
    ]

    queue["pending"].extend(new_segments)
    queue["last_check_turn"] = current_turn
    save_queue(queue)

    return len(new_segments)

# ─── Archive Management ──────────────────────────────────────────────

def prune_old_archives():
    """Remove archives older than ARCHIVE_AGE_DAYS"""
    archive_dir = get_archive_dir()
    cutoff = datetime.now() - timedelta(days=ARCHIVE_AGE_DAYS)

    pruned = 0
    for archive_file in archive_dir.glob("*.json"):
        if archive_file.stat().st_mtime < cutoff.timestamp():
            archive_file.unlink()
            pruned += 1

    return pruned

# ─── Main Hook Logic ─────────────────────────────────────────────────

def load_session_messages(session_id: str) -> List[Dict]:
    """Load conversation messages from session file"""
    session_file = Path.home() / ".claude" / "data" / "sessions" / f"{session_id}.json"

    if not session_file.exists():
        return []

    try:
        with open(session_file, 'r') as f:
            session_data = json.load(f)
            return session_data.get("messages", [])
    except Exception:
        return []

def main():
    try:
        # Read hook input
        input_data = json.load(sys.stdin)

        # Get session ID
        session_id = input_data.get("sessionId", os.environ.get("CLAUDE_SESSION_ID", "unknown"))

        # Load conversation history from session file
        messages = load_session_messages(session_id)

        if not messages:
            # No conversation history available, skip analysis
            sys.exit(0)

        # Count turns
        current_turn = count_turns(messages)

        # Load queue to check last check turn
        queue = load_queue()
        last_check = queue.get("last_check_turn", 0)

        # Only check every CHECK_FREQUENCY turns
        if current_turn - last_check < CHECK_FREQUENCY:
            sys.exit(0)

        # Estimate context usage
        context_pct = estimate_context_usage(messages)

        # Extract and analyze segments
        segments = extract_segments(messages)
        cold_segments = identify_cold_segments(segments, current_turn)

        # Check if compression is needed
        if context_pct > CONTEXT_THRESHOLD and cold_segments:
            # Queue segments for compression
            queued_count = queue_segments_for_compression(cold_segments, current_turn)

            if queued_count > 0:
                # Write flag for status line
                flag_dir = Path("/tmp/claude")
                flag_dir.mkdir(parents=True, exist_ok=True)
                (flag_dir / "compacting_custom").write_text(json.dumps({
                    "queued": queued_count,
                    "context_pct": round(context_pct),
                    "cold_topics": len(cold_segments),
                    "timestamp": datetime.now().isoformat()
                }))

                # Output system reminder for Claude to see
                print(
                    f"\n⚡ CONTEXT_MANAGER: {queued_count} cold segments ready for compression "
                    f"(context at {context_pct:.0f}%, {len(cold_segments)} cold topics)\n",
                    file=sys.stderr
                )

        # Periodic archive pruning (every 50 turns)
        if current_turn % 50 == 0:
            pruned = prune_old_archives()
            if pruned > 0:
                print(f"📦 CONTEXT_MANAGER: Pruned {pruned} old archives", file=sys.stderr)

    except Exception as e:
        # Non-blocking: log error but don't fail
        print(f"Context manager error (non-blocking): {e}", file=sys.stderr)

    # Always exit 0 (non-blocking)
    sys.exit(0)

if __name__ == "__main__":
    main()
