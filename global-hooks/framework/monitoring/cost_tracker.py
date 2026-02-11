#!/usr/bin/env python3
"""
Cost Tracking Utility for Claude Agentic Framework

Tracks API usage by model tier (Haiku/Sonnet/Opus), calculates costs
based on token usage, and logs to ~/.claude/logs/cost_tracking.jsonl.

Usage:
    # As a library - record usage
    from cost_tracker import CostTracker
    tracker = CostTracker()
    tracker.record_usage(
        session_id="abc-123",
        model="claude-sonnet-4-5",
        input_tokens=1200,
        output_tokens=350,
        agent_name="builder",
        event_type="PostToolUse"
    )

    # Get summaries
    summary = tracker.get_summary(period="today")
    weekly = tracker.get_summary(period="week")

    # As CLI - see model_usage_cli.py
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


# Pricing per 1M tokens (Anthropic 2026)
MODEL_PRICING = {
    # Haiku tier
    "claude-haiku-4-5": {"input": 0.25, "output": 1.25, "tier": "haiku"},
    "haiku": {"input": 0.25, "output": 1.25, "tier": "haiku"},
    # Sonnet tier
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00, "tier": "sonnet"},
    "sonnet": {"input": 3.00, "output": 15.00, "tier": "sonnet"},
    # Opus tier
    "claude-opus-4-6": {"input": 15.00, "output": 75.00, "tier": "opus"},
    "opus": {"input": 15.00, "output": 75.00, "tier": "opus"},
}

# Fallback: match partial model names
TIER_PATTERNS = [
    ("haiku", "haiku"),
    ("sonnet", "sonnet"),
    ("opus", "opus"),
]

DEFAULT_LOG_PATH = Path.home() / ".claude" / "logs" / "cost_tracking.jsonl"


def resolve_model_tier(model_name: str) -> dict:
    """Resolve a model name string to pricing info.

    Tries exact match first, then falls back to pattern matching on the model
    name string. Returns pricing dict with keys: input, output, tier.
    """
    if not model_name:
        return {"input": 3.00, "output": 15.00, "tier": "unknown"}

    lower = model_name.lower()

    # Exact match
    if lower in MODEL_PRICING:
        return MODEL_PRICING[lower]

    # Pattern match
    for pattern, tier_key in TIER_PATTERNS:
        if pattern in lower:
            return MODEL_PRICING[tier_key]

    # Default to sonnet pricing for unknown models
    return {"input": 3.00, "output": 15.00, "tier": "unknown"}


def calculate_cost(input_tokens: int, output_tokens: int, pricing: dict) -> float:
    """Calculate cost in USD given token counts and pricing dict."""
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


class CostTracker:
    """Tracks model usage costs by logging to a JSONL file."""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or DEFAULT_LOG_PATH
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def record_usage(
        self,
        session_id: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        agent_name: str = "",
        event_type: str = "",
        tool_name: str = "",
        metadata: Optional[dict] = None,
    ) -> dict:
        """Record a single usage event to the cost tracking log.

        Returns the entry that was written.
        """
        pricing = resolve_model_tier(model)
        cost = calculate_cost(input_tokens, output_tokens, pricing)

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "epoch_ms": int(time.time() * 1000),
            "session_id": session_id,
            "model": model,
            "tier": pricing["tier"],
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
            "agent_name": agent_name,
            "event_type": event_type,
            "tool_name": tool_name,
        }

        if metadata:
            entry["metadata"] = metadata

        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except IOError as e:
            # Fail silently - cost tracking should never block operations
            import sys
            print(f"Cost tracker write error: {e}", file=sys.stderr)

        return entry

    def read_entries(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        tier: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> list:
        """Read and filter entries from the cost tracking log."""
        if not self.log_path.exists():
            return []

        entries = []
        since_iso = since.isoformat() + "Z" if since else None
        until_iso = until.isoformat() + "Z" if until else None

        try:
            with open(self.log_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Apply filters
                    ts = entry.get("timestamp", "")
                    if since_iso and ts < since_iso:
                        continue
                    if until_iso and ts > until_iso:
                        continue
                    if tier and entry.get("tier") != tier:
                        continue
                    if session_id and entry.get("session_id") != session_id:
                        continue
                    if agent_name and entry.get("agent_name") != agent_name:
                        continue

                    entries.append(entry)
        except IOError:
            return []

        return entries

    def get_summary(self, period: str = "today") -> dict:
        """Get a cost summary for a time period.

        Args:
            period: One of "today", "yesterday", "week", "month", "all"

        Returns:
            Dictionary with cost breakdown by tier, agent, and totals.
        """
        now = datetime.now(timezone.utc)

        if period == "today":
            since = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "yesterday":
            since = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            until = now.replace(hour=0, minute=0, second=0, microsecond=0)
            entries = self.read_entries(since=since, until=until)
            return self._build_summary(entries, period)
        elif period == "week":
            since = now - timedelta(days=7)
        elif period == "month":
            since = now - timedelta(days=30)
        elif period == "all":
            since = None
        else:
            since = now.replace(hour=0, minute=0, second=0, microsecond=0)

        entries = self.read_entries(since=since)
        return self._build_summary(entries, period)

    def get_daily_breakdown(self, days: int = 7) -> list:
        """Get cost breakdown by day for the last N days.

        Returns list of daily summaries, most recent first.
        """
        now = datetime.now(timezone.utc)
        daily = []

        for i in range(days):
            day_start = (now - timedelta(days=i)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            day_end = day_start + timedelta(days=1)
            entries = self.read_entries(since=day_start, until=day_end)
            summary = self._build_summary(entries, day_start.strftime("%Y-%m-%d"))
            summary["date"] = day_start.strftime("%Y-%m-%d")
            daily.append(summary)

        return daily

    def get_projection(self, days: int = 7) -> dict:
        """Project costs for the next N days based on recent usage patterns.

        Uses the average daily cost from the last 7 days (or available data)
        to project forward.
        """
        daily = self.get_daily_breakdown(days=7)

        # Filter out days with zero cost (no data)
        active_days = [d for d in daily if d["total_cost"] > 0]

        if not active_days:
            return {
                "projection_days": days,
                "avg_daily_cost": 0.0,
                "projected_total": 0.0,
                "confidence": "no_data",
                "based_on_days": 0,
                "tier_breakdown": {},
            }

        avg_daily = sum(d["total_cost"] for d in active_days) / len(active_days)
        projected = round(avg_daily * days, 4)

        # Tier breakdown averages
        tier_totals = {}
        for d in active_days:
            for tier_name, tier_data in d.get("by_tier", {}).items():
                if tier_name not in tier_totals:
                    tier_totals[tier_name] = 0.0
                tier_totals[tier_name] += tier_data.get("cost", 0.0)

        tier_breakdown = {}
        for tier_name, total in tier_totals.items():
            avg = total / len(active_days)
            tier_breakdown[tier_name] = {
                "avg_daily": round(avg, 4),
                "projected": round(avg * days, 4),
            }

        confidence = "high" if len(active_days) >= 5 else (
            "medium" if len(active_days) >= 3 else "low"
        )

        return {
            "projection_days": days,
            "avg_daily_cost": round(avg_daily, 4),
            "projected_total": projected,
            "confidence": confidence,
            "based_on_days": len(active_days),
            "tier_breakdown": tier_breakdown,
        }

    def _build_summary(self, entries: list, period: str) -> dict:
        """Build a cost summary from a list of entries."""
        by_tier = {}
        by_agent = {}
        by_session = {}
        total_cost = 0.0
        total_input = 0
        total_output = 0
        event_count = len(entries)

        for entry in entries:
            tier = entry.get("tier", "unknown")
            agent = entry.get("agent_name", "unknown") or "unknown"
            session = entry.get("session_id", "unknown")
            cost = entry.get("cost_usd", 0.0)
            inp = entry.get("input_tokens", 0)
            out = entry.get("output_tokens", 0)

            total_cost += cost
            total_input += inp
            total_output += out

            # By tier
            if tier not in by_tier:
                by_tier[tier] = {"cost": 0.0, "input_tokens": 0, "output_tokens": 0, "events": 0}
            by_tier[tier]["cost"] += cost
            by_tier[tier]["input_tokens"] += inp
            by_tier[tier]["output_tokens"] += out
            by_tier[tier]["events"] += 1

            # By agent
            if agent not in by_agent:
                by_agent[agent] = {"cost": 0.0, "input_tokens": 0, "output_tokens": 0, "events": 0, "tier": tier}
            by_agent[agent]["cost"] += cost
            by_agent[agent]["input_tokens"] += inp
            by_agent[agent]["output_tokens"] += out
            by_agent[agent]["events"] += 1

            # By session
            if session not in by_session:
                by_session[session] = {"cost": 0.0, "events": 0}
            by_session[session]["cost"] += cost
            by_session[session]["events"] += 1

        # Round costs
        total_cost = round(total_cost, 6)
        for tier_data in by_tier.values():
            tier_data["cost"] = round(tier_data["cost"], 6)
        for agent_data in by_agent.values():
            agent_data["cost"] = round(agent_data["cost"], 6)
        for session_data in by_session.values():
            session_data["cost"] = round(session_data["cost"], 6)

        return {
            "period": period,
            "total_cost": total_cost,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "event_count": event_count,
            "by_tier": by_tier,
            "by_agent": by_agent,
            "by_session": by_session,
            "session_count": len(by_session),
        }


def generate_sample_data(days: int = 7) -> None:
    """Generate sample cost tracking data for testing and projection demos.

    Creates realistic usage patterns over the specified number of days,
    simulating a development workflow with varying model usage.
    """
    import random

    tracker = CostTracker()
    now = datetime.now(timezone.utc)

    # Typical usage patterns per agent
    agent_profiles = {
        "orchestrator": {"tier": "opus", "model": "claude-opus-4-6", "avg_calls": 8, "input_range": (2000, 8000), "output_range": (500, 3000)},
        "builder": {"tier": "sonnet", "model": "claude-sonnet-4-5", "avg_calls": 25, "input_range": (3000, 15000), "output_range": (1000, 8000)},
        "researcher": {"tier": "sonnet", "model": "claude-sonnet-4-5", "avg_calls": 10, "input_range": (5000, 20000), "output_range": (2000, 10000)},
        "validator": {"tier": "haiku", "model": "claude-haiku-4-5", "avg_calls": 30, "input_range": (1000, 5000), "output_range": (200, 1500)},
        "meta-agent": {"tier": "sonnet", "model": "claude-sonnet-4-5", "avg_calls": 5, "input_range": (2000, 8000), "output_range": (3000, 12000)},
        "docs-scraper": {"tier": "haiku", "model": "claude-haiku-4-5", "avg_calls": 15, "input_range": (500, 3000), "output_range": (100, 800)},
        "critical-analyst": {"tier": "opus", "model": "claude-opus-4-6", "avg_calls": 3, "input_range": (5000, 15000), "output_range": (2000, 8000)},
        "project-architect": {"tier": "opus", "model": "claude-opus-4-6", "avg_calls": 2, "input_range": (8000, 25000), "output_range": (3000, 15000)},
    }

    sessions_per_day = [3, 5, 4, 2, 6, 4, 3]  # Vary by day

    for day_offset in range(days):
        day = now - timedelta(days=days - 1 - day_offset)
        num_sessions = sessions_per_day[day_offset % len(sessions_per_day)]

        for s in range(num_sessions):
            session_id = f"sample-{day.strftime('%Y%m%d')}-{s:03d}"
            # Each session uses a subset of agents
            active_agents = random.sample(
                list(agent_profiles.keys()),
                k=random.randint(3, min(6, len(agent_profiles)))
            )

            for agent_name in active_agents:
                profile = agent_profiles[agent_name]
                num_calls = max(1, int(profile["avg_calls"] * random.uniform(0.3, 1.5)))

                for _ in range(num_calls):
                    input_tokens = random.randint(*profile["input_range"])
                    output_tokens = random.randint(*profile["output_range"])

                    # Create entry with correct timestamp for the day
                    hour = random.randint(8, 22)
                    minute = random.randint(0, 59)
                    ts = day.replace(hour=hour, minute=minute, second=random.randint(0, 59))

                    pricing = resolve_model_tier(profile["model"])
                    cost = calculate_cost(input_tokens, output_tokens, pricing)

                    entry = {
                        "timestamp": ts.isoformat() + "Z",
                        "epoch_ms": int(ts.timestamp() * 1000),
                        "session_id": session_id,
                        "model": profile["model"],
                        "tier": profile["tier"],
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cost_usd": cost,
                        "agent_name": agent_name,
                        "event_type": random.choice(["PostToolUse", "SubagentStop", "PreToolUse"]),
                        "tool_name": random.choice(["Bash", "Read", "Write", "Edit", "Grep", "Task"]),
                    }

                    try:
                        with open(tracker.log_path, "a") as f:
                            f.write(json.dumps(entry) + "\n")
                    except IOError:
                        pass

    print(f"Generated {days} days of sample data at {tracker.log_path}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--generate-sample":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        generate_sample_data(days)
    else:
        # Quick self-test
        tracker = CostTracker()
        entry = tracker.record_usage(
            session_id="test-session",
            model="claude-sonnet-4-5",
            input_tokens=5000,
            output_tokens=1500,
            agent_name="builder",
            event_type="PostToolUse",
        )
        print(f"Recorded: {json.dumps(entry, indent=2)}")

        summary = tracker.get_summary("today")
        print(f"\nToday's summary: {json.dumps(summary, indent=2)}")
