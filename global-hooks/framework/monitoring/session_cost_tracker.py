#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Session Cost Tracker - SubagentStop Hook

Reads the agent transcript JSONL to extract actual token usage,
records to cost_tracker, and writes a running session total to
/tmp/caf_session_cost.jsonl for the orchestrator to read.

Hook event: SubagentStop
Exit codes:
  0 = Always (never blocks)
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# Resolve cost_tracker relative to this file
sys.path.insert(0, str(Path(__file__).parent))
from cost_tracker import CostTracker, resolve_model_tier, calculate_cost


def extract_tokens_from_transcript(transcript_path: str) -> dict:
    """
    Read the agent transcript JSONL and extract total token usage including cache tokens.
    Returns dict with: input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, model.
    """
    path = Path(transcript_path)
    if not path.exists():
        return {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0, "model": "unknown"}

    total_input = 0
    total_output = 0
    total_cache_read = 0
    total_cache_write = 0
    model = "unknown"

    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Claude Code transcript format: assistant messages with usage
                if entry.get("type") == "assistant":
                    msg = entry.get("message", {})
                    usage = msg.get("usage", {})
                    total_input += usage.get("input_tokens", 0)
                    total_output += usage.get("output_tokens", 0)
                    total_cache_read += usage.get("cache_read_input_tokens", 0)
                    total_cache_write += usage.get("cache_creation_input_tokens", 0)
                    if not model or model == "unknown":
                        model = msg.get("model", "unknown")

                # Alternative format: direct usage records
                elif entry.get("type") == "usage":
                    total_input += entry.get("input_tokens", 0)
                    total_output += entry.get("output_tokens", 0)
                    total_cache_read += entry.get("cache_read_input_tokens", 0)
                    total_cache_write += entry.get("cache_creation_input_tokens", 0)
                    if not model or model == "unknown":
                        model = entry.get("model", "unknown")

    except Exception:
        pass

    return {
        "input_tokens": total_input,
        "output_tokens": total_output,
        "cache_read_tokens": total_cache_read,
        "cache_write_tokens": total_cache_write,
        "model": model,
    }


def update_session_running_total(session_id: str, agent_name: str,
                                  input_tokens: int, output_tokens: int,
                                  model: str) -> dict:
    """
    Write/update the running session cost total to /tmp/caf_session_cost.jsonl.
    The orchestrator reads this for its completion report.
    """
    session_file = Path(f"/tmp/caf_session_cost_{session_id}.jsonl")
    pricing = resolve_model_tier(model)
    cost = calculate_cost(input_tokens, output_tokens, pricing)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent_name,
        "model": model,
        "tier": pricing["tier"],
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
    }

    try:
        with open(session_file, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass

    return record


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)

        hook_input = json.loads(raw)

        session_id = hook_input.get("session_id", "unknown")
        agent_id = hook_input.get("agent_id", "unknown")
        agent_type = hook_input.get("agent_type", "unknown")
        transcript_path = hook_input.get("agent_transcript_path", "")

        # Derive agent name from type or id
        agent_name = agent_type if agent_type else f"agent-{agent_id[:7]}"

        # Extract actual token usage from transcript (including cache tokens)
        usage = extract_tokens_from_transcript(transcript_path)
        input_tokens = usage["input_tokens"]
        output_tokens = usage["output_tokens"]
        cache_read = usage["cache_read_tokens"]
        cache_write = usage["cache_write_tokens"]
        model = usage["model"]

        # Skip if no token data (transcript unreadable or empty)
        if input_tokens == 0 and output_tokens == 0 and cache_read == 0:
            sys.exit(0)

        # Record to persistent cost log
        tracker = CostTracker()
        tracker.record_usage(
            session_id=session_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            agent_name=agent_name,
            event_type="SubagentStop",
            tool_name="",
            metadata={
                "agent_id": agent_id,
                "cache_read_tokens": cache_read,
                "cache_write_tokens": cache_write,
                # Cache efficiency: what % of input came from cache
                "cache_hit_rate": round(cache_read / max(input_tokens + cache_read, 1), 3),
            },
        )

        # Update running session total (read by orchestrator for completion report)
        update_session_running_total(session_id, agent_name, input_tokens, output_tokens, model)

    except Exception:
        pass  # Never fail, never block

    sys.exit(0)


if __name__ == "__main__":
    main()
