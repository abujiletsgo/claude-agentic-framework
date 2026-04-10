#!/usr/bin/env python3
"""
CAF Activity Report — always-on report panel.

Three modes: sprint (active sprint detected), orchestrate (/tmp/caf_plan.md recent), idle.
Polls every 5s. stdlib only.

Usage: python3 dashboard/activity_report.py [poll_seconds]
"""
import sys, os, json, time, shutil
from pathlib import Path
from datetime import datetime, timezone

# ── ANSI ──────────────────────────────────────────────────────────────────────
R  = "\033[0m"
B  = "\033[1m"
CY = "\033[96m"
GR = "\033[92m"
YL = "\033[93m"
RD = "\033[91m"
M  = "\033[95m"
D  = "\033[2m"

# ── Constants ─────────────────────────────────────────────────────────────────
SPRINT_DIR   = Path("/tmp/caf_sprint")
PLAN_FILE    = Path("/tmp/caf_plan.md")
ORCH_STATUS  = Path("/tmp/caf_orch_status.jsonl")
DATA_DIR     = Path.home() / ".claude" / "data"
COMPLETIONS  = DATA_DIR / "task_completions.jsonl"
ALERTS_FILE  = DATA_DIR / "subagent_alerts.jsonl"
ACTIVITY_LOG = DATA_DIR / "activity_log.jsonl"
SESSION_BASE = Path("/tmp/caf_session")
TASK_ID: "int | None" = None  # set from --task arg at bottom

WAVE_LABELS = {0: "PLAN", 1: "BUILD", 2: "VALIDATE", 3: "SHIP"}
LEAD_ORDER  = [
    "planning-lead", "engineering-lead", "frontend-lead", "review-lead",
    "qa-lead", "security-lead", "release-lead", "docs-lead",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def W() -> int:
    return shutil.get_terminal_size((100, 40)).columns

def trunc(s: str, width: int = 0) -> str:
    w = width or (W() - 2)
    return s[:w] if len(s) > w else s

def pr(s: str = "") -> None:
    print(trunc(s))

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def fmt_ts(ts_str: str) -> str:
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except Exception:
        return ts_str[:5] if ts_str else "??:??"

# ── Session/task readers ──────────────────────────────────────────────────────

def find_current_session() -> "str | None":
    try:
        return (SESSION_BASE / "current_session_id").read_text().strip() or None
    except Exception:
        return None

def read_session_task(task_id: int) -> dict:
    """Return task metadata dict from tasks.jsonl for given task_id."""
    session_id = find_current_session()
    if not session_id:
        return {}
    path = SESSION_BASE / session_id / "tasks.jsonl"
    task_start = {}
    task_end = {}
    try:
        for line in path.read_text().splitlines():
            if not line.strip(): continue
            try:
                e = json.loads(line)
                if e.get("task_id") == task_id:
                    if e.get("type") == "task_start":
                        task_start = e
                    elif e.get("type") in ("task_done", "task_failed"):
                        task_end = e
            except Exception:
                pass
    except Exception:
        pass
    return {**task_start, **task_end, "end_ts": task_end.get("ts")}

def read_orch_status_for_task(task_meta: dict) -> list:
    """Filter /tmp/caf_orch_status.jsonl to this task's time window."""
    start_ts = task_meta.get("ts", "")
    end_ts = task_meta.get("end_ts")
    entries = []
    try:
        for line in ORCH_STATUS.read_text(errors="replace").splitlines():
            if not line.strip(): continue
            try:
                e = json.loads(line)
                ts = e.get("ts", "")
                if start_ts and ts < start_ts:
                    continue
                if end_ts and ts > end_ts:
                    continue
                entries.append(e)
            except Exception:
                pass
    except Exception:
        pass
    return entries

# ── Data readers ──────────────────────────────────────────────────────────────

def sprint_matches_project(sprint_id: str) -> bool:
    """True if sprint belongs to PROJECT_CWD (or no filter, or no cwd file in sprint)."""
    if not PROJECT_CWD:
        return True
    try:
        cwd = (SPRINT_DIR / sprint_id / "cwd").read_text().strip()
        return cwd == PROJECT_CWD
    except Exception:
        return False  # no cwd file = unknown project, hide when filtering


def find_current_sprint() -> "str | None":
    """Return sprint_id if active sprint dir exists and matches current project."""
    id_file = SPRINT_DIR / "current_sprint_id"
    try:
        sprint_id = id_file.read_text().strip()
        if sprint_id and (SPRINT_DIR / sprint_id).is_dir() and sprint_matches_project(sprint_id):
            return sprint_id
    except Exception:
        pass
    return None

def read_pm_plan(sprint_id: str, n: int = 15) -> list:
    """First n lines of pm_plan.md for the sprint."""
    path = SPRINT_DIR / sprint_id / "pm_plan.md"
    try:
        lines = path.read_text(errors="replace").splitlines()
        return lines[:n]
    except Exception:
        return []

def read_sprint_events(sprint_id: str) -> list:
    """All events from events.jsonl."""
    path = SPRINT_DIR / sprint_id / "events.jsonl"
    events = []
    try:
        for line in path.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                pass
    except Exception:
        pass
    return events

def read_lead_result(sprint_id: str, role: str) -> list:
    """First 3 non-empty lines of results/<role>_result.md."""
    path = SPRINT_DIR / sprint_id / "results" / f"{role}_result.md"
    try:
        lines = [l for l in path.read_text(errors="replace").splitlines() if l.strip()]
        return lines[:3]
    except Exception:
        return []

def read_all_statuses(sprint_id: str) -> dict:
    """role -> {status, error} from <role>.status files."""
    statuses = {}
    sprint_path = SPRINT_DIR / sprint_id
    for role in LEAD_ORDER:
        status_file = sprint_path / f"{role}.status"
        try:
            data = json.loads(status_file.read_text())
            statuses[role] = data
        except Exception:
            pass
    return statuses

def read_gate(sprint_id: str) -> dict:
    """Read gate.json -> {unlocked_waves: [...]}."""
    path = SPRINT_DIR / sprint_id / "gate.json"
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}

