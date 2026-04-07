# Orchestrator Reference

Companion document to [orchestrator.md](orchestrator.md). Contains detailed protocols, templates, and examples extracted to reduce the main agent file size.

## Strategy Execution Examples

### Research Wave Example (Wave 0)

```python
# Wave 0: Research — spawn both in ONE message
Agent(
    name="researcher-1",
    subagent_type="researcher",
    maxTurns=25,
    prompt=f"""
## Pre-digested Context (DO NOT re-read these files)
{project_ctx_summary}
{facts_summary}
{arch_summary}

## Research Question
[First specific question — NOT the raw user request]

## What's Already Known
[bullets from context layers]

## What to Find (gaps only)
[specific unknowns]

Write findings to /tmp/caf_{SESSION_ID}_research_1.md
"""
)
Agent(
    name="researcher-2", 
    subagent_type="researcher",
    maxTurns=25,
    prompt=f"""
## Pre-digested Context (DO NOT re-read these files)
{project_ctx_summary}
{facts_summary}

## Research Question
[Second specific question — different angle from researcher-1]

## What's Already Known
[bullets]

## What to Find
[different specific unknowns]

Write findings to /tmp/caf_{SESSION_ID}_research_2.md
"""
)
```

### Build Wave Example (Wave 1)

```python
# Write plan before spawning builders
Write(f"/tmp/caf_{SESSION_ID}_plan.md", plan_content)

# Wave 1: Multiple parallel builders + watchdog in ONE message
Agent(
    subagent_type="agent-watchdog",
    name="watchdog",
    run_in_background=True,
    prompt=f"""Monitor parallel batch for session {SESSION_ID}.
    Agents: builder-1, builder-2, builder-3 (if applicable).
    Expected outputs: /tmp/caf_{SESSION_ID}_build_N.md
    Alert via SendMessage(to='orchestrator') if any agent stalls >3min or errors.
    State: /tmp/caf_{SESSION_ID}_watchdog.md"""
)
Task(
    subagent_type="builder",
    name="builder-1",
    model="sonnet",  # or haiku — see model selection below
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
# Add builder-2, builder-3 here if tasks are independent
```

### Validator Example

```python
Task(
    subagent_type="validator",
    name=f"validator-{iteration}",
    model="haiku",
    maxTurns=15,
    prompt=f"""Read /tmp/caf_{SESSION_ID}_plan.md 'Acceptance Criteria {iteration}'.
Read /tmp/caf_{SESSION_ID}_build_{iteration}.md.
Run the checks. Write PASS/FAIL to /tmp/caf_{SESSION_ID}_validate_{iteration}.md.
SESSION_ID: {SESSION_ID}"""
)
```

### RLM Example

```python
Task(
    subagent_type="rlm-root",
    description="Explore authentication system",
    prompt=f"""
## Pre-digested Project Context (DO NOT re-read source files)
{project_summary}
{relevant_facts}
{relevant_arch_sections}

## Exploration Task
[user's question/task]

## What's Already Known
[bullets from context layers]

## What to Find (gaps only)
[specific unknowns]

## Expected Outcome
[what we need to learn]

Return: Executive summary, key findings, file locations, recommended next steps.
"""
)
```

---

## Context Loading Phase

### Rule 2: Context Loading Phase (for any task involving a codebase or system you don't fully know)

**Before planning or building, spawn parallel chunk-reader agents to load context.**

You cannot read files yourself. Instead of guessing or working from stale injected context, spawn haiku agents — each owns one file or section — and have them return structured summaries. Then orchestrate from those summaries.

#### When to run this phase

**Skip entirely if**: the task was already scoped this session (prior agents already read the relevant files), or the task is self-contained (no codebase knowledge needed), or the user gave you all required context in the prompt.

**Run only for**: files/modules not yet read this session, unfamiliar codebases, or tasks where guessing file contents would produce a wrong plan.

**Only spawn chunk-readers for what you actually lack.** If you already know the test command from session context, skip `ctx-project`. If the task doesn't touch architecture, skip `ctx-arch`. Start from what you know; spawn only for genuine gaps.

#### How to run it

Identify the relevant context sources, then spawn one haiku agent per chunk — all in one message:

```python
# Spawn all chunk-readers in ONE message
Agent(
    name="ctx-facts",
    model="haiku", maxTurns=6,
    prompt="""Read .claude/FACTS.md. Return a structured summary:
    ## Confirmed Facts (bullet list)
    ## Gotchas (bullet list)
    ## Key Paths (bullet list)
    ## Gaps / Unclear Items (anything that seems incomplete)
    Be exhaustive on Gotchas — these prevent bugs."""
)
Agent(
    name="ctx-arch",
    model="haiku", maxTurns=6,
    prompt="""Read .claude/ARCHITECTURE.md section [relevant section].
    Return:
    ## Component Map (what calls what)
    ## Data Flow (how data moves through the system)
    ## Blast Radius (what breaks if X changes)
    ## Gaps / Unclear Items"""
)
Agent(
    name="ctx-project",
    model="haiku", maxTurns=6,
    prompt="""Read /tmp/caf_project_context.md if it exists (else skip).
    Return:
    ## Test Command
    ## Conventions (naming, patterns)
    ## Key Entry Points
    ## Gaps / Unclear Items"""
)
Agent(
    name="ctx-task-scope",
    model="haiku", maxTurns=8,
    prompt="""For task: [task description]
    Read the relevant source files (grep for entry points, read 50 lines each).
    Return:
    ## Files in Scope (paths + purpose)
    ## Current Behavior (what the code does now)
    ## Dependencies (what these files import/call)
    ## Gaps / Unclear Items (anything you couldn't determine)"""
)
```

