#!/usr/bin/env python3
"""
CAF Sprint Dashboard — right-pane summary display.

Live mode:  python3 dashboard/sprint_dashboard.py <sprint_id>
Demo mode:  python3 dashboard/sprint_dashboard.py demo
"""
import sys, os, re, json, time, shutil
from pathlib import Path
from datetime import datetime

# ── ANSI ──────────────────────────────────────────────────────────────────────
R  = "\033[0m"
B  = "\033[1m"
D  = "\033[2m"
CY = "\033[36m"
GR = "\033[32m"
YL = "\033[33m"
RD = "\033[31m"
BL = "\033[34m"
M  = "\033[35m"

STRIP_ANSI = re.compile(r'\033\[[0-9;]*m')

def cols():    return shutil.get_terminal_size((100, 40)).columns
def cls():     sys.stdout.write("\033[2J\033[H"); sys.stdout.flush()
def rule(c="─", color=D): print(f"{color}{c * cols()}{R}")

def bar(pct, w=28):
    filled = int(w * max(0, min(100, pct)) / 100)
    return f"{GR}{'█' * filled}{D}{'░' * (w - filled)}{R}"

STATUS_CHIP = {
    "done":    f"{B}{GR} ✓ DONE    {R}",
    "running": f"{B}{YL} ► ACTIVE  {R}",
    "waiting": f"{D} ○ WAITING {R}",
    "failed":  f"{B}{RD} ✗ FAILED  {R}",
}
WAVE_COLOR = [BL, CY, M, GR]


# ── Log parser ────────────────────────────────────────────────────────────────

def read_log(sprint_id: str, role: str, n: int = 60) -> list[str]:
    f = Path(f"/tmp/caf_sprint/{sprint_id}/logs/{role}.log")
    try:
        lines = f.read_text(errors="replace").splitlines()
        return [STRIP_ANSI.sub("", l) for l in lines if l.strip()][-n:]
    except Exception:
        return []

def parse_log(lines: list[str]) -> dict:
    done, next_up = [], []
    current = None
    summary = None
    for raw in lines:
        l = raw.strip()
        if l.startswith("✓ "):
            done.append(l)
        elif l.startswith("► "):
            current = l
        elif l.startswith("→ ") or (l.startswith("  ") and l.strip()):
            t = l.lstrip()
            if not t.startswith("✓") and not t.startswith("►"):
                next_up.append(t)
        if ("DONE" in l or "FAILED" in l) and len(l) < 100 and "━" not in l:
            summary = l
    return {"done": done[-4:], "current": current, "next": next_up[:3], "summary": summary}


# ── IPC reader ────────────────────────────────────────────────────────────────

def read_status(sprint_id: str) -> dict:
    try:
        return json.loads(Path(f"/tmp/caf_sprint/{sprint_id}/status.json").read_text())
    except Exception:
        return {}


# ── Renderer ──────────────────────────────────────────────────────────────────

ROLE_ORDER = ["planning-lead", "engineering-lead", "review-lead", "qa-lead",
              "security-lead", "release-lead", "infra-lead", "docs-lead"]

def render_lead(role: str, info: dict, parsed: dict):
    status = info.get("status", "waiting")
    pct    = info.get("pct", 0)
    wave   = info.get("wave", 0)
    wc     = WAVE_COLOR[min(wave, 3)]
    sc     = {" done": GR, "running": YL, "waiting": D, "failed": RD}.get(status, "")

    # Role + wave + status chip
    chip = STATUS_CHIP.get(status, f" {status} ")
    print(f"  {sc}{B}{role:<22}{R}  {wc}{D}W{wave}{R}  {chip}")

    # Progress bar
    pc = GR if status == "done" else (YL if status == "running" else D)
    print(f"  {bar(pct)}  {pc}{B}{pct:3d}%{R}")

    # Current task
    if parsed["current"] and status == "running":
        print(f"  {YL}{parsed['current']}{R}")

    # Accomplished (last 3)
    for t in parsed["done"][-3:]:
        print(f"  {GR}{t}{R}")

    # Waiting message
    if status == "waiting" and not parsed["done"]:
        print(f"  {D}  waiting for prior wave to complete{R}")
    elif status == "running" and not parsed["done"] and not parsed["current"]:
        print(f"  {D}  initializing...{R}")

    # Coming next (2 items)
    for t in parsed["next"][:2]:
        print(f"  {D}  → {t}{R}")

    # Final output line
    if parsed["summary"] and status in ("done", "failed"):
        print(f"  {D}└─ {parsed['summary']}{R}")

    rule()