def read_orchestrate_plan() -> "str | None":
    """Return plan text if /tmp/caf_plan.md or /tmp/caf_orch_status.jsonl exists and mtime < 4h."""
    try:
        # Check orch status file first (written per-wave, more current)
        if ORCH_STATUS.exists():
            age = now_utc().timestamp() - ORCH_STATUS.stat().st_mtime
            if age <= 4 * 3600:
                # Return plan file content if available, else a stub
                if PLAN_FILE.exists():
                    return PLAN_FILE.read_text(errors="replace")
                return "# Orchestration in progress\n(plan file not found)"
        # Fall back to plan file alone
        if not PLAN_FILE.exists():
            return None
        age = now_utc().timestamp() - PLAN_FILE.stat().st_mtime
        if age > 4 * 3600:
            return None
        return PLAN_FILE.read_text(errors="replace")
    except Exception:
        return None

def read_task_completions(n: int = 10) -> list:
    """Last n entries from task_completions.jsonl, filtered by PROJECT_CWD if set."""
    entries = []
    try:
        for line in COMPLETIONS.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                if PROJECT_CWD and e.get("cwd") and e.get("cwd") != PROJECT_CWD:
                    continue
                entries.append(e)
            except Exception:
                pass
    except Exception:
        pass
    return entries[-n:]

def read_alerts(n: int = 3) -> list:
    """Last n entries from subagent_alerts.jsonl."""
    entries = []
    try:
        for line in ALERTS_FILE.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
    except Exception:
        pass
    return entries[-n:]

def read_activity_log(n: int = 3) -> list:
    """Last n entries from activity_log.jsonl, filtered by PROJECT_CWD if set."""
    entries = []
    try:
        for line in ACTIVITY_LOG.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                if PROJECT_CWD and e.get("cwd") != PROJECT_CWD:
                    continue
                entries.append(e)
            except Exception:
                pass
    except Exception:
        pass
    return entries[-n:]

# ── Section printers ──────────────────────────────────────────────────────────

def print_header(title: str) -> None:
    w = W()
    bar = "═" * w
    pr(f"{B}{CY}{bar}{R}")
    pr(f"{B}{CY}  {title}{R}")
    pr(f"{B}{CY}{bar}{R}")
    pr()

def print_section(label: str) -> None:
    pr(f"{B}{YL}── {label} {R}")

def print_plan_lines(lines: list) -> None:
    for line in lines:
        pr(f"  {line}")
    pr()

def print_completions(entries: list) -> None:
    if not entries:
        pr(f"  {D}(none){R}")
        pr()
        return
    for e in entries:
        ts   = fmt_ts(e.get("timestamp", ""))
        subj = e.get("task_subject", "") or e.get("task_id", "")
        who  = e.get("teammate_name", "") or e.get("agent_name", "")
        tid  = e.get("task_id", "")
        # Show task_id as "who" if teammate_name blank (API limitation)
        who_str = f"{D}[{who}]{R}" if who else (f"{D}[task {tid}]{R}" if tid else "")
        pr(f"  {GR}✓{R}  {D}{ts}{R}  {subj}  {who_str}")
    pr()

def print_alerts(entries: list) -> None:
    if not entries:
        pr(f"  {D}(none){R}")
    for e in entries:
        ts    = fmt_ts(e.get("timestamp", ""))
        agent = e.get("agent_name", "")
        types = ", ".join(e.get("anomaly_types", []))
        exc   = (e.get("error_excerpt") or "")[:80]
        pr(f"  {RD}!{R}  {D}{ts}{R}  {M}{agent}{R}  {YL}{types}{R}")
        if exc:
            pr(f"      {D}{exc}{R}")
    pr()