#### After chunk-readers return

1. **Synthesize**: Combine their summaries into your working context
2. **Identify gaps**: Collect all "Gaps / Unclear Items" across agents
3. **Fill gaps**: For each significant gap, spawn a targeted follow-up researcher:
   ```python
   Agent(
       name="gap-researcher-1",
       model="sonnet", maxTurns=15,
       prompt="""Specific question: [gap from chunk-reader].
       Look in: [files the chunk-reader flagged].
       Return a precise answer — not a summary, just the answer to the question."""
   )
   ```
4. **Proceed** to planning and building with complete, verified context

#### Design rules for chunk-readers

- **Always haiku** — they read and summarize, no judgment needed
- **One file or section per agent** — never "read everything"
- **Structured return format** — always include a "Gaps" section
- **maxTurns=6-8** — if it needs more, the chunk is too large, split it
- **Parallel always** — all chunk-readers in one message

---

## Recovery Loop Protocol

```python
SESSION_ID = "orch_MMDD_NN"   # generate mentally, e.g. "orch_0406_01"
# GIT_HASH: instruct your first agent to run "git rev-parse HEAD" and return it

# Write plan BEFORE spawning any agents
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

# Spawn guardian alongside watchdog at loop start (if modifying existing code)
# See Background Guardian Protocol below for template
# Guardian runs in background for ALL iterations — no need to re-spawn per iteration

while iteration <= MAX:
    # WAVE: BUILD
    Task(builder-{iteration}, model=<haiku|sonnet>, maxTurns=<12|20>,
        "Read /tmp/caf_{SESSION_ID}_plan.md Build Task {iteration}. "
        "Execute. Write /tmp/caf_{SESSION_ID}_build_{iteration}.md.")

    build_status = read STATUS from /tmp/caf_{SESSION_ID}_build_{iteration}.md

    if build_status in ["BLOCKED", "FAILED"]:
        write synthetic FAIL validate report
    else:
        # CHECK: Did guardian already alert a regression?
        # If /tmp/caf_{SESSION_ID}_guardian.md has a GUARDIAN_ALERT for this iteration:
        #   → Skip validator (regression already confirmed) → go straight to debug
        #   → Saves ~500-800 tokens (validator run + report)
        # If no guardian alert (or guardian not spawned):
        #   → WAVE: VALIDATE — always
        Task(validator-{iteration}, model="haiku", maxTurns=15,
            "Read /tmp/caf_{SESSION_ID}_plan.md Acceptance Criteria {iteration}. "
            "Read /tmp/caf_{SESSION_ID}_build_{iteration}.md. "
            "Write PASS/FAIL to /tmp/caf_{SESSION_ID}_validate_{iteration}.md.")

        validate_status = read STATUS from /tmp/caf_{SESSION_ID}_validate_{iteration}.md

    if validate_status == "PASS":
        # Spawn micro-agent to commit
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

    # RE-PLAN (coordinator work — update plan file)
    # - Increment CURRENT_ITERATION
    # - Write "Build Task N+1" from debugger's "Files to Change"
    # - Write "Acceptance Criteria N+1"
    # - Append to Dead Ends
    # - Add row to Iteration History
    iteration += 1

escalate()  # hit MAX_ITERATIONS
```

**Escalation:**
```
[ORCHESTRATOR] Escalating after N iteration(s).
Task: {original task}
Last error: {one line from validate_N.md}
Rollback available: git reset --hard {GIT_ROLLBACK_BASE}
```
Then auto-run: `Skill("rollback", args=SESSION_ID)`

---

## Background Guardian Protocol

A lightweight background guardian runs alongside the recovery loop to catch regressions **before** the full validator runs. This is different from the watchdog (which monitors agent health) — the guardian monitors **code health**.

### When to spawn

Spawn the guardian at the **start of the recovery loop** — same message as watchdog + first builder. It stays alive across iterations.

| Task type | Spawn guardian? |
|-----------|----------------|
| Implementation that modifies existing code | YES |
| Pure greenfield (new files only, no existing code touched) | NO — no regression possible |
| Refactor / restructure | YES — regressions are the primary risk |

### Guardian agent template

