# Orchestrator Reference

Companion document to [orchestrator.md](orchestrator.md). Contains full templates for protocols summarized in the main agent file.

---

## Build Wave Template (Wave 1)

```python
# Write plan before spawning builders
Write(f"/tmp/caf_{SESSION_ID}_plan.md", plan_content)

# Wave 1: watchdog + guardian (if modifying existing code) + parallel builders — ONE message
Agent(
    subagent_type="agent-watchdog",
    name="watchdog",
    run_in_background=True,
    prompt=f"""Monitor parallel batch for session {SESSION_ID}.
    Agents: builder-1, builder-2 (if applicable).
    Expected outputs: /tmp/caf_{SESSION_ID}_build_N.md
    Alert via SendMessage(to='orchestrator') if any agent stalls >3min or errors.
    State: /tmp/caf_{SESSION_ID}_watchdog.md"""
)
Task(
    subagent_type="builder",
    name="builder-1",
    model="sonnet",  # or haiku — see model selection in orchestrator.md
    maxTurns=20,
    prompt=f"""## Context (pre-digested)
{conventions}
{relevant_facts}
{relevant_gotchas}

## Task
Read /tmp/caf_{SESSION_ID}_plan.md section 'Build Task 1'.
Execute it. Write status to /tmp/caf_{SESSION_ID}_build_1.md.
Prepend [TIMESTAMP] AGENT:builder-1 STATUS:STARTED to /tmp/caf_{SESSION_ID}_watchdog.md
SESSION_ID: {SESSION_ID}"""
)
```

---

## Recovery Loop Protocol

```python
SESSION_ID = "orch_MMDD_NN"   # e.g. "orch_0406_01"

Write(f"/tmp/caf_{SESSION_ID}_plan.md", f"""
# CAF Plan
SESSION_ID: {SESSION_ID}
TASK: {task}
CREATED: {now}
CURRENT_ITERATION: 1
MAX_ITERATIONS: 5
GIT_ROLLBACK_BASE: {GIT_HASH}

## Goals
{goals}

## Acceptance Criteria 1
{criteria}

## Build Task 1
{build_instructions}

## Dead Ends
(none yet)

## Iteration History
| N | Build | Validate | Debug | Approach |
|---|-------|----------|-------|----------|
""")

iteration = 1
MAX = 5

while iteration <= MAX:
    # WAVE: BUILD
    Task(builder-{iteration}, model=<haiku|sonnet>, maxTurns=<12|20>,
        "Read /tmp/caf_{SESSION_ID}_plan.md Build Task {iteration}. "
        "Execute. Write /tmp/caf_{SESSION_ID}_build_{iteration}.md.")

    build_status = read STATUS from /tmp/caf_{SESSION_ID}_build_{iteration}.md

    if build_status in ["BLOCKED", "FAILED"]:
        write synthetic FAIL validate report
    else:
        # If guardian alerted for this iteration, skip validator — regression already confirmed
        Task(validator-{iteration}, model="haiku", maxTurns=15,
            "Read /tmp/caf_{SESSION_ID}_plan.md Acceptance Criteria {iteration}. "
            "Read /tmp/caf_{SESSION_ID}_build_{iteration}.md. "
            "Write PASS/FAIL to /tmp/caf_{SESSION_ID}_validate_{iteration}.md.")

        validate_status = read STATUS from /tmp/caf_{SESSION_ID}_validate_{iteration}.md

    if validate_status == "PASS":
        # QUALITY GATE: critical-analyst reviews on complex/critical tasks
        if quality_need in ["critical", "high"] or complexity in ["complex", "massive"]:
            Agent(name=f"evaluator-{iteration}", subagent_type="critical-analyst", model="sonnet", maxTurns=20,
                prompt=f"""Post-build quality review. You are the quality gate between validator PASS and commit.

Read these files:
1. /tmp/caf_{SESSION_ID}_plan.md — original goals and acceptance criteria
2. /tmp/caf_{SESSION_ID}_build_{iteration}.md — what was built
3. /tmp/caf_{SESSION_ID}_validate_{iteration}.md — validator results
4. Run `git diff` to see actual changes

Evaluate:
1. Does the change ACTUALLY solve the stated problem, or just pass the tests?
2. Are there edge cases the acceptance criteria missed?
3. Is there a simpler way to achieve this?
4. Blast radius — did we change more than necessary?
5. Any security, performance, or maintainability concerns?

Output to /tmp/caf_{SESSION_ID}_evaluate_{iteration}.md:
STATUS: APPROVE | CONCERNS | REJECT
[If CONCERNS: list specific issues, but don't block commit]
[If REJECT: explain what's wrong — this triggers a debug cycle]""")

            eval_status = read STATUS from /tmp/caf_{SESSION_ID}_evaluate_{iteration}.md

            if eval_status == "REJECT":
                # Treat as validation failure — enter debug cycle
                # Copy evaluator concerns to validate file so debugger sees them
                continue  # back to debug wave

        # All gates passed — commit
        Agent(name="git-commit", model="haiku", maxTurns=5,
            prompt=f"Run: git add -A && git commit -m 'orchestrate: iteration {iteration} passed'. Return the commit hash.")
        SendMessage(to="watchdog", message="WATCHDOG_STOP")
        report_success()
        return

    # WAVE: DEBUG
    Task(debugger-{iteration}, model="sonnet", maxTurns=25,
        "Read /tmp/caf_{SESSION_ID}_validate_{iteration}.md (failures). "
        "Read /tmp/caf_{SESSION_ID}_build_{iteration}.md. "
        "Read /tmp/caf_{SESSION_ID}_plan.md Dead Ends (do NOT repeat). "
        "Write fix plan to /tmp/caf_{SESSION_ID}_debug_{iteration}.md.")

    debug_status = read STATUS from /tmp/caf_{SESSION_ID}_debug_{iteration}.md

    if debug_status in ["ESCALATE", "DEAD_END"]:
        escalate()
        return

    # RE-PLAN: increment CURRENT_ITERATION, write Build Task N+1, Acceptance Criteria N+1,
    # append Dead Ends, add row to Iteration History
    iteration += 1

escalate()  # hit MAX_ITERATIONS
```

