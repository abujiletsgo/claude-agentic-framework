---
name: qa-cycle
description: Autonomous plan-driven QA for ANY app (web, CLI, TUI, desktop/built). Enumerates every feature/option/button, writes an expected-behavior test matrix (Opus), executes it tiered (Haiku/Sonnet by complexity), produces a planned-vs-expected-vs-actual report, auto-fixes failures, then re-runs the FULL matrix to catch regressions — looping until all green. Triggers "qa-cycle", "full qa", "qa until it works", "regression qa".
argument-hint: "[--report-only] [--max-iter N] [--area <name>]"
user-invocable: true
---

# qa-cycle: Plan → Test → Report → Fix → Regress

A single persistent artifact — the **test matrix** — anchors the whole cycle. The
planner writes it, the testers fill it, the report renders it, the regression loop
re-runs all of it after each fix. Every check is one row:

```
id | area | control | action | preconditions | expected | severity | complexity | status | actual | evidence
```

You are the QA conductor. You own the matrix and the loop; sub-agents do the work.

## Flags
- `--report-only` — stop after Phase 3. Never touch source. (Same as gstack /qa-only, plus the matrix.)
- `--max-iter N` — cap fix→regress iterations (default 5). On reaching the cap with rows still red, stop and report what remains.
- `--area <name>` — scope the whole cycle to one area from the surface map (faster targeted runs).

## Setup (run first)
1. If `/tmp/caf_project_context.md` is missing, run **project-adapter** — it gives you the run command, test command, conventions, and paths. Don't re-discover what it already knows.
2. Create the artifact dir: `mkdir -p .qa` (gitignore it if not already ignored).
3. Pick a run id: `QA_RUN=qa_$(date +%s)`.

---

## Phase 0 — Discover the app (any tier)

Detect the app type, then map its surface. **Do not judge behavior yet — just inventory.**

**Detect type** (in priority order, from project context + repo signals):
- **web** — dev-server script / port in package.json, framework config (vite/next/etc.). Start it if not running; record the URL.
- **cli** — bin entry, `argparse`/`commander`/`clap`, `--help` output. The surface is subcommands, flags, args.
- **tui** — curses/ink/ratatui/bubbletea. Surface is screens + keybindings.
- **desktop/built** — Electron/Tauri/native (.app, Xcode, exe). Launch the built artifact; surface is windows, menus, controls.

**Map the surface** for the detected type. Be exhaustive:
- web/desktop/tui: every route/screen, button, input, toggle, dropdown, menu item, keyboard shortcut, download, and every empty / error / loading state.
- cli: every subcommand, flag, positional arg, stdin mode, exit code, and the no-args / bad-args / `--help` paths.

**Enumerate the DATA behind data-bound controls, not just the control.** A list,
dropdown, file-picker, model/project selector, or table is ONE control but each
value it can hold is a distinct input that may behave completely differently. For
every such control, inventory its real values (or, if huge, at least: count, the
**smallest**, the **largest/heaviest**, and any value that is a **different KIND**
than the rest — an assembly among parts, a 0-row table, a 200 MB file among small
ones). Record these as an `inputs` array on the control. The single most common
miss in QA is testing a control against the one easy value that works while a
one-click-away value silently hangs or fails — surface those values now so the
planner is forced to cover them.
- **web** → gstack `browse` skill or `claude-in-chrome` MCP tools (load via ToolSearch). Read the DOM, enumerate interactive elements.
- **cli/tui** → Bash: run `--help`, introspect subcommands, read the arg parser source.
- **desktop** → launch + accessibility tree / screenshots, or the relevant gstack ios-* skill for iOS.

Write the raw inventory to `.qa/surface.json`:
```json
{ "app_type": "web|cli|tui|desktop", "entry": "<url|command|app path>",
  "areas": [ { "name": "...", "controls": [ { "id": "...", "kind": "button|input|flag|list|filepicker|...", "label": "...",
    "states": ["default","empty","error"],
    "inputs": [ { "value": "<id/label>", "trait": "typical|smallest|largest|odd-kind|malformed", "note": "why notable" } ] } ] } ] }
```

---

## Phase 1 — PLAN the matrix (model: opus)

Spawn an **Opus** planner. Planning is the part that needs the strong model — the
"expected" column IS the contract you grade against, so it must be right.

```
Agent(name="qa-cycle-planner", model="opus", prompt="""
Read .qa/surface.json and /tmp/caf_project_context.md.
For EACH control, emit one or more matrix rows to .qa/matrix.json. Each row:
{ id, area, control, action, preconditions, expected, severity:"critical|high|medium|low",
  complexity:"trivial|moderate|hard", status:"todo", actual:null, evidence:null }

Rules for `expected` — write the SPEC, not a vague hope:
- State the precise observable outcome: state change, returned value, file written,
  exit code, console-clean, rendered text/diff. Gradeable by assertion, not opinion.
- EVERY action that can take >1s gets a TIME BUDGET and a TERMINAL-STATE clause:
  "reaches success OR a clear, actionable error within N s; shows progress meanwhile."
  An indefinite spinner, a silent no-op, or an N-second wait with no feedback is a
  FAIL — even if it would "eventually" work. Unsupported input must be REJECTED
  FAST and CLEARLY, never hang. (This is the rule that catches the dead-spinner bug
  output+console checks miss.)
Cover happy path AND edges for every control:
- empty input, invalid input, max/overflow, double-click / rapid-repeat,
  out-of-bounds, cancel mid-flight, reload mid-state, missing precondition.
DATA COVERAGE — for every data-bound control (the `inputs` array in surface.json),
emit rows for the typical value AND the largest/heaviest AND the odd-kind value AND
a malformed one. Never test a list/picker against only the easy value that works.
NAIVE-USER LENS — assume a user who clicks the most prominent option, not the one
you know works. If a value is selectable in the UI, it is in scope, INCLUDING the
one you suspect is unsupported — its expected is "fast, clear rejection," and a
hang/silent-fail there is a `critical` row, not "by design."
Set `complexity` per row — it selects the tester model in Phase 2:
- trivial/moderate: single click, filter, value check, one flag.
- hard: multi-step flow, race condition, visual diff, stateful sequence.
Return ONLY a one-paragraph TEST PLAN summary (row count, areas, notable edges).
""")
```