def render_all(sprint_id: str, status_data: dict, parsed_logs: dict, elapsed_s: int):
    cls()
    w = cols()
    ts = datetime.utcnow().strftime("%H:%M:%S UTC")
    elapsed_str = f"{elapsed_s//60:02d}:{elapsed_s%60:02d}"

    # Header
    print(f"{B}{CY}{'━' * w}{R}")
    title = f"  CAF SPRINT  {sprint_id}"
    right = f"{D}elapsed {elapsed_str}   {ts}  {R}"
    # crude right-align (ANSI codes don't count for width)
    pad = max(0, w - len(title) - 24)
    print(f"{B}{CY}{title}{' ' * pad}{right}")
    print(f"{B}{CY}{'━' * w}{R}")
    print()

    if not status_data:
        print(f"  {D}No leads started yet — waiting for wave 0...{R}")
        print()
        return

    roles = [r for r in ROLE_ORDER if r in status_data]
    for role in roles:
        render_lead(role, status_data[role], parsed_logs.get(role, {"done":[],"current":None,"next":[],"summary":None}))

    # Overall summary bar
    leads = [v for v in status_data.values() if isinstance(v, dict)]
    n_done    = sum(1 for v in leads if v.get("status") == "done")
    n_running = sum(1 for v in leads if v.get("status") == "running")
    n_waiting = sum(1 for v in leads if v.get("status") == "waiting")
    n_failed  = sum(1 for v in leads if v.get("status") == "failed")
    avg_pct   = sum(v.get("pct", 0) for v in leads) // max(len(leads), 1)

    print()
    print(f"  {B}OVERALL{R}  {bar(avg_pct, 32)}  {B}{avg_pct:3d}%{R}")
    parts = []
    if n_done:    parts.append(f"{GR}✓ {n_done} done{R}")
    if n_running: parts.append(f"{YL}► {n_running} active{R}")
    if n_waiting: parts.append(f"{D}○ {n_waiting} waiting{R}")
    if n_failed:  parts.append(f"{RD}✗ {n_failed} failed{R}")
    print("  " + "   ".join(parts))

    if leads and n_done == len(leads):
        print()
        print(f"  {B}{GR}  ✓ ALL WAVES COMPLETE — ready to ship{R}")
    elif n_failed:
        print(f"  {B}{RD}  ✗ SPRINT BLOCKED — {n_failed} lead(s) failed{R}")

    print()
    rule("━", CY)


# ── Demo snapshots ────────────────────────────────────────────────────────────

