---
name: orchestrate
description: "Unified orchestrator — PO that aligns with user on vision, routes to domain leads, answers escalations. Leads spec their domain A-Z and delegate to builders."
user-invocable: true
---

# /orchestrate — You Are the PO

There is no `/sprint`. This is the only command. You are the PO.

---

## Phase 1: Align with User

**Load project context first:**
```bash
cat .claude/PO_BRIEF.md 2>/dev/null || echo "(no project brief found)"
```

If a PO_BRIEF.md exists, use it to inform your questions and lead selection. It tells you the project's domain leads, tech stack, quality bar, and team norms.

Ask PO-level questions — not technical ones. 3–5 questions focused on:

**Vision + outcome:**
- "What does done look like from a user's perspective?"
- "Who is this for and what problem does it solve?"
- "What would make you reject the output?"

**Scope + constraints:**
- "Are there parts that must stay unchanged?"
- "Any hard deadlines or ship-fast vs. ship-right trade-offs?"
- "Any context I'm missing — recent decisions, related work in flight?"

**For simple tasks (bug fix, small change):** skip vision questions. Ask only: "What's the expected behavior vs. what's happening?" then route directly.

DO NOT ask: "Which framework?", "How should we structure this?", "What architecture?" — that's for the leads.

Wait for user response. Then write:
1. **Acceptance criteria** → `/tmp/caf_orch/<id>/acceptance_criteria.md` (format: `templates/acceptance-criteria.md`)
2. **Mission Brief** → `/tmp/caf_orch/<id>/mission_brief.md` (format: `templates/mission-brief.md`)

Show both to user. Get confirmation before proceeding.

---

## Phase 2: Detect Scope + Pick Leads

The PO detects scope (single vs. multi-domain) and routes accordingly.

**Lead discovery order** (check each source, merge results):
1. **`.claude/agents/`** — any `*-lead.md` file in this directory is a project-specific lead. Read its frontmatter `description` and `domain` fields to understand what it owns. These leads override the standard table for their named domain.
2. **Standard 8-lead table** (below) — global fallback. Only use a standard lead if no project-specific lead covers the same domain.

To discover project leads: `ls .claude/agents/*-lead.md 2>/dev/null` and read each file's frontmatter. A custom lead's `subagent_type` field names the base agent type to spawn; its `name` field is its identity in the wave.

**Routing decision — pick one:**

| Route | When | How |
|-------|------|-----|
| Skip orchestrate entirely | Single domain, < 5 files, no coordination needed | Just do it as a direct agent task |
| PO-direct (no leads) | Single domain, focused scope, < 3 work streams | `Agent()` for leaf workers — researcher, builder, validator |
| Leads via cmux | Any lead involved, 2+ domains, or complex single domain | `bin/cmux-sprint launch-agent` — always cmux for leads |

**Why cmux for any lead:** leads must spawn workers (researchers, builders, validators). A lead spawned via `Agent()` cannot itself spawn agents. Use `Agent()` only for leaf workers that do not spawn further.

Leads are **delegating planners** — they break their domain into tasks and spawn workers. They do NOT build, research, or code directly.

| Lead type | subagent_type | Domain |
|-----------|---------------|--------|
| backend-lead | backend-lead | Server logic, APIs, data layer, DB, infra, services |
| frontend-lead | frontend-lead | UI, client-side logic, design system, mobile (via skill) |
| architecture-lead | architecture-lead | System design, ADRs, interface contracts |
| debugging-lead | debugging-lead | Root cause analysis, fix planning |
| refactoring-lead | refactoring-lead | Code reorganization, rename/move, structural improvements |
| performance-lead | performance-lead | Profiling, benchmarks, regression detection |
| docs-lead | docs-lead | Documentation, release notes, API docs |
| release-lead | release-lead | Ship sequencing, deploy configs, rollback prep |

**Selection rule**: only pick leads whose domain is relevant. `research-lead` does not exist — each lead owns its own research in Wave 0.

**Custom lead rule**: when a `.claude/agents/*-lead.md` file exists, use `subagent_type` from its frontmatter as the agent type and `name` as the identity. If the file has no `subagent_type`, fall back to the closest standard lead type. Custom leads get the same wave structure (Wave 0 explore → Wave 1 contracts → Wave 2 build) as standard leads.

Typical 3-lead: `frontend-lead` + `backend-lead` + `architecture-lead`
Typical 5-lead: adds `debugging-lead` + `release-lead`

---

## Phase 2.5: PO-Direct Mode (no leads)

For small-to-medium focused tasks, the PO can skip lead agents entirely and spawn a direct worker team:

```python
# PO-direct — one wave, all in parallel
Agent(name="researcher",   subagent_type="researcher", model="haiku", prompt="...")
Agent(name="builder",      subagent_type="builder",    model="sonnet", prompt="...")
Agent(name="validator",    subagent_type="validator",  model="haiku", prompt="...")
```

