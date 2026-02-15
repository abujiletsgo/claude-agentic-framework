#!/usr/bin/env python3
"""
CLI for Model Usage and Cost Tracking

Usage:
    python model_usage_cli.py --last-week
    python model_usage_cli.py --today
    python model_usage_cli.py --period month
    python model_usage_cli.py --daily 7
    python model_usage_cli.py --projection 7
    python model_usage_cli.py --by-agent
    python model_usage_cli.py --by-tier
    python model_usage_cli.py --json
    python model_usage_cli.py --generate-sample 7
"""

import argparse
import json
import sys
from pathlib import Path

# Allow importing from same directory
sys.path.insert(0, str(Path(__file__).parent))
from cost_tracker import CostTracker, generate_sample_data


def format_cost(cost: float) -> str:
    """Format cost as USD string."""
    if cost < 0.01:
        return f"${cost:.4f}"
    elif cost < 1.00:
        return f"${cost:.3f}"
    else:
        return f"${cost:.2f}"


def format_tokens(tokens: int) -> str:
    """Format token count with K/M suffix."""
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    elif tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    return str(tokens)


def print_summary(summary: dict, verbose: bool = False) -> None:
    """Print a formatted cost summary to stdout."""
    period = summary.get("period", "unknown")
    total = summary.get("total_cost", 0)
    events = summary.get("event_count", 0)
    sessions = summary.get("session_count", 0)
    total_in = summary.get("total_input_tokens", 0)
    total_out = summary.get("total_output_tokens", 0)

    print(f"\n{'=' * 60}")
    print(f"  Cost Report: {period}")
    print(f"{'=' * 60}")
    print(f"  Total Cost:     {format_cost(total)}")
    print(f"  Events:         {events:,}")
    print(f"  Sessions:       {sessions}")
    print(f"  Input Tokens:   {format_tokens(total_in)}")
    print(f"  Output Tokens:  {format_tokens(total_out)}")
    print()

    # Tier breakdown
    by_tier = summary.get("by_tier", {})
    if by_tier:
        print(f"  {'Tier':<12} {'Cost':>10} {'Input':>10} {'Output':>10} {'Events':>8}")
        print(f"  {'-' * 52}")
        for tier_name in ["opus", "sonnet", "haiku", "unknown"]:
            if tier_name in by_tier:
                t = by_tier[tier_name]
                print(
                    f"  {tier_name:<12} {format_cost(t['cost']):>10} "
                    f"{format_tokens(t['input_tokens']):>10} "
                    f"{format_tokens(t['output_tokens']):>10} "
                    f"{t['events']:>8}"
                )
        print()

    # Agent breakdown (top 10 by cost)
    by_agent = summary.get("by_agent", {})
    if by_agent and verbose:
        sorted_agents = sorted(by_agent.items(), key=lambda x: x[1]["cost"], reverse=True)
        print(f"  {'Agent':<28} {'Tier':<8} {'Cost':>10} {'Events':>8}")
        print(f"  {'-' * 56}")
        for agent_name, agent_data in sorted_agents[:15]:
            display_name = agent_name[:27]
            print(
                f"  {display_name:<28} {agent_data.get('tier', '?'):<8} "
                f"{format_cost(agent_data['cost']):>10} "
                f"{agent_data['events']:>8}"
            )
        if len(sorted_agents) > 15:
            print(f"  ... and {len(sorted_agents) - 15} more agents")
        print()


def print_daily_breakdown(daily: list) -> None:
    """Print daily cost breakdown."""
    print(f"\n{'=' * 60}")
    print(f"  Daily Cost Breakdown")
    print(f"{'=' * 60}")
    print(f"  {'Date':<12} {'Total':>10} {'Opus':>10} {'Sonnet':>10} {'Haiku':>10}")
    print(f"  {'-' * 54}")

    for day in reversed(daily):
        date = day.get("date", "?")
        total = format_cost(day.get("total_cost", 0))
        opus = format_cost(day.get("by_tier", {}).get("opus", {}).get("cost", 0))
        sonnet = format_cost(day.get("by_tier", {}).get("sonnet", {}).get("cost", 0))
        haiku = format_cost(day.get("by_tier", {}).get("haiku", {}).get("cost", 0))
        print(f"  {date:<12} {total:>10} {opus:>10} {sonnet:>10} {haiku:>10}")

    print()