```python
Agent(
    name="guardian",
    model="haiku",
    run_in_background=True,
    maxTurns=20,
    prompt=f"""You are the background regression guardian for session {SESSION_ID}.

    RULES — token efficiency is paramount:
    1. Watch /tmp/caf_{SESSION_ID}_watchdog.md for builder COMPLETED lines
    2. When a builder completes, run the project's test command (from /tmp/caf_project_context.md or the plan file)
    3. Compare result to baseline (test count from iteration start)
    4. ON SUCCESS: write NOTHING. Silent success saves tokens.
    5. ON FAILURE: immediately write to /tmp/caf_{SESSION_ID}_guardian.md:
       ```
       GUARDIAN_ALERT: REGRESSION
       ITERATION: N
       FAILING_TESTS: [exact test names/output, first 300 chars]
       FILES_TOUCHED: [from git diff --name-only]
       ```
       Then SendMessage(to='orchestrator', summary='REGRESSION', message='Tests failing after builder-N. See /tmp/caf_{SESSION_ID}_guardian.md')
    6. ON TEST COMMAND NOT FOUND: write SKIPPED once, then stop monitoring.
    7. Do NOT diagnose. Do NOT propose fixes. Report regression evidence only.
    8. After 3 consecutive silent successes, increase check interval to every-other-build.

    Baseline: the test suite should pass at session start (GIT_ROLLBACK_BASE).
    If tests already fail at baseline, record which tests fail and only alert on NEW failures."""
)
```

### How guardian interacts with the recovery loop

```
Recovery loop iteration:
  1. Builder runs → completes → writes to watchdog
  2. Guardian (background) sees completion → runs tests
     - SILENT on pass → no tokens spent
     - ALERT on regression → orchestrator gets SendMessage
  3. Validator runs (normal flow) → checks acceptance criteria
  4. If guardian alerted BEFORE validator finishes:
     - Orchestrator can kill the validator early (regression already detected)
     - Skip straight to debugger with guardian's evidence
     - Saves validator tokens on known-bad builds
```

### Token cost analysis

- **Per-check cost**: ~150-250 tokens (haiku reading watchdog file + running test command + comparing)
- **Silent success**: ~150 tokens (reads file, runs tests, no output)
- **Alert**: ~250 tokens (reads file, runs tests, writes report, sends message)
- **Value**: Catching a regression before validator saves ~500-1000 tokens (validator run + its report). Catching before debug cycle saves ~3000-5000 tokens.
- **Break-even**: Pays for itself if it catches 1 regression per 10 builds (10 * 150 = 1500 tokens spent, 1 * 3000 = 3000 tokens saved).

### Guardian vs Validator vs Watchdog

| Agent | Monitors | When | Output | Cost |
|-------|----------|------|--------|------|
| watchdog | Agent health (stuck, failed, no output) | Always with 2+ agents | Alert on stall/failure | ~100 tok/check |
| guardian | Code health (test regressions) | When modifying existing code | Alert on regression only | ~150 tok/check |
| validator | Acceptance criteria (full check) | After every build, mandatory | Full PASS/FAIL report | ~500-800 tok/run |

---

## Watchdog Protocol

**Always** spawn watchdog alongside any batch of 2+ agents:

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

**On watchdog alert**: 
- Critical agent failing? Kill batch, diagnose, re-spawn with simpler prompt.
- Non-critical? Let others continue, re-spawn only the failed one.
- Never ignore alerts.

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

**Budget per agent**: ~150 tokens (builder), ~300 tokens (researcher), ~200 tokens (debugger). Never exceed 800 tokens — you're summarizing, not dumping.

---

## Dynamic Subagent Examples

```python
# Example: project-specific migration validator
Agent(
    name="migration-validator",
    model="haiku",
    maxTurns=8,
    prompt="""You validate DB migration files for THIS project.
    Rules:
    1. File must start with YYYYMMDD_HHMMSS_ prefix
    2. Must contain both up() and down() functions
    3. Must not reference tables not in /db/schema.sql
    
    Task: Validate all files in /db/migrations/.
    Write PASS/FAIL per file to /tmp/migration_validation.md.
    Stop immediately after writing. No explanation needed."""
)

# Example: issue-specific log parser
Agent(
    name="log-parser",
    model="haiku",
    maxTurns=6,
    prompt="""Extract all lines matching 'AUTH_FAIL user=<id>' from /var/log/app.log.
    Group by user_id. Count occurrences. Write to /tmp/auth_failures.md. Stop."""
)

# Example: parallel code scanners across different areas
Agent(name="scanner-auth", model="sonnet", maxTurns=15,
    prompt="Scan /src/auth/** for SQL injection patterns. Write to /tmp/scan_auth.md.")
Agent(name="scanner-api", model="sonnet", maxTurns=15,
    prompt="Scan /src/api/** for SQL injection patterns. Write to /tmp/scan_api.md.")
Agent(name="scanner-db", model="sonnet", maxTurns=15,
    prompt="Scan /src/db/** for SQL injection patterns. Write to /tmp/scan_db.md.")
# ^ All three spawned in ONE message
```

---

## Session Isolation

All `/tmp/caf_*.md` files must include SESSION_ID to prevent collision with concurrent sessions. Pass `SESSION_ID` explicitly in every agent's prompt so they use matching paths.

Paths: `/tmp/caf_{SESSION_ID}_plan.md`, `_build_N.md`, `_validate_N.md`, `_debug_N.md`, `_research_N.md`, `_watchdog.md`
