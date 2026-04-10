#!/usr/bin/env python3
"""
CAF Sprint Report — bottom-right pane.
Appends completed lead summaries as they finish. Readable, scrollable.

Live mode:  python3 dashboard/sprint_report.py <sprint_id>
Demo mode:  python3 dashboard/sprint_report.py demo
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
WH = "\033[97m"

STRIP_ANSI = re.compile(r'\033\[[0-9;]*m')

def cols(): return shutil.get_terminal_size((100, 40)).columns
def rule(c="─", color=D): print(f"{color}{c * cols()}{R}")
def w(n=0): return cols() - n


# ── Report entry renderer ─────────────────────────────────────────────────────

WAVE_LABEL = {0: "PLAN", 1: "BUILD", 2: "VALIDATE", 3: "SHIP"}
WAVE_COLOR = {0: BL, 1: CY, 2: M, 3: GR}

def print_header(sprint_id: str, started_at: str):
    print()
    rule("━", CY)
    print(f"{B}{CY}  SPRINT REPORT  ·  {sprint_id}{R}")
    print(f"{D}  started {started_at}{R}")
    rule("━", CY)

def print_lead_report(role: str, info: dict, log_lines: list[str], finished_at: str):
    """Print a full readable section for one completed lead."""
    wave  = info.get("wave", 0)
    wc    = WAVE_COLOR.get(wave, CY)
    wl    = WAVE_LABEL.get(wave, f"W{wave}")
    status = info.get("status", "done")
    sc    = GR if status == "done" else RD
    chip  = f"{sc}{'✓ DONE' if status == 'done' else '✗ FAILED'}{R}"

    print()
    print(f"  {wc}{B}{'─' * 4}  {role.upper()}  [{wl}]{R}  {chip}  {D}{finished_at}{R}")
    print()

    # Parse log into sections
    done_tasks = []
    failed_tasks = []
    decisions = []
    files_changed = []
    test_results = []
    output_summary = None

    for raw in log_lines:
        l = STRIP_ANSI.sub("", raw).strip()
        if l.startswith("✓ "):
            done_tasks.append(l[2:])
        elif l.startswith("✗ "):
            failed_tasks.append(l[2:])
        # heuristics for structured output leads write
        if any(x in l.lower() for x in ["changed", "modified", ".py", ".ts", ".yaml", ".json", ".md"]) \
                and ("file" in l.lower() or "." in l):
            files_changed.append(l)
        if any(x in l.lower() for x in ["test", "pass", "fail", "assert", "spec", "e2e", "coverage"]):
            test_results.append(l)
        if any(x in l.lower() for x in ["decided", "adr", "selected", "approved", "rejected", "chose"]):
            decisions.append(l)
        if ("DONE" in l or "complete" in l.lower()) and len(l) < 120 and "━" not in l:
            output_summary = l

    # ── Accomplished ──────────────────────────────────────────────────────────
    if done_tasks:
        print(f"  {B}Accomplished{R}")
        for t in done_tasks:
            print(f"    {GR}✓{R}  {t}")
        print()

    # ── Decisions ────────────────────────────────────────────────────────────
    if decisions:
        print(f"  {B}Decisions{R}")
        seen = set()
        for d in decisions:
            if d not in seen:
                seen.add(d)
                print(f"    {BL}→{R}  {d}")
        print()

    # ── Files changed ─────────────────────────────────────────────────────────
    if files_changed:
        print(f"  {B}Files{R}")
        seen = set()
        for f in files_changed[:6]:
            if f not in seen:
                seen.add(f)
                print(f"    {D}·{R}  {f}")
        print()

    # ── Test results ──────────────────────────────────────────────────────────
    if test_results:
        print(f"  {B}Tests{R}")
        seen = set()
        for t in test_results[:4]:
            if t not in seen:
                seen.add(t)
                color = GR if "pass" in t.lower() else (RD if "fail" in t.lower() else D)
                print(f"    {color}{t}{R}")
        print()

    # ── Failed tasks ──────────────────────────────────────────────────────────
    if failed_tasks:
        print(f"  {B}{RD}Failures{R}")
        for t in failed_tasks:
            print(f"    {RD}✗{R}  {t}")
        print()

    # ── Summary line ──────────────────────────────────────────────────────────
    if output_summary:
        print(f"  {D}└─ {output_summary}{R}")

    rule()


def print_sprint_summary(sprint_id: str, status_data: dict, duration_s: int):
    """Final summary block printed when all leads finish."""
    leads  = {k: v for k, v in status_data.items() if isinstance(v, dict)}
    n_done = sum(1 for v in leads.values() if v.get("status") == "done")
    n_fail = sum(1 for v in leads.values() if v.get("status") == "failed")
    mins   = duration_s // 60
    secs   = duration_s % 60

    print()
    rule("━", GR if not n_fail else RD)
    if not n_fail:
        print(f"  {B}{GR}✓  SPRINT COMPLETE{R}  {D}{sprint_id}{R}")
    else:
        print(f"  {B}{RD}✗  SPRINT FINISHED WITH {n_fail} FAILURE(S){R}")
    print(f"  {D}{n_done} leads done  ·  {mins:02d}:{secs:02d} elapsed{R}")
    print()

    # Wave summary
    waves_done = sorted(set(v.get("wave", 0) for v in leads.values()))
    for wn in waves_done:
        wl    = WAVE_LABEL.get(wn, f"W{wn}")
        wc    = WAVE_COLOR.get(wn, CY)
        roles = [k for k, v in leads.items() if isinstance(v, dict) and v.get("wave") == wn]
        stati = [v.get("status","?") for v in leads.values() if isinstance(v, dict) and v.get("wave") == wn]
        all_ok = all(s == "done" for s in stati)
        icon   = f"{GR}✓{R}" if all_ok else f"{RD}✗{R}"
        print(f"  {icon}  {wc}Wave {wn} — {wl}{R}  {D}{', '.join(roles)}{R}")

    print()
    rule("━", GR if not n_fail else RD)


# ── IPC helpers ───────────────────────────────────────────────────────────────

def read_status(sprint_id: str) -> dict:
    try:
        return json.loads(Path(f"/tmp/caf_sprint/{sprint_id}/status.json").read_text())
    except Exception:
        return {}

def read_log(sprint_id: str, role: str, n: int = 80) -> list[str]:
    f = Path(f"/tmp/caf_sprint/{sprint_id}/logs/{role}.log")
    try:
        lines = f.read_text(errors="replace").splitlines()
        return [l for l in lines if l.strip()][-n:]
    except Exception:
        return []


# ── Live mode ─────────────────────────────────────────────────────────────────

ROLE_ORDER = ["planning-lead", "engineering-lead", "review-lead",
              "qa-lead", "security-lead", "release-lead", "infra-lead", "docs-lead"]

def run_live(sprint_id: str, poll: int = 3):
    started_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    start_ts   = time.time()
    reported   = set()

    print_header(sprint_id, started_at)
    print(f"  {D}Waiting for leads to complete...{R}")

    while True:
        status = read_status(sprint_id)
        leads  = {k: v for k, v in status.items() if isinstance(v, dict)}

        for role in ROLE_ORDER:
            if role in leads and role not in reported:
                info = leads[role]
                if info.get("status") in ("done", "failed"):
                    log   = read_log(sprint_id, role)
                    ts    = datetime.now(UTC).strftime("%H:%M UTC")
                    print_lead_report(role, info, log, ts)
                    reported.add(role)

        all_done = leads and all(v.get("status") in ("done","failed") for v in leads.values())
        if all_done:
            print_sprint_summary(sprint_id, status, int(time.time() - start_ts))
            break

        time.sleep(poll)


# ── Demo mode ─────────────────────────────────────────────────────────────────

DEMO_REPORTS = [
    ("planning-lead", {"status":"done","wave":0}, [
        "✓ reviewed existing auth design — middleware.py, session.py, auth/utils.py",
        "✓ identified 3 migration risks: token leakage on refresh, replay attacks, clock skew",
        "✓ drafted ADR-012: JWT RS256 selected over session tokens",
        "    decided: RS256 asymmetric signing — public key verifiable by all services",
        "    decided: 15min access token + 7-day refresh with rotation",
        "    decided: Redis blacklist for logout invalidation",
        "✓ validated against OWASP Top-10 auth checklist — all items addressed",
        "✓ published migration plan to /tmp/caf_sprint/sprint-001/results/planning_result.md",
        "DONE — ADR-012 written. JWT RS256 selected. 3 risks mitigated in plan.",
    ], 1.5),
    ("engineering-lead", {"status":"done","wave":1}, [
        "✓ read ADR-012 and migration plan (2,400 tokens context)",
        "✓ scaffolded auth/jwt_handler.py — sign_token(), verify_token(), refresh_token()",
        "✓ updated auth/middleware.py — replaced session.get() with jwt.verify()",
        "✓ updated auth/utils.py — added token blacklist check via Redis",
        "    modified: auth/jwt_handler.py  (+218 lines)",
        "    modified: auth/middleware.py   (+34 / -21 lines)",
        "    modified: auth/utils.py        (+12 lines)",
        "    modified: openapi.yaml         (+40 lines — new /auth/refresh endpoint)",
        "✓ implemented validate_token() + refresh_token() with clock skew tolerance (30s)",
        "✓ 12/12 unit tests passing — jwt_handler_test.py",
        "    test: test_sign_verify PASS",
        "    test: test_expired_token PASS",
        "    test: test_clock_skew_tolerance PASS",
        "    test: test_refresh_rotation PASS",
        "DONE — 3 files changed, 264 insertions, 21 deletions. 12/12 tests green. Wave 1 gate unlocked.",
    ], 1.5),
    ("review-lead", {"status":"done","wave":2}, [
        "✓ read jwt_handler.py diff — 218 lines, clean structure",
        "✓ no hardcoded secrets, no debug logs with token values",
        "✓ checked token expiry handling — correct, uses UTC timestamps",
        "✓ clock skew tolerance (30s) is appropriate — consistent with industry standard",
        "✓ error responses follow RFC 7807 — no token data leaked in errors",
        "✓ refresh token rotation implemented correctly — old token invalidated on use",
        "    decided: filed nit #1 — add type hints to verify_token() return value",
        "    decided: filed nit #2 — extract magic number 30 to AUTH_CLOCK_SKEW_SECONDS config",
        "DONE — LGTM. 2 minor nits filed as issues #234 and #235. No blockers. Approved.",
    ], 1.5),
    ("qa-lead", {"status":"done","wave":2}, [
        "✓ booted test environment — docker-compose up, all services healthy",
        "✓ E2E: login flow — POST /auth/login → 200 + JWT returned  PASS",
        "✓ E2E: valid token accepted — GET /api/me with valid JWT → 200  PASS",
        "✓ E2E: token refresh — POST /auth/refresh → new token pair  PASS",
        "✓ E2E: expired token rejected — GET /api/me with expired JWT → 401  PASS",
        "✓ E2E: logout + blacklist — POST /auth/logout → token invalidated → 401  PASS",
        "✓ E2E: replay attack prevention — reuse of rotated refresh token → 401  PASS",
        "    test: 6/6 E2E scenarios PASS",
        "    test: 14/14 regression tests PASS (existing session-based tests adapted)",
        "    test: 0 failures, 0 flakes",
        "DONE — All 20 tests passed (6 E2E + 14 regression). Zero failures. Zero flakes.",
    ], 1.5),
    ("security-lead", {"status":"done","wave":3}, [
        "✓ scanned all dependencies — 0 critical, 2 low CVEs (non-auth)",
        "✓ audited JWT RS256 config — key size 2048-bit, appropriate",
        "✓ verified token expiry enforced at middleware layer",
        "✓ confirmed no secrets in source (gitleaks scan clean)",
        "    decided: approved auth implementation for production",
        "DONE — 0 critical findings. JWT config approved. Security sign-off granted.",
    ], 1.5),
    ("release-lead", {"status":"done","wave":3}, [
        "✓ merged auth feature branch to main",
        "✓ tagged v2.1.0 — auth JWT migration complete",
        "✓ built docker image: myapp:v2.1.0 (412MB)",
        "    modified: Dockerfile (+3 lines — REDIS_URL env)",
        "    modified: docker-compose.yaml (+redis service)",
        "✓ pushed to registry: registry.example.com/myapp:v2.1.0",
        "✓ triggered staging deploy — all health checks green",
        "DONE — v2.1.0 tagged and pushed. Staging healthy.",
    ], 0),
]

def run_demo():
    started_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    start_ts   = time.time()

    print_header("sprint-demo-001", started_at)
    print(f"  {D}Waiting for leads to complete...{R}")

    for role, info, log_lines, pause in DEMO_REPORTS:
        if pause > 0:
            time.sleep(pause)
        ts = datetime.now(UTC).strftime("%H:%M UTC")
        print_lead_report(role, info, log_lines, ts)
        if pause > 0:
            time.sleep(pause * 0.5)

    fake_status = {role: info for role, info, _, _ in DEMO_REPORTS}
    print_sprint_summary("sprint-demo-001", fake_status, int(time.time() - start_ts))


# ── Idle mode ─────────────────────────────────────────────────────────────────

def _last_sprint_id() -> str | None:
    """Return most recently archived sprint id, or None."""
    archive = Path.home() / ".claude/data/sprint_events"
    if not archive.exists():
        return None
    files = sorted(archive.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    return files[-1].stem if files else None


def run_idle(poll: int = 5):
    """Show idle panel until a live sprint appears, then hand off to run_live."""
    ipc_base = Path("/tmp/caf_sprint")
    last_sprint = _last_sprint_id()

    while True:
        # Check if a sprint has started while we were idle
        if ipc_base.exists():
            sprints = sorted(
                (d for d in ipc_base.iterdir() if d.is_dir()),
                key=lambda d: d.stat().st_mtime,
                reverse=True,
            )
            for d in sprints:
                status_file = d / "status.json"
                if status_file.exists():
                    try:
                        data = json.loads(status_file.read_text())
                        if any(isinstance(v, dict) for v in data.values()):
                            # Live sprint detected — hand off, then return to idle
                            sys.stdout.write("\033[2J\033[H")
                            run_live(d.name, poll=poll)
                            last_sprint = d.name  # update last sprint id
                            break  # fall back to idle loop
                    except Exception:
                        pass

        # Draw idle panel
        w = cols()
        ts = datetime.now(UTC).strftime("%H:%M UTC")
        sys.stdout.write("\033[2J\033[H")

        print(f"{B}{CY}{'━' * w}{R}")
        print(f"{B}{CY}  SPRINT REPORT{R}")
        print(f"{D}{'━' * w}{R}")
        print()
        print(f"  {D}○  no active sprint{R}")
        print()
        print(f"  {D}run /sprint to begin{R}")
        print(f"  {D}lead summaries appear here as each wave completes{R}")
        print()

        if last_sprint:
            print(f"  {D}last sprint: {last_sprint}{R}")
            print()

        rule("─", D)
        print(f"  {D}{ts}{R}", end="", flush=True)

        time.sleep(poll)


# ── Entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sprint_id = sys.argv[1] if len(sys.argv) > 1 else "idle"
    if sprint_id == "demo":
        run_demo()
    elif sprint_id == "idle":
        run_idle(poll=int(sys.argv[2]) if len(sys.argv) > 2 else 5)
    else:
        run_live(sprint_id, poll=int(sys.argv[2]) if len(sys.argv) > 2 else 3)