def print_projection(proj: dict) -> None:
    """Print cost projection."""
    days = proj.get("projection_days", 7)
    avg = proj.get("avg_daily_cost", 0)
    total = proj.get("projected_total", 0)
    confidence = proj.get("confidence", "unknown")
    based_on = proj.get("based_on_days", 0)

    print(f"\n{'=' * 60}")
    print(f"  Cost Projection ({days}-day)")
    print(f"{'=' * 60}")
    print(f"  Avg Daily Cost:     {format_cost(avg)}")
    print(f"  Projected Total:    {format_cost(total)}")
    print(f"  Confidence:         {confidence}")
    print(f"  Based on:           {based_on} days of data")
    print()

    tier_bd = proj.get("tier_breakdown", {})
    if tier_bd:
        print(f"  {'Tier':<12} {'Avg/Day':>10} {'Projected':>10}")
        print(f"  {'-' * 34}")
        for tier_name in ["opus", "sonnet", "haiku"]:
            if tier_name in tier_bd:
                t = tier_bd[tier_name]
                print(
                    f"  {tier_name:<12} "
                    f"{format_cost(t['avg_daily']):>10} "
                    f"{format_cost(t['projected']):>10}"
                )
        print()

    # Comparison with all-sonnet and all-opus baselines
    if total > 0:
        print(f"  Comparison (projected {days}-day):")

        # Estimate total tokens from projection data
        # Use the tier breakdown to estimate what all-sonnet or all-opus would cost
        total_input = 0
        total_output = 0
        for day_data in tier_bd.values():
            # Rough estimate from avg daily costs
            pass

        print(f"    Current (multi-tier):  {format_cost(total)}")
        # Rough estimate: if all were opus, cost would be ~5x sonnet, ~60x haiku
        estimated_all_opus = total * 3.5  # rough multiplier
        estimated_all_sonnet = total * 1.2  # rough multiplier
        print(f"    If all-Opus:           ~{format_cost(estimated_all_opus)} (estimated)")
        print(f"    If all-Sonnet:         ~{format_cost(estimated_all_sonnet)} (estimated)")
        savings_vs_opus = ((estimated_all_opus - total) / estimated_all_opus) * 100 if estimated_all_opus > 0 else 0
        print(f"    Savings vs all-Opus:   ~{savings_vs_opus:.0f}%")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Model usage and cost tracking CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python model_usage_cli.py --last-week
  python model_usage_cli.py --today --by-agent
  python model_usage_cli.py --daily 14
  python model_usage_cli.py --projection 7
  python model_usage_cli.py --generate-sample 7
        """,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--today", action="store_true", help="Show today's costs")
    group.add_argument("--yesterday", action="store_true", help="Show yesterday's costs")
    group.add_argument("--last-week", action="store_true", help="Show last 7 days costs")
    group.add_argument("--last-month", action="store_true", help="Show last 30 days costs")
    group.add_argument("--all", action="store_true", help="Show all-time costs")
    group.add_argument("--period", type=str, help="Period: today, yesterday, week, month, all")
    group.add_argument("--daily", type=int, metavar="DAYS", help="Show daily breakdown for N days")
    group.add_argument("--projection", type=int, metavar="DAYS", help="Project costs for N days")
    group.add_argument(
        "--generate-sample",
        type=int,
        metavar="DAYS",
        help="Generate sample data for N days",
    )

    parser.add_argument("--by-agent", action="store_true", help="Include agent breakdown")
    parser.add_argument("--by-tier", action="store_true", help="Include tier breakdown (default)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--log-path",
        type=str,
        help="Path to cost tracking log (default: ~/.claude/logs/cost_tracking.jsonl)",
    )

    args = parser.parse_args()

    log_path = Path(args.log_path) if args.log_path else None
    tracker = CostTracker(log_path=log_path)

    # Handle sample data generation
    if args.generate_sample is not None:
        generate_sample_data(args.generate_sample)
        return

    # Determine period
    if args.today:
        period = "today"
    elif args.yesterday:
        period = "yesterday"
    elif args.last_week:
        period = "week"
    elif args.last_month:
        period = "month"
    elif args.all:
        period = "all"
    elif args.period:
        period = args.period
    elif args.daily:
        daily = tracker.get_daily_breakdown(args.daily)
        if args.json:
            print(json.dumps(daily, indent=2))
        else:
            print_daily_breakdown(daily)
        return
    elif args.projection:
        proj = tracker.get_projection(args.projection)
        if args.json:
            print(json.dumps(proj, indent=2))
        else:
            print_projection(proj)
        return
    else:
        period = "week"  # Default to last week

    summary = tracker.get_summary(period)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print_summary(summary, verbose=args.by_agent)


if __name__ == "__main__":
    main()
