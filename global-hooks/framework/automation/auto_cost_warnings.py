#!/usr/bin/env python3
"""
Auto Cost Warnings - PostToolUse Hook

Tracks session costs and outputs warnings to stderr when budget thresholds
are exceeded (75%, 90%). Never blocks workflow (always exit 0).

Usage:
    Called automatically after each tool use by Claude Code.
    Reads thresholds from data/budget_config.yaml.
    Uses cost_tracker.py to track and analyze costs.

Configuration:
    data/budget_config.yaml:
        alerts:
          warning_threshold: 0.75    # 75% of budget
          critical_threshold: 0.90   # 90% of budget

Exit codes:
    0: Always (never block workflow)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "monitoring"))
sys.path.insert(0, str(Path(__file__).parent.parent / "guardrails"))

try:
    from cost_tracker import CostTracker
except ImportError:
    # Fail silently if cost tracker not available
    sys.exit(0)


def load_budget_config():
    """Load budget configuration from YAML file."""
    config_path = Path(__file__).parent.parent.parent.parent / "data" / "budget_config.yaml"

    # Default config
    default = {
        "budgets": {"daily": 10.0, "weekly": 50.0, "monthly": 150.0},
        "alerts": {"warning_threshold": 0.75, "critical_threshold": 0.90}
    }

    if not config_path.exists():
        return default

    try:
        import yaml
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}

        # Merge with defaults
        budgets = config.get("budgets", default["budgets"])
        alerts = config.get("alerts", default["alerts"])

        return {
            "budgets": budgets,
            "alerts": alerts
        }
    except Exception:
        return default


def check_budget_thresholds(tracker, config, session_id):
    """Check if any budget thresholds have been exceeded.

    Returns list of warning messages to display.
    """
    warnings = []

    budgets = config.get("budgets", {})
    alerts = config.get("alerts", {})

    warning_threshold = alerts.get("warning_threshold", 0.75)
    critical_threshold = alerts.get("critical_threshold", 0.90)

    # Check daily budget
    daily_budget = budgets.get("daily", 10.0)
    daily_summary = tracker.get_summary("today")
    daily_cost = daily_summary.get("total_cost", 0.0)
    daily_pct = (daily_cost / daily_budget) if daily_budget > 0 else 0.0

    if daily_pct >= critical_threshold:
        warnings.append(
            f"🚨 CRITICAL: Daily budget at {daily_pct*100:.0f}% "
            f"(${daily_cost:.2f} / ${daily_budget:.2f})"
        )
    elif daily_pct >= warning_threshold:
        warnings.append(
            f"⚠️  WARNING: Daily budget at {daily_pct*100:.0f}% "
            f"(${daily_cost:.2f} / ${daily_budget:.2f})"
        )

    # Check weekly budget
    weekly_budget = budgets.get("weekly", 50.0)
    weekly_summary = tracker.get_summary("week")
    weekly_cost = weekly_summary.get("total_cost", 0.0)
    weekly_pct = (weekly_cost / weekly_budget) if weekly_budget > 0 else 0.0

    if weekly_pct >= critical_threshold:
        warnings.append(
            f"🚨 CRITICAL: Weekly budget at {weekly_pct*100:.0f}% "
            f"(${weekly_cost:.2f} / ${weekly_budget:.2f})"
        )
    elif weekly_pct >= warning_threshold:
        warnings.append(
            f"⚠️  WARNING: Weekly budget at {weekly_pct*100:.0f}% "
            f"(${weekly_cost:.2f} / ${weekly_budget:.2f})"
        )

    # Check monthly budget
    monthly_budget = budgets.get("monthly", 150.0)
    monthly_summary = tracker.get_summary("month")
    monthly_cost = monthly_summary.get("total_cost", 0.0)
    monthly_pct = (monthly_cost / monthly_budget) if monthly_budget > 0 else 0.0

    if monthly_pct >= critical_threshold:
        warnings.append(
            f"🚨 CRITICAL: Monthly budget at {monthly_pct*100:.0f}% "
            f"(${monthly_cost:.2f} / ${monthly_budget:.2f})"
        )
    elif monthly_pct >= warning_threshold:
        warnings.append(
            f"⚠️  WARNING: Monthly budget at {monthly_pct*100:.0f}% "
            f"(${monthly_cost:.2f} / ${monthly_budget:.2f})"
        )

    return warnings


def main():
    """Main entry point for auto cost warnings hook."""
    try:
        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        # Extract session info
        session_id = hook_input.get("sessionId", "unknown")
        model = hook_input.get("model", "")
        agent_name = hook_input.get("agentName", "")
        tool_name = hook_input.get("toolName", "")

        # Extract token usage
        input_tokens = hook_input.get("inputTokens", 0)
        output_tokens = hook_input.get("outputTokens", 0)

        # Skip if no token usage to track
        if input_tokens == 0 and output_tokens == 0:
            sys.exit(0)

        # Initialize cost tracker
        tracker = CostTracker()

        # Record this usage
        tracker.record_usage(
            session_id=session_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            agent_name=agent_name,
            event_type="PostToolUse",
            tool_name=tool_name,
        )

        # Load budget config
        config = load_budget_config()

        # Check thresholds
        warnings = check_budget_thresholds(tracker, config, session_id)

        # Output warnings to stderr if any
        if warnings:
            print("\n" + "="*60, file=sys.stderr)
            print("💰 BUDGET ALERT", file=sys.stderr)
            print("="*60, file=sys.stderr)
            for warning in warnings:
                print(warning, file=sys.stderr)
            print("="*60 + "\n", file=sys.stderr)

    except Exception as e:
        # Fail silently - cost tracking should never block operations
        print(f"Auto cost warnings error (non-blocking): {e}", file=sys.stderr)

    # Always exit 0 (never block workflow)
    sys.exit(0)


if __name__ == "__main__":
    main()