def print_events(events: list, n: int = 8) -> None:
    recent = events[-n:]
    if not recent:
        pr(f"  {D}(none){R}")
    for ev in recent:
        ts     = fmt_ts(ev.get("ts", ""))
        etype  = ev.get("type", "")
        wave   = ev.get("wave")
        name   = ev.get("name", ev.get("commit", ""))
        detail = f"W{wave}" if wave is not None else ""
        if name:
            detail = f"{detail}  {name}" if detail else name
        pr(f"  {D}{ts}{R}  {CY}{etype}{R}  {detail}")
    pr()

def print_activity_sessions(entries: list) -> None:
    if not entries:
        pr(f"  {D}(none){R}")
        return
    for e in entries:
        ts      = e.get("ts", "")[:10]
        commit  = e.get("commit", "")
        changed = e.get("changed", [])
        tasks   = e.get("tasks", [])
        pr(f"  {B}{CY}{ts}{R}  {commit[:60]}")
        if changed:
            shown = "  ".join(changed[:3])
            extra = f"  (+{len(changed)-3} more)" if len(changed) > 3 else ""
            pr(f"    {D}files: {shown}{extra}{R}")
        if tasks:
            for t in tasks[:2]:
                pr(f"    {GR}✓{R}  {D}{t[:70]}{R}")
        pr()

# ── Wave/lead status for sprint mode ─────────────────────────────────────────

def role_wave(role: str) -> int:
    """Map role to wave index based on LEAD_ORDER position."""
    wave_map = {
        "planning-lead":    0,
        "engineering-lead": 1,
        "frontend-lead":    1,
        "review-lead":      1,
        "qa-lead":          2,
        "security-lead":    2,
        "release-lead":     3,
        "docs-lead":        3,
    }
    return wave_map.get(role, 1)

def print_waves(sprint_id: str, statuses: dict) -> None:
    gate = read_gate(sprint_id)
    unlocked = set(gate.get("unlocked_waves", [0]))

    waves: dict = {}
    for role in LEAD_ORDER:
        w = role_wave(role)
        waves.setdefault(w, []).append(role)

    for wave_idx in sorted(waves.keys()):
        label = WAVE_LABELS.get(wave_idx, f"W{wave_idx}")
        roles_in_wave = waves[wave_idx]

        known = [statuses[r] for r in roles_in_wave if r in statuses]
        all_done    = bool(known) and all(s.get("status") == "done"   for s in known)
        any_failed  = any(s.get("status") == "failed" for s in known)
        any_running = wave_idx in unlocked and not all_done and not any_failed

        if all_done:
            wave_color = GR
            wave_mark  = "✓"
        elif any_failed:
            wave_color = RD
            wave_mark  = "✗"
        elif any_running:
            wave_color = YL
            wave_mark  = "▶"
        else:
            wave_color = D
            wave_mark  = "○"

        pr(f"  {wave_color}{B}WAVE {wave_idx} — {label}  {wave_mark}{R}")

        for role in roles_in_wave:
            st = statuses.get(role, {})
            status_str = st.get("status", "")
            err        = st.get("error", "")

            if status_str == "done":
                icon  = f"{GR}[DONE]{R}   "
            elif status_str == "failed":
                icon  = f"{RD}[FAILED]{R} "
            elif wave_idx in unlocked:
                icon  = f"{YL}[running]{R}"
            else:
                icon  = f"{D}[waiting]{R}"

            pr(f"    {icon}  {role}")
            if err:
                pr(f"           {RD}{err[:70]}{R}")

            # Show first 3 lines of result
            result_lines = read_lead_result(sprint_id, role)
            for rl in result_lines:
                pr(f"           {D}{rl}{R}")
        pr()

# ── Task mode renderer ────────────────────────────────────────────────────────

def render_task(task_id: int) -> None:
    task_meta = read_session_task(task_id)
    task_name = task_meta.get("task_name", f"task {task_id}")
    task_type = task_meta.get("task_type", "other")
    sprint_id = task_meta.get("sprint_id")

    print_header(f"TASK {task_id} — {task_name}")

    if task_type == "sprint" and sprint_id:
        # reuse existing sprint render
        statuses = read_all_statuses(sprint_id)
        events = read_sprint_events(sprint_id)
        alerts = read_alerts(n=3)
        plan_lines = read_pm_plan(sprint_id, n=15)
        print_section("PLAN")
        print_plan_lines(plan_lines)
        print_section("WAVE STATUS")
        print_waves(sprint_id, statuses)
        print_section("EVENTS")
        print_events(events, n=8)
        print_section("ALERTS")
        print_alerts(alerts)
    else:
        # orchestrate mode filtered to task window
        orch_waves = read_orch_status_for_task(task_meta)
        completions = read_task_completions(n=10)
        alerts = read_alerts(n=3)

        # show plan if available
        plan_text = read_orchestrate_plan()
        if plan_text:
            print_section("PLAN")
            print_plan_lines(plan_text.splitlines()[:15])

        print_section("AGENT WAVES")
        print_orch_waves(orch_waves)
        print_section("COMPLETED TASKS")
        print_completions(completions)
        print_section("ALERTS")
        print_alerts(alerts)