DEMO = [
    # (pause_seconds, status_dict, {role: parsed_log_dict})
    (5, {
        "planning-lead":    {"status":"done",    "pct":100, "wave":0},
        "engineering-lead": {"status":"running", "pct":52,  "wave":1},
        "review-lead":      {"status":"waiting", "pct":0,   "wave":2},
        "qa-lead":          {"status":"running", "pct":40,  "wave":2},
        "security-lead":    {"status":"waiting", "pct":0,   "wave":3},
        "release-lead":     {"status":"waiting", "pct":0,   "wave":3},
        "infra-lead":       {"status":"waiting", "pct":0,   "wave":3},
        "docs-lead":        {"status":"waiting", "pct":0,   "wave":3},
    }, {
        "planning-lead":    {"done":["✓ reviewed existing auth design (middleware.py, session.py)",
                                    "✓ identified 3 migration risks (token leakage, replay, clock skew)",
                                    "✓ drafted ADR-012: JWT RS256 selected",
                                    "✓ validated against OWASP Top-10 auth checklist"],
                             "current":None, "next":[],
                             "summary":"ADR-012 written. JWT RS256 selected. 3 risks mitigated in plan."},
        "engineering-lead": {"done":["✓ read ADR-012 and migration plan",
                                     "✓ scaffolded auth/jwt_handler.py (sign, verify, refresh)",
                                     "✓ updated auth/middleware.py → replaced session lookup with JWT verify"],
                             "current":"► implementing token validation (jwt_handler.py:validate_token)",
                             "next":["write unit tests for jwt_handler.py", "run full test suite"],
                             "summary":None},
        "review-lead":      {"done":[], "current":None,
                             "next":["review auth/jwt_handler.py diff",
                                     "check token expiry + refresh edge cases",
                                     "verify no secrets in source"],
                             "summary":None},
        "qa-lead":          {"done":["✓ booted test environment (docker-compose up)",
                                     "✓ E2E: login flow → PASS",
                                     "✓ E2E: valid token accepted → PASS"],
                             "current":"► running E2E: token refresh flow (attempt 2/3)",
                             "next":["E2E: expired token rejection", "E2E: logout + token invalidation"],
                             "summary":None},
        "security-lead":    {"done":[], "current":None,
                             "next":["scan dependencies"], "summary":None},
        "release-lead":     {"done":[], "current":None,
                             "next":["tag v2.1.0"], "summary":None},
        "infra-lead":       {"done":[], "current":None,
                             "next":["update terraform"], "summary":None},
        "docs-lead":        {"done":[], "current":None,
                             "next":["update API docs"], "summary":None},
    }),
    (5, {
        "planning-lead":    {"status":"done",    "pct":100, "wave":0},
        "engineering-lead": {"status":"running", "pct":72,  "wave":1},
        "review-lead":      {"status":"waiting", "pct":0,   "wave":2},
        "qa-lead":          {"status":"running", "pct":60,  "wave":2},
        "security-lead":    {"status":"waiting", "pct":0,   "wave":3},
        "release-lead":     {"status":"waiting", "pct":0,   "wave":3},
        "infra-lead":       {"status":"waiting", "pct":0,   "wave":3},
        "docs-lead":        {"status":"waiting", "pct":0,   "wave":3},
    }, {
        "planning-lead":    {"done":["✓ reviewed auth design","✓ 3 risks identified",
                                    "✓ ADR-012: JWT RS256","✓ OWASP validated"],
                             "current":None,"next":[],
                             "summary":"ADR-012 written. JWT RS256. 3 risks mitigated."},
        "engineering-lead": {"done":["✓ scaffolded auth/jwt_handler.py",
                                     "✓ updated auth/middleware.py",
                                     "✓ implemented validate_token() + refresh_token()"],
                             "current":"► writing unit tests (12 cases, 9/12 passing)",
                             "next":["fix 3 failing tests (clock skew edge case)","run full suite"],
                             "summary":None},
        "review-lead":      {"done":[],"current":None,
                             "next":["review jwt_handler.py diff","check expiry edge cases"],
                             "summary":None},
        "qa-lead":          {"done":["✓ login flow → PASS","✓ valid token accepted → PASS",
                                     "✓ token refresh → PASS"],
                             "current":"► E2E: expired token rejection test",
                             "next":["logout + invalidation","regression: 14 existing session tests"],
                             "summary":None},
        "security-lead":    {"done":[], "current":None,
                             "next":["scan dependencies"], "summary":None},
        "release-lead":     {"done":[], "current":None,
                             "next":["tag v2.1.0"], "summary":None},
        "infra-lead":       {"done":[], "current":None,
                             "next":["update terraform"], "summary":None},
        "docs-lead":        {"done":[], "current":None,
                             "next":["update API docs"], "summary":None},
    }),
    (5, {
        "planning-lead":    {"status":"done",    "pct":100, "wave":0},
        "engineering-lead": {"status":"done",    "pct":100, "wave":1},
        "review-lead":      {"status":"running", "pct":35,  "wave":2},
        "qa-lead":          {"status":"running", "pct":80,  "wave":2},
        "security-lead":    {"status":"running", "pct":20,  "wave":3},
        "release-lead":     {"status":"waiting", "pct":0,   "wave":3},
        "infra-lead":       {"status":"waiting", "pct":0,   "wave":3},
        "docs-lead":        {"status":"waiting", "pct":0,   "wave":3},
    }, {
        "planning-lead":    {"done":["✓ ADR-012 published","✓ OWASP validated","✓ migration plan done"],
                             "current":None,"next":[],
                             "summary":"ADR-012 written. JWT RS256. 3 risks mitigated."},
        "engineering-lead": {"done":["✓ jwt_handler.py (sign/verify/refresh)",
                                     "✓ middleware.py updated","✓ 12/12 unit tests passing",
                                     "✓ API docs updated (openapi.yaml)"],
                             "current":None,"next":[],
                             "summary":"3 files changed. 12 tests green. Wave 1 gate unlocked."},
        "review-lead":      {"done":["✓ read jwt_handler.py diff (218 lines)",
                                     "✓ no hardcoded secrets found"],
                             "current":"► checking token expiry + clock skew handling (line 47-89)",
                             "next":["verify error response formats","check refresh token rotation"],
                             "summary":None},
        "qa-lead":          {"done":["✓ login → PASS","✓ valid token → PASS",
                                     "✓ refresh → PASS","✓ expired rejection → PASS"],
                             "current":"► E2E: logout + token invalidation (redis blacklist check)",
                             "next":["regression: 14 existing session tests"],
                             "summary":None},
        "security-lead":    {"done":["✓ scanned dependencies"], "current":"► auditing JWT RS256 config",
                             "next":["verify token expiry","confirm no secrets"],
                             "summary":None},
        "release-lead":     {"done":[], "current":None,
                             "next":["tag v2.1.0"], "summary":None},
        "infra-lead":       {"done":[], "current":None,
                             "next":["update terraform"], "summary":None},
        "docs-lead":        {"done":[], "current":None,
                             "next":["update API docs"], "summary":None},
    }),
    (0, {
        "planning-lead":    {"status":"done","pct":100,"wave":0},
        "engineering-lead": {"status":"done","pct":100,"wave":1},
        "review-lead":      {"status":"done","pct":100,"wave":2},
        "qa-lead":          {"status":"done","pct":100,"wave":2},
        "security-lead":    {"status":"done","pct":100,"wave":3},
        "release-lead":     {"status":"done","pct":100,"wave":3},
        "infra-lead":       {"status":"done","pct":100,"wave":3},
        "docs-lead":        {"status":"done","pct":100,"wave":3},
    }, {
        "planning-lead":    {"done":["✓ ADR-012: JWT RS256","✓ OWASP validated","✓ migration plan"],
                             "current":None,"next":[],
                             "summary":"ADR-012 written. JWT RS256. 3 risks mitigated."},
        "engineering-lead": {"done":["✓ jwt_handler.py","✓ middleware.py","✓ 12/12 tests","✓ openapi.yaml"],
                             "current":None,"next":[],
                             "summary":"3 files changed. 12 tests green. Docs updated."},
        "review-lead":      {"done":["✓ diff reviewed","✓ no secrets","✓ expiry/clock-skew OK",
                                     "✓ error formats correct","✓ refresh rotation verified"],
                             "current":None,"next":[],
                             "summary":"LGTM. 2 nits filed. No blockers. Approved."},
        "qa-lead":          {"done":["✓ login → PASS","✓ refresh → PASS",
                                     "✓ expired rejection → PASS","✓ logout+invalidation → PASS",
                                     "✓ 14 regression tests → PASS"],
                             "current":None,"next":[],
                             "summary":"All 6 E2E + 14 regression passed. Zero failures."},
        "security-lead":    {"done":["✓ scanned dependencies","✓ audited JWT RS256 config",
                                     "✓ verified token expiry","✓ confirmed no secrets"],
                             "current":None,"next":[],
                             "summary":"0 critical findings. JWT config approved."},
        "release-lead":     {"done":["✓ tagged v2.1.0","✓ built docker image",
                                     "✓ pushed to registry","✓ triggered staging deploy"],
                             "current":None,"next":[],
                             "summary":"v2.1.0 tagged and pushed to registry."},
        "infra-lead":       {"done":["✓ updated terraform","✓ plan apply",
                                     "✓ verified health","✓ health checks green"],
                             "current":None,"next":[],
                             "summary":"Terraform applied. Redis healthy."},
        "docs-lead":        {"done":["✓ updated API docs","✓ wrote changelog",
                                     "✓ published","✓ live"],
                             "current":None,"next":[],
                             "summary":"Docs published. Changelog live."},
    }),
]


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sprint_id = sys.argv[1] if len(sys.argv) > 1 else "demo"

    if sprint_id == "demo":
        start = time.time()
        for i, (pause, status_snap, parsed_snap) in enumerate(DEMO):
            render_all("demo-001", status_snap, parsed_snap, int(time.time() - start))
            if pause > 0:
                for remaining in range(pause, 0, -1):
                    sys.stdout.write(f"\r  {D}updating in {remaining}s...{' ' * 10}{R}")
                    sys.stdout.flush()
                    time.sleep(1)
    else:
        poll = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        start = time.time()
        while True:
            status = read_status(sprint_id)
            roles  = [r for r in ROLE_ORDER if r in status]
            parsed = {r: parse_log(read_log(sprint_id, r)) for r in roles}
            render_all(sprint_id, status, parsed, int(time.time() - start))

            leads = [v for v in status.values() if isinstance(v, dict)]
            if leads and all(v.get("status") == "done" for v in leads):
                break

            for remaining in range(poll, 0, -1):
                sys.stdout.write(f"\r  {D}updating in {remaining}s...{' ' * 10}{R}")
                sys.stdout.flush()
                time.sleep(1)
