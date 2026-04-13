# Benchmark Task 01 — Add `status` subcommand to orch-shared

Add a new subcommand `status <orch_id>` to `bin/orch-shared` that prints a
health table for a running orchestration job.

The command should show:
- Count of pending questions (shared/questions.jsonl where status=="pending")
- Count of queued tests (shared/test_queue.jsonl, all lines)
- Count of test results (shared/test_results.jsonl, all lines)
- Count of memory entries (shared/working_memory.jsonl, all lines)
- Registered domains from shared/domains.json
- Active surfaces from surfaces.json
- Per-lead wave status from *.status files at the job root

Must work on uninitialized jobs (no crash), initialized empty jobs, and jobs
with data. Stdlib only. Update module docstring, USAGE string, and main()
dispatch.
