# /orchestrate — Unified Smart Orchestrator

**Purpose**: Single entry point for all complex work. Analyzes the task, picks the right team and strategy, executes with role separation, and self-corrects on failure. Replaces `/solve`.

---

## Usage

```
/orchestrate [task description]
/orchestrate                     ← omit args to trigger interview mode
```

---

## What It Does

The Orchestrator agent receives your task and runs the full intelligence pipeline:

1. **Clarify** — If the task is ambiguous, asks 1-3 focused questions before planning
2. **Classify** — Complexity, task type, quality need, codebase scope (4-dimension analysis)
3. **Select strategy** — Direct / Research / RLM / Orchestrate / Brainstorm / Skills
4. **Assemble team** — Right agents, right models, right maxTurns per role
5. **Execute** — Parallel where possible, sequential where dependent
6. **Self-correct** — On failure: Debug → Re-plan → Rebuild (up to 5 iterations)
7. **Report** — Executive summary with what changed, test results, rollback info

---

## Strategy Selection (automatic)

The orchestrator picks the strategy. You don't need to specify it.

| Signal | Strategy |
|--------|----------|
| Single action, < 3 steps | Direct — does it inline |
| Unknown scope ("how does X work?") | RLM — iterative exploration |
| Broad codebase ("audit everything") | RLM — prevents context rot |
| 2+ independent workstreams | Orchestrate — parallel team |
| Bug with clear error trace | Recovery loop — builder → validator → debugger |
| Complex design decision | Brainstorm + Plan |
| Matches a skill | Delegates to skill first |

**Fusion** is never auto-selected. See "When to suggest Fusion" below.

---

## Team Composition (automatic)

The orchestrator assembles the right team per task:

| Role | Agent | Model | When Used |
|------|-------|-------|-----------|
| Implementer | `builder` | sonnet | Any code change |
| Checker | `validator` | haiku | After every build |
| Fixer | `debugger` | sonnet | After any failure |
| Researcher | `researcher` | sonnet | Unknown scope |
| Critic | `critical-analyst` | sonnet | Challenging hypotheses |
| Mapper | `scout-report-suggest` | sonnet | Codebase exploration |
| Monitor | `agent-watchdog` | haiku | Background, any parallel batch |
| Architect | `project-architect` | opus | System design |

You never need to specify the team. But you can hint:

```
/orchestrate "Add caching to the API — prioritize correctness over speed"
/orchestrate "Refactor auth module — keep changes small and reviewable"
```

---

## Self-Correction Loop

When implementation fails, the orchestrator runs a structured recovery loop instead of retrying blindly:

```
Write plan → Builder → Validator
                          ↓ FAIL
                       Debugger (reads error, writes fix plan)
                          ↓
                    Update plan (add dead end, new approach)
                          ↓
                       Builder (round 2)
                          ↓
                       Validator
                          ↓ FAIL again → repeat up to 5×
                          ↓ PASS → commit + report
```

Dead ends are tracked so the same approach is never tried twice. After 5 failed iterations, the orchestrator escalates to you with a full audit trail and rollback command.

---

## When to Suggest Fusion

The orchestrator will **suggest** (not auto-run) Fusion when:

- Multiple valid solution architectures exist and correctness is hard to determine upfront
- The task is irreversible (production schema changes, published APIs)
- You've asked for the "best" solution explicitly, not just "a" solution
- The recovery loop has tried 2+ approaches and the problem is design-level, not implementation-level

When suggesting, the orchestrator will say:

> "This looks like a case where Fusion (Best-of-N) could find a better solution than a single approach. Want me to run 3 parallel implementations and fuse the best? It costs ~3× the tokens but gives you a scored comparison. Type `/fusion [task]` or say 'yes' to proceed."

You decide. If you say yes, it spawns Fusion. If not, it proceeds with its best single approach.

---

## Compared to Old Commands

| Old | New |
|-----|-----|
| `/solve "fix this bug"` | `/orchestrate "fix this bug"` |
| `/orchestrate "implement X"` | `/orchestrate "implement X"` (unchanged) |
| `/fusion "..."` | Still available standalone — now also suggested by orchestrate when appropriate |

---

## Examples

```
/orchestrate "the login endpoint returns 500 for valid users"
→ Interviews if needed, traces error, recovery loop

/orchestrate "add rate limiting to all API routes"
→ Research → plan → builder team → validator → report

/orchestrate "how does the auth system work?"
→ RLM exploration → architecture summary

/orchestrate
→ Interview mode — asks what you need
```

---

## Dynamic Subagents (project-specific + issue-specific)

The orchestrator can spawn purpose-built subagents on the fly — no agent file needed. These are more accurate and cheaper than forcing a general agent to handle specialized work.

The orchestrator will do this automatically when it detects:
- A task requires project-specific domain knowledge (your schema, your DSL, your custom formats)
- A narrow, repetitive operation would run faster as a focused 5-turn haiku agent than a general 20-turn sonnet
- The fixed team (builder/validator/debugger) isn't the right fit for the sub-problem

You can also hint at it:

```
/orchestrate "validate all migration files against our schema rules"
→ Orchestrator reads the schema, creates a migration-validator agent inline,
  runs it on all migration files, reports results. No general agent overhead.

/orchestrate "find every auth failure in the last 24h of logs and group by user"
→ Spawns a focused log-parser haiku agent. Done in 5 turns, not 20.
```

The rule: **smallest model that can do it, tightest scope possible, explicit stop condition.** Dynamic subagents shouldn't think — they should execute a narrow job and stop.

---

## Token Efficiency

- Watchdog (haiku) runs in background — doesn't block
- Validator is always haiku — fast and cheap
- RLM only triggers for genuinely broad/unknown scope
- Fusion is opt-in, never default
- Recovery loop caps at 5 iterations with escalation to human
- Every spawned agent has explicit `maxTurns` — no silent runaway agents

---

## Invoke

```
Agent(subagent_type="orchestrator", description="Unified orchestration", prompt="<user's full message and any args>")
```
