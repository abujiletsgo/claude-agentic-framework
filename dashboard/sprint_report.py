#!/usr/bin/env python3
"""
CAF Idle Report — two-column ANSI dashboard for between-job state.

Left column:  Last completed orch job (task, acceptance criteria, verdict)
              + Recent job history (last 5)
Right column: Pending questions from any active job
              + Framework health (hooks / agents / skills)

Refreshes every 5s. Shows meaningful data or explicit "nothing yet" — no
silent blanks.

Usage: uv run python dashboard/sprint_report.py [--cwd <dir>]
"""
import sys, os, json, time, shutil, re, argparse
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
MAG   = "\033[95m"
WHT   = "\033[97m"
GRAY  = "\033[90m"

# ── Paths ─────────────────────────────────────────────────────────────────────
ORCH_BASE    = Path("/tmp/caf_orch")
ORCH_RESULTS = Path.home() / ".claude" / "data" / "orch_results"
REFRESH_S    = 5


# ── Terminal ──────────────────────────────────────────────────────────────────

def term_size() -> tuple[int, int]:
    sz = shutil.get_terminal_size((120, 40))
    return sz.columns, sz.lines

def now_str() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

def ago(mtime: float) -> str:
    secs = int(time.time() - mtime)
    if secs < 60:   return f"{secs}s ago"
    if secs < 3600: return f"{secs // 60}m ago"
    h = secs // 3600
    m = (secs % 3600) // 60
    return f"{h}h{m:02d}m ago"

def strip_ansi(s: str) -> str:
    return re.sub(r'\033\[[0-9;]*m', '', s)

def pad(s: str, width: int) -> str:
    """Pad/truncate to exact visible width (ANSI-aware)."""
    visible = len(strip_ansi(s))
    if visible > width:
        # truncate raw string until visible width fits
        result, vlen = [], 0
        in_escape = False
        for ch in s:
            if ch == '\033':
                in_escape = True
            if in_escape:
                result.append(ch)
                if ch.isalpha():
                    in_escape = False
                continue
            if vlen < width - 1:
                result.append(ch)
                vlen += 1
            else:
                result.append('…')
                vlen += 1
                break
        return ''.join(result) + RESET
    return s + ' ' * (width - visible)


# ── Data readers ──────────────────────────────────────────────────────────────

def parse_acceptance_criteria(path: Path) -> tuple[str, list[tuple[bool, str]]]:
    """Return (task_line, [(checked, text), ...])."""
    task_line = ""
    criteria: list[tuple[bool, str]] = []
    if not path.exists():
        return task_line, criteria
    try:
        after_task_heading = False
        for line in path.read_text(errors="replace").splitlines():
            stripped = line.strip()
            if "**Task**:" in line:
                task_line = line.split("**Task**:", 1)[-1].strip()
                after_task_heading = False
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

