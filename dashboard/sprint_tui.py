#!/usr/bin/env python3
"""CAF Sprint TUI Dashboard — real-time sprint monitoring."""
import os
import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

from widgets.lead_panel import LeadPanel
from widgets.log_viewer import LogViewer
from widgets.report_panel import ReportPanel
from widgets.wave_progress import WaveProgress


class SprintTUI(App):
    """Sprint monitoring dashboard."""

    CSS_PATH = "sprint_tui.css"
    TITLE = "CAF Sprint Dashboard"
    ANSI_COLOR = True

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_all", "Refresh"),
        Binding("f", "focus_filter", "Filter logs"),
        Binding("tab", "cycle_focus", "Cycle focus"),
    ]

    def __init__(self, sprint_id: str):
        super().__init__()
        self.sprint_id = sprint_id
        self.ipc_dir = Path(f"/tmp/caf_sprint/{sprint_id}")

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(id="main-panels"):
                yield LeadPanel(self.ipc_dir, id="lead-panel")
                yield LogViewer(self.ipc_dir, id="log-viewer")
                yield ReportPanel(self.ipc_dir, id="report-panel")
            yield WaveProgress(self.ipc_dir, id="wave-progress")

    def action_refresh_all(self) -> None:
        for widget in [self.query_one(LeadPanel), self.query_one(LogViewer),
                       self.query_one(ReportPanel), self.query_one(WaveProgress)]:
            widget.refresh_data()

    def action_focus_filter(self) -> None:
        try:
            self.query_one(LogViewer).focus_filter()
        except Exception:
            pass

    def action_cycle_focus(self) -> None:
        focusable = ["#lead-panel", "#log-viewer", "#report-panel"]
        current = self.focused
        if current and current.id in [f[1:] for f in focusable]:
            idx = [f[1:] for f in focusable].index(current.id)
            next_id = focusable[(idx + 1) % len(focusable)]
        else:
            next_id = focusable[0]
        try:
            self.query_one(next_id).focus()
        except Exception:
            pass


def main():
    sprint_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CAF_SPRINT_ID", "")
    if not sprint_id:
        print("Usage: sprint_tui.py <sprint-id>", file=sys.stderr)
        sys.exit(1)
    app = SprintTUI(sprint_id)
    app.run()


if __name__ == "__main__":
    main()
