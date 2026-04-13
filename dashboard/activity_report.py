#!/usr/bin/env python3
"""
CAF Activity Report — multi-panel ANSI HUD for /orchestrate jobs.

Finds the most-recently-modified orch job under /tmp/caf_orch/ and renders
a live two-column HUD.  Full redraw every 3s; questions polled every 1s.

Usage: python3 dashboard/activity_report.py [--cwd <project_dir>]
"""
import sys, os, json, re, time, shutil, argparse
from pathlib import Path
from datetime import datetime, timezone

# ── ANSI ──────────────────────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"
RED   = "\033[91m"
YLW   = "\033[93m"
GRN   = "\033[92m"
BLU   = "\033[94m"
CYN   = "\033[96m"
WHT   = "\033[97m"
GRAY  = "\033[90m"

# ── Constants ─────────────────────────────────────────────────────────────────
ORCH_BASE    = Path("/tmp/caf_orch")
ACTIVITY_LOG = Path.home() / ".claude" / "data" / "activity_log.jsonl"

LEAD_ORDER = [
    "planning-lead", "engineering-lead", "frontend-lead", "backend-lead",
    "review-lead", "qa-lead", "security-lead", "release-lead", "docs-lead",
]

_ANSI_RE = re.compile(r'\033\[[0-9;]*m')

def visible_len(s: str) -> int:
    """Length of string excluding ANSI escape codes."""
    return len(_ANSI_RE.sub('', s))

def rpad(s: str, width: int) -> str:
    """Pad string to exact visible width (ANSI-aware)."""
    vlen = visible_len(s)
    if vlen >= width:
        return s
    return s + ' ' * (width - vlen)


# ── Terminal helpers ──────────────────────────────────────────────────────────

def term_width() -> int:
    return shutil.get_terminal_size((100, 40)).columns

def clamp(s: str, width: int) -> str:
    """Strip ANSI codes for length measurement, then hard-clamp visible chars."""
    # Use raw len as proxy — ANSI codes will make lines shorter on screen.
    # We build lines manually so visible text is already bounded.
    if len(s) > width + 50:   # rough guard
        return s[:width + 50]
    return s

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def elapsed_str(mtime: float) -> str:
    secs = int(now_utc().timestamp() - mtime)
    if secs < 60:
        return f"{secs}s"
    elif secs < 3600:
        return f"{secs // 60}m"
    else:
        return f"{secs // 3600}h{(secs % 3600) // 60}m"

def fmt_ts(ts_str: str) -> str:
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except Exception:
        return (ts_str[:5] if ts_str else "??:??")


# ── Job discovery ─────────────────────────────────────────────────────────────

def _job_cwd(d: Path) -> str:
    """Read the project CWD recorded in meta.json for this orch job."""
    try:
        return json.loads((d / "meta.json").read_text()).get("cwd", "")
    except Exception:
        return ""

def find_active_orch_id(cwd: str = "") -> str:
    """Return the orch_id of the most-recently-modified subdir that has
    acceptance_criteria.md, preferring jobs whose CWD matches ours."""
    if not cwd:
        cwd = str(Path.cwd())
    try:
        all_dirs = [d for d in ORCH_BASE.iterdir() if d.is_dir()]
        # Prefer jobs matching this project's CWD
        scoped = [d for d in all_dirs if _job_cwd(d) == cwd and (d / "acceptance_criteria.md").exists()]
        if scoped:
            scoped.sort(key=lambda d: d.stat().st_mtime, reverse=True)
            return scoped[0].name
        # Fallback: any dir with acceptance_criteria
        with_crit = [d for d in all_dirs if (d / "acceptance_criteria.md").exists()]
        if with_crit:
            with_crit.sort(key=lambda d: d.stat().st_mtime, reverse=True)
            return with_crit[0].name
        # Last resort: any dir
        all_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
        return all_dirs[0].name if all_dirs else ""
    except Exception:
        return ""


# ── Data readers ──────────────────────────────────────────────────────────────

