"""Lead status panel — shows per-lead status as styled text lines."""
import json
from pathlib import Path
from textual.widgets import RichLog, Static
from textual.widget import Widget
from datetime import datetime, timezone


class LeadPanel(Widget):
    """Displays lead role status as colored text, polled every 2s."""

    def __init__(self, ipc_dir: Path, **kwargs):
        super().__init__(**kwargs)
        self.ipc_dir = ipc_dir
        self.can_focus = True
        self._last_hash = ""

    def compose(self):
        yield Static("Lead Status", classes="panel-title")
        yield RichLog(id="lead-log", highlight=False, markup=True)

    def on_mount(self) -> None:
        self.refresh_data()
        self.set_interval(2, self.refresh_data)

    def refresh_data(self) -> None:
        status_file = self.ipc_dir / "status.json"
        log = self.query_one("#lead-log", RichLog)
        try:
            if not status_file.exists():
                return
            raw = status_file.read_text()
            if raw == self._last_hash:
                return
            self._last_hash = raw
            data = json.loads(raw)
            log.clear()

            # Header
            log.write("[bold underline]Role              Wave  Status    Elapsed[/]")

            now = datetime.now(timezone.utc)
            for role, info in sorted(data.items(), key=lambda x: x[1].get("wave", 0)):
                status = info.get("status", "unknown")
                wave = f"W{info.get('wave', '?')}"

                color_map = {"done": "green", "running": "yellow", "failed": "red"}
                symbol_map = {"done": "✓", "running": "●", "failed": "✗"}
                color = color_map.get(status, "dim")
                symbol = symbol_map.get(status, "○")

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

                line = f"[{color}]{symbol} {role:<18} {wave:<5} {status:<9} {elapsed}[/{color}]"
                log.write(line)

        except (json.JSONDecodeError, OSError):
            pass