**Escalation format:**
```
[ORCHESTRATOR] Escalating after N iteration(s).
Task: {original task}
Last error: {one line from validate_N.md}
Rollback available: git reset --hard {GIT_ROLLBACK_BASE}
```
Then auto-run: `Skill("rollback", args=SESSION_ID)`

---

## Adaptive Iteration Budget

Don't use a flat max. Estimate complexity after research phase and set the budget:

| Complexity | Max iterations | Criteria |
|---|---|---|
| Simple | 3 | Clear error message, one file, obvious fix path |
| Medium | 6 | Multiple files, unclear cause, needs investigation |
| Hard | 10 | Architectural, no clear error, cross-cutting concern |

Write the budget to the plan file. If you hit the budget, stop — don't auto-extend.

---

## Spiral Detection (CRITICAL)

Track a health check after each build→validate iteration: files modified, tests before/after, worse Y/N, approach category.

**Hard rules:**

1. **Test regression → immediate revert.** Tests went DOWN → `git revert HEAD` and rethink. Do NOT "fix the fix."
2. **Same-file spiral.** Same file modified 3+ times across iterations → stop and ask user.
3. **Same-approach spiral.** Same approach category 3 times → stop and ask user.
4. **Blast radius creep.** Total modified files > 5 and unsolved → stop and ask user.
5. **No-progress detector.** Last 2 iterations produced no new verified info → stop and ask user.

### Kill-and-Reassign (instead of just escalating)

When spiral is detected: write a `DEAD_END` entry to plan file (what was tried, why it failed, what was learned), then spawn a **fresh builder** with ONLY the verified facts. The fresh builder reads DEAD_END entries to avoid repeating mistakes:

```python
Agent(name="fresh-builder", model="sonnet", maxTurns=20,
  prompt=f"Previous approach failed. Read /tmp/caf_{SESSION_ID}_plan.md for dead ends to avoid. "
         f"Verified facts: [list only confirmed facts with citations]. "
         f"Find a NEW approach to: [problem]. Do not retry: [dead end approaches].")
```

### Blast Radius Control

