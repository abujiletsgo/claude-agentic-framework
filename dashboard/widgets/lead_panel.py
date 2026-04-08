"""Lead status table widget — shows per-lead status from status.json."""
import json
from pathlib import Path
from textual.widgets import DataTable, Static
from textual.widget import Widget
from textual.containers import Vertical
from datetime import datetime, timezone


class LeadPanel(Widget):
    """Displays lead role status in a DataTable, polled every 2s."""

    def __init__(self, ipc_dir: Path, **kwargs):
        super().__init__(**kwargs)
        self.ipc_dir = ipc_dir
        self.can_focus = True

    def compose(self):
        yield Static("Lead Status", classes="panel-title")
        yield DataTable(id="lead-table")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Role", "Wave", "Status", "Elapsed")
        self.refresh_data()
        self.set_interval(2, self.refresh_data)

    def refresh_data(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        status_file = self.ipc_dir / "status.json"
        try:
            if not status_file.exists():
                table.add_row("Waiting...", "", "", "")
                return
            data = json.loads(status_file.read_text())
            now = datetime.now(timezone.utc)
            for role, info in sorted(data.items(), key=lambda x: x[1].get("wave", 0)):
                status = info.get("status", "unknown")
                wave = f"W{info.get('wave', '?')}"
                symbol = {"done": "[green]done[/]", "running": "[yellow]running[/]",
                          "failed": "[red]failed[/]"}.get(status, f"[dim]{status}[/]")
                started = info.get("started", "")
                elapsed = ""
                if started:
                    try:
                        start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                        delta = now - start_dt
                        mins, secs = divmod(int(delta.total_seconds()), 60)
                        hrs, mins = divmod(mins, 60)
                        elapsed = f"{hrs:02d}:{mins:02d}:{secs:02d}"
                    except (ValueError, TypeError):
                        elapsed = "?"
                table.add_row(role, wave, symbol, elapsed)
        except (json.JSONDecodeError, OSError):
            table.add_row("Error reading status", "", "", "")
