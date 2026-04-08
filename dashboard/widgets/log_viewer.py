"""Live log stream widget — tails logs/*.log with role-color prefixes."""
import json
from pathlib import Path
from textual.widgets import RichLog, Input, Static
from textual.widget import Widget
from textual.containers import Vertical


ROLE_COLORS = {
    "planning-lead": "cyan",
    "engineering-lead": "green",
    "review-lead": "blue",
    "qa-lead": "yellow",
    "security-lead": "magenta",
    "release-lead": "white",
}


class LogViewer(Widget):
    """Streams lead logs with color-coded role prefixes, polled every 0.5s."""

    def __init__(self, ipc_dir: Path, **kwargs):
        super().__init__(**kwargs)
        self.ipc_dir = ipc_dir
        self.log_positions: dict[str, int] = {}  # file path -> last read position
        self.filter_text = ""
        self.can_focus = True

    def compose(self):
        yield Static("Live Logs", classes="panel-title")
        yield Input(placeholder="Filter logs...", id="log-filter")
        yield RichLog(id="log-output", highlight=True, markup=True)

    def on_mount(self) -> None:
        self.refresh_data()
        self.set_interval(0.5, self.refresh_data)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "log-filter":
            self.filter_text = event.value.lower()

    def focus_filter(self) -> None:
        try:
            self.query_one("#log-filter", Input).focus()
        except Exception:
            pass

    def refresh_data(self) -> None:
        log_dir = self.ipc_dir / "logs"
        if not log_dir.exists():
            return
        rich_log = self.query_one("#log-output", RichLog)
        for log_file in sorted(log_dir.glob("*.log")):
            role = log_file.stem
            color = ROLE_COLORS.get(role, "white")
            file_key = str(log_file)
            last_pos = self.log_positions.get(file_key, 0)
            try:
                with open(log_file, "r") as f:
                    f.seek(last_pos)
                    new_content = f.read()
                    new_pos = f.tell()
                if new_content and new_pos > last_pos:
                    self.log_positions[file_key] = new_pos
                    for line in new_content.splitlines():
                        if self.filter_text and self.filter_text not in line.lower() and self.filter_text not in role.lower():
                            continue
                        rich_log.write(f"[{color}][{role}][/{color}] {line}")
            except OSError:
                pass