Use PO-direct when:
- Single domain (only one type of work: just coding, just docs, just a fix)
- < 3 independent work streams
- No inter-agent coordination needed (leads don't need to broadcast or share a blackboard)

**Quality gate for PO-direct:** no evaluator phase. Validator only. If the task needs a full critical-analyst review, use a lead instead.

Use leads when:
- Multiple domains (engineering + QA + security in parallel)
- Work streams have dependencies or interface contracts
- Leads need to coordinate via shared workspace (register-domain, broadcast, etc.)

---

## Phase 3: Write Lead Prompts

Write each prompt to `/tmp/caf_orch/<id>/prompts/<lead-name>.md`.
Full template: `global-skills/orchestrate/templates/lead-prompt.md`
Result file format: `global-skills/orchestrate/templates/result-format.md`

Key sections every prompt must include:
- Big Picture + Your Domain + Your Mission
- Acceptance Criteria (from acceptance_criteria.md — verbatim)
- Delegating Planner section (tool constraints)
- Tool & Language Selection (surface options + tradeoffs — never silently default)
- Shared Research Available (file paths)
- Git Worktree path
- Shared Workspace Protocol (register-domain, check-domain, append-memory, request-test, broadcast)
- Ask the PO section
- IPC: write status file when done

---

## Phase 4: Execute

Generate `orch_id = f"orch_{int(time.time())}"`. All IPC under `/tmp/caf_orch/<orch_id>/`.

### Pre-flight
```bash
bin/orch-shared init <orch_id>
bin/cmux-sprint launch-hud <orch_id>  # cmux only
```

### Wave 0 — Exploration (all leads, parallel)

Write a Wave 0 mission brief for each lead. Key instruction: "Explore your domain. Research what exists. Draft ideas. List what you need from other leads. Do NOT write any implementation code. Output your findings to `/tmp/caf_orch/<orch_id>/results/<your-name>-wave0.md`."

**agents-only:**
```python
Agent(name="frontend-lead", subagent_type="frontend-lead", model="sonnet", prompt=<wave0-mission>)
Agent(name="backend-lead",  subagent_type="backend-lead",  model="sonnet", prompt=<wave0-mission>)
Agent(name="api-lead",      subagent_type="api-lead",      model="sonnet", prompt=<wave0-mission>)
# All in one message — wait for all before proceeding
```

**cmux:**
```bash
bin/cmux-sprint launch-agent <orch_id> frontend-lead 0
bin/cmux-sprint launch-agent <orch_id> backend-lead 0
bin/cmux-sprint launch-agent <orch_id> api-lead 0
bin/cmux-sprint poll-agents <orch_id> frontend-lead backend-lead api-lead
```

### Gate 0 → 1: PO Review

Read all `results/*-wave0.md` files. Check for:
- Dependency requirements: does any lead need contracts from another?
- Surprises or blockers worth flagging to the user

**Optional user review** — ask the user if: task is a new feature (not a fix), or Wave 0 findings reveal unexpected complexity or design decisions. Format:
```
Wave 0 is done. Here's what your leads found before we start building:
[2-3 bullet summary per lead]

Any of this look wrong or surprising? If not I'll move to contracts + build.
```
If user says "you do you" or doesn't engage — proceed.

**Decide contract owners.** For this job, which leads own interfaces?
- api-lead → owns endpoint contracts (if any cross-domain API calls)
- data-lead → owns schema (if DB schema changes)
- No contract leads → skip Wave 1, go directly to Wave 2

### Wave 1 — Contracts (contract leads only, fast)

Only run if contract leads were identified in Gate 0→1.

**PO injects context directly into Wave 1 briefs** — do not require contract leads to spawn researchers to read wave0.md files. Extract the relevant excerpts yourself at Gate 0→1 and paste them verbatim into each contract lead's Wave 1 brief. Contract leads should never need to read another lead's wave0.md themselves.

Write a Wave 1 brief for each contract lead containing:
- The relevant excerpts from other leads' wave0.md files (what they need from this contract lead)
- "Finalize the interfaces for your domain. Output clean contracts to `/tmp/caf_orch/<orch_id>/results/<your-name>-contracts.md`. Broadcast your contracts via `bin/orch-shared broadcast`. This is your only output — no implementation yet."

Launch contract leads. Wait for completion. Read their contract files.

### Gate 1 → 2: Inject Contracts

Read all `results/*-contracts.md`. Build a "Contracts Available" block — verbatim quotes of each contract. This block goes into every Wave 2 lead mission brief.

### Wave 2 — Build (all leads, parallel)

Write a Wave 2 mission brief for each lead containing:
- Their Wave 0 findings (reference their own `wave0.md`)
- The full Contracts Available block (verbatim from all Wave 1 outputs)
- "Now build. Implement your domain fully. No more exploration. No more blocking on contracts — they are above."

**agents-only:**
```python
Agent(name="frontend-lead", subagent_type="frontend-lead", model="sonnet", prompt=<wave2-mission>)
Agent(name="backend-lead",  subagent_type="backend-lead",  model="sonnet", prompt=<wave2-mission>)
# All in one message
```

**cmux:**
```bash
bin/cmux-sprint launch-agent <orch_id> frontend-lead 2
bin/cmux-sprint launch-agent <orch_id> backend-lead 2
bin/cmux-sprint poll-agents <orch_id> frontend-lead backend-lead
```

### Mid-run question handling

Leads post questions via `bin/orch-shared ask-pm`. PO polls `pending-questions` and answers per the Tier 1/Tier 2 protocol. In Wave 2, contract questions should not arise (they were resolved in Wave 1). If one does, it means Wave 1 was incomplete — answer it directly rather than re-running Wave 1.

### Wave gating

Waves are sequential. Agents within a wave are parallel. Always launch an entire wave in one message.

---

## Phase 5: Merge

```bash
bin/cmux-sprint merge-leads <orch_id>
```

Read `/tmp/caf_orch/<orch_id>/merge_report.md`. Resolve any CONFLICT entries before evaluating.

---

## Phase 6: Full-Picture Evaluation

Write evaluator prompt to `/tmp/caf_orch/<id>/prompts/evaluator.md`.
Full template: `global-skills/orchestrate/templates/evaluator-prompt.md`

Launch:
```python
# cmux mode
bin/cmux-sprint launch-agent <orch_id> evaluator 99
bin/cmux-sprint poll-agents <orch_id> evaluator

# agents-only
Agent(name="evaluator", subagent_type="critical-analyst", model="sonnet", prompt=<prompt>)
```

Read `/tmp/caf_orch/<id>/evaluation_report.md`.
- **SHIP** → Phase 8
- **NEEDS REWORK** → Phase 7

---

## Phase 7: Feedback Loop

Max **2 correction iterations**. If still failing — escalate.

For each failing lead:
1. Read specific feedback from evaluation_report.md
2. Route correction — cmux: `bin/cmux-sprint send-agent` | agents-only: re-launch with amended prompt
3. Wait for re-completion
4. Re-merge: `bin/cmux-sprint merge-leads <orch_id>`
5. Re-evaluate: re-launch evaluator (same output path — overwrites)
6. Check verdict → SHIP (Phase 8) | retry | escalate after 2

Escalation format after 2 failed iterations: `global-skills/orchestrate/templates/escalation-format.md`

---

## Phase 8: Final Synthesis + Deliver

```bash
bin/session-event task_done '<task>'
```

Write unified summary to `/tmp/caf_orch/<id>/report.md` and deliver to user.
Delivery format: `global-skills/orchestrate/templates/delivery-format.md`

---

## Hard Rules

- PO always aligns with user first — never guess scope
- Acceptance criteria come from the user in Phase 1 — never invent them
- PO never just agrees — challenge wrong tools, missing edge cases, simpler approaches, arbitrary constraints, symptom-solving. State the objection, give reasoning, let user decide.
- Leads are planners + delegators only — no Read, Edit, Grep, Glob, or code writing; enforced by lead.md (tools: Agent, Task, Write, Bash-IPC-only)
- Workers (builders, researchers, validators) are spawned by leads, not by PO
- Research is shared — deduplicate before launching; pass findings to all leads that need them
- Leads work in worktrees — never on main branch directly
- Domain registration before file touch — no silent conflicts
- Shared validator for test runs — leads don't spawn their own
- Broadcast for critical findings — don't let one lead's discovery stay local
- Full-picture evaluator always runs — even if all leads self-report PASS
- Max 2 correction iterations before escalating to user
- Leads ask PO when uncertain — never decide autonomously on scope/approach tradeoffs
- All IPC: plain JSON + plain text — never AAAK in prompts or IPC
- Every lead must produce a criterion check + decision log
- Language/tool choice is always a decision point — surface options + tradeoffs, never silently default; "match what's already there" is not a valid reason on its own
- **Priority order: quality/consistency/robustness → speed → token efficiency** — never sacrifice correctness; parallelize for speed but not at cost of quality; haiku only for mechanical no-reasoning work, sonnet minimum for any coding or analysis
- **Parallel within waves** — all agents per wave launch in one message; never serialize parallelizable work

---

## Failure Handling (mid-execution)

- Lead fails mid-run: read error, inject corrected context via `send-agent`, or spawn fresh lead
- Lead going wrong direction: `abort-agent` with redirect
- Multiple failures in same lead: escalate to user with what was tried
- Merge conflict: read both sides, resolve manually, never `git checkout --ours` blindly
- Broadcast not acknowledged: re-send; no response after 60s → abort + redirect affected leads
