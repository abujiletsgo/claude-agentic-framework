# Task 03 Reference Score — read-events subcommand

Built: 2026-04-13 (direct)
Validator: smoke tests PASS (5/5 cases)

## Score
- Functional correctness: 50/50
  - PASS: prints last n events (default 20)
  - PASS: prints "(no events)" when file missing, exits 0
  - PASS: prints "(no events)" when file empty, exits 0
  - PASS: n arg works (read-events <id> 2 shows last 2)
  - PASS: existing subcommands unaffected
- Code quality: 20/20
  - PASS: uses ORCH_BASE consistently (not shared_dir — events.jsonl is at job root)
  - PASS: read-only, no locking needed
  - PASS: try/except per line (malformed JSON skipped silently)
  - PASS: stdlib only
- Integration: 20/20
  - PASS: module docstring updated
  - PASS: USAGE string updated (both inline list and description block)
  - PASS: main() dispatch added with arg count check
- Quality bar: 10/10
  - PASS: output format matches read-memory style ([HH:MM] + aligned columns)
  - PASS: read-only command, no stdout summary needed

## Total: 100/100 — SHIP

## Note on orch-event deprecation warning
bin/orch-event uses datetime.utcnow() which is deprecated in Python 3.12+.
Out of scope for this task but worth fixing separately.
