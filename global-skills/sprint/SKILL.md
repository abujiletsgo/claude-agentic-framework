---
name: sprint
description: "Project Manager sprint orchestrator. Decomposes work, assigns leads
  to tmux panes (full root sessions that CAN spawn workers), gates phase waves,
  stores results in mempalace for cross-sprint memory."
user-invocable: true
---

# /sprint — PM Sprint Orchestrator

You are the Project Manager (PM). You decompose tasks, assign leads to tmux panes
(full root sessions with Agent() access), gate wave transitions, and store results
in mempalace for cross-sprint memory.

## Pre-flight

Check available infrastructure:

```bash
bin/gstack-bridge check   # → GSTACK_AVAILABLE (exit 0) or not (exit 1/2/3)
```

Execution mode (cmux-native — always use `bin/cmux-sprint`):

| gstack | Mode |
|--------|------|
| yes    | **cmux-full** — `bin/cmux-sprint` + gstack leads |
| no     | **cmux-only** — `bin/cmux-sprint` + CAF agents |

If `CMUX_SURFACE_ID` is not set, fall back to **agents-only** (sequential `Agent()` calls, no panes).

Log mode selection to events.jsonl via `bin/sprint-event`.

## Step 1: Memory Recall

Before decomposing, check what we already know:

```
mcp__mempalace__mempalace_search(query=<user task>, wing="claude-agentic-framework", room="sprint_results", limit=3)
→ prior sprint outcomes for similar tasks

mcp__mempalace__mempalace_kg_query(predicate="decided", limit=10)
→ project-level decisions
```

Inject prior context into planning (plain text, ≤800 tokens). **No AAAK** — you must read it.
If mempalace is unavailable, skip this step (fail-open).

## Step 2: Decompose Task

Read `data/sprint_config.yaml`. Determine which leads are needed for this task.
Write decomposition to `/tmp/caf_sprint/<id>/pm_plan.md`.

Keep PM plan to ≤1000 tokens. Just the task breakdown.

If `.claude/sprint.yaml` exists, merge it (project overrides win on conflicts).

## Step 3: Write Lead Prompts

For each lead, write `/tmp/caf_sprint/<id>/prompts/<role>.md` (PLAIN TEXT — never AAAK):

```
# You are the <Role> Lead for sprint <id>

## Your Mission
<2-3 sentences: specific task, expected output>

## Context from Prior Sprints
<plain text summary from memory recall — ≤200 tokens>

## gstack Skills Available
<list from sprint_config.yaml, or "none — use CAF agents" if gstack unavailable>

## You Are a Root Session
You have full Agent() access. Spawn builders, validators, researchers as needed.

## Project Context
If /tmp/caf_project_context.md exists, read it first.

## IPC Protocol (REQUIRED)
When done, write results to: /tmp/caf_sprint/<id>/results/<role>_result.md
Mark done: write {"status":"done"} to /tmp/caf_sprint/<id>/<role>.status
```

~500 tokens per prompt.

## Step 4: Execute Waves

### cmux-full / cmux-only mode:
For each wave (0 → 3):
1. Filter leads assigned to this wave (from sprint_config.yaml)
2. Write `{"status":"running"}` to `/tmp/caf_sprint/<id>/<role>.status` for each lead (dashboard shows ►)
3. `bin/sprint-event <id> wave_start '{"wave":<n>,"name":"<label>"}'`
4. `bin/cmux-sprint launch-lead <id> <role> <wave>` for each (parallel within wave)
   — each lead gets its own cmux pane; dashboard pane auto-shows live progress
5. `bin/cmux-sprint poll-wave <id> <wave>` — blocks until all done or any failed
6. Read results from `results/`
7. Synthesize wave summary (3-5 sentences), append to `report.md`
8. `bin/cmux-sprint gate <id> <wave>` — unlock next wave
9. On failure: retry once with additional context, then escalate to user

### Agents-only mode (no CMUX_SURFACE_ID):
For each wave, for each lead:
1. Read the prompt file content
2. Write `{"status":"running"}` to `/tmp/caf_sprint/<id>/<role>.status` (dashboard shows ► immediately)
3. Call `bin/sprint-event <id> lead_started` to stream event to dashboard
4. Call `Agent(name="<role>", model="sonnet", prompt=<prompt content>)`
5. Write agent result to `results/<role>_result.md`
6. Write `{"status":"done"}` (or `{"status":"failed","error":"..."}`) to `<role>.status`
7. Call `bin/sprint-event <id> lead_completed` (or `lead_failed`)
8. Continue to next wave after all leads complete

### Minimal mode:
Skip sprint structure. Equivalent to `/orchestrate`.

## Step 5: Merge and Store

After all waves complete:
1. Generate unified sprint report from all `results/*.md`
2. Store decisions in mempalace KG: `mcp__mempalace__mempalace_kg_add(subj, pred, obj)`
3. Archive: `bin/tmux-sprint teardown <id>`

## Wave Definitions

| Wave | Name | Parallel | Gate | Failure Policy |
|------|------|----------|------|----------------|
| 0 | Plan | yes | yes | block |
| 1 | Build | yes | yes | escalate |
| 2 | Validate | yes | yes | escalate |
| 3 | Ship | no | no | block |

## Lead Roles

| Role | Wave | gstack Skills | CAF Fallback |
|------|------|---------------|--------------|
| planning-lead | 0 | /plan-ceo-review, /plan-eng-review, /plan-design-review, /plan-devex-review, /autoplan | researcher |
| engineering-lead | 1 | /investigate, /pair-agent, /careful | builder, validator, researcher |
| review-lead | 2 | /review, /devex-review, /codex | critical-analyst |
| qa-lead | 2 | /qa, /qa-only, /browse | validator |
| security-lead | 2 | /cso | scout-report-suggest |
| release-lead | 3 | /ship, /land-and-deploy, /canary, /document-release, /retro | (none) |

## Token Budgets

| Role | Budget |
|------|--------|
| planning-lead | 50,000 |
| engineering-lead | 100,000 |
| review-lead | 60,000 |
| qa-lead | 80,000 |
| security-lead | 40,000 |
| release-lead | 30,000 |

## Key Rules

- All IPC files are plain text / JSON — debuggable with cat and jq
- AAAK is for STORAGE only (mempalace palace writes) — never for prompts, IPC, or TUI
- gstack is NEVER modified — only discovered via bin/gstack-bridge
- Every component must work when optional dependencies (gstack, tmux, mempalace) are absent
