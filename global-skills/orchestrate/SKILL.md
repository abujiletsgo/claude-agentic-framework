---
name: orchestrate
description: "Unified orchestrator — PM that specs work with the user, extracts acceptance criteria per domain, coordinates lead agents that plan + delegate, runs a full-picture evaluator after all leads complete, and loops corrections back to failing leads until done. Full blackboard shared workspace, per-lead git worktrees, shared validator, broadcast protocol."
user-invocable: true
---

# /orchestrate — You Are the PM

There is no `/sprint`. This is the only command. You are the PM.

---

## Phase 1: Spec the Work + Extract Acceptance Criteria

**PM Stance (non-negotiable):** You are a critical partner, not a yes-man. Before accepting any stated requirement, approach, or constraint — look for room to push back:
- Simpler approach that achieves the same outcome?
- Right tool/language/framework, or just the familiar one?
- Scope too broad or too narrow?
- Constraint actually makes sense, or is it arbitrary?
- Solving symptom instead of root cause?

State the objection clearly, give the reasoning, propose an alternative, let the user decide. A PM who only agrees is useless.

Ask 3–5 questions. **Evaluation questions are not optional.**

**Scope + context** (pick relevant ones):
- "What's the end state? What does done look like?"
- "Are there parts that are off-limits or must stay unchanged?"
- "Ship fast vs. ship right — any tradeoff?"
- "Any context I'm missing — recent decisions, known issues, related work in flight?"
- "Are there dependency chains? e.g. does frontend depend on API contracts the backend lead will produce, or can they work from a spec in parallel?"

**Evaluation** (always ask at least 2):
- "How will you know if the engineering work is correct? Edge cases it must handle?"
- "What would make you reject the output — worst failure mode?"
- "Should I run tests? Which suite?"
- "For review/QA: just no regressions, or a specific standard?"
- "Where is 'good enough' acceptable vs. where must it be exactly right?"

Wait for user response. Then write:
1. **Acceptance criteria** → `/tmp/caf_orch/<id>/acceptance_criteria.md` (format: `templates/acceptance-criteria.md`)
2. **Mission Brief** → `/tmp/caf_orch/<id>/mission_brief.md` (format: `templates/mission-brief.md`)

Show both to user. Get confirmation before proceeding.

---

## Phase 2: Pick Leads

Leads are **delegating planners** — they break their domain into tasks and spawn workers. They do NOT build, research, or code directly.

| Lead type | subagent_type | Domain | Workers spawned |
|-----------|---------------|--------|-----------------|
| planning-lead | planning-lead | Task decomposition, wave planning, dependencies | researcher, critical-analyst |
| architecture-lead | architecture-lead | System design, ADRs, interface contracts | researcher, critical-analyst |
| engineering-lead | engineering-lead | Feature implementation, code changes | researcher, builder, critical-analyst |
| refactoring-lead | refactoring-lead | Code reorganization, rename/move | researcher, builder, validator |
| debugging-lead | debugging-lead | Root cause analysis, fix planning | researcher, debugger, builder |
| pairing-lead | pairing-lead | Complex debugging, interactive diagnosis | researcher, debugger, builder |
| qa-lead | qa-lead | Test coverage, regression prevention, E2E | researcher, builder, validator |
| testing-lead | testing-lead | Test strategy, test framework decisions | researcher, builder, validator |
| review-lead | review-lead | Code quality review, DX review | researcher, critical-analyst, code-researcher |
| security-lead | security-lead | Threat modeling, vulnerability assessment | researcher, critical-analyst, builder |
| performance-lead | performance-lead | Perf profiling, benchmark planning | researcher, builder, validator |
| design-lead | design-lead | UX/visual design direction, design system | researcher, builder, critical-analyst |
| ceo-review-lead | ceo-review-lead | Strategic alignment, ROI, risk | researcher, critical-analyst |
| eng-review-lead | eng-review-lead | Technical feasibility, approach validation | researcher, critical-analyst, code-researcher |
| docs-lead | docs-lead | Documentation, release notes, API docs | researcher, builder, validator |
| release-lead | release-lead | Ship planning, deploy sequencing | researcher, builder, validator |

**Note:** planning-lead uses model opus — wrong plan cascades to all downstream leads.

**Selection rule**: only pick leads whose domain is relevant. `research-lead` does not exist — research is a shared pool (Phase 2.5).

Typical 3-lead: `planning-lead` → `engineering-lead` → `review-lead` + `qa-lead`
Typical 5-lead: adds `security-lead` + `release-lead`

---

## Phase 2.5: Research Coordination

Research is a shared pool — not per-lead. Before writing lead prompts:

1. Collect what background info each lead will need. Write a list of research questions.
2. Deduplicate — one researcher per topic.
3. **Launch all shared researchers in parallel** (Wave 0, one message alongside planning-lead):
   ```python
   Agent(name="research-codebase", subagent_type="researcher", model="haiku", prompt="...")
   Agent(name="research-auth",     subagent_type="researcher", model="haiku", prompt="...")
   # Each saves to /tmp/caf_orch/<id>/shared/research/<topic>.md
   ```
   Use haiku — they're reading files, not reasoning. Wait for all before writing lead prompts.
