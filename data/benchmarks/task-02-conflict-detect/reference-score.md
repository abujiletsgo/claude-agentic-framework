# Task 02 Reference Score — register-domain conflict detection

Built: 2026-04-13 (direct, not via orchestrate)
Validator: smoke tests PASS (3/3 cases: conflict blocked, idempotent OK, non-overlap OK)

## Score
- Functional correctness: 50/50
  - PASS: overlapping glob blocked with CONFLICT message to stderr
  - PASS: conflict written to discoveries.jsonl
  - PASS: same-lead re-register succeeds (idempotent)
  - PASS: non-overlapping glob succeeds
  - PASS: existing subcommands unaffected
- Code quality: 20/20
  - PASS: uses shared_dir, ts, fcntl locking helpers
  - PASS: imports fnmatch locally (good — only needed here)
  - PASS: consistent error handling
  - PASS: stdlib only
- Integration: 15/20
  - N/A: no new subcommand, no USAGE/dispatch changes needed
  - PASS: discoveries.jsonl format matches existing broadcast entries
  - PARTIAL: no update to module docstring to mention conflict detection behavior
- Quality bar: 10/10
  - PASS: stderr messages clearly identify which globs conflict and who owns them
  - PASS: exit 1 on conflict, exit 0 on success

## Total: 95/100 — SHIP
## Note: -5 for missing docstring update
