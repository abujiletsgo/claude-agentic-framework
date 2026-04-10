#!/usr/bin/env python3
"""
CAF Sprint Report — always-on dashboard panel.
Polls every 5s. Clear + redraw. No args, no demo, no mode switching.
"""
import json
import os
import sys
import time
import shutil
from datetime import datetime, timezone
from pathlib import Path

# ── ANSI ──────────────────────────────────────────────────────────────────────
R  = "\033[0m"
B  = "\033[1m"
CY = "\033[96m"
GR = "\033[92m"
YL = "\033[93m"
RD = "\033[91m"
M  = "\033[95m"

# ── Constants ─────────────────────────────────────────────────────────────────
SPRINT_BASE = Path("/tmp/caf_sprint")
ACTIVITY_LOG = Path.home() / ".claude/data/activity_log.jsonl"
SESSION_BASE = Path("/tmp/caf_session")

LEAD_ORDER = [
    "planning-lead",
    "engineering-lead",
    "frontend-lead",
    "review-lead",
    "qa-lead",
    "security-lead",
    "release-lead",
    "docs-lead",
]

WAVE_LABELS = {0: "PLAN", 1: "BUILD", 2: "VALIDATE", 3: "SHIP"}

# Lead -> wave assignment by index (approx): first 2=W0, next 3=W1, next 2=W2, last 1=W3
LEAD_WAVE = {
    "planning-lead":    0,
    "engineering-lead": 1,
    "frontend-lead":    1,
    "review-lead":      1,
    "qa-lead":          2,
    "security-lead":    2,
    "release-lead":     3,
    "docs-lead":        3,
}


# ── Terminal helpers ──────────────────────────────────────────────────────────

def term_width() -> int:
    return shutil.get_terminal_size((100, 40)).columns


def trunc(line: str, w: int) -> str:
    """Truncate line to w chars."""
    if len(line) > w:
        return line[:w - 1] + "…"
    return line


def out(line: str = ""):
    w = term_width() - 2
    print(trunc(line, w))


# ── Data readers ──────────────────────────────────────────────────────────────

def sprint_cwd(sprint_id: str) -> str | None:
    """Read cwd file from sprint dir, return cwd string or None."""
    try:
        return (SPRINT_BASE / sprint_id / "cwd").read_text().strip() or None
    except Exception:
        return None


def sprint_matches_project(sprint_id: str) -> bool:
    """True if sprint belongs to PROJECT_CWD (or no filter set)."""
    if not PROJECT_CWD:
        return True
    cwd = sprint_cwd(sprint_id)
    if cwd is None:
        return False  # no cwd file = unknown project, hide when filtering
    return cwd == PROJECT_CWD


def find_active_sprint() -> str | None:
    """Return sprint_id if current_sprint_id pointer exists, dir exists, and matches project."""
    pointer = SPRINT_BASE / "current_sprint_id"
    try:
        sprint_id = pointer.read_text().strip()
        if sprint_id and (SPRINT_BASE / sprint_id).is_dir() and sprint_matches_project(sprint_id):
            return sprint_id
    except Exception:
        pass
    return None


def find_last_sprint() -> str | None:
    """Scan /tmp/caf_sprint/ dirs by mtime descending, pick most recent matching sprint dir."""
    try:
        if not SPRINT_BASE.exists():
            return None
        dirs = sorted(
            (d for d in SPRINT_BASE.iterdir() if d.is_dir()),
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )
        for d in dirs:
            if sprint_matches_project(d.name):
                return d.name
    except Exception:
        pass
    return None


def read_events(sprint_id: str) -> list:
    """Read events.jsonl for a sprint, return list of dicts."""
    path = SPRINT_BASE / sprint_id / "events.jsonl"
    events = []
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return events


def read_all_statuses(sprint_id: str) -> dict:
    """Read all <role>.status files, return {role: {status, error}}."""
    result = {}
    base = SPRINT_BASE / sprint_id
    try:
        for lead in LEAD_ORDER:
            status_file = base / f"{lead}.status"
            try:
                data = json.loads(status_file.read_text())
                result[lead] = data
            except Exception:
                pass
    except Exception:
        pass
    return result


def read_gate(sprint_id: str) -> dict:
    """Read gate.json, return dict."""
    path = SPRINT_BASE / sprint_id / "gate.json"
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def current_wave_from_events(events: list) -> int:
    """Determine current wave from wave_start events."""
    wave = 0
    for ev in events:
        if ev.get("type") == "wave_start":
            w = ev.get("wave")
            if isinstance(w, int) and w > wave:
                wave = w
    return wave


