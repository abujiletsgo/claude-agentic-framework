"""Aggregated report panel — renders report.md as Markdown."""
from pathlib import Path
from textual.widgets import Markdown, Static
from textual.widget import Widget
from textual.containers import Vertical, VerticalScroll


class ReportPanel(Widget):
    """Displays report.md (or concatenated results), polled every 5s."""

    def __init__(self, ipc_dir: Path, **kwargs):
        super().__init__(**kwargs)
        self.ipc_dir = ipc_dir
        self.last_mtime = 0.0
        self.can_focus = True

    def compose(self):
        yield Static("Report", classes="panel-title")
        with VerticalScroll():
            yield Markdown("*Waiting for report...*", id="report-content")

    def on_mount(self) -> None:
        self.refresh_data()
        self.set_interval(5, self.refresh_data)

    def refresh_data(self) -> None:
        report_file = self.ipc_dir / "report.md"
        md_widget = self.query_one("#report-content", Markdown)
        try:
            if report_file.exists() and report_file.stat().st_size > 0:
                mtime = report_file.stat().st_mtime
                if mtime != self.last_mtime:
                    self.last_mtime = mtime
                    md_widget.update(report_file.read_text())
                return

            # Fallback: concatenate results
            results_dir = self.ipc_dir / "results"
            if results_dir.exists():
                parts = []
                for rf in sorted(results_dir.glob("*_result.md")):
                    parts.append(f"## {rf.stem}\n\n{rf.read_text()}")
                if parts:
                    md_widget.update("\n\n---\n\n".join(parts))
                    return

            md_widget.update("*Waiting for report...*")
        except OSError:
            md_widget.update("*Error reading report*")
