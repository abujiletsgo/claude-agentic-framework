"""
Display helpers for CAF sprint lead agents.
Works in any terminal. Integrates with cmux sidebar when available.
Uses `rich` if installed; falls back to ANSI escape codes.
"""
import os
import sys
from datetime import datetime, UTC

# Optional rich support
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich import box
    _RICH = True
except ImportError:
    _RICH = False

# Optional cmux support
try:
    from lib.cmux_client import is_available as _cmux_available, set_status, set_progress, log as cmux_log
    _CMUX = _cmux_available()
except Exception:
    _CMUX = False


# ── ANSI fallback helpers ─────────────────────────────────────────────────────

_RESET = "\033[0m"
_BOLD  = "\033[1m"
_GREEN = "\033[32m"
_RED   = "\033[31m"
_CYAN  = "\033[36m"
_DIM   = "\033[2m"

def _bar(pct: int, width: int = 30) -> str:
    filled = int(width * pct / 100)
    return "[" + "█" * filled + "░" * (width - filled) + f"] {pct}%"


# ── LeadDisplay ───────────────────────────────────────────────────────────────

class LeadDisplay:
    """
    Visual display for a sprint lead agent running in its own terminal pane.

    Usage:
        d = LeadDisplay("engineering-lead", "Refactor auth middleware")
        d.task("read files", "done")
        d.task("write implementation", "running")
        d.progress(40, "building...")
        d.done("Refactor complete. 3 files changed.")
    """

    def __init__(self, role: str, mission: str):
        self.role = role
        self.mission = mission
        self._tasks: list[tuple[str, str]] = []
        if _RICH:
            self._console = Console()
        self._render_header()

    def _render_header(self) -> None:
        sprint_id = os.environ.get("CAF_SPRINT_ID", "?")
        ts = datetime.now(UTC).strftime("%H:%M:%S")
        if _RICH:
            self._console.print(Panel(
                f"[bold cyan]{self.role}[/bold cyan]\n"
                f"[dim]Sprint {sprint_id} | {ts} UTC[/dim]\n\n"
                f"{self.mission}",
                title="[bold]CAF Sprint Lead[/bold]",
                border_style="cyan",
            ))
        else:
            w = 60
            print(f"{_BOLD}{_CYAN}{'═' * w}{_RESET}")
            print(f"{_BOLD}{_CYAN}  CAF Sprint Lead — {self.role}{_RESET}")
            print(f"{_DIM}  Sprint {sprint_id} | {ts} UTC{_RESET}")
            print(f"{_CYAN}{'─' * w}{_RESET}")
            print(f"  {self.mission}")
            print(f"{_CYAN}{'═' * w}{_RESET}")
            print()
        if _CMUX:
            set_status(f"{self.role}: starting")
            set_progress(0)

    def task(self, name: str, status: str = "running") -> None:
        """Print a task row. status: 'running' | 'done' | 'failed' | 'waiting'"""
        icons = {"done": "✓", "running": "►", "failed": "✗", "waiting": "○"}
        colors_rich = {"done": "green", "running": "yellow", "failed": "red", "waiting": "dim"}
        icon = icons.get(status, "·")
        if _RICH:
            color = colors_rich.get(status, "white")
            self._console.print(f"  [{color}]{icon}[/{color}] {name}")
        else:
            ansi = {"done": _GREEN, "failed": _RED, "running": _CYAN}.get(status, "")
            print(f"  {ansi}{icon}{_RESET} {name}")
        if _CMUX and status == "running":
            set_status(f"{self.role}: {name}")

    def progress(self, pct: int, label: str = "") -> None:
        """Print a progress bar."""
        if _RICH:
            with Progress(
                SpinnerColumn(),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn(label),
                console=self._console,
                transient=True,
            ) as prog:
                t = prog.add_task("", total=100)
                prog.update(t, completed=pct)
        else:
            print(f"  {_bar(pct)}  {label}")
        if _CMUX:
            set_progress(pct)
            if label:
                set_status(f"{self.role}: {label}")

    def section(self, title: str) -> None:
        """Print a section divider."""
        if _RICH:
            self._console.rule(f"[dim]{title}[/dim]")
        else:
            print(f"\n{_DIM}── {title} {'─' * max(0, 50 - len(title))}{_RESET}")

    def info(self, text: str) -> None:
        if _RICH:
            self._console.print(f"  [dim]{text}[/dim]")
        else:
            print(f"  {_DIM}{text}{_RESET}")

    def done(self, summary: str) -> None:
        """Print success panel and update cmux to 100%."""
        if _RICH:
            self._console.print(Panel(
                f"[green]{summary}[/green]",
                title="[bold green]✓ DONE[/bold green]",
                border_style="green",
            ))
        else:
            w = 60
            print(f"\n{_GREEN}{_BOLD}{'═' * w}{_RESET}")
            print(f"{_GREEN}{_BOLD}  ✓ DONE — {self.role}{_RESET}")
            print(f"{_GREEN}{'─' * w}{_RESET}")
            print(f"  {summary}")
            print(f"{_GREEN}{'═' * w}{_RESET}\n")
        if _CMUX:
            set_progress(100)
            set_status(f"{self.role}: done")

    def fail(self, error: str) -> None:
        """Print failure panel and update cmux status."""
        if _RICH:
            self._console.print(Panel(
                f"[red]{error}[/red]",
                title="[bold red]✗ FAILED[/bold red]",
                border_style="red",
            ))
        else:
            w = 60
            print(f"\n{_RED}{_BOLD}{'═' * w}{_RESET}")
            print(f"{_RED}{_BOLD}  ✗ FAILED — {self.role}{_RESET}")
            print(f"{_RED}{'─' * w}{_RESET}")
            print(f"  {error}")
            print(f"{_RED}{'═' * w}{_RESET}\n")
        if _CMUX:
            set_status(f"{self.role}: FAILED")
