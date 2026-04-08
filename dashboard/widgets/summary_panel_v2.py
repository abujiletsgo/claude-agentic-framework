"""SummaryPanelV2 — narrative summary of what leads/agents are doing."""
import json
import os
import time
from pathlib import Path

from textual.widget import Widget
from textual.widgets import Static
from textual import work

POLL_INTERVAL = 3.0  # seconds

WAVE_ORDER = [
    "planning",
    "engineering",
    "review",
    "qa",
    "security",
    "release",
]

STATUS_ICONS = {
    "running": "[yellow]\u26a1[/yellow]",
    "done": "[green]\u2713[/green]",
    "pending": "[dim]\u23f3[/dim]",
    "locked": "[dim]\U0001f512[/dim]",
}


def find_sprint_id() -> str:
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


class SummaryPanelV2(Widget):
    """Narrative summary of what leads/agents are doing.

    Sprint mode: one line per lead in wave order.
    Orchestrate mode: one line per agent step.
    Height fixed at ~6 lines.
    """

    DEFAULT_CSS = """
    SummaryPanelV2 {
        height: 8;
    }
    """

    def __init__(self, sprint_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.sprint_id = sprint_id
        self.can_focus = False

    def compose(self):
        yield Static("", id="summary-title", classes="panel-title")
        yield Static("", id="summary-body", markup=True)

    def on_mount(self) -> None:
        self._refresh_data()
        self._poll()

    @work(exclusive=True, thread=True)
    def _poll(self) -> None:
        while True:
            time.sleep(POLL_INTERVAL)
            self.call_from_thread(self._refresh_data)

    def _refresh_data(self) -> None:
        sprint_id = self.sprint_id or find_sprint_id()
        if sprint_id:
            self._render_sprint(sprint_id)
        else:
            self._render_orchestrate()

    def _render_sprint(self, sprint_id: str) -> None:
        title = self.query_one("#summary-title", Static)
        body = self.query_one("#summary-body", Static)
        title.update(f"Summary  [dim](sprint: {sprint_id[:16]})[/dim]")

        sprint_dir = Path(f"/tmp/caf_sprint/{sprint_id}")
        results_dir = sprint_dir / "results"
        status_file = sprint_dir / "status.json"

        # Load status.json if available
        status_map: dict = {}
        if status_file.exists():
            try:
                status_map = json.loads(status_file.read_text())
            except Exception:
                pass

        lines = []
        for role in WAVE_ORDER:
            lead_name = f"{role}-lead"

            # Determine status icon
            lead_status = status_map.get(lead_name, {})
            if isinstance(lead_status, dict):
                st = lead_status.get("status", "pending")
            else:
                st = str(lead_status)
            icon = STATUS_ICONS.get(st, "[dim]\u23f3[/dim]")

            # Try to read result file
            result_file = results_dir / f"{lead_name}_result.md" if results_dir.exists() else None
            if result_file and result_file.exists():
                try:
                    content = result_file.read_text()
                    snippet = content.strip()[:100].replace("\n", " ")
                    lines.append(f"  [bold]{lead_name:<20}[/bold] {icon}  {snippet}…")
                except OSError:
                    lines.append(f"  [bold]{lead_name:<20}[/bold] {icon}  (unreadable)")
            elif st == "running":
                lines.append(f"  [bold]{lead_name:<20}[/bold] {icon}  running…")
            else:
                wave_num = (WAVE_ORDER.index(role) // 2) + 1
                lines.append(f"  [dim]{lead_name:<20}[/dim] {icon}  waiting wave {wave_num}")

        body.update("\n".join(lines))

    def _render_orchestrate(self) -> None:
        title = self.query_one("#summary-title", Static)
        body = self.query_one("#summary-body", Static)
        title.update("Summary  [dim](orchestrate)[/dim]")

        live_file = Path("/tmp/caf_live_agents.json")
        if not live_file.exists():
            body.update("  [dim]No agents yet.[/dim]")
            return

        try:
            data = json.loads(live_file.read_text())
        except Exception:
            body.update("  [dim]Error reading agent data.[/dim]")
            return

        agents = data.get("agents", [])
        if not agents:
            body.update("  [dim]No agents yet.[/dim]")
            return

        lines = []
        for i, agent in enumerate(agents, start=1):
            name = agent.get("name", "?")[:30]
            status = agent.get("status", "?")
            snippet = agent.get("snippet", "")[:50]
            icon = STATUS_ICONS.get(status, "[dim]?[/dim]")
            lines.append(f"  Step {i:<3} [bold]{name:<30}[/bold] {icon}  {snippet}")

        # Show newest at bottom — take last 6 to fit fixed height
        lines = lines[-6:]
        body.update("\n".join(lines))