def read_acceptance_criteria(orch_id: str) -> tuple[str, list[tuple[bool, str]]]:
    """Return (task_line, [(checked, text), ...])."""
    path = ORCH_BASE / orch_id / "acceptance_criteria.md"
    task_line = ""
    criteria: list[tuple[bool, str]] = []
    try:
        lines = path.read_text(errors="replace").splitlines()
        after_task_heading = False
        for line in lines:
            stripped = line.strip()
            # Inline format: "**Task**: <text>"
            if "**Task**:" in line:
                task_line = line.split("**Task**:", 1)[-1].strip()
                after_task_heading = False
            # Heading format: "## Task" followed by text on next non-empty line
            elif stripped in ("## Task", "### Task"):
                after_task_heading = True
            elif after_task_heading and stripped and not stripped.startswith("#"):
                task_line = stripped
                after_task_heading = False
            else:
                after_task_heading = False
            if stripped.startswith("- [x]") or stripped.startswith("- [X]"):
                criteria.append((True, stripped[5:].strip()))
            elif stripped.startswith("- [ ]"):
                criteria.append((False, stripped[5:].strip()))
    except Exception:
        pass
    return task_line, criteria


def read_evaluation_report(orch_id: str) -> tuple[dict[str, str], str]:
    """Return (criterion_statuses, verdict_text)."""
    path = ORCH_BASE / orch_id / "evaluation_report.md"
    crit_statuses: dict[str, str] = {}   # criterion text snippet -> PASS/FAIL/PARTIAL
    verdict = ""
    try:
        text = path.read_text(errors="replace")
        # Parse per-criterion Status lines
        current_crit = ""
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("###") or stripped.startswith("**Criterion"):
                current_crit = stripped.lstrip("#").strip().strip("*").strip()
            elif stripped.startswith("Status:") or stripped.startswith("**Status**:"):
                val = stripped.split(":", 1)[-1].strip().strip("*").strip()
                if current_crit:
                    crit_statuses[current_crit.lower()[:30]] = val
        # Parse overall verdict section
        if "## Overall Verdict" in text:
            verdict_section = text.split("## Overall Verdict", 1)[1]
            # grab first non-empty line
            for ln in verdict_section.splitlines():
                ln = ln.strip()
                if ln:
                    verdict = ln[:80]
                    break
    except Exception:
        pass
    return crit_statuses, verdict


def read_lead_statuses(orch_id: str) -> dict[str, dict]:
    """role -> {status, error, mtime}"""
    result = {}
    base = ORCH_BASE / orch_id
    for role in LEAD_ORDER:
        f = base / f"{role}.status"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                data["mtime"] = f.stat().st_mtime
                result[role] = data
            except Exception:
                result[role] = {"status": "unknown", "mtime": f.stat().st_mtime}
    # Also pick up any other *-lead.status files not in LEAD_ORDER
    try:
        for f in base.glob("*-lead.status"):
            role = f.stem  # e.g. "hud-lead"
            if role not in result:
                try:
                    data = json.loads(f.read_text())
                    data["mtime"] = f.stat().st_mtime
                    result[role] = data
                except Exception:
                    pass
    except Exception:
        pass
    return result


def read_working_memory(orch_id: str) -> list[dict]:
    """Last entries from shared/working_memory.jsonl."""
    path = ORCH_BASE / orch_id / "shared" / "working_memory.jsonl"
    entries = []
    try:
        for line in path.read_text(errors="replace").splitlines():
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


def read_events(orch_id: str) -> list[dict]:
    """Read all events from events.jsonl (written by orch-event + _emit_event)."""
    path = ORCH_BASE / orch_id / "events.jsonl"
    entries = []
    try:
        for line in path.read_text(errors="replace").splitlines():
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


def read_questions(orch_id: str) -> list[dict]:
    """All entries from shared/questions.jsonl with status==pending."""
    path = ORCH_BASE / orch_id / "shared" / "questions.jsonl"
    entries = []
    try:
        for line in path.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                if e.get("status") == "pending":
                    entries.append(e)
            except Exception:
                pass
    except Exception:
        pass
    return entries


