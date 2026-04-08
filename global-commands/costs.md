# /costs - API Usage and Cost Tracking

Show API usage breakdown by model tier, agent, and time period.

## Usage
```
/costs                # Today s usage summary
/costs --week         # This week s usage
/costs --month        # This month s usage
/costs --by-agent     # Break down by agent name
/costs --by-tier      # Break down by model tier
/costs --budget       # Show budget status and alerts
/costs --projection 7 # Project costs for next N days
```

## Implementation

When the user runs `/costs`:

1. **Read cost data**:
   ```bash
   uv run global-hooks/framework/monitoring/model_usage_cli.py --today
   ```

2. **Display summary**:
   ```
   === Cost Report: Today ===

   Tier     | Calls | Input Tokens | Output Tokens | Cost
   ---------|-------|-------------|--------------|------
   Opus     |    12 |       45.2K |        15.1K | USD 1.81
   Sonnet   |    34 |      120.5K |        42.3K | USD 0.99
   Haiku    |    89 |      250.1K |        80.2K | USD 0.16
   ---------|-------|-------------|--------------|------
   Total    |   135 |      415.8K |       137.6K | USD 2.96

   Budget: USD 10.00/day | Used: USD 2.96 (29.6%) | Remaining: USD 7.04
   ```

3. **Budget alerts**:
   - At 75%: Show warning
   - At 90%: Show critical alert
   - At 100%: Recommend switching to lower tiers

4. **Projection** (if `--projection N`):
   - Calculate average daily spend from past 7 days
   - Project forward N days
   - Show projected total

## Budget Configuration

Set budgets in `data/budget_config.yaml`:
```yaml
budgets:
  daily: 10.00    # USD per day
  weekly: 50.00   # USD per week
  monthly: 150.00 # USD per month

alerts:
  warning_threshold: 0.75   # 75% of budget
  critical_threshold: 0.90  # 90% of budget

tier_limits:
  opus_max_daily_calls: 50     # Limit expensive Opus calls
  sonnet_max_daily_calls: 200  # Moderate limit for Sonnet
  haiku_max_daily_calls: 0     # Unlimited for Haiku
```

## Notes
- Cost data is stored in `~/.claude/logs/cost_tracking.jsonl`
- The PostToolUse hook automatically records usage (when wired)
- Pricing reflects Anthropic 2026 rates from `data/model_tiers.yaml`
- Run `uv run global-hooks/framework/monitoring/model_usage_cli.py --help` for full CLI options