Show the user the one-paragraph plan summary. If `--area` was given, the planner scopes to that area only.

---

## Phase 2 — RUN the matrix (tiered model per row)

Group `.qa/matrix.json` rows by complexity and dispatch testers **in parallel**
(independent rows → one message, multiple Agent calls). Tier the model to the work:

- **trivial / moderate** rows → `model="haiku"` (clicks, filters, value checks, flags)
- **hard** rows → `model="sonnet"` (multi-step flows, races, visual diffs)
- a row that **fails twice ambiguously** → escalate that row to `model="opus"` for diagnosis.

Each tester, per row:
```
1. Set preconditions.
2. Perform `action` against the live app (browser tool / Bash command / UI driver — match app_type).
3. Capture `actual`: DOM snapshot, returned value, exit code, file contents, console output, or screenshot path under .qa/evidence/<id>.*
4. ASSERT actual vs `expected`. Set status: pass | fail | blocked.
5. Write `actual` and `evidence` back into the row.
```

**Hard rules for testers:**
- Never trust "looks fine." Grade against `expected` with an explicit assertion.
- Check the console / stderr after EVERY interaction. A clean-looking UI with a
  console error is a **FAIL**, not a pass.
- TIME every action against its budget. If it doesn't reach success or a clear
  error within the expected time, it's a **FAIL** — a spinner that never resolves
  is the canonical fail, not a "still loading." Don't wait politely forever; if the
  budget says 10s, fail it at 10s and record the wall-clock in `actual`.
- For a data-bound control, actually run it against the **heaviest** and the
  **odd-kind** input the row names — not a stand-in. The bug usually lives there.
- `blocked` (precondition couldn't be met) is distinct from `fail` — record why.

Write each completed row back to `.qa/matrix.json` (the artifact is the source of truth, not agent chat).

---

## Phase 3 — REPORT (planned vs expected vs actual)

Render `.qa/report-<QA_RUN>.md` — **never overwrite prior reports**, keep the history:
- **Summary:** N tested · P pass · F fail · B blocked · health score (P/N as %) · run duration · iteration #.
- **Per failing row:** control · what *should* have happened (`expected`) · what *actually* happened (`actual`) · severity · evidence link · suspected source file.
- **What was done:** the executed plan (the matrix is the record of intent vs reality).

Print the summary line + the failing-row table to the user. If `--report-only`, **stop here**.

---

## Phase 4 — FIX (auto, unless --report-only)

For each failing row (highest severity first), dispatch a **builder** to fix the
root cause in source — not the symptom, not the test.

```
Agent(name="qa-cycle-fixer", subagent_type="builder", prompt="""
Read .qa/report-<QA_RUN>.md row <id>. Expected: <...>. Actual: <...>. Suspected file: <...>.
Fix the ROOT CAUSE in source so `actual` will match `expected`. Do not edit the matrix.
Do not weaken the assertion. Report the file(s) changed and a one-line rationale.
""")
```

Batch independent fixes in parallel; serialize fixes that touch the same file. Commit
each atomically if the project convention is atomic commits (check project context).

---

## Phase 5 — REGRESS (re-run the FULL matrix)

This is the point of the cycle: a fix can break a row that was green.

1. Reset every row's `status`/`actual`/`evidence` to the todo state (keep `expected`).
2. **Re-run Phase 2 over the ENTIRE matrix** — not just the rows that were red.
3. Re-render a new timestamped report (Phase 3).
4. **Loop:** if any row is red and iteration < `--max-iter`, go back to Phase 4.
   Converge when **all rows pass** (or only `blocked` remain with reasons), or the
   cap is hit.

**Loop discipline:**
- If the same row fails 2 iterations running with no progress, escalate it to an
  **opus** diagnosis agent before fixing again — don't spin on the same wrong fix.
- Track red-count per iteration. If it isn't trending down, stop and report: you're
  likely fighting a spec disagreement, not a bug. Surface it to the user.

---

## Final report

When green (or capped), print:
- Before → after health score across iterations (e.g. `62% → 88% → 100%`).
- Total rows, fixes applied, files touched, iterations, wall-clock.
- Any remaining `blocked` rows with the reason each couldn't be tested.
- Ship-readiness verdict: GREEN (all pass) / YELLOW (blocked-only remain) / RED (capped with failures).

The persistent matrix (`.qa/matrix.json`) and report history (`.qa/report-*.md`)
stay on disk as the audit trail.

---

## Relationship to other skills
- **gstack `/qa`** — web-only, browser-daemon driven, fixes inline. Use it for a fast
  web-only pass. Use **qa-cycle** when you want the persistent matrix, tiered-model
  economics, non-web apps, or a true regression loop.
- **`/qa-only`** ≈ qa-cycle `--report-only`.
- **project-adapter** — always feeds qa-cycle its run/test commands and conventions.
- **builder** — does the actual fixing in Phase 4.
