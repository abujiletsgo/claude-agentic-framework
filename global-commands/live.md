# /live — Live Agent Dashboard

Launch the live agents TUI to watch running subagents in real time.

## Usage

```bash
# In a separate terminal or tmux pane:
cd /Users/tomkwon/Documents/caf-team
uv run python dashboard/live_tui.py

# Clear history and start fresh:
uv run python dashboard/live_tui.py --clear
```

## What It Shows

A live-updating table of all subagents spawned this session:

| Agent | Status | Model | Duration | Snippet |
|-------|--------|-------|----------|---------|
| researcher-health | ✓ done | sonnet | 84.3s | CAF conventions + MCP server list... |
| builder-onboard-1 | ⚡ running | sonnet | 12s… | Build /onboard skill + planner... |

Refreshes every 1.5 seconds. Keybindings:
- `q` — quit
- `c` — clear done agents (keep only running)
- `r` — manual refresh

## Data Source

`/tmp/caf_live_agents.json` — written by SubagentStart/SubagentStop hooks.
Persists across the session. Use `--clear` to reset between runs.

## Launch with tmux

To watch alongside your main session:

```bash
tmux split-window -h "cd /Users/tomkwon/Documents/caf-team && uv run python dashboard/live_tui.py"
```
