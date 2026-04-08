#!/usr/bin/env python3
"""CAF Dashboard — Layout A main app.

Combines TopBar, LeadsGrid, AgentsWidget, EventLogWidget, SummaryPanelV2,
WaveProgress, and RightSidebar into a single Textual application.
"""
import argparse
import os
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical

from dashboard.widgets.top_bar import TopBar
from dashboard.widgets.leads_grid import LeadsGrid
from dashboard.widgets.agents_widget import AgentsWidget
from dashboard.widgets.event_log_widget import EventLogWidget
from dashboard.widgets.summary_panel_v2 import SummaryPanelV2
from dashboard.widgets.right_sidebar import RightSidebar
from dashboard.widgets.wave_progress import WaveProgress


def find_sprint_id() -> str:
    import os
    from pathlib import Path
    sid = os.environ.get("CAF_SPRINT_ID", "")
    if not sid:
        p = Path("/tmp/caf_sprint")
        dirs = sorted(p.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True) if p.exists() else []
        sid = dirs[0].name if dirs else ""
    return sid


class CAFDashboard(App):
    CSS_PATH = "caf_dashboard.css"
    TITLE = "CAF Dashboard"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_all", "Refresh"),
        Binding("m", "toggle_mode", "Toggle mode"),
        Binding("l", "toggle_leads", "Toggle leads"),
    ]

    def __init__(self, sprint_id: str = ""):
        super().__init__()
        self.sprint_id = sprint_id
        self.mode = "sprint" if sprint_id else "orchestrate"

    def compose(self) -> ComposeResult:
        yield TopBar(sprint_id=self.sprint_id)
        with Horizontal():
            with Vertical(id="center-zone"):
                with Horizontal(id="top-center"):
                    yield LeadsGrid(sprint_id=self.sprint_id)
                    yield AgentsWidget()
                    yield EventLogWidget(sprint_id=self.sprint_id)
                yield SummaryPanelV2(sprint_id=self.sprint_id)
                yield WaveProgress(self.ipc_dir if self.sprint_id else None, id="timeline")
            yield RightSidebar()

    @property
    def ipc_dir(self) -> Path:
        return Path(f"/tmp/caf_sprint/{self.sprint_id}") if self.sprint_id else None

    def on_mount(self) -> None:
        if self.mode == "orchestrate":
            self.query_one(LeadsGrid).display = False

    def action_refresh_all(self) -> None:
        """Refresh all widgets."""
        for widget in self.query("*"):
            if hasattr(widget, "refresh_data"):
                widget.refresh_data()

    def action_toggle_mode(self) -> None:
        """Toggle between sprint and orchestrate mode."""
        if self.mode == "sprint":
            self.mode = "orchestrate"
            self.query_one(LeadsGrid).display = False
        else:
            self.mode = "sprint"
            self.query_one(LeadsGrid).display = True

    def action_toggle_leads(self) -> None:
        """Toggle leads grid visibility."""
        leads = self.query_one(LeadsGrid)
        leads.display = not leads.display


def main():
    parser = argparse.ArgumentParser(description="CAF Dashboard")
    parser.add_argument("--sprint", default="", help="Sprint ID to monitor")
    args = parser.parse_args()
    sprint_id = args.sprint or find_sprint_id()
    app = CAFDashboard(sprint_id=sprint_id)
    app.run()


if __name__ == "__main__":
    main()
