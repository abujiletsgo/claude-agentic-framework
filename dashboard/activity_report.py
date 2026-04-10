#!/usr/bin/env python3
"""
CAF Activity Report — always-on session journal panel.

Shows recent session summaries from activity_log.jsonl + MEMORY.md.
Auto-switches to sprint live mode when /sprint starts.

Usage: python3 dashboard/activity_report.py [poll_seconds]
"""
import sys, os, re, json, time, shutil
from pathlib import Path
from datetime import datetime, UTC

# ── ANSI ──────────────────────────────────────────────────────────────────────
R  = "\033[0m"
B  = "\033[1m"
D  = "\033[2m"
CY = "\033[36m"
GR = "\033[32m"
YL = "\033[33m"
RD = "\033[31m"
M  = "\033[35m"
BL = "\033[34m"

STRIP_ANSI = re.compile(r'\033\[[0-9;]*m')

def cols(): return shutil.get_terminal_size((100, 40)).columns
def rule(c="─", color=D): print(f"{color}{c * cols()}{R}")


# ── Data sources ──────────────────────────────────────────────────────────────

LOG_PATH = Path.home() / ".claude" / "data" / "activity_log.jsonl"


def read_activity_log(n: int = 12) -> list[dict]:
    if not LOG_PATH.exists():
        return []
    try:
        lines = [l for l in LOG_PATH.read_text().splitlines() if l.strip()]
        entries = []
        for l in lines[-n:]:
            try:
                entries.append(json.loads(l))
            except Exception:
                pass
        return list(reversed(entries))  # newest first
    except Exception:
        return []


def read_memory_entries(cwd: str, n: int = 5) -> list[dict]:
    """Parse MEMORY.md as fallback / supplement."""
    path = Path(cwd) / ".claude" / "MEMORY.md"
    if not path.exists():
        return []
    try:
        text = path.read_text(errors="replace")
    except Exception:
        return []

    pattern = re.compile(r'^## (\d{4}-\d{2}-\d{2}.*?)$', re.MULTILINE)
    matches = list(pattern.finditer(text))
    entries = []
    for i, m in enumerate(matches):
        header = m.group(1)
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():body_end].strip()
        commit, changed, tasks = "", [], []
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("**Commit:**"):
                commit = line[11:].strip()
            elif line.startswith("  ") and "|" in line:
                changed.append(line.strip())
            elif line.startswith("- Task:"):
                tasks.append(line[7:].strip())
        entries.append({"header": header, "commit": commit, "changed": changed, "tasks": tasks})
    return list(reversed(entries))[-n:]


# ── Renderer ──────────────────────────────────────────────────────────────────

def fmt_ts(iso: str) -> str:
    """ISO timestamp → human label like '2026-04-10 04:20'."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return iso[:16]


def render_activity_entry(entry: dict):
    """Render one activity_log entry."""
    ts   = fmt_ts(entry.get("ts", ""))
    commit  = entry.get("commit", "")
    changed = entry.get("changed", [])
    tasks   = entry.get("tasks", [])

    print(f"  {B}{CY}{ts}{R}")
    if commit:
        short = commit[: cols() - 6]
        print(f"  {D}{short}{R}")
    for f in changed[:3]:
        print(f"  {D}  · {f}{R}")
    if len(changed) > 3:
        print(f"  {D}  · … +{len(changed) - 3} more{R}")
    for t in tasks[:3]:
        parts = t.split(" → ", 1)
        if len(parts) == 2:
            print(f"  {GR}  ✓{R} {D}{parts[0]}{R}  {D}→ {parts[1][:60]}{R}")
        else:
            print(f"  {D}  · {t}{R}")
    if not commit and not changed and not tasks:
        print(f"  {D}  (no changes recorded){R}")
    print()


def render_memory_entry(entry: dict):
    """Render one MEMORY.md entry (fallback when no activity_log entries)."""
    header  = entry.get("header", "")
    commit  = entry.get("commit", "")
    changed = entry.get("changed", [])
    tasks   = entry.get("tasks", [])

    print(f"  {B}{CY}{header}{R}")
    if commit:
        short = commit[: cols() - 6]
        print(f"  {D}{short}{R}")
    for f in changed[:3]:
        print(f"  {D}  · {f}{R}")
    if len(changed) > 3:
        print(f"  {D}  · … +{len(changed) - 3} more{R}")
    for t in tasks[:3]:
        parts = t.split(" → ", 1)
        if len(parts) == 2:
            print(f"  {GR}  ✓{R} {D}{parts[0]}{R}  {D}→ {parts[1][:60]}{R}")
        else:
            print(f"  {D}  · {t}{R}")
    print()


def render_idle(cwd: str):
    w = cols()
    ts = datetime.now(UTC).strftime("%H:%M UTC")
    sys.stdout.write("\033[2J\033[H")

    # Header
    print(f"{B}{CY}{'━' * w}{R}")
    print(f"{B}{CY}  ACTIVITY REPORT{R}")
    print(f"{D}{'━' * w}{R}")
    print()

    activity = read_activity_log(n=8)
    if activity:
        for entry in activity:
            render_activity_entry(entry)
    else:
        # Fallback: MEMORY.md entries
        mem = read_memory_entries(cwd, n=5)
        if mem:
            for entry in mem:
                render_memory_entry(entry)
        else:
            print(f"  {D}no session history yet{R}")
            print()

    # Status line
    rule("─", D)
    print(f"  {D}○  {ts}{R}", end="", flush=True)


# ── Main loop ─────────────────────────────────────────────────────────────────

def run(poll: int = 5):
    cwd = str(Path(__file__).parent.parent)
    while True:
        render_idle(cwd)
        time.sleep(poll)


if __name__ == "__main__":
    poll = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    try:
        run(poll=poll)
    except KeyboardInterrupt:
        print()
