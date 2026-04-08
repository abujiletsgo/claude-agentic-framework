"""Wave progress bars — shows completion percentage per wave."""
import json
from pathlib import Path
from textual.widgets import Static, ProgressBar, Label
from textual.widget import Widget
from textual.containers import Horizontal, Vertical


WAVE_NAMES = {0: "Plan", 1: "Build", 2: "Validate", 3: "Ship"}


class WaveProgress(Widget):
    """Shows progress bars for each wave, polled every 2s."""

    def __init__(self, ipc_dir: Path, **kwargs):
        super().__init__(**kwargs)
        self.ipc_dir = ipc_dir

    def compose(self):
        with Horizontal():
            for wave_num in range(4):
                name = WAVE_NAMES[wave_num]
                with Vertical(classes="wave-container"):
                    yield Label(f"W{wave_num}: {name}", classes="wave-label")
                    yield ProgressBar(total=100, show_eta=False,
                                      id=f"wave-bar-{wave_num}")

    def on_mount(self) -> None:
        self.refresh_data()
        self.set_interval(2, self.refresh_data)

    def refresh_data(self) -> None:
        if self.ipc_dir is None:
            return
        status_data = {}
        gate_data = {"unlocked_waves": []}

        try:
            status_file = self.ipc_dir / "status.json"
            if status_file.exists():
                status_data = json.loads(status_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass

        try:
            gate_file = self.ipc_dir / "gate.json"
            if gate_file.exists():
                gate_data = json.loads(gate_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass

        unlocked = set(gate_data.get("unlocked_waves", []))

        # Build wave-to-leads mapping from status.json
        wave_leads = {}
        for lead, info in status_data.items():
            w = info.get("wave", -1)
            if w not in wave_leads:
                wave_leads[w] = []
            wave_leads[w].append(lead)

        for wave_num in range(4):
            bar = self.query_one(f"#wave-bar-{wave_num}", ProgressBar)
            leads = wave_leads.get(wave_num, [])
            if not leads:
                bar.update(progress=0)
                continue

            done_count = sum(
                1 for lead in leads
                if status_data.get(lead, {}).get("status") == "done"
            )
            total = len(leads)
            pct = int((done_count / total) * 100) if total > 0 else 0

            # If wave not unlocked and no leads running, show 0
            if wave_num not in unlocked and done_count == 0:
                pct = 0

            bar.update(progress=pct)
