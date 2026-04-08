"""AgentsWidget — live agents table, embeddable in Layout A."""
import json
import time
from pathlib import Path

from textual.widget import Widget
from textual.widgets import DataTable, Static
from textual.containers import Vertical
from textual import work

LIVE_FILE = Path("/tmp/caf_live_agents.json")
POLL_INTERVAL = 1.5  # seconds


class AgentsWidget(Widget):
    """Live agents table — embeddable in Layout A."""

    def compose(self):
        yield Static("Agents", classes="panel-title")
        yield DataTable(id="agents-table")

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

        if not LIVE_FILE.exists():
            table.clear()
            table.add_row("No agents yet", "", "", "", "")
            return

        try:
            data = json.loads(LIVE_FILE.read_text())
        except Exception:
            return

        agents = data.get("agents", [])
        if not agents:
            table.clear()
            table.add_row("No agents yet", "", "", "", "")
            return

        # Show last 20 agents (center column is smaller than standalone TUI)
        agents = agents[-20:]

        table.clear()
        for agent in reversed(agents):
            name = agent.get("name", "?")[:38]
            status = agent.get("status", "?")
            model = agent.get("model", "?")
            snippet = agent.get("snippet", "")[:55]

            if status == "running":
                elapsed_s = time.time() - agent.get("started", time.time())
                duration = f"{elapsed_s:.0f}s\u2026"
                status_display = "\u26a1 running"
            else:
                duration = f"{agent.get('duration_s', 0):.1f}s"
                status_display = "\u2713 done"

            table.add_row(name, status_display, model, duration, snippet)
