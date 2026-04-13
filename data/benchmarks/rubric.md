# Benchmark Rubric — orch-shared subcommand additions

Each benchmark task evaluates how well /orchestrate handles adding a new
subcommand to bin/orch-shared. Tasks 1 and 2 have reference implementations
(already built and validated). Task 3 is a live benchmark.

---

## Scoring per task

Grade each criterion: PASS (1) | PARTIAL (0.5) | FAIL (0)

### Functional correctness (50 pts)
- [ ] Correct output format (as specified in acceptance criteria)
- [ ] Handles missing/empty files without crashing
- [ ] Handles initialized but empty job
- [ ] Edge cases covered (empty input, bad orch_id, etc.)
- [ ] Regression: existing subcommands still work

### Code quality (20 pts)
- [ ] Uses existing helpers (shared_dir, ORCH_BASE, ts, load_surfaces, etc.)
- [ ] fcntl locking on all writes to shared files
- [ ] Error handling consistent with rest of file (try/except, never crash)
- [ ] No new external dependencies (stdlib only)

### Integration (20 pts)
- [ ] Module docstring at top of file updated
- [ ] USAGE string updated (correct placement, correct format)
- [ ] main() dispatch added (correct sub name, correct arg count check)

### Quality bar (10 pts)
- [ ] Output is readable and consistent with existing subcommands
- [ ] Summary message to stdout on write ops (like other commands)

## Total: /100

## Scoring guide
- 90-100: SHIP — correct and clean
- 75-89: SHIP with notes — minor gaps, acceptable
- 50-74: NEEDS REWORK — functional but missing coverage or integration
- <50: FAIL — broken or incomplete

---

## How to run a benchmark

1. Give the orchestrate skill the task prompt from `task-NN-*/prompt.md`
2. Let it run to completion
3. Grade the output against this rubric + the task's `acceptance_criteria.md`
4. Record in `task-NN-*/run-<date>.md`: score, verdict, notable gaps
