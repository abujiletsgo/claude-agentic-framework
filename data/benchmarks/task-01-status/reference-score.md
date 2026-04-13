# Task 01 Reference Score — status subcommand

Built: 2026-04-13 (orch_1776052841)
Validator: 7/7 tests PASS

## Score
- Functional correctness: 50/50
  - PASS: correct output format (health table with all sections)
  - PASS: handles uninitialized job (prints NOT INITIALIZED, exits 0)
  - PASS: handles initialized empty job (all counts 0)
  - PASS: handles job with data (counts increment correctly)
  - PASS: all 14 existing subcommands still work
- Code quality: 20/20
  - PASS: uses shared_dir, ORCH_BASE, load_surfaces helpers
  - PASS: no writes (read-only command), no locking needed
  - PASS: try/except on all file reads
  - PASS: stdlib only
- Integration: 20/20
  - PASS: module docstring updated
  - PASS: USAGE string updated with full description
  - PASS: main() dispatch added with arg count check
- Quality bar: 10/10
  - PASS: output aligned with fixed-width labels
  - PASS: read-only command, no stdout summary needed

## Total: 100/100 — SHIP
