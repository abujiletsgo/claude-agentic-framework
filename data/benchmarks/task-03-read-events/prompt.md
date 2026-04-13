# Benchmark Task 03 — Add `read-events` subcommand to orch-shared

Add a new subcommand `read-events <orch_id> [n]` to `bin/orch-shared` that
prints recent events from a job's events.jsonl file.

## Background
`bin/orch-event` writes structured events to `/tmp/caf_orch/<id>/events.jsonl`
when leads change state (running, done, failed). Each event looks like:
  {"ts":"2026-04-13T04:00:00Z","wave":0,"agent":"backend-lead","status":"running","summary":"...","orch_id":"..."}

There is currently no way to read these events via `orch-shared`.

## Spec
`read-events <orch_id> [n]`

- Print the last n events from `/tmp/caf_orch/<orch_id>/events.jsonl` (default n=20)
- Output format per event:
  `[HH:MM] wave<N> <agent>  <status>  <summary_or_blank>`
- If file doesn't exist or is empty: print "(no events)"
- Summary field is optional — omit if missing
- Consistent with read-memory output style (timestamps, aligned columns)

## Acceptance criteria
- [ ] Prints last n events (default 20) from events.jsonl
- [ ] Output format: [HH:MM] wave<N> <agent_padded> <status_padded> [summary]
- [ ] Works when events.jsonl doesn't exist — prints "(no events)", exits 0
- [ ] Works when events.jsonl is empty — prints "(no events)", exits 0
- [ ] Works when n arg provided: read-events <id> 5 shows last 5
- [ ] Handles malformed JSON lines silently (skip)
- [ ] Module docstring updated
- [ ] USAGE string updated
- [ ] main() dispatch added

## This is the live benchmark task
Run /orchestrate with this prompt. Grade the output against rubric.md.
