"""TopBar widget — single horizontal status bar across the full TUI width.

Sections left→right:
  1. WAVE  — visual progress through 4 sprint phases (or "ORCHESTRATE" label)
  2. Cost  — estimated session cost from cost_estimator
  3. Tokens — total token estimate across all agents
  4. Depth — agent hierarchy ("PM → Lead → Worker" or "Orchestrate")
  5. Agents — running / done counts

Polls every 3 seconds via @work(thread=True).
"""
import json
import os
import time
from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Label

from dashboard.cost_estimator import (
    estimate_session_cost,
    format_cost,
    load_agents,
    TOKENS_PER_RUN,
)

POLL_INTERVAL = 3.0  # seconds

WAVE_NAMES = ["PLAN", "BUILD", "VALIDATE", "SHIP"]

# Characters used to represent wave state
_WAVE_DONE_L = "▓"
_WAVE_DONE_R = "▓"
_WAVE_FUTURE_L = "░"
_WAVE_FUTURE_R = "░"


# ---------------------------------------------------------------------------
# Sprint discovery
# ---------------------------------------------------------------------------

def find_sprint_id() -> str:
    """Return the most-recent sprint ID from env or /tmp/caf_sprint/, or ''."""
    sid = os.environ.get("CAF_SPRINT_ID", "")
    if not sid:
        sprint_dir = Path("/tmp/caf_sprint")
        if sprint_dir.exists():
            dirs = sorted(
                sprint_dir.iterdir(),
                key=lambda d: d.stat().st_mtime,
                reverse=True,
            )
            if dirs:
                sid = dirs[0].name
    return sid


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

class TopBar(Widget):
    """Single-line horizontal status bar for the CAF dashboard."""

    DEFAULT_CSS = """
    TopBar {
        height: 1;
        background: $primary;
        color: $text;
        text-style: bold;
    }
    TopBar .top-bar {
        height: 1;
        background: $primary;
        color: $text;
        text-style: bold;
    }
    TopBar Label {
        height: 1;
        padding: 0 1;
        background: $primary;
        color: $text;
        text-style: bold;
    }
    """

    def __init__(self, sprint_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.sprint_id = sprint_id

    def _get_sprint_id(self) -> str:
        return self.sprint_id or find_sprint_id()

    def compose(self) -> ComposeResult:
        with Horizontal(classes="top-bar"):
            yield Label("", id="tb-wave")
            yield Label("", id="tb-cost")
            yield Label("", id="tb-tokens")
            yield Label("", id="tb-depth")
            yield Label("", id="tb-agents")

    def on_mount(self) -> None:
        self._poll()

    @work(exclusive=True, thread=True)
    def _poll(self) -> None:
        while True:
            self.call_from_thread(self._refresh)
            time.sleep(POLL_INTERVAL)

    # ------------------------------------------------------------------
    # Data refresh (called on the main thread via call_from_thread)
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        agents = load_agents()
        sprint_id = self._get_sprint_id()

        self._update_wave(sprint_id)
        self._update_cost(agents)
        self._update_tokens(agents)
        self._update_depth(sprint_id)
        self._update_agents(agents)

    # ------------------------------------------------------------------
    # Section updaters
    # ------------------------------------------------------------------

    def _update_wave(self, sprint_id: str) -> None:
        label = self.query_one("#tb-wave", Label)

        if not sprint_id:
            label.update("ORCHESTRATE")
            return

        gate_file = Path("/tmp/caf_sprint") / sprint_id / "gate.json"
        unlocked_waves: list[int] = []
        active_wave: int | None = None

        try:
            if gate_file.exists():
                gate_data = json.loads(gate_file.read_text())
                unlocked_waves = gate_data.get("unlocked_waves", [])
                active_wave = gate_data.get("current_wave")
        except (json.JSONDecodeError, OSError):
            pass

        unlocked_set = set(unlocked_waves)

        parts: list[str] = []
        for i, name in enumerate(WAVE_NAMES):
            if i == active_wave:
                # Active wave: highlighted with solid blocks
                parts.append(f"{_WAVE_DONE_L}{name}{_WAVE_DONE_R}")
            elif i in unlocked_set and i != active_wave:
                # Done (unlocked, not active)
                parts.append(f"{_WAVE_DONE_L}{name}{_WAVE_DONE_R}")
            else:
                # Future / locked
                parts.append(f"{_WAVE_FUTURE_L}{name}{_WAVE_FUTURE_R}")

        label.update("  ".join(parts))

    def _update_cost(self, agents: list[dict]) -> None:
        label = self.query_one("#tb-cost", Label)
        result = estimate_session_cost(agents)
        cost_str = format_cost(result["total_usd"])
        label.update(f"{cost_str} est.")

    def _update_tokens(self, agents: list[dict]) -> None:
        label = self.query_one("#tb-tokens", Label)
        total_tokens = 0
        for agent in agents:
            model_lower = agent.get("model", "").lower()
            if "haiku" in model_lower:
                total_tokens += TOKENS_PER_RUN["haiku"]
            elif "sonnet" in model_lower:
                total_tokens += TOKENS_PER_RUN["sonnet"]
            elif "opus" in model_lower:
                total_tokens += TOKENS_PER_RUN["opus"]
            else:
                # Unknown model: use sonnet as default
                total_tokens += TOKENS_PER_RUN["sonnet"]

        k = total_tokens // 1000
        label.update(f"{k}k tok")

    def _update_depth(self, sprint_id: str) -> None:
        label = self.query_one("#tb-depth", Label)
        if sprint_id:
            label.update("PM \u2192 Lead \u2192 Worker")
        else:
            label.update("Orchestrate")

    def _update_agents(self, agents: list[dict]) -> None:
        label = self.query_one("#tb-agents", Label)
        running = sum(1 for a in agents if a.get("status") == "running")
        done = sum(1 for a in agents if a.get("status") == "done")
        label.update(f"{running} running  {done} done")
