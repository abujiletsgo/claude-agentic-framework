"""Report panel — renders report as styled text lines."""
from pathlib import Path
from textual.widgets import RichLog, Static
from textual.widget import Widget


class ReportPanel(Widget):
    """Displays report.md as styled text, polled every 5s."""

    def __init__(self, ipc_dir: Path, **kwargs):
        super().__init__(**kwargs)
        self.ipc_dir = ipc_dir
        self.last_mtime = 0.0
        self.can_focus = True

    def compose(self):
        yield Static("Report", classes="panel-title")
        yield RichLog(id="report-log", highlight=False, markup=True, wrap=True)

    def on_mount(self) -> None:
        self.refresh_data()
        self.set_interval(5, self.refresh_data)

    def refresh_data(self) -> None:
        log = self.query_one("#report-log", RichLog)
        report_file = self.ipc_dir / "report.md"
        try:
            if report_file.exists() and report_file.stat().st_size > 0:
                mtime = report_file.stat().st_mtime
                if mtime == self.last_mtime:
                    return
                self.last_mtime = mtime
                log.clear()
                self._render_md(log, report_file.read_text())
                return

            # Fallback: concatenate results
            results_dir = self.ipc_dir / "results"
            if results_dir.exists():
                result_files = sorted(results_dir.glob("*_result.md"))
                if result_files:
                    log.clear()
                    for rf in result_files:
                        log.write(f"[bold cyan]{rf.stem}[/]")
                        log.write("")
                        self._render_md(log, rf.read_text())
                        log.write("[dim]───────────────────[/]")
                    return

        except OSError:
            pass

    def _render_md(self, log: RichLog, text: str) -> None:
        """Simple markdown-to-rich-markup renderer."""
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                log.write(f"[bold underline]{stripped[2:]}[/]")
            elif stripped.startswith("## "):
                log.write(f"[bold]{stripped[3:]}[/]")
            elif stripped.startswith("### "):
                log.write(f"[bold dim]{stripped[4:]}[/]")
            elif stripped.startswith("- "):
                log.write(f"  • {stripped[2:]}")
            elif stripped.startswith("---"):
                log.write("[dim]───────────────────[/]")
            elif stripped.startswith("**") and stripped.endswith("**"):
                log.write(f"[bold]{stripped[2:-2]}[/]")
            elif stripped.startswith("`") and stripped.endswith("`"):
                log.write(f"[italic]{stripped[1:-1]}[/]")
            elif stripped:
                log.write(f"  {stripped}")
            else:
                log.write("")