def read_discoveries(orch_id: str) -> list[dict]:
    """Last 2 entries from shared/discoveries.jsonl."""
    path = ORCH_BASE / orch_id / "shared" / "discoveries.jsonl"
    entries = []
    try:
        for line in path.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
    except Exception:
        pass
    return entries[-2:]


def read_token_usage() -> str:
    """Sum session tokens from caf_session_cost_*.jsonl (written by Rust SessionCostTracker).
    Reads the most-recently-modified cost file. Returns '~42k tok | $0.12' or ''."""
    import glob as _glob
    cost_files = sorted(
        _glob.glob("/tmp/caf_session_cost_*.jsonl"),
        key=lambda p: Path(p).stat().st_mtime,
        reverse=True,
    )
    if not cost_files:
        return ""
    total_tok = 0
    total_cost = 0.0
    try:
        for line in Path(cost_files[0]).read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                total_tok  += (e.get("input_tokens", 0) or 0) + (e.get("output_tokens", 0) or 0)
                total_cost += e.get("cost_usd", 0.0) or 0.0
            except Exception:
                pass
    except Exception:
        return ""
    if total_tok == 0:
        return ""
    k = total_tok // 1000
    return f"~{k}k tok ${total_cost:.2f}"


# ── Layout helpers ────────────────────────────────────────────────────────────

def box_line(left_content: str, right_content: str,
             left_w: int, right_w: int,
             left_color: str = "", right_color: str = "") -> str:
    """Render one row of a two-column box (ANSI-aware padding)."""
    lc = rpad(left_content, left_w)
    rc = rpad(right_content, right_w)
    lc_colored = f"{left_color}{lc}{RESET}" if left_color else lc
    rc_colored = f"{right_color}{rc}{RESET}" if right_color else rc
    return f"{BOLD}{CYN}║{RESET}{lc_colored}{BOLD}{CYN}║{RESET}{rc_colored}{BOLD}{CYN}║{RESET}"


def h_rule_double(w: int) -> str:
    return f"{BOLD}{CYN}{'═' * w}{RESET}"

def h_rule_split(left_w: int, right_w: int) -> str:
    """╠══════╦══════╣"""
    return (f"{BOLD}{CYN}╠{'═' * left_w}╦{'═' * right_w}╣{RESET}")

def h_rule_join(left_w: int, right_w: int) -> str:
    """╠══════╩══════╣"""
    return (f"{BOLD}{CYN}╠{'═' * left_w}╩{'═' * right_w}╣{RESET}")

def h_rule_single_full(w: int) -> str:
    """╠══════════════╣"""
    return f"{BOLD}{CYN}╠{'═' * (w - 2)}╣{RESET}"

def top_border(w: int) -> str:
    return f"{BOLD}{CYN}╔{'═' * (w - 2)}╗{RESET}"

def bot_border(w: int) -> str:
    return f"{BOLD}{CYN}╚{'═' * (w - 2)}╝{RESET}"

def full_row(content: str, w: int, color: str = "") -> str:
    inner = w - 2
    colored = f"{color}{rpad(content, inner)}{RESET}" if color else rpad(content, inner)
    return f"{BOLD}{CYN}║{RESET}{colored}{BOLD}{CYN}║{RESET}"


# ── Lead status rendering ─────────────────────────────────────────────────────

def lead_symbol(status: str) -> str:
    if status == "done":
        return f"{GRN}✓{RESET}"
    elif status == "running":
        return f"{CYN}●{RESET}"
    elif status == "failed":
        return f"{RED}✗{RESET}"
    elif status == "aborted":
        return f"{GRAY}⊘{RESET}"
    else:
        return f"{GRAY}◌{RESET}"

def lead_color(status: str) -> str:
    if status == "done":
        return GRN
    elif status == "running":
        return CYN
    elif status == "failed":
        return RED
    else:
        return GRAY


def last_memory_for_lead(lead: str, mem_entries: list[dict]) -> str:
    """Return summary text of last working_memory entry for this lead."""
    for e in reversed(mem_entries):
        if e.get("lead") == lead or e.get("role") == lead or e.get("agent") == lead:
            return (e.get("summary") or e.get("content") or e.get("text") or "")[:40]
    return ""