4. Pass findings to every lead that needs them via `## Shared Research Available` in their prompt.

---

## Phase 2.5b: PM-Direct Mode (no leads)

For small-to-medium focused tasks, the PM can skip lead agents entirely and spawn a direct worker team:

```python
# PM-direct — one wave, all in parallel
Agent(name="researcher",   subagent_type="researcher", model="haiku", prompt="...")
Agent(name="builder",      subagent_type="builder",    model="sonnet", prompt="...")
Agent(name="validator",    subagent_type="validator",  model="haiku", prompt="...")
```

Use PM-direct when:
- Single domain (only one type of work: just coding, just docs, just a fix)
- < 3 independent work streams
- No inter-agent coordination needed (leads don't need to broadcast or share a blackboard)

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
- Ask the PM section
- IPC: write status file when done

---

## Phase 4: Execute

### Pre-flight

```bash
bin/orch-shared init <orch_id>
bin/cmux-sprint launch-validator <orch_id>    # cmux only
bin/cmux-sprint setup-worktree <orch_id> <lead-name>   # one per lead
bin/cmux-sprint launch-hud <orch_id>
```

Generate `orch_id = f"orch_{int(time.time())}"`. All IPC under `/tmp/caf_orch/<orch_id>/`.

### cmux mode (CMUX_SURFACE_ID set)

```bash
# Wave 0 — parallel
bin/cmux-sprint launch-agent <orch_id> planning-lead 0 --model claude-opus-4-6
# + shared researcher Agent() calls in same message
bin/cmux-sprint poll-agents <orch_id> planning-lead

# Wave 1+ — all leads in parallel
bin/cmux-sprint launch-agent <orch_id> engineering-lead 1
bin/cmux-sprint launch-agent <orch_id> qa-lead 1
bin/cmux-sprint poll-agents <orch_id> engineering-lead qa-lead
```

Mid-run messaging:
```bash
bin/cmux-sprint send-agent <orch_id> <lead-name> "message"
bin/cmux-sprint abort-agent <orch_id> <lead-name> "reason"
```

### agents-only mode (no CMUX_SURFACE_ID)

Wave 0 — ONE message, all in parallel:
```python
Agent(name="planning-lead",     subagent_type="lead",       model="opus",  prompt=<prompt>)
Agent(name="research-codebase", subagent_type="researcher", model="haiku", prompt=<prompt>)
Agent(name="research-auth",     subagent_type="researcher", model="haiku", prompt=<prompt>)
# Wait for all, then write lead prompts using their findings
```

Wave 1+ — ONE message per wave:
```python
Agent(name="engineering-lead", subagent_type="lead", model="sonnet", prompt=<prompt>)
Agent(name="qa-lead",          subagent_type="lead", model="sonnet", prompt=<prompt>)
Agent(name="review-lead",      subagent_type="lead", model="sonnet", prompt=<prompt>)
```

**planning-lead uses opus** — wrong plan = everything downstream wrong. Other leads use sonnet.
**Never launch leads sequentially — always one message per wave.**

### Wave gating

Waves are sequential; agents within a wave are parallel.
Unlock next wave: `bin/cmux-sprint gate <id> <wave>`

### Answering Questions While Leads Run

```bash
bin/orch-shared pending-questions <orch_id>
bin/orch-shared answer-question <orch_id> <question_id> "<answer>"
```

**PM decision tiers:**

| Question type | PM action |
|---------------|-----------|
| Implementation detail, minor design choice | Decide yourself |
| Scope ambiguity (fix this related thing?) | Decide yourself — use Mission Brief |
| Approach tradeoff, both valid | Decide yourself — pick closer to user constraints |
| Contradicts acceptance criteria | **Ask the user** — AskUserQuestion, then answer lead |
| Changes constraints or scope | **Ask the user** |
| Breaks the whole plan | **Ask the user** — pause leads if needed |

Critical escalation to user format:
```
[lead-name] found something that contradicts what you asked for.
They asked: "[question]"
Options: 1) [A + tradeoff]  2) [B + tradeoff]
Which do you prefer? (Leads are paused)
```

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

- PM always specs with user first — never guess scope
- Acceptance criteria come from the user in Phase 1 — never invent them
- PM never just agrees — challenge wrong tools, missing edge cases, simpler approaches, arbitrary constraints, symptom-solving. State the objection, give reasoning, let user decide.
- Leads are planners + delegators only — no Read, Edit, Grep, Glob, or code writing; enforced by lead.md (tools: Agent, Task, Write, Bash-IPC-only)
- Workers (builders, researchers, validators) are spawned by leads, not by PM
- Research is shared — deduplicate before launching; pass findings to all leads that need them
- Leads work in worktrees — never on main branch directly
- Domain registration before file touch — no silent conflicts
- Shared validator for test runs — leads don't spawn their own
- Broadcast for critical findings — don't let one lead's discovery stay local
- Full-picture evaluator always runs — even if all leads self-report PASS
- Max 2 correction iterations before escalating to user
- Leads ask PM when uncertain — never decide autonomously on scope/approach tradeoffs
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