Before editing any file:
1. Use Grep to find imports and references — check what depends on it
2. If more than 3 files depend on it, explain blast radius to user before proceeding
3. Prefer adding new code over modifying existing code when both work
4. When modifying shared code, run FULL test suite after

---

## Pre-Edit Gate (for builders)

Include in builder prompts when editing existing code (not greenfield). Before every Edit/Write, builders must:

1. **Grounding check**: "file:line X proves this change is correct because [reason]." If you cannot write this sentence, go back to research.
2. **Duplication check**: Grep for the function name first. Exact duplicate: reuse. Near duplicate: extend.
3. **Redundancy check**: After edit, verify no redundant imports or dead code left over.

For changes affecting shared code (3+ dependents), spawn a haiku guardian:
```python
Agent(model="haiku", prompt="Validate this change is correct.
File: [path], Lines: [range], Change: [description]
Check: 1) Does function still exist at cited location? 2) Does change match intent? 3) Obvious errors?
Reply: VALID or INVALID with reason.")
```

---

## Background Guardian Protocol

Spawn at recovery loop start alongside watchdog. Stays alive across all iterations. Catches regressions before the full validator runs.

**When to spawn:**

| Task type | Spawn guardian? |
|-----------|----------------|
| Modifies existing code | YES |
| Pure greenfield (new files only) | NO |
| Refactor / restructure | YES |

**Template:**

```python
Agent(
    name="guardian",
    model="haiku",
    run_in_background=True,
    maxTurns=20,
    prompt=f"""You are the background regression guardian for session {SESSION_ID}.

    RULES:
    1. Watch /tmp/caf_{SESSION_ID}_watchdog.md for builder COMPLETED lines
    2. When a builder completes, run the project's test command (from /tmp/caf_project_context.md)
    3. ON SUCCESS: write NOTHING.
    4. ON FAILURE: write to /tmp/caf_{SESSION_ID}_guardian.md:
       GUARDIAN_ALERT: REGRESSION
       ITERATION: N
       FAILING_TESTS: [exact output, first 300 chars]
       FILES_TOUCHED: [from git diff --name-only]
       Then SendMessage(to='orchestrator', summary='REGRESSION', message='Tests failing after builder-N.')
    5. ON TEST COMMAND NOT FOUND: write SKIPPED once, then stop.
    6. Do NOT diagnose. Report regression evidence only.
    7. After 3 consecutive silent successes, check every-other-build only.

    Baseline: GIT_ROLLBACK_BASE. If tests already fail at baseline, only alert on NEW failures."""
)
```

**Token cost:** ~150 tok/check (silent), ~250 tok/check (alert). Saves ~3,000-5,000 tokens per caught regression.

---

## Watchdog Protocol

Always spawn alongside any batch of 2+ agents:

```python
Agent(
    subagent_type="agent-watchdog",
    name="watchdog",
    run_in_background=True,
    prompt=f"""Monitor parallel batch for orchestrator session {SESSION_ID}.
    Agents: [list names]
    Expected outputs: [list /tmp paths]
    Alert via SendMessage(to='orchestrator') if any agent errors, stalls >3min, or produces no output.
    State: /tmp/caf_{SESSION_ID}_watchdog.md"""
)
```

Each agent MUST prepend to the watchdog state file:
```
[ISO_TIMESTAMP] AGENT:<name> STATUS:<STARTED|IN_PROGRESS|COMPLETED|FAILED> TASK:<brief> OUTPUT:<path>
```

On alert: critical agent failing → kill batch, re-spawn with simpler prompt. Non-critical → let others continue, re-spawn only the failed one.

---

## Context Injection Template

Standard prompt template for all sub-agents:

```python
prompt = f"""
## Session Context
Read /tmp/caf_{SESSION_ID}_context.md FIRST — everything discovered this session is there.
Do NOT re-research anything already in it.

## Project Context (pre-digested)
- Project: {name}, {lang}, {test_cmd}
- Known facts: {relevant_bullets}
- Gotchas: {known_gotchas}

## Your Task
{specific_task_description}

## Output
Return findings in your final message: file paths, line numbers, actual values.
SESSION_ID: {SESSION_ID}
"""
```

Per-agent injection budget: researcher ~500 tok, builder ~300 tok, debugger ~400 tok, validator ~150 tok.