# ── Questions panel ───────────────────────────────────────────────────────────

def render_questions_panel(questions: list[dict], inner_w: int) -> list[str]:
    """Return list of lines (no ║ borders — caller adds them)."""
    lines = []
    if not questions:
        lines.append(f"{GRAY}(no pending questions){RESET}")
        return lines

    for q in questions:
        critical = q.get("critical", False)
        bc = RED if critical else YLW
        qid   = str(q.get("id", ""))
        lead  = str(q.get("lead", q.get("from", "")))
        qtext = str(q.get("question", q.get("text", "")))[:60]
        # inner box width: inner_w - 4 for margins
        bw = min(inner_w - 4, 30)
        lines.append(f"{bc}╔{'═' * bw}╗{RESET}")
        lines.append(f"{bc}║{BOLD}⚠ WAITING PM{RESET}{bc}{'─' * max(0, bw - 12)}║{RESET}")
        lines.append(f"{bc}║{RESET}[{qid}] {lead[:bw-4]}{' ' * max(0, bw - 4 - len(qid) - len(lead))} {bc}║{RESET}")
        # question text wrapped at bw-2
        for chunk_start in range(0, len(qtext), bw - 2):
            chunk = qtext[chunk_start:chunk_start + bw - 2]
            lines.append(f"{bc}║{RESET}{chunk.ljust(bw - 2)}{bc}║{RESET}")
        cmd = f"orch-shared answer-q {qid}"
        lines.append(f"{bc}║{RESET}{GRAY}{cmd[:bw-2].ljust(bw-2)}{RESET}{bc}║{RESET}")
        lines.append(f"{bc}╚{'═' * bw}╝{RESET}")

    return lines


# ── HUD renderer ──────────────────────────────────────────────────────────────

