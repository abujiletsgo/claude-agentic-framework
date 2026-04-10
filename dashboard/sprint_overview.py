#!/usr/bin/env python3
"""
CAF Sprint Overview — compact status panel for bottom-right corner.
Shows overall progress bar, wave status, elapsed time.
"""
import sys, os, json, time, shutil
from pathlib import Path
from datetime import datetime, UTC

R  = "\033[0m"
B  = "\033[1m"
D  = "\033[2m"
CY = "\033[36m"
GR = "\033[32m"
YL = "\033[33m"
RD = "\033[31m"
M  = "\033[35m"
BL = "\033[34m"

def cols(): return shutil.get_terminal_size((80, 20)).columns

def bar(pct, w=None):
    w = w or max(8, cols() - 10)
    filled = int(w * max(0, min(100, pct)) / 100)
    return f"{GR}{'█' * filled}{D}{'░' * (w - filled)}{R}"

def read_status(sprint_id: str) -> dict:
    try:
        return json.loads(Path(f"/tmp/caf_sprint/{sprint_id}/status.json").read_text())
    except Exception:
        return {}

WAVE_COLOR = {0: BL, 1: CY, 2: M, 3: GR}
WAVE_LABEL = {0: "PLAN", 1: "BUILD", 2: "VALIDATE", 3: "SHIP"}

DEMO_WAVES = [
    (0, "PLAN",     ["planning-lead"],                                   "done"),
    (1, "BUILD",    ["engineering-lead"],                                 "done"),
    (2, "VALIDATE", ["review-lead", "qa-lead", "security-lead"],         "done"),
    (3, "SHIP",     ["release-lead", "infra-lead", "docs-lead"],         "done"),
]


def render(sprint_id: str, status: dict, elapsed_s: int):
    w = cols()
    leads = {k: v for k, v in status.items() if isinstance(v, dict)}
    n_done    = sum(1 for v in leads.values() if v.get("status") == "done")
    n_running = sum(1 for v in leads.values() if v.get("status") == "running")
    n_waiting = sum(1 for v in leads.values() if v.get("status") == "waiting")
    n_failed  = sum(1 for v in leads.values() if v.get("status") == "failed")
    total     = max(len(leads), 1)
    avg_pct   = sum(v.get("pct", 0) for v in leads.values()) // total

    elapsed_str = f"{elapsed_s//60:02d}:{elapsed_s%60:02d}"
    ts = datetime.now(UTC).strftime("%H:%M")

    sys.stdout.write("\033[2J\033[H")

    # Header
    print(f"{B}{CY}{'━' * w}{R}")
    print(f"{B}{CY}  OVERVIEW{R}  {D}{sprint_id}  {elapsed_str}  {ts}{R}")
    print()

    # Overall bar
    print(f"  {bar(avg_pct)}  {B}{avg_pct:3d}%{R}")
    parts = []
    if n_done:    parts.append(f"{GR}✓{n_done}{R}")
    if n_running: parts.append(f"{YL}►{n_running}{R}")
    if n_waiting: parts.append(f"{D}○{n_waiting}{R}")
    if n_failed:  parts.append(f"{RD}✗{n_failed}{R}")
    print(f"  {'  '.join(parts)}")
    print()

    # Wave rows
    waves = sorted(set(v.get("wave", 0) for v in leads.values())) if leads else range(4)
    for wn in waves:
        wc = WAVE_COLOR.get(wn, CY)
        wl = WAVE_LABEL.get(wn, f"W{wn}")
        wave_leads = [v for v in leads.values() if isinstance(v, dict) and v.get("wave") == wn]
        if not wave_leads:
            print(f"  {D}W{wn} {wl}{R}")
            continue
        all_done = all(v.get("status") == "done" for v in wave_leads)
        any_fail = any(v.get("status") == "failed" for v in wave_leads)
        any_run  = any(v.get("status") == "running" for v in wave_leads)
        icon = f"{GR}✓{R}" if all_done else (f"{RD}✗{R}" if any_fail else (f"{YL}►{R}" if any_run else f"{D}○{R}"))
        wpct = sum(v.get("pct", 0) for v in wave_leads) // len(wave_leads)
        print(f"  {icon} {wc}{wl}{R}  {D}{wpct}%{R}")

    if leads and n_done == len(leads):
        print()
        print(f"  {B}{GR}✓ ALL COMPLETE{R}")
    elif n_failed:
        print(f"  {B}{RD}✗ BLOCKED{R}")

    print()
    print(f"{D}{'─' * w}{R}", end="", flush=True)


def run_demo():
    start = time.time()
    # Build up a status dict gradually matching sprint_dashboard demo cadence
    demo_status = {
        "planning-lead":    {"status": "done",    "pct": 100, "wave": 0},
        "engineering-lead": {"status": "running", "pct": 52,  "wave": 1},
        "review-lead":      {"status": "waiting", "pct": 0,   "wave": 2},
        "qa-lead":          {"status": "running", "pct": 40,  "wave": 2},
        "security-lead":    {"status": "waiting", "pct": 0,   "wave": 2},
        "release-lead":     {"status": "waiting", "pct": 0,   "wave": 3},
        "infra-lead":       {"status": "waiting", "pct": 0,   "wave": 3},
        "docs-lead":        {"status": "waiting", "pct": 0,   "wave": 3},
    }
    snapshots = [
        (5, demo_status),
        (5, {**demo_status,
             "engineering-lead": {"status": "running", "pct": 72, "wave": 1},
             "qa-lead":          {"status": "running", "pct": 60, "wave": 2}}),
        (5, {**demo_status,
             "engineering-lead": {"status": "done",    "pct": 100, "wave": 1},
             "review-lead":      {"status": "running", "pct": 35,  "wave": 2},
             "qa-lead":          {"status": "running", "pct": 80,  "wave": 2},
             "security-lead":    {"status": "running", "pct": 20,  "wave": 2}}),
        (0, {k: {"status": "done", "pct": 100, "wave": v["wave"]}
             for k, v in demo_status.items()}),
    ]
    for pause, snap in snapshots:
        render("sprint-demo-001", snap, int(time.time() - start))
        if pause > 0:
            for remaining in range(pause, 0, -1):
                sys.stdout.write(f"\r  {D}updating in {remaining}s...{R}  ")
                sys.stdout.flush()
                time.sleep(1)


def run_live(sprint_id: str, poll: int = 3):
    start = time.time()
    while True:
        status = read_status(sprint_id)
        render(sprint_id, status, int(time.time() - start))
        leads = [v for v in status.values() if isinstance(v, dict)]
        if leads and all(v.get("status") in ("done", "failed") for v in leads):
            break
        for remaining in range(poll, 0, -1):
            sys.stdout.write(f"\r  {D}updating in {remaining}s...{R}  ")
            sys.stdout.flush()
            time.sleep(1)


if __name__ == "__main__":
    sprint_id = sys.argv[1] if len(sys.argv) > 1 else "demo"
    if sprint_id == "demo":
        run_demo()
    else:
        run_live(sprint_id, poll=int(sys.argv[2]) if len(sys.argv) > 2 else 3)
