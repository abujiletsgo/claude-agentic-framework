---
name: model-usage
description: "Show model usage costs and projections. Use when the user asks about API costs, model usage, spending, or cost optimization."
---

# Model Usage Cost Tracker

Show cost tracking data from the multi-model tier system.

## How to Run

Execute the cost tracking CLI with the requested period:

```bash
# Default: last week summary
python3 /Users/tomkwon/Documents/claude-agentic-framework/global-hooks/framework/monitoring/model_usage_cli.py --last-week --by-agent

# Today only
python3 /Users/tomkwon/Documents/claude-agentic-framework/global-hooks/framework/monitoring/model_usage_cli.py --today --by-agent

# Daily breakdown (last 7 days)
python3 /Users/tomkwon/Documents/claude-agentic-framework/global-hooks/framework/monitoring/model_usage_cli.py --daily 7

# 1-week projection
python3 /Users/tomkwon/Documents/claude-agentic-framework/global-hooks/framework/monitoring/model_usage_cli.py --projection 7

# JSON output for programmatic use
python3 /Users/tomkwon/Documents/claude-agentic-framework/global-hooks/framework/monitoring/model_usage_cli.py --last-week --json
```

## Arguments

| Flag | Description |
|------|-------------|
| `--today` | Show today's costs |
| `--yesterday` | Show yesterday's costs |
| `--last-week` | Show last 7 days (default) |
| `--last-month` | Show last 30 days |
| `--all` | Show all-time costs |
| `--daily N` | Daily breakdown for N days |
| `--projection N` | Project costs for N days |
| `--by-agent` | Include per-agent breakdown |
| `--json` | Output raw JSON |
| `--generate-sample N` | Generate N days of sample data for testing |

## Workflow

1. Run the CLI command matching the user's request
2. Present the results in a clean, readable format
3. If the user asks about optimization, reference `data/model_tiers.yaml` for tier assignments
4. If no data exists yet, offer to generate sample data with `--generate-sample 7`

## Integration

- Cost data is logged to `~/.claude/logs/cost_tracking.jsonl`
- The observability dashboard (`apps/observability/`) has a CostTracker widget
- Tier configuration lives in `data/model_tiers.yaml`
- The `multi-model-tiers` skill has full tier documentation