def render_hud(cwd: str = "") -> None:
    w = term_width()
    out: list[str] = []

    def emit(line: str = "") -> None:
        out.append(line)

    orch_id = find_active_orch_id(cwd)

    # ── Gather data ───────────────────────────────────────────────────────────
    task_line, criteria      = read_acceptance_criteria(orch_id) if orch_id else ("", [])
    crit_statuses, verdict   = read_evaluation_report(orch_id) if orch_id else ({}, "")
    lead_statuses            = read_lead_statuses(orch_id) if orch_id else {}
    mem_entries              = read_working_memory(orch_id) if orch_id else []
    events                   = read_events(orch_id) if orch_id else []
    questions                = read_questions(orch_id) if orch_id else []
    discoveries              = read_discoveries(orch_id) if orch_id else []
    tok_usage                = read_token_usage()

    # ── Column widths ─────────────────────────────────────────────────────────
    # total inner width = w - 2 (for ║ on each side)
    # criteria need ~45 chars to be readable; leads need ~40
    inner = w - 2
    left_w  = min(45, inner * 2 // 5)
    right_w = inner - left_w - 1  # -1 for middle ║

    # ── Header ────────────────────────────────────────────────────────────────
    task_short = task_line[:55] if task_line else "(no task)"
    elapsed_total = ""
    if orch_id:
        orch_dir = ORCH_BASE / orch_id
        try:
            elapsed_total = elapsed_str(orch_dir.stat().st_mtime)
        except Exception:
            elapsed_total = "?"
    usage_str  = f"📊 {tok_usage}" if tok_usage else ""
    header_parts = [
        f"{BOLD}{CYN}{orch_id or 'no-job'}{RESET}",
        f"{WHT}{task_short}{RESET}",
        f"{GRAY}⏱ {elapsed_total}{RESET}",
        f"{BLU}{usage_str}{RESET}" if usage_str else "",
    ]
    header_inner = "  │  ".join(p for p in header_parts if p)
    emit(top_border(w))
    emit(full_row(f"  {header_inner}", w))
    emit(h_rule_split(left_w, right_w))

    # ── Column headers ────────────────────────────────────────────────────────
    emit(box_line(
        f" {BOLD}CRITERIA{RESET}",
        f" {BOLD}LEAD STATUS{RESET}",
        left_w, right_w,
    ))

    # ── Criteria + Lead rows (interleaved) ────────────────────────────────────
    # Determine how many rows to show
    leads_to_show = [r for r in LEAD_ORDER if r in lead_statuses]
    # Add any discovered leads not in LEAD_ORDER
    for r in lead_statuses:
        if r not in leads_to_show:
            leads_to_show.append(r)

    max_rows = max(len(criteria), len(leads_to_show))

    for i in range(max_rows):
        # ── Left: criterion ──────────────────────────────────────────────────
        if i < len(criteria):
            checked, ctext = criteria[i]
            # check eval overlay
            ctext_key = ctext.lower()[:30]
            eval_status = ""
            for ck, cv in crit_statuses.items():
                if ck in ctext_key or ctext_key in ck:
                    eval_status = cv
                    break
            if eval_status == "PASS":
                box_char = f"{GRN}x{RESET}"
            elif checked:
                box_char = f"{GRN}x{RESET}"
            elif eval_status == "FAIL":
                box_char = f"{RED} {RESET}"
            else:
                box_char = " "
            ctext_disp = ctext[:left_w - 6]
            left_str = f" [{box_char}] {ctext_disp}"
        else:
            left_str = ""

        # ── Right: lead status ────────────────────────────────────────────────
        if i < len(leads_to_show):
            role   = leads_to_show[i]
            info   = lead_statuses[role]
            status = info.get("status", "pending")
            sym    = lead_symbol(status)
            col    = lead_color(status)
            mtime  = info.get("mtime")
            el     = elapsed_str(mtime) if mtime else "?"
            role_short = role[:20]
            status_short = status[:7]
            right_str = f" {sym} {col}{role_short:<20}{RESET} {GRAY}{status_short:<7}{RESET} ({el})"
        else:
            right_str = ""

        emit(box_line(left_str, right_str, left_w, right_w))

        # ── Sub-row: last memory for lead ──────────────────────────────────────
        if i < len(leads_to_show):
            role   = leads_to_show[i]
            status = lead_statuses[role].get("status", "")
            if status == "running":
                mem_text = last_memory_for_lead(role, mem_entries)
                if mem_text:
                    mem_disp = f"  └ {GRAY}\"{mem_text[:right_w - 6]}\"{RESET}"
                    emit(box_line("", mem_disp, left_w, right_w))

    # Criteria overall eval status label
    if verdict:
        emit(box_line(
            f" {GRN if 'PASS' in verdict.upper() else YLW}eval: {verdict[:left_w-8]}{RESET}",
            "",
            left_w, right_w,
        ))
    else:
        emit(box_line(f" {GRAY}eval: pending{RESET}", "", left_w, right_w))

    # ── Middle divider ────────────────────────────────────────────────────────
    emit(h_rule_split(left_w, right_w))

    # ── Questions + Event Feed ────────────────────────────────────────────────
    event_count = len(events)
    emit(box_line(
        f" {BOLD}❓ QUESTIONS{RESET}",
        f" {BOLD}EVENT FEED{RESET} {GRAY}({event_count} total){RESET}",
        left_w, right_w,
    ))

    # Left: questions panel lines
    q_lines = render_questions_panel(questions, left_w)

    # Right: event feed — last 8 events, newest at bottom
    _STATUS_ICON = {
        "running":      f"{CYN}●{RESET}",
        "done":         f"{GRN}✓{RESET}",
        "failed":       f"{RED}✗{RESET}",
        "memory":       f"{GRAY}·{RESET}",
        "domain-claim": f"{BLU}⊕{RESET}",
        "broadcast":    f"{YLW}»{RESET}",
        "question":     f"{YLW}?{RESET}",
        "answer":       f"{GRN}✉{RESET}",
        "test-req":     f"{GRAY}⚙{RESET}",
        "aborted":      f"{GRAY}⊘{RESET}",
    }
    ev_lines: list[str] = []
    for ev in events[-8:]:
        ts_raw  = ev.get("ts", "")
        ts_disp = fmt_ts(ts_raw) if ts_raw else "??:??"
        status  = ev.get("status", "")
        agent   = ev.get("agent", "?")[:10]
        summary = (ev.get("summary") or "")
        icon    = _STATUS_ICON.get(status, f"{GRAY}·{RESET}")
        status_color = {
            "running": CYN, "done": GRN, "failed": RED,
            "question": YLW, "answer": GRN, "broadcast": YLW,
        }.get(status, GRAY)
        summary_disp = summary[:right_w - 22] if summary else f"{GRAY}{status}{RESET}"
        ev_lines.append(
            f" {GRAY}{ts_disp}{RESET} {icon} {status_color}{agent:<10}{RESET} {summary_disp}"
        )
    if not ev_lines:
        ev_lines = [f" {GRAY}(no events yet){RESET}"]

    max_q_rows = max(len(q_lines), len(ev_lines), 1)
    for i in range(max_q_rows):
        left_str  = q_lines[i]  if i < len(q_lines)  else ""
        right_str = ev_lines[i] if i < len(ev_lines) else ""
        emit(box_line(left_str, right_str, left_w, right_w))

    # ── Broadcast bar ─────────────────────────────────────────────────────────
    emit(h_rule_join(left_w, right_w))
    if discoveries:
        last_d = discoveries[-1]
        topic  = str(last_d.get("topic", last_d.get("type", "broadcast")))
        msg    = str(last_d.get("message", last_d.get("content", last_d.get("text", ""))))[:80]
        bcast  = f" 📡 {BOLD}{topic}{RESET}: {msg}"
    else:
        bcast  = f" {GRAY}📡 (no broadcasts yet){RESET}"
    emit(full_row(bcast, w))

    # ── Evaluation panel ──────────────────────────────────────────────────────
    emit(h_rule_single_full(w))
    # Determine eval state
    all_leads_done = bool(lead_statuses) and all(
        v.get("status") in ("done", "failed") for v in lead_statuses.values()
    )
    eval_f = ORCH_BASE / orch_id / "evaluation_report.md" if orch_id else Path("/dev/null")
    eval_running = False
    eval_status_f = ORCH_BASE / orch_id / "evaluator.status" if orch_id else Path("/dev/null")
    try:
        es = json.loads(eval_status_f.read_text())
        if es.get("status") == "running":
            eval_running = True
    except Exception:
        pass

    if eval_running:
        eval_text = f" {CYN}● evaluating...{RESET}"
    elif verdict:
        if "PASS" in verdict.upper():
            # count criteria
            total = len(criteria)
            passed = sum(1 for _, ct in criteria
                        for ck, cv in crit_statuses.items()
                        if (ck in ct.lower()[:30] or ct.lower()[:30] in ck) and cv == "PASS")
            eval_text = f" {GRN}{BOLD}PASS {passed}/{total} criteria{RESET}"
        else:
            failed_leads = [r for r, v in lead_statuses.items() if v.get("status") == "failed"]
            fl_str = ", ".join(failed_leads[:3]) if failed_leads else "see report"
            eval_text = f" {RED}{BOLD}NEEDS REWORK — {verdict[:50]}{RESET}  {GRAY}({fl_str}){RESET}"
    elif not orch_id:
        eval_text = f" {GRAY}pending — no active job{RESET}"
    else:
        eval_text = f" {GRAY}pending — runs after all leads complete{RESET}"

    emit(full_row(f" EVALUATION: {eval_text}", w))
    emit(bot_border(w))

    # ── Flush ─────────────────────────────────────────────────────────────────
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.write("\n".join(out) + "\n")
    sys.stdout.flush()


# ── Main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", default=os.getcwd(),
                        help="Project root (for CWD-scoped job filtering)")
    args = parser.parse_args()
    cwd = str(Path(args.cwd).resolve())

    tick = 0
    while True:
        try:
            if tick % 3 == 0:
                render_hud(cwd)
            else:
                # Fast poll: only re-render if there are pending questions
                orch_id = find_active_orch_id(cwd)
                if orch_id and read_questions(orch_id):
                    render_hud(cwd)
        except Exception as e:
            sys.stdout.write("\033[2J\033[H")
            print(f"{RED}render error: {e}{RESET}")
        time.sleep(1)
        tick += 1


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