def parse_verdict(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        text = path.read_text(errors="replace")
        if "## Overall Verdict" in text:
            section = text.split("## Overall Verdict", 1)[1]
            for line in section.splitlines():
                line = line.strip().lstrip('#').strip().lstrip('*').rstrip('*').strip()
                if line:
                    return line[:80]
    except Exception:
        pass
    return ""

def _job_meta_cwd(d: Path) -> str:
    """Read project CWD from meta.json in an orch job dir."""
    try:
        return json.loads((d / "meta.json").read_text()).get("cwd", "")
    except Exception:
        return ""

def list_completed_jobs(cwd: str = "") -> list[dict]:
    """Return completed jobs from orch_results, filtered by cwd if provided."""
    jobs = []
    if not ORCH_RESULTS.exists():
        return jobs
    try:
        for d in ORCH_RESULTS.iterdir():
            if not d.is_dir():
                continue
            if cwd and _job_meta_cwd(d) not in ("", cwd):
                continue
            mtime = d.stat().st_mtime
            task, criteria = parse_acceptance_criteria(d / "acceptance_criteria.md")
            verdict = parse_verdict(d / "evaluation_report.md")
            jobs.append({
                "id":       d.name,
                "mtime":    mtime,
                "task":     task,
                "criteria": criteria,
                "verdict":  verdict,
            })
    except Exception:
        pass
    jobs.sort(key=lambda j: j["mtime"], reverse=True)
    return jobs

def find_active_job(cwd: str = "") -> str:
    """Return orch_id of most-recently-modified active job for this project."""
    try:
        all_dirs = [d for d in ORCH_BASE.iterdir() if d.is_dir()]
        if cwd:
            scoped = [d for d in all_dirs if _job_meta_cwd(d) == cwd]
            if scoped:
                scoped.sort(key=lambda d: d.stat().st_mtime, reverse=True)
                return scoped[0].name
        # Fallback: global most-recent
        all_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
        return all_dirs[0].name if all_dirs else ""
    except Exception:
        pass
    return ""

def read_pending_questions(orch_id: str) -> list[dict]:
    """Read pending questions from active job shared/questions.jsonl."""
    if not orch_id:
        return []
    p = ORCH_BASE / orch_id / "shared" / "questions.jsonl"
    if not p.exists():
        return []
    pending = []
    try:
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("status") == "pending":
                pending.append(e)
    except Exception:
        pass
    return pending

def read_claude_md_stats(cwd: Path) -> dict[str, int]:
    """Parse hook/agent/skill counts from CLAUDE.md structure section."""
    stats = {"hooks": 0, "agents": 0, "skills": 0}
    claude_md = cwd / "CLAUDE.md"
    if not claude_md.exists():
        return stats
    try:
        text = claude_md.read_text(errors="replace")
        for line in text.splitlines():
            m = re.search(r'(\d+)\s+hooks\b', line)
            if m:
                stats["hooks"] = int(m.group(1))
            m = re.search(r'(\d+)\s+agents\b', line)
            if m:
                stats["agents"] = int(m.group(1))
            m = re.search(r'(\d+)\s+skills\b', line)
            if m:
                stats["skills"] = int(m.group(1))
    except Exception:
        pass
    return stats


# ── Rendering ─────────────────────────────────────────────────────────────────

def verdict_color(verdict: str) -> str:
    v = verdict.upper()
    if "SHIP" in v or "PASS" in v:
        return GRN
    if "REWORK" in v or "FAIL" in v:
        return RED
    if "PARTIAL" in v:
        return YLW
    return WHT

def render_left(jobs: list[dict], col_w: int) -> list[str]:
    lines = []

    def rule():
        lines.append(GRAY + "─" * col_w + RESET)

    def hdr(text: str):
        lines.append(f"  {BOLD}{CYN}{text}{RESET}")

    # ── Last job ──────────────────────────────────────────────────────────────
    hdr("LAST JOB")
    rule()

    if not jobs:
        lines.append(f"{GRAY}  No completed jobs in orch_results/{RESET}")
    else:
        j = jobs[0]
        oid_short = j["id"][-12:] if len(j["id"]) > 12 else j["id"]
        lines.append(f"  {GRAY}id:{RESET}      {WHT}{oid_short}{RESET}")
        lines.append(f"  {GRAY}when:{RESET}    {DIM}{ago(j['mtime'])}{RESET}")
        task = j["task"] or "(no task line)"
        # wrap task to col_w - 4
        wrap_w = col_w - 4
        words, cur = task.split(), ""
        task_lines = []
        for w in words:
            if len(cur) + len(w) + 1 <= wrap_w:
                cur = (cur + " " + w).lstrip()
            else:
                if cur:
                    task_lines.append(cur)
                cur = w
        if cur:
            task_lines.append(cur)
        lines.append(f"  {GRAY}task:{RESET}    {WHT}{task_lines[0] if task_lines else ''}{RESET}")
        for tl in task_lines[1:]:
            lines.append(f"           {WHT}{tl}{RESET}")

        # Criteria
        if j["criteria"]:
            lines.append("")
            lines.append(f"  {BOLD}Acceptance criteria:{RESET}")
            for (done, text) in j["criteria"][:8]:
                mark  = f"{GRN}[x]{RESET}" if done else f"{GRAY}[ ]{RESET}"
                short = text[:col_w - 8] + ("…" if len(text) > col_w - 8 else "")
                lines.append(f"    {mark} {short}")
            if len(j["criteria"]) > 8:
                lines.append(f"    {GRAY}… +{len(j['criteria']) - 8} more{RESET}")

        # Verdict
        if j["verdict"]:
            lines.append("")
            vc = verdict_color(j["verdict"])
            lines.append(f"  {BOLD}Verdict:{RESET} {vc}{j['verdict']}{RESET}")

    lines.append("")

    # ── History ───────────────────────────────────────────────────────────────
    hdr("RECENT JOBS")
    rule()

    if len(jobs) <= 1:
        lines.append(f"{GRAY}  No prior jobs.{RESET}")
    else:
        for j in jobs[1:6]:
            oid_short = j["id"][-12:] if len(j["id"]) > 12 else j["id"]
            vc = verdict_color(j["verdict"])
            verdict_tag = f"{vc}{j['verdict'][:8]}{RESET}" if j["verdict"] else f"{GRAY}--{RESET}"
            task_short  = (j["task"][:col_w - 28] + "…") if len(j["task"]) > col_w - 28 else j["task"]
            task_short  = task_short or "(no task)"
            lines.append(f"  {GRAY}{oid_short:<14}{RESET} {verdict_tag:<20} {DIM}{task_short}{RESET}")

    lines.append("")
    return lines

def render_right(questions: list[dict], stats: dict, active_id: str, col_w: int) -> list[str]:
    lines = []

    def rule():
        lines.append(GRAY + "─" * col_w + RESET)

    def hdr(text: str):
        lines.append(f"  {BOLD}{CYN}{text}{RESET}")

    # ── Pending questions ─────────────────────────────────────────────────────
    hdr("PENDING QUESTIONS")
    rule()

    if not active_id:
        lines.append(f"{GRAY}  No active job.{RESET}")
    elif not questions:
        lines.append(f"{GRN}  No pending questions.{RESET}")
    else:
        for q in questions[:6]:
            crit_tag = f" {RED}[CRITICAL]{RESET}" if q.get("critical") else ""
            lines.append(f"  {YLW}[{q.get('id','?')}]{RESET}{crit_tag} {GRAY}from {q.get('lead','?')}{RESET}")
            qtext = q.get("question", "")
            wrap_w = col_w - 4
            words, cur = qtext.split(), ""
            q_lines = []
            for w in words:
                if len(cur) + len(w) + 1 <= wrap_w:
                    cur = (cur + " " + w).lstrip()
                else:
                    if cur:
                        q_lines.append(cur)
                    cur = w
            if cur:
                q_lines.append(cur)
            for i, ql in enumerate(q_lines[:3]):
                prefix = "    " if i == 0 else "    "
                lines.append(f"{prefix}{ql}")
            if len(q_lines) > 3:
                lines.append(f"    {GRAY}…{RESET}")
            lines.append(f"    {GRAY}answer: bin/orch-shared answer-question {active_id} {q.get('id','?')} '<ans>'{RESET}")
            lines.append("")
        if len(questions) > 6:
            lines.append(f"  {GRAY}… +{len(questions) - 6} more questions{RESET}")

    lines.append("")

    # ── Framework health ──────────────────────────────────────────────────────
    hdr("FRAMEWORK HEALTH")
    rule()

    rows = [
        ("Hooks",   str(stats["hooks"])  if stats["hooks"]  else GRAY + "?" + RESET),
        ("Agents",  str(stats["agents"]) if stats["agents"] else GRAY + "?" + RESET),
        ("Skills",  str(stats["skills"]) if stats["skills"] else GRAY + "?" + RESET),
    ]
    for label, val in rows:
        lines.append(f"  {GRAY}{label:<8}{RESET} {WHT}{val}{RESET}")

    lines.append("")
    return lines


def render_frame(jobs: list[dict], questions: list[dict], stats: dict,
                 active_id: str, cwd: Path) -> str:
    cols, rows = term_size()
    col_w = (cols - 3) // 2   # 3 = left-margin + divider + right-margin

    right_col_w = cols - col_w - 1
    left  = render_left(jobs, col_w)
    right = render_right(questions, stats, active_id, right_col_w)

    # Pad to equal height
    height = max(len(left), len(right))
    left  += [""] * (height - len(left))
    right += [""] * (height - len(right))

    out = []

    # Header bar
    title   = f"{BOLD}{CYN} caf-hud idle {RESET}"
    ts_part = f"{GRAY}{now_str()}  cwd:{str(cwd)[:40]}{RESET}"
    spacer  = " " * max(0, cols - len(strip_ansi(title)) - len(strip_ansi(ts_part)) - 2)
    out.append(title + spacer + ts_part)
    out.append(GRAY + "═" * cols + RESET)

    # Column headers
    left_hdr  = pad(f" {BOLD}HISTORY{RESET}", col_w)
    right_hdr = pad(f" {BOLD}QUESTIONS & HEALTH{RESET}", cols - col_w - 1)
    out.append(left_hdr + GRAY + "│" + RESET + right_hdr)
    out.append(GRAY + "─" * col_w + "┼" + "─" * (cols - col_w - 1) + RESET)

    # Body
    divider = GRAY + "│" + RESET
    for l_line, r_line in zip(left, right):
        lp = pad(l_line, col_w)
        rp = pad(r_line, cols - col_w - 1)
        out.append(lp + divider + rp)

    # Footer
    out.append(GRAY + "═" * cols + RESET)
    active_label = f"active: {active_id}" if active_id else "active: none"
    jobs_label   = f"completed: {len(jobs)}"
    q_label      = f"questions: {len(questions)}"
    out.append(f"{GRAY} {active_label}   {jobs_label}   {q_label}   refresh: {REFRESH_S}s{RESET}")

    return "\n".join(out)


# ── Main loop ─────────────────────────────────────────────────────────────────

def clear():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", default=os.getcwd(),
                        help="Project root (for CLAUDE.md stats)")
    args = parser.parse_args()
    cwd = Path(args.cwd).resolve()

    try:
        cwd_str = str(cwd)
        while True:
            jobs       = list_completed_jobs(cwd_str)
            active_id  = find_active_job(cwd_str)
            questions  = read_pending_questions(active_id)
            stats      = read_claude_md_stats(cwd)

            frame = render_frame(jobs, questions, stats, active_id, cwd)
            clear()
            print(frame, flush=True)
            time.sleep(REFRESH_S)
    except KeyboardInterrupt:
        clear()
        print(f"{GRAY}caf idle — stopped.{RESET}")

if __name__ == "__main__":
    main()