def read_report_md(sprint_id: str) -> dict:
    """Parse report.md for wave completion status.
    Returns {wave_idx: 'done'|'failed'|None, 'complete': bool, 'mtime': float}."""
    import re
    path = SPRINT_BASE / sprint_id / "report.md"
    result = {"complete": False, "mtime": None}
    try:
        text = path.read_text(errors="replace")
        result["mtime"] = path.stat().st_mtime
        result["complete"] = "COMPLETE" in text and "✓" in text
        for m in re.finditer(r"##\s+Wave\s+(\d+)[^✓✗\n]*([✓✗])?", text):
            wn = int(m.group(1))
            mark = m.group(2)
            if mark == "✓":
                result[wn] = "done"
            elif mark == "✗":
                result[wn] = "failed"
            else:
                result[wn] = None
    except Exception:
        pass
    return result


PROJECT_CWD: "str | None" = None


def find_current_session() -> "str | None":
    try:
        return (SESSION_BASE / "current_session_id").read_text().strip() or None
    except Exception:
        return None


def read_session_tasks() -> list:
    """Read tasks.jsonl, return latest-status dict per task_id, sorted by task_id."""
    session_id = find_current_session()
    if not session_id: return []
    path = SESSION_BASE / session_id / "tasks.jsonl"
    by_task = {}
    try:
        for line in path.read_text().splitlines():
            if not line.strip(): continue
            try:
                e = json.loads(line)
                tid = e.get("task_id")
                if tid is None: continue
                # keep latest ts per task_id
                if tid not in by_task or e.get("ts","") > by_task[tid].get("ts",""):
                    by_task[tid] = e
                # preserve start_ts separately
                if e.get("type") == "task_start":
                    by_task.setdefault(tid, {})["start_ts"] = e.get("ts","")
            except Exception:
                pass
    except Exception:
        pass
    # Second pass: attach start_ts to all entries
    start_ts_map = {}
    try:
        for line in path.read_text().splitlines():
            if not line.strip(): continue
            try:
                e = json.loads(line)
                if e.get("type") == "task_start":
                    start_ts_map[e.get("task_id")] = e.get("ts","")
            except Exception:
                pass
    except Exception:
        pass
    result = []
    for tid, ev in sorted(by_task.items()):
        ev["start_ts"] = start_ts_map.get(tid, ev.get("ts",""))
        result.append(ev)
    return result


def read_activity_log(n: int = 3) -> list:
    """Read last n entries from activity_log.jsonl, filtered by PROJECT_CWD if set."""
    entries = []
    try:
        lines = ACTIVITY_LOG.read_text().splitlines()
        for line in reversed(lines):
            line = line.strip()
            if line:
                try:
                    e = json.loads(line)
                    if PROJECT_CWD and e.get("cwd") != PROJECT_CWD:
                        continue
                    entries.append(e)
                    if len(entries) >= n:
                        break
                except Exception:
                    pass
    except Exception:
        pass
    return entries  # most recent first


# ── Formatters ────────────────────────────────────────────────────────────────

def calc_elapsed(start_ts: str, end_ts: "str | None") -> str:
    """Returns elapsed as 'Xm' or 'ongoing'."""
    try:
        start = parse_ts(start_ts)
        end = parse_ts(end_ts) if end_ts else time.time()
        if start is None: return ""
        secs = int((end or time.time()) - start)
        if secs < 60: return f"{secs}s"
        return f"{secs // 60}m"
    except Exception:
        return ""


def progress_bar(filled: int, total: int, width: int = 20) -> str:
    if total == 0:
        pct = 0
        n = 0
    else:
        pct = int(filled / total * 100)
        n = int(filled / total * width)
    bar = "#" * n + "." * (width - n)
    return f"[{bar}]  {pct}%"


def format_elapsed(start_ts: float) -> str:
    """Format elapsed seconds as HH:MM."""
    elapsed = int(time.time() - start_ts)
    hours = elapsed // 3600
    mins = (elapsed % 3600) // 60
    return f"{hours:02d}:{mins:02d}"


def parse_ts(ts_str: str) -> float | None:
    """Parse ISO timestamp to float, return None on failure."""
    if not ts_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(ts_str.replace("Z", "+00:00") if ts_str.endswith("Z") else ts_str, fmt)
            return dt.timestamp()
        except Exception:
            pass
    try:
        return float(ts_str)
    except Exception:
        return None


def fmt_hhmm(ts_str: str) -> str:
    """Format a timestamp string as HH:MM."""
    ts = parse_ts(ts_str)
    if ts is None:
        return "??:??"
    dt = datetime.fromtimestamp(ts)
    return dt.strftime("%H:%M")


def fmt_date(ts_str: str) -> str:
    """Format timestamp as YYYY-MM-DD."""
    ts = parse_ts(ts_str)
    if ts is None:
        return "????"
    dt = datetime.fromtimestamp(ts)
    return dt.strftime("%Y-%m-%d")


