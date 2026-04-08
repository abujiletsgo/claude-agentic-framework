"""LeadsGrid widget — 6 lead cards in a 3-column x 2-row grid."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, Label
from textual.containers import Grid
from textual import work


LEADS = [
    {"role": "planning-lead",     "wave": 0, "budget": 50000},
    {"role": "engineering-lead",  "wave": 1, "budget": 100000},
    {"role": "review-lead",       "wave": 2, "budget": 60000},
    {"role": "qa-lead",           "wave": 2, "budget": 80000},
    {"role": "security-lead",     "wave": 2, "budget": 40000},
    {"role": "release-lead",      "wave": 3, "budget": 30000},
]

STATUS_ICONS = {
    "running": "⚡",
    "done":    "✓",
    "pending": "⏳",
    "locked":  "🔒",
    "failed":  "✗",
}

# budget / 1000 = max seconds shown for progress bar
BUDGET_TO_MAX_SECS = 1000


def find_sprint_id() -> str:
    import os
    from pathlib import Path
    sid = os.environ.get("CAF_SPRINT_ID", "")
    if not sid:
        dirs = sorted(Path("/tmp/caf_sprint").iterdir(), key=lambda d: d.stat().st_mtime, reverse=True) if Path("/tmp/caf_sprint").exists() else []
        sid = dirs[0].name if dirs else ""
    return sid


def _build_bar(elapsed: float, max_secs: float, width: int = 10) -> str:
    """Draw a Unicode block progress bar of given width."""
    if max_secs <= 0:
        ratio = 0.0
    else:
        ratio = min(elapsed / max_secs, 1.0)
    filled = int(ratio * width)
    empty = width - filled
    return "▓" * filled + "░" * empty


class LeadCard(Widget):
    """A single lead status card with border."""

    DEFAULT_CSS = """
    LeadCard {
        border: round $primary-darken-2;
        height: 7;
        padding: 0 1;
    }
    """

    def __init__(self, role: str, wave: int, budget: int, **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.wave = wave
        self.budget = budget
        self._status_info: dict = {}

    def compose(self) -> ComposeResult:
        yield Label("", id=f"card-title-{self.role}")
        yield Label("", id=f"card-status-{self.role}")
        yield Label("", id=f"card-bar-{self.role}")

    def on_mount(self) -> None:
        self._render_card()

    def update_status(self, status: dict) -> None:
        """Called by LeadsGrid with fresh status data for this role."""
        self._status_info = status
        self._render_card()

    def _render_card(self) -> None:
        info = self._status_info
        status = info.get("status", "pending")
        icon = STATUS_ICONS.get(status, "⏳")

        # Elapsed time
        elapsed_secs = 0.0
        elapsed_str = "--"
        started = info.get("started", "")
        if started:
            try:
                start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                elapsed_secs = (datetime.now(timezone.utc) - start_dt).total_seconds()
                elapsed_secs = max(0.0, elapsed_secs)
                elapsed_str = f"{int(elapsed_secs)}s"
            except (ValueError, TypeError):
                elapsed_str = "?"

        model = info.get("model", "")

        max_secs = self.budget / BUDGET_TO_MAX_SECS
        bar = _build_bar(elapsed_secs, max_secs, width=10)
        used_k = int(elapsed_secs / 1000) if elapsed_secs else 0
        budget_k = self.budget // 1000
        bar_line = f"{bar}  {used_k}k / {budget_k}k"

        title_label = self.query_one(f"#card-title-{self.role}", Label)
        status_label = self.query_one(f"#card-status-{self.role}", Label)
        bar_label = self.query_one(f"#card-bar-{self.role}", Label)

        title_label.update(f"{self.role} — W{self.wave}")
        status_label.update(f"{icon}  {elapsed_str}    {model}")
        bar_label.update(bar_line)


class LeadsGrid(Widget):
    """6 lead cards in a 3-column x 2-row grid, polled every 2s."""

    DEFAULT_CSS = """
    LeadsGrid {
        layout: vertical;
    }
    #leads-grid {
        grid-size: 3;
        grid-gutter: 1;
        height: 1fr;
    }
    """

    def __init__(self, sprint_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.sprint_id = sprint_id or find_sprint_id()
        self._no_sprint = not bool(self.sprint_id)

    def compose(self) -> ComposeResult:
        if self._no_sprint:
            yield Static("No active sprint", id="no-sprint-msg")
            return
        with Grid(id="leads-grid"):
            for lead in LEADS:
                yield LeadCard(
                    role=lead["role"],
                    wave=lead["wave"],
                    budget=lead["budget"],
                    id=f"leadcard-{lead['role']}",
                )

    def on_mount(self) -> None:
        if not self._no_sprint:
            self._poll()

    @work(exclusive=True, thread=True)
    def _poll(self) -> None:
        """Poll status.json every 2s and update cards."""
        import time
        status_file = Path(f"/tmp/caf_sprint/{self.sprint_id}/status.json")
        while True:
            try:
                if status_file.exists():
                    raw = status_file.read_text()
                    data: dict = json.loads(raw)
                    # Schedule UI updates on the main thread
                    for lead in LEADS:
                        role = lead["role"]
                        info = data.get(role, {})
                        card_id = f"leadcard-{role}"
                        self.app.call_from_thread(
                            self._update_card, card_id, info
                        )
            except (json.JSONDecodeError, OSError):
                pass
            time.sleep(2)

    def _update_card(self, card_id: str, info: dict) -> None:
        try:
            card = self.query_one(f"#{card_id}", LeadCard)
            card.update_status(info)
        except Exception:
            pass
