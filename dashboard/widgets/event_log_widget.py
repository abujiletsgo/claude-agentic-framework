"""EventLogWidget — tall scrollable event log reading events.jsonl."""
import json
import os
import time
from datetime import datetime
from pathlib import Path

from textual.widget import Widget
from textual.widgets import RichLog, Static
from textual import work

POLL_INTERVAL = 1.0  # seconds

TYPE_SHORT = {
    "SubagentStart": "Start",
    "SubagentStop": "Stop",
    "wave_start": "Wave",
    "sprint_complete": "Done",
}


def find_sprint_id() -> str:
    import os
    from pathlib import Path

    sid = os.environ.get("CAF_SPRINT_ID", "")
    if not sid:
        p = Path("/tmp/caf_sprint")
        dirs = (
            sorted(p.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True)
            if p.exists()
            else []
        )
        sid = dirs[0].name if dirs else ""
    return sid


class EventLogWidget(Widget):
    """Tall scrollable event log from events.jsonl."""

    def __init__(self, sprint_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.sprint_id = sprint_id
        self._last_line_count: int = 0
        self.can_focus = True

    def compose(self):
        yield Static("Events", classes="panel-title")
        yield RichLog(id="event-log", highlight=False, markup=True, wrap=False)

    def on_mount(self) -> None:
        self._poll()

    @work(exclusive=True, thread=True)
    def _poll(self) -> None:
        while True:
            self.call_from_thread(self._refresh_data)
            time.sleep(POLL_INTERVAL)

    def _refresh_data(self) -> None:
        log = self.query_one("#event-log", RichLog)
        sprint_id = self.sprint_id or find_sprint_id()

        if sprint_id:
            events_file = Path(f"/tmp/caf_sprint/{sprint_id}/events.jsonl")
            if events_file.exists():
                self._load_jsonl(log, events_file)
                return

        # Fallback: derive synthetic events from caf_live_agents.json
        live_file = Path("/tmp/caf_live_agents.json")
        if live_file.exists():
            self._load_synthetic(log, live_file)

    def _load_jsonl(self, log: RichLog, events_file: Path) -> None:
        """Read events.jsonl and append only new lines."""
        try:
            lines = events_file.read_text().splitlines()
        except OSError:
            return

        new_lines = lines[self._last_line_count :]
        if not new_lines:
            return

        self._last_line_count = len(lines)

        for raw in new_lines:
            raw = raw.strip()
            if not raw:
                continue
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                continue

            ts_raw = ev.get("ts", ev.get("timestamp", ""))
            ts = self._fmt_ts(ts_raw)

            ev_type = ev.get("type", ev.get("event", ""))
            short = TYPE_SHORT.get(ev_type, ev_type[:8])

            # Extract key data snippet
            data = ev.get("data", ev.get("name", ev.get("role", "")))
            if isinstance(data, dict):
                data = data.get("name", data.get("role", str(data)))
            snippet = str(data)[:60] if data else ""

            log.write(f"[dim]{ts}[/dim]  [cyan]{short:<6}[/cyan]  {snippet}")

        log.scroll_end(animate=False)

    def _load_synthetic(self, log: RichLog, live_file: Path) -> None:
        """Synthesize start/stop events from caf_live_agents.json."""
        try:
            data = json.loads(live_file.read_text())
        except Exception:
            return

        agents = data.get("agents", [])
        # Build synthetic event list from agents
        events = []
        for agent in agents:
            started = agent.get("started", 0)
            name = agent.get("name", "?")
            status = agent.get("status", "?")
            if started:
                events.append((started, "Start", name))
            if status == "done":
                duration_s = agent.get("duration_s", 0)
                events.append((started + duration_s, "Stop", name))

        events.sort(key=lambda x: x[0])

        if len(events) <= self._last_line_count:
            return

        new_events = events[self._last_line_count :]
        self._last_line_count = len(events)

        for ts_epoch, short, name in new_events:
            ts = self._fmt_epoch(ts_epoch)
            log.write(f"[dim]{ts}[/dim]  [cyan]{short:<6}[/cyan]  {name[:60]}")

        log.scroll_end(animate=False)

    def _fmt_ts(self, ts_raw: str) -> str:
        """Format ISO timestamp to HH:MM:SS."""
        if not ts_raw:
            return "--:--:--"
        try:
            # Handle ISO format like 2024-01-01T12:34:56.789Z
            ts_raw = ts_raw.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts_raw)
            return dt.strftime("%H:%M:%S")
        except Exception:
            return ts_raw[:8]

    def _fmt_epoch(self, epoch: float) -> str:
        """Format epoch seconds to HH:MM:SS."""
        if not epoch:
            return "--:--:--"
        try:
            return datetime.fromtimestamp(epoch).strftime("%H:%M:%S")
        except Exception:
            return "--:--:--"