# ── Render: session summary ───────────────────────────────────────────────────

def render_session_summary() -> None:
    tasks = read_session_tasks()
    if not tasks:
        out(f"  (no tasks this session)")
        return
    session_id = find_current_session() or ""
    # Extract date from session_id like "session_20260410_142300"
    parts = session_id.split("_")
    date_str = parts[1] if len(parts) > 1 else session_id[:10]
    out(f"{B}SESSION  {date_str}  [{len(tasks)} tasks]{R}")
    out()
    ICONS = {"done": f"{GR}✓{R}", "failed": f"{RD}✗{R}", "running": f"{YL}►{R}"}
    for ev in tasks:
        status = ev.get("status", "pending")
        icon = ICONS.get(status, "○")
        name = (ev.get("task_name","") or "")[:35].ljust(35)
        ttype = (ev.get("task_type","") or "")[:12].ljust(12)
        start_ts = ev.get("start_ts", ev.get("ts",""))
        end_ts = ev.get("ts","") if ev.get("type") in ("task_done","task_failed") else None
        elapsed = calc_elapsed(start_ts, end_ts)
        start_hm = fmt_hhmm(start_ts) if start_ts else "??:??"
        tid = ev.get("task_id","")
        out(f"  {tid:>3}  {icon}  {name}  {start_hm}  {ttype}  {elapsed}")


# ── Render: sprint active ─────────────────────────────────────────────────────

def render_sprint(sprint_id: str):
    events   = read_events(sprint_id)
    statuses = read_all_statuses(sprint_id)
    report   = read_report_md(sprint_id)

    cur_wave = current_wave_from_events(events)
    # If no events but report.md says complete, treat as past last wave
    if not events and report.get("complete"):
        cur_wave = max((k for k in report if isinstance(k, int)), default=0)
    wave_label = WAVE_LABELS.get(cur_wave, f"W{cur_wave}")

    out(f"{B}{CY}SPRINT  {sprint_id}  [W{cur_wave} — {wave_label}]{R}")
    out()

    # Group leads by wave
    waves: dict[int, list[str]] = {}
    for lead in LEAD_ORDER:
        w = LEAD_WAVE.get(lead, 0)
        waves.setdefault(w, []).append(lead)

    max_wave = max(waves.keys()) if waves else 3

    # Determine wave completion status
    for wn in sorted(waves.keys()):
        wlabel = WAVE_LABELS.get(wn, f"W{wn}")
        leads_in_wave = waves[wn]

        # Wave-level status
        lead_statuses_in_wave = [statuses.get(l, {}) for l in leads_in_wave]
        done_leads = [l for l in leads_in_wave if statuses.get(l, {}).get("status") == "done"]
        failed_leads = [l for l in leads_in_wave if statuses.get(l, {}).get("status") == "failed"]
        running_leads = [l for l in leads_in_wave if l in statuses and statuses[l].get("status") not in ("done", "failed")]
        waiting_leads = [l for l in leads_in_wave if l not in statuses]

        all_done = len(done_leads) == len(leads_in_wave)
        any_running = len(running_leads) > 0 or (wn == cur_wave and not all_done and len(done_leads) + len(failed_leads) < len(leads_in_wave))

        # Fall back to report.md if no .status files
        report_wave = report.get(wn)
        if all_done and not failed_leads:
            wave_icon = f"{GR}✓{R}"
        elif failed_leads or report_wave == "failed":
            wave_icon = f"{RD}✗{R}"
        elif report_wave == "done" or wn < cur_wave:
            wave_icon = f"{GR}✓{R}"
        elif wn == cur_wave:
            wave_icon = f"{YL}►{R}"
        else:
            wave_icon = "○"

        # Build lead chips
        lead_chips = []
        for lead in leads_in_wave:
            st = statuses.get(lead, {})
            status_val = st.get("status", "")
            if status_val == "done":
                icon = f"{GR}✓{R}"
            elif status_val == "failed":
                icon = f"{RD}✗{R}"
            elif lead in statuses:
                icon = f"{YL}►{R}"
            else:
                icon = "○"
            lead_chips.append(f"{lead} {icon}")

        chips_str = "  ".join(lead_chips) if lead_chips else ""
        wlabel_padded = f"W{wn} {wlabel:<8}"
        if chips_str:
            out(f"  {wlabel_padded} {wave_icon}  {chips_str}")
        else:
            out(f"  {wlabel_padded} {wave_icon}")

    out()

    # Progress bar
    completed_waves = sum(1 for wn in waves if wn < cur_wave) + (
        1 if all(statuses.get(l, {}).get("status") in ("done", "failed")
                 for l in waves.get(cur_wave, [])) else 0
    )
    total_waves = max_wave + 1

    # Elapsed from first event or report.md mtime
    elapsed_str = "00:00"
    if events:
        first_ts = parse_ts(events[0].get("ts", ""))
        if first_ts:
            elapsed_str = format_elapsed(first_ts)
    elif report.get("mtime"):
        elapsed_str = format_elapsed(report["mtime"])

    bar = progress_bar(completed_waves, total_waves)
    out(f"  {B}Progress:{R} {bar}   elapsed {elapsed_str}")


