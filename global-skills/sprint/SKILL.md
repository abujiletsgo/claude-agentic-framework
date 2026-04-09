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
# Detect cmux (highest priority — richest visuals)
[ -n "${CMUX_SURFACE_ID:-}" ] && command -v cmux >/dev/null 2>&1 && CMUX_AVAILABLE=true || CMUX_AVAILABLE=false

bin/gstack-bridge check   # → GSTACK_AVAILABLE (exit 0) or not (exit 1/2/3)
command -v tmux           # → TMUX_AVAILABLE
```

```bash
# Focus dashboard pane so it's visible when sprint starts
if [ -n "${TMUX:-}" ]; then
  tmux select-pane -t caf-team:0.3 2>/dev/null || true
fi
```

Determine execution mode:

| cmux | tmux | gstack | Mode |
|------|------|--------|------|
| yes  | -    | yes    | **cmux-full** — `bin/cmux-sprint` + gstack leads |
| yes  | -    | no     | **cmux-only** — `bin/cmux-sprint` + CAF agents |
| no   | yes  | yes    | **tmux-full** — `bin/tmux-sprint` + gstack leads |
| no   | yes  | no     | **tmux-only** — `bin/tmux-sprint` + CAF agents |
| no   | no   | yes    | **agents-only** — sequential Agent() calls |
| no   | no   | no     | **minimal** — /orchestrate equivalent |

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
Use `bin/cmux-sprint` instead of `bin/tmux-sprint`. Same wave/gate logic applies:
1. Filter leads assigned to this wave (from sprint_config.yaml)
2. `bin/cmux-sprint launch-lead <id> <role> <wave>` for each (parallel within wave)
3. `bin/cmux-sprint poll-wave <id> <wave>` — blocks until all done or any failed
4. Read results from `results/`
5. Synthesize wave summary (3-5 sentences), append to `report.md`
6. `bin/cmux-sprint gate <id> <wave>` — unlock next wave
7. On failure: retry once with additional context, then escalate to user

### Full / tmux-only mode:
For each wave (0 → 3):
1. Filter leads assigned to this wave (from sprint_config.yaml)
2. `bin/tmux-sprint launch-lead <id> <role> <wave>` for each (parallel within wave)
3. `bin/tmux-sprint poll-wave <id> <wave>` — blocks until all done or any failed
4. Read results from `results/`
5. Synthesize wave summary (3-5 sentences), append to `report.md`
6. `bin/tmux-sprint gate <id> <wave>` — unlock next wave
7. On failure: retry once with additional context, then escalate to user

### Agents-only mode:
For each wave, for each lead:
1. Read the prompt file content
2. Call `Agent(name="<role>", model="sonnet", prompt=<prompt content>)`
3. Write agent result to `results/<role>_result.md`
4. Continue to next wave after all leads complete

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
