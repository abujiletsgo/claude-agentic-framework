#!/usr/bin/env python3
"""SessionStart hook: auto-launch live agents TUI in a tmux pane."""
import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    # Only run if inside a tmux session
    if not os.environ.get("TMUX"):
        print(json.dumps({}))
        return

    # Skip if live_tui is already running
    result = subprocess.run(
        ["pgrep", "-f", "live_tui.py"],
        capture_output=True,
    )
    if result.returncode == 0:
        print(json.dumps({}))
        return

    repo_dir = Path(__file__).resolve().parent.parent.parent
    tui_path = repo_dir / "dashboard" / "live_tui.py"

    if not tui_path.exists():
        print(json.dumps({}))
        return

    # Clear stale data from prior session
    live_file = Path("/tmp/caf_live_agents.json")
    live_file.unlink(missing_ok=True)

    # Split a small pane on the right (28% width) and launch TUI
    subprocess.Popen(
        [
            "tmux", "split-window", "-h", "-p", "28",
            f"cd {repo_dir} && uv run --no-project python dashboard/live_tui.py",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print(json.dumps({}))


if __name__ == "__main__":
    main()
