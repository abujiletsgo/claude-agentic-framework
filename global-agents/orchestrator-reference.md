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
