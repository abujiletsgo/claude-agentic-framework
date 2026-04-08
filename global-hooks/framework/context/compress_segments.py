#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Segment Compression Helper

Used by Claude to compress queued segments and save to L2 storage.

Usage (called by Claude):
  uv run compress_segments.py --segment-id seg_42_0 --compressed-content "..."
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# ─── Paths ───────────────────────────────────────────────────────────

def get_queue_path():
    """Get path to compression queue file"""
    session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")
    queue_dir = Path.home() / ".claude" / "data" / "context_queue"
    return queue_dir / f"{session_id}_pending.json"

def get_l2_storage_dir():
    """Get path to L2 storage directory (knowledge-db)"""
    # Use project directory if available, else global
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        storage_dir = Path(project_dir) / "data" / "knowledge-db" / "compressed_context"
    else:
        storage_dir = Path.home() / ".claude" / "data" / "knowledge-db" / "compressed_context"

    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir

# ─── Queue Management ────────────────────────────────────────────────

def load_queue() -> Dict:
    """Load pending compression queue"""
    queue_path = get_queue_path()
    if queue_path.exists():
        with open(queue_path, 'r') as f:
            return json.load(f)
    return {"pending": [], "compressed": [], "last_check_turn": 0}

def save_queue(queue: Dict):
    """Save compression queue"""
    queue_path = get_queue_path()
    with open(queue_path, 'w') as f:
        json.dump(queue, f, indent=2)

def get_pending_segments() -> list:
    """Get list of segments pending compression"""
    queue = load_queue()
    return queue.get("pending", [])

def mark_segment_compressed(segment_id: str, storage_location: str,
                           original_tokens: int, compressed_tokens: int):
    """Mark a segment as compressed and move to compressed list"""
    queue = load_queue()

    # Find and remove from pending
    pending_seg = None
    for i, seg in enumerate(queue["pending"]):
        if seg["segment_id"] == segment_id:
            pending_seg = queue["pending"].pop(i)
            break

    if not pending_seg:
        print(f"Warning: Segment {segment_id} not found in pending queue", file=sys.stderr)
        return

    # Add to compressed list
    compressed_entry = {
        **pending_seg,
        "compressed_at_turn": pending_seg.get("queued_at_turn", 0) + 5,  # Estimate
        "original_tokens": original_tokens,
        "compressed_tokens": compressed_tokens,
        "compression_ratio": round(original_tokens / compressed_tokens, 1) if compressed_tokens > 0 else 0,
        "storage_location": storage_location,
        "timestamp": datetime.now().isoformat()
    }

    queue["compressed"].append(compressed_entry)
    save_queue(queue)

# ─── L2 Storage ──────────────────────────────────────────────────────

def save_compressed_segment(segment_id: str, topic: str, compressed_content: str,
                           key_decisions: list, key_files: list,
                           original_tokens: int, compressed_tokens: int,
                           metadata: Dict[str, Any]) -> str:
    """
    Save compressed segment to L2 storage (knowledge-db).

    Returns: storage location path
    """
    storage_dir = get_l2_storage_dir()
    storage_path = storage_dir / f"{segment_id}.json"

    session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")

    segment_data = {
        "segment_id": segment_id,
        "topic": topic,
        "session_id": session_id,
        "start_turn": metadata.get("start_turn", 0),
        "end_turn": metadata.get("end_turn", 0),
        "original_tokens": original_tokens,
        "compressed_tokens": compressed_tokens,
        "compression_ratio": round(original_tokens / compressed_tokens, 1) if compressed_tokens > 0 else 0,
        "compressed_at": datetime.now().isoformat(),
        "last_accessed": datetime.now().isoformat(),
        "access_count": 0,
        "relevance_score": 0.85,  # Default, can be updated later
        "compressed_content": compressed_content,
        "key_decisions": key_decisions,
        "key_files": key_files,
        "metadata": {
            "contains_code": any(f.endswith(('.py', '.js', '.ts', '.go', '.rs')) for f in key_files),
            "contains_errors": "error" in compressed_content.lower() or "fix" in compressed_content.lower(),
            "task_completed": metadata.get("completed", True),
            **metadata
        }
    }

    with open(storage_path, 'w') as f:
        json.dump(segment_data, f, indent=2)

    return str(storage_path)

# ─── CLI Interface ───────────────────────────────────────────────────

def cli_save_segment():
    """CLI interface for Claude to save compressed segments"""
    import argparse

    parser = argparse.ArgumentParser(description="Save compressed segment to L2 storage")
    parser.add_argument("--segment-id", required=True, help="Segment ID")
    parser.add_argument("--topic", required=True, help="Segment topic")
    parser.add_argument("--compressed-content", required=True, help="Compressed content")
    parser.add_argument("--key-decisions", help="JSON array of key decisions")
    parser.add_argument("--key-files", help="JSON array of key files")
    parser.add_argument("--original-tokens", type=int, default=0, help="Original token count")
    parser.add_argument("--compressed-tokens", type=int, default=0, help="Compressed token count")
    parser.add_argument("--start-turn", type=int, default=0)
    parser.add_argument("--end-turn", type=int, default=0)

    args = parser.parse_args()

    # Parse JSON arrays
    key_decisions = json.loads(args.key_decisions) if args.key_decisions else []
    key_files = json.loads(args.key_files) if args.key_files else []

    # Save to L2 storage
    storage_location = save_compressed_segment(
        segment_id=args.segment_id,
        topic=args.topic,
        compressed_content=args.compressed_content,
        key_decisions=key_decisions,
        key_files=key_files,
        original_tokens=args.original_tokens,
        compressed_tokens=args.compressed_tokens,
        metadata={"start_turn": args.start_turn, "end_turn": args.end_turn}
    )

    # Mark as compressed in queue
    mark_segment_compressed(
        segment_id=args.segment_id,
        storage_location=storage_location,
        original_tokens=args.original_tokens,
        compressed_tokens=args.compressed_tokens
    )

    print(f"✅ Saved compressed segment to: {storage_location}")
    print(f"   Original tokens: {args.original_tokens}")
    print(f"   Compressed tokens: {args.compressed_tokens}")
    print(f"   Compression ratio: {args.original_tokens / max(args.compressed_tokens, 1):.1f}x")

def cli_list_pending():
    """List pending segments"""
    pending = get_pending_segments()
    print(f"\n📋 Pending Compression ({len(pending)} segments):\n")
    for seg in pending:
        print(f"  • {seg['segment_id']}")
        print(f"    Topic: {seg['topic']}")
        print(f"    Turns: {seg['start_turn']}-{seg['end_turn']} (silent for {seg['turns_since_mention']} turns)")
        print(f"    Messages: {seg['message_count']}")
        print()

# ─── Main ────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        cli_list_pending()
    else:
        cli_save_segment()

if __name__ == "__main__":
    main()
