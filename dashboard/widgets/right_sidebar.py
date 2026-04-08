"""Right sidebar widget — stacked: Sessions + Memory + Models + Est. Cost.

Polling:
  - Sessions: static (on mount)
  - Memory:   static (on mount)
  - Models:   every 3s
  - Cost:     every 5s
"""
import json
import time
import urllib.parse
from pathlib import Path

from textual.app import ComposeResult
from textual.widgets import Static, Rule
from textual.widget import Widget
from textual import work

from dashboard.cost_estimator import (
    estimate_session_cost,
    format_cost,
    load_agents,
    _resolve_model_key,
)

LIVE_FILE = Path("/tmp/caf_live_agents.json")
MEMPALACE_HEALTH = Path("/tmp/caf_mempalace_health.json")
PROJECTS_DIR = Path.home() / ".claude" / "projects"

MODEL_ORDER = ["sonnet", "haiku", "opus"]
BAR_MAX_WIDTH = 8


def _decode_project_name(raw: str) -> str:
    """Convert URL-encoded dir name to human-readable path fragment.

    ~/.claude/projects dirs are named like -Users-tomkwon-Documents-caf-team.
    Strip the leading dash and replace remaining dashes with slashes, then
    take the last 2 components for compactness.
    """
    # Percent-decode first in case there is any URL encoding
    decoded = urllib.parse.unquote(raw)
    # Leading dash → strip it, rest of dashes → slashes
    if decoded.startswith("-"):
        decoded = decoded[1:]
    decoded = decoded.replace("-", "/")
    parts = decoded.strip("/").split("/")
    # Show last 2 path parts to keep it compact
    return "/".join(parts[-2:]) if len(parts) >= 2 else decoded


def _bar(count: int, max_count: int) -> str:
    """Return a Unicode block bar string proportional to count/max_count."""
    if max_count == 0:
        return ""
    filled = round(BAR_MAX_WIDTH * count / max_count)
    return "\u2593" * filled + " " * (BAR_MAX_WIDTH - filled)


class RightSidebar(Widget):
    """Stacked sidebar: Sessions, Memory, Models, Est. Cost."""

    DEFAULT_CSS = """
    RightSidebar {
        width: 22;
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
    }
    .sidebar-header {
        text-style: bold;
        color: $text;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Sessions", classes="sidebar-header")
        yield Static(id="sessions-content")
        yield Rule()
        yield Static("Memory", classes="sidebar-header")
        yield Static(id="memory-content")
        yield Rule()
        yield Static("Models", classes="sidebar-header")
        yield Static(id="models-content")
        yield Rule()
        yield Static("Est. Cost", classes="sidebar-header")
        yield Static(id="cost-content")

    def on_mount(self) -> None:
        self._refresh_sessions()
        self._refresh_memory()
        self._poll_models()
        self._poll_cost()

    # ------------------------------------------------------------------
    # Sessions (static — read once on mount)
    # ------------------------------------------------------------------

    def _refresh_sessions(self) -> None:
        widget = self.query_one("#sessions-content", Static)
        lines = ["\u2500" * 14]

        if not PROJECTS_DIR.is_dir():
            lines.append("(no projects dir)")
            widget.update("\n".join(lines))
            return

        try:
            dirs = sorted(
                (d for d in PROJECTS_DIR.iterdir() if d.is_dir()),
                key=lambda d: d.stat().st_mtime,
                reverse=True,
            )[:5]
        except OSError:
            dirs = []

        if not dirs:
            lines.append("(none)")
        else:
            for d in dirs:
                name = _decode_project_name(d.name)
                lines.append(name)

        widget.update("\n".join(lines))

    # ------------------------------------------------------------------
    # Memory (static — read once on mount)
    # ------------------------------------------------------------------

    def _refresh_memory(self) -> None:
        widget = self.query_one("#memory-content", Static)
        lines = ["\u2500" * 14]

        if not MEMPALACE_HEALTH.exists():
            lines.append("mempalace: N/A")
            widget.update("\n".join(lines))
            return

        try:
            health = json.loads(MEMPALACE_HEALTH.read_text())
            latency_ms = health.get("latency_ms", "?")
            hit_rate = health.get("hit_rate", None)
            lines.append(f"\u2713 mempalace  {latency_ms}ms")
            if hit_rate is not None:
                lines.append(f"hit rate: {int(hit_rate * 100)}%")
        except (json.JSONDecodeError, OSError):
            lines.append("mempalace: error")

        widget.update("\n".join(lines))

    # ------------------------------------------------------------------
    # Models (live — poll every 3s)
    # ------------------------------------------------------------------

    @work(exclusive=True, thread=True)
    def _poll_models(self) -> None:
        while True:
            self.call_from_thread(self._refresh_models)
            time.sleep(3.0)

    def _refresh_models(self) -> None:
        widget = self.query_one("#models-content", Static)
        lines = ["\u2500" * 14]

        agents = load_agents()
        if not agents:
            lines.append("(no agents)")
            widget.update("\n".join(lines))
            return

        counts: dict[str, int] = {"haiku": 0, "sonnet": 0, "opus": 0}
        for agent in agents:
            key = _resolve_model_key(agent.get("model", ""))
            if key and key in counts:
                counts[key] += 1

        max_count = max(counts.values()) if counts else 1

        for model in MODEL_ORDER:
            count = counts[model]
            bar = _bar(count, max_count)
            lines.append(f"{model:<6} {bar} {count}")

        widget.update("\n".join(lines))

    # ------------------------------------------------------------------
    # Est. Cost (live — poll every 5s)
    # ------------------------------------------------------------------

    @work(exclusive=True, thread=True)
    def _poll_cost(self) -> None:
        while True:
            self.call_from_thread(self._refresh_cost)
            time.sleep(5.0)

    def _refresh_cost(self) -> None:
        widget = self.query_one("#cost-content", Static)
        lines = ["\u2500" * 14]

        agents = load_agents()
        if not agents:
            lines.append("~$0.00 session")
            lines.append("~$0.00/min")
            lines.append("\u2500" * 13)
            for model in MODEL_ORDER:
                lines.append(f"{model:<6} ~$0.00")
            lines.append("(est. based on API pricing)")
            widget.update("\n".join(lines))
            return

        result = estimate_session_cost(agents)
        total = result["total_usd"]
        rate = result["rate_per_min"]
        by_model = result["by_model"]

        lines.append(f"{format_cost(total)} session")
        lines.append(f"{format_cost(rate)}/min")
        lines.append("\u2500" * 13)
        for model in MODEL_ORDER:
            cost = by_model.get(model, 0.0)
            lines.append(f"{model:<6} {format_cost(cost)}")
        lines.append("(est. based on API pricing)")

        widget.update("\n".join(lines))