# ── Mode renderers ────────────────────────────────────────────────────────────

def render_sprint(sprint_id: str) -> None:
    statuses = read_all_statuses(sprint_id)
    events   = read_sprint_events(sprint_id)
    alerts   = read_alerts(n=3)
    plan_lines = read_pm_plan(sprint_id, n=15)

    print_header(f"AGENT REPORT — {sprint_id}")

    print_section("PLAN")
    print_plan_lines(plan_lines)

    print_section("WAVE STATUS")
    print_waves(sprint_id, statuses)

    print_section("EVENTS")
    print_events(events, n=8)

    print_section("ALERTS")
    print_alerts(alerts)


def read_orch_status() -> list:
    """Read /tmp/caf_orch_status.jsonl — live orchestrate wave updates."""
    entries = []
    try:
        for line in ORCH_STATUS.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
    except Exception:
        pass
    return entries


def print_orch_waves(entries: list) -> None:
    """Print live orchestrate wave status from caf_orch_status.jsonl."""
    if not entries:
        pr(f"  {D}(no wave updates yet){R}")
        pr()
        return
    for e in entries:
        ts      = fmt_ts(e.get("ts", ""))
        wave    = e.get("wave", "")
        agent   = e.get("agent", "")
        status  = e.get("status", "")
        summary = e.get("summary", "")

        if status == "running":
            icon = f"{YL}►{R}"
        elif status == "done":
            icon = f"{GR}✓{R}"
        elif status == "failed":
            icon = f"{RD}✗{R}"
        else:
            icon = f"{D}○{R}"

        wave_label = f"W{wave}" if wave != "" else ""
        pr(f"  {icon}  {D}{ts}{R}  {M}{agent}{R}  {D}{wave_label}{R}")
        if summary:
            pr(f"       {D}{summary[:80]}{R}")
    pr()


def render_orchestrate(plan_text: str) -> None:
    orch_waves  = read_orch_status()
    completions = read_task_completions(n=10)
    alerts      = read_alerts(n=3)
    plan_lines  = plan_text.splitlines()[:15]

    print_header("AGENT REPORT — orchestrate")

    print_section("PLAN")
    print_plan_lines(plan_lines)

    print_section("AGENT WAVES")
    print_orch_waves(orch_waves)

    print_section("COMPLETED TASKS")
    print_completions(completions)

    print_section("ALERTS")
    print_alerts(alerts)


def render_idle() -> None:
    completions = read_task_completions(n=8)
    sessions    = read_activity_log(n=3)

    print_header("AGENT REPORT — idle")

    pr(f"  {D}No active orchestration.{R}")
    pr()

    print_section("RECENT TASKS")
    print_completions(completions)

    print_section("RECENT SESSIONS")
    print_activity_sessions(sessions)


# ── Main render loop ──────────────────────────────────────────────────────────

def render() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

    if TASK_ID is not None:
        render_task(TASK_ID)
    else:
        # existing logic unchanged
        sprint_id = find_current_sprint()
        if sprint_id:
            render_sprint(sprint_id)
        else:
            plan_text = read_orchestrate_plan()
            if plan_text is not None:
                render_orchestrate(plan_text)
            else:
                render_idle()

    # Footer
    ts = now_utc().strftime("%H:%M UTC")
    pr(f"{D}{'─' * (W()-2)}{R}")
    pr(f"  {D}○  {ts}  (refresh every 5s){R}")


PROJECT_CWD: "str | None" = None


def main(poll: int = 5) -> None:
    while True:
        try:
            render()
        except Exception as e:
            sys.stdout.write("\033[2J\033[H")
            print(f"{RD}render error: {e}{R}")
        time.sleep(poll)


if __name__ == "__main__":
    args = sys.argv[1:]
    poll = 5
    i = 0
    while i < len(args):
        if args[i] == "--cwd" and i + 1 < len(args):
            PROJECT_CWD = args[i + 1]; i += 2
        elif args[i] == "--task" and i + 1 < len(args):
            TASK_ID = int(args[i + 1]); poll = 3; i += 2
        else:
            try: poll = int(args[i])
            except ValueError: pass
            i += 1
    try:
        main(poll=poll)
    except KeyboardInterrupt:
        print()