# ── Render: no sprint ─────────────────────────────────────────────────────────

def render_no_sprint():
    out(f"{B}{YL}NO SPRINT ACTIVE{R}")

    last_id = find_last_sprint()
    if last_id:
        # Try events.jsonl first, fall back to report.md mtime
        last_events = read_events(last_id)
        if last_events:
            last_ts = last_events[-1].get("ts", "")
            last_date = fmt_date(last_ts) if last_ts else "unknown"
        else:
            sprint_dir = SPRINT_BASE / last_id
            try:
                mtime = max(f.stat().st_mtime for f in sprint_dir.iterdir() if f.is_file())
                last_date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
            except Exception:
                last_date = "unknown"

        report_path = SPRINT_BASE / last_id / "report.md"
        if report_path.exists():
            try:
                first_line = report_path.read_text().splitlines()[3].strip()  # "Status: COMPLETE ✓"
                state = "completed" if "COMPLETE" in first_line else "unknown"
            except Exception:
                state = "unknown"
        else:
            last_statuses = read_all_statuses(last_id)
            all_done = bool(last_statuses) and all(
                v.get("status") in ("done", "failed") for v in last_statuses.values()
            )
            state = "completed" if all_done else "unknown"

        out(f"  Last sprint: {last_id}  ({last_date})  [{state}]")
    else:
        out("  No previous sprint found.")

    out(f"  Run /sprint to start a new sprint.")


# ── Render: events ────────────────────────────────────────────────────────────

def render_events(sprint_id: str):
    events = read_events(sprint_id)
    last5 = events[-5:] if len(events) >= 5 else events
    last5 = list(reversed(last5))  # most recent first

    out()
    out(f"{B}EVENTS{R}")
    if not last5:
        out("  (no events)")
        return

    for ev in last5:
        ts_str = fmt_hhmm(ev.get("ts", ""))
        ev_type = ev.get("type", "?")
        wave = ev.get("wave")
        name = ev.get("name", "")
        commit = ev.get("commit", "")

        parts = [f"  {ts_str}  {ev_type}"]
        if wave is not None:
            parts.append(f"[W{wave}]")
        if name:
            parts.append(name)
        if commit:
            parts.append(commit[:40])

        out("  ".join(parts))


# ── Render: recent sessions ───────────────────────────────────────────────────

def render_activity():
    entries = read_activity_log(3)

    out()
    out(f"{B}RECENT SESSIONS{R}")
    if not entries:
        out("  (no sessions logged)")
        return

    for entry in entries:
        ts_str = entry.get("ts", "")
        date_str = fmt_date(ts_str) if ts_str else "????"
        commit = entry.get("commit", "(no commit)")
        changed = entry.get("changed", [])
        tasks = entry.get("tasks", [])

        out(f"  {date_str}  {commit}")

        if changed:
            if len(changed) <= 2:
                files_str = "  ".join(changed)
            else:
                files_str = "  ".join(changed[:2]) + f"  (+{len(changed) - 2} more)"
            out(f"    files: {files_str}")

        if tasks:
            tasks_str = "  ".join(str(t) for t in tasks[:2])
            out(f"    tasks: {tasks_str}")


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    w = term_width()
    # Clear screen
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

    # Header
    out(f"{B}{CY}+-- CAF DASHBOARD {'-' * max(0, w - 19)}+{R}")
    out()

    sprint_id = find_active_sprint()
    if sprint_id:
        render_sprint(sprint_id)
        render_events(sprint_id)
        out()
        out(f"{B}SESSION{R}")
        render_session_summary()
    else:
        out(f"{B}SESSION SUMMARY{R}")
        out()
        render_session_summary()

    render_activity()

    out()
    now = datetime.now().strftime("%H:%M:%S")
    out(f"  {now}  (refreshes every 5s)")


def main_loop(poll: int = 5):
    while True:
        try:
            render()
        except Exception as e:
            sys.stdout.write("\033[2J\033[H")
            print(f"render error: {e}")
        time.sleep(poll)


if __name__ == "__main__":
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--cwd" and i + 1 < len(args):
            PROJECT_CWD = args[i + 1]
            i += 2
        else:
            i += 1
    main_loop()
