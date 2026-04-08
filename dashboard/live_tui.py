#!/usr/bin/env python3
"""CAF Live Agents TUI — real-time visibility into all running subagents.

Usage:
  uv run python dashboard/live_tui.py        # watch /tmp/caf_live_agents.json
  uv run python dashboard/live_tui.py --clear  # clear history and start fresh
"""
import json
import sys
import time
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, Label
from textual.containers import Vertical
from textual import work

LIVE_FILE = Path("/tmp/caf_live_agents.json")
POLL_INTERVAL = 1.5  # seconds


class LiveAgentsApp(App):
    """Real-time agent visibility dashboard."""

    CSS = """
    Screen {
        background: $surface;
    }
    #title {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    #status-bar {
        height: 1;
        background: $surface-darken-1;
        color: $text-muted;
        padding: 0 1;
    }
    DataTable {
        height: 1fr;
    }
    """

    TITLE = "CAF Live Agents"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("c", "clear_done", "Clear done"),
        Binding("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Label("", id="status-bar")
            yield DataTable(id="agents-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Agent", "Status", "Model", "Duration", "Snippet")
        table.cursor_type = "row"
        self._poll()

    @work(exclusive=True, thread=True)
    def _poll(self) -> None:
        while True:
            self.call_from_thread(self._refresh_data)
            time.sleep(POLL_INTERVAL)

    def _refresh_data(self) -> None:
        table = self.query_one(DataTable)
        status_label = self.query_one("#status-bar", Label)

        if not LIVE_FILE.exists():
            status_label.update("Waiting for agents... (no data yet)")
            return

        try:
            data = json.loads(LIVE_FILE.read_text())
        except Exception:
            return

        agents = data.get("agents", [])
        if not agents:
            status_label.update("No agents recorded yet.")
            return

        # Filter: show last 30 entries
        agents = agents[-30:]

        running = sum(1 for a in agents if a.get("status") == "running")
        done = sum(1 for a in agents if a.get("status") == "done")
        session_start = data.get("session_start", 0)
        elapsed = int(time.time() - session_start) if session_start else 0

        status_label.update(
            f"  {running} running  |  {done} done  |  session elapsed: {elapsed}s  |  [r] refresh  [c] clear done  [q] quit"
        )

        table.clear()
        for agent in reversed(agents):
            name = agent.get("name", "?")[:38]
            status = agent.get("status", "?")
            model = agent.get("model", "?")
            snippet = agent.get("snippet", "")[:55]

            if status == "running":
                elapsed_s = time.time() - agent.get("started", time.time())
                duration = f"{elapsed_s:.0f}s…"
                status_display = "⚡ running"
            else:
                duration = f"{agent.get('duration_s', 0):.1f}s"
                status_display = "✓ done"

            table.add_row(name, status_display, model, duration, snippet)

    def action_clear_done(self) -> None:
        if not LIVE_FILE.exists():
            return
        try:
            data = json.loads(LIVE_FILE.read_text())
            data["agents"] = [a for a in data.get("agents", []) if a.get("status") == "running"]
            LIVE_FILE.write_text(json.dumps(data, indent=2))
            self._refresh_data()
        except Exception:
            pass

    def action_refresh(self) -> None:
        self._refresh_data()


def main():
    if "--clear" in sys.argv:
        LIVE_FILE.unlink(missing_ok=True)
        print("Cleared agent history.")
        return

    app = LiveAgentsApp()
    app.run()


if __name__ == "__main__":
    main()
