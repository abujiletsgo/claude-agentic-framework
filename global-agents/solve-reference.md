# solve — Reference Details

Supplementary reference for the `solve` agent. Contains verbose examples and templates extracted from solve.md to reduce token cost. Read specific sections on demand.

---

## Parallel Fan-Out Patterns (with code examples)

**Research fan-out** — spawn 3-5 researcher agents simultaneously, each investigating a different angle:
```
# ALL in one message block = truly parallel
Agent(name="r1", model="sonnet", prompt="Angle 1: error trace analysis. Write to /tmp/solve_r1.md")
Agent(name="r2", model="sonnet", prompt="Angle 2: data flow analysis. Write to /tmp/solve_r2.md")
Agent(name="r3", model="sonnet", prompt="Angle 3: git history analysis. Write to /tmp/solve_r3.md")
Agent(name="r4", model="sonnet", prompt="Angle 4: dependency analysis. Write to /tmp/solve_r4.md")
Agent(name="r5", model="haiku", prompt="Angle 5: test coverage scan. Write to /tmp/solve_r5.md")
```

**Hypothesis fan-out** — spawn independent hypothesis generators that cross-pollinate:
```
Agent(name="h1", model="sonnet", prompt="Propose solution A. Read /tmp/solve_shared.md first.")
Agent(name="h2", model="sonnet", prompt="Propose solution B. Read /tmp/solve_shared.md first.")
Agent(name="h3", model="sonnet", prompt="Propose solution C. Read /tmp/solve_shared.md first.")
```

**Validation fan-out** — verify multiple things simultaneously:
```
Agent(name="v1", model="haiku", prompt="Verify function X exists at file:line")
Agent(name="v2", model="haiku", prompt="Verify no other callers of Y")
Agent(name="v3", model="haiku", prompt="Run test suite Z and report pass/fail")
```

---

## Inter-Agent Communication via SendMessage

```
# Root sends task assignments
SendMessage(to="trace-researcher", summary="new lead found", message="Also check config.py:42, found related error path")

# Root broadcasts to all agents
SendMessage(to="*", summary="shared finding", message="Root cause narrowed to auth module. Focus there.")
```

---

## Guardian Agent Prompt Template

```
Agent(name="guardian", model="haiku", run_in_background=true,
  prompt="You are the continuous validation guardian. Run in a loop:
  1. Watch /tmp/solve_state.md for new iterations
  2. After each iteration checkpoint, run the test suite
  3. Verify no regressions: compare test counts to baseline in state file
  4. Check blast radius: grep for imports/references of modified files
  5. Write validation report to /tmp/solve_guardian_report.md
  6. If regression detected, immediately alert root via SendMessage(to='solve')

  Baseline tests passing: [N]. Files under watch: [list].
  Run tests after every checkpoint commit.")
```

---

## Eval Agent Prompt Template

```
Agent(name="eval-builder", model="sonnet", run_in_background=true,
  prompt="You are the eval harness builder. Your job:
  1. Read /tmp/solve_state.md to understand the problem and expected behavior
  2. Create a focused test/eval script at /tmp/solve_eval.sh that:
     - Tests the SPECIFIC behavior the user reported as broken
     - Tests edge cases around the fix
     - Produces a clear PASS/FAIL output
  3. Run the eval after each checkpoint (watch /tmp/solve_state.md for updates)
  4. Report results to /tmp/solve_eval_results.md
  5. If FAIL, SendMessage to root with details

  The eval should be lightweight, fast, and targeted — not a full test suite.
  Think: 'what would a QA engineer write to verify THIS specific fix?'")
```

Spawn eval-builder when: problem has clear expected vs actual, or bug with repro steps. Skip for refactoring with no behavior change.

---

## Phase 1: Research — Full Agent Batch Example

```
# Create tasks first for visibility
TaskCreate(subject="Research: error trace", description="Follow stack trace to root cause")
TaskCreate(subject="Research: data flow", description="Trace input → transform → output")
TaskCreate(subject="Research: git history", description="git log/blame for recent changes")
TaskCreate(subject="Research: test analysis", description="Find and run related tests")
TaskCreate(subject="Research: dependency map", description="What depends on the affected code")

# Spawn watchdog + ALL researchers in ONE message = true parallelism
Agent(name="watchdog", subagent_type="agent-watchdog", model="haiku", run_in_background=true,
  prompt="Monitor parallel batch for solve agent (root name: 'solve').
  Agents: trace-researcher, flow-researcher, history-researcher, test-researcher, dep-researcher.
  Expected outputs: /tmp/solve_research_trace.md, /tmp/solve_research_flow.md, /tmp/solve_research_history.md, /tmp/solve_research_tests.md, /tmp/solve_research_deps.md
  Alert via SendMessage(to='solve') if any agent errors, stalls, or produces no output within 3 minutes.
  State file: /tmp/caf_watchdog.md")

Agent(name="trace-researcher", model="sonnet", subagent_type="researcher",
  prompt="Task: error trace analysis. Follow the stack trace to source.
  Cite file:line for every finding. Write to /tmp/solve_research_trace.md
  Status protocol: append to /tmp/caf_watchdog.md — STARTED at begin, PROGRESS every 2 min, COMPLETED/FAILED at end.")

Agent(name="flow-researcher", model="sonnet", subagent_type="researcher",
  prompt="Task: data flow analysis. Trace input → transformation → output.
  Cite file:line for every finding. Write to /tmp/solve_research_flow.md
  Status protocol: append to /tmp/caf_watchdog.md — STARTED at begin, PROGRESS every 2 min, COMPLETED/FAILED at end.")

Agent(name="history-researcher", model="sonnet", subagent_type="researcher",
  prompt="Task: git history analysis. Use git log/blame to understand recent changes.
  Cite file:line for every finding. Write to /tmp/solve_research_history.md
  Status protocol: append to /tmp/caf_watchdog.md — STARTED at begin, PROGRESS every 2 min, COMPLETED/FAILED at end.")

Agent(name="test-researcher", model="sonnet", subagent_type="researcher",
  prompt="Task: test analysis. Find related tests, run them, report pass/fail.
  Write to /tmp/solve_research_tests.md
  Status protocol: append to /tmp/caf_watchdog.md — STARTED at begin, PROGRESS every 2 min, COMPLETED/FAILED at end.")

Agent(name="dep-researcher", model="sonnet", subagent_type="researcher",
  prompt="Task: dependency analysis. What imports/calls the affected code?
  Write to /tmp/solve_research_deps.md
  Status protocol: append to /tmp/caf_watchdog.md — STARTED at begin, PROGRESS every 2 min, COMPLETED/FAILED at end.")
```

---

## Phase 2: Hypothesize — Full Agent Batch Example

```
Agent(name="hypothesis-A", model="sonnet",
  prompt="Given findings in /tmp/solve_research_*.md, propose solution approach A.
  Read /tmp/solve_shared_findings.md first. Write to /tmp/solve_approach_A.md.
  Append new discoveries to /tmp/solve_shared_findings.md.")

Agent(name="hypothesis-B", model="sonnet",
  prompt="Same problem, DIFFERENT angle from approach A.
  Read /tmp/solve_shared_findings.md first. Write to /tmp/solve_approach_B.md.
  Append new discoveries to /tmp/solve_shared_findings.md.")

Agent(name="hypothesis-C", model="sonnet",
  prompt="Propose the most unconventional/lateral approach.
  Read /tmp/solve_shared_findings.md first. Write to /tmp/solve_approach_C.md.
  Append new discoveries to /tmp/solve_shared_findings.md.")
```

---

## Phase 3: Challenge — Full Agent Batch Example

```
Agent(name="challenger-A", model="sonnet", subagent_type="critical-analyst",
  prompt="Challenge hypothesis A in /tmp/solve_approach_A.md.
  Find counter-examples, edge cases, and disproving evidence. Write to /tmp/solve_challenge_A.md")

Agent(name="challenger-B", model="sonnet", subagent_type="critical-analyst",
  prompt="Challenge hypothesis B in /tmp/solve_approach_B.md.
  Find counter-examples, edge cases, and disproving evidence. Write to /tmp/solve_challenge_B.md")

Agent(name="challenger-C", model="sonnet", subagent_type="critical-analyst",
  prompt="Challenge hypothesis C in /tmp/solve_approach_C.md.
  Find counter-examples, edge cases, and disproving evidence. Write to /tmp/solve_challenge_C.md")
```

---

## Phase 4: Plan File Template

```markdown
# CAF Plan
TASK: [one sentence from your hypothesis]
CREATED: [ISO timestamp]
CURRENT_ITERATION: 1
MAX_ITERATIONS: 5
GIT_ROLLBACK_BASE: [hash]

## Goals
[What the surviving hypothesis from Phase 3 says must be true]

## Acceptance Criteria 1
[Every check the hypothesis implies — run tests, verify file contents, etc.]

## Build Task 1
[Specific file:line changes from the challenger-approved hypothesis]

## Dead Ends
[Empty at start — populated after each failed iteration]

## Iteration History
| N | Build | Validate | Debug | Approach |
|---|-------|----------|-------|----------|
```

---

## Phase 5: Auto-Skill-Creation Protocol

At end of each iteration, update skill tracker in `/tmp/solve_state.md`:

```markdown
## Skill Tracker
| Pattern | Count | Description |
|---------|-------|-------------|
| [approach-category] | N | [one sentence: what the reusable operation is] |
```

**Auto-trigger**: When pattern reaches count=2, or clearly recurs across sessions, spawn:

```python
Agent(name="auto-skill-builder", model="sonnet", maxTurns=15,
  prompt=f"""You are invoking the skill-builder skill.
  
  Create a skill based on this repeated pattern:
  Pattern: [name from tracker]
  Description: [one sentence from tracker]
  What it does: [concrete steps]
  Scope: global (place in ~/.claude/skills/auto-generated/)
  
  Read the skill-builder guide at global-skills/skill-builder/SKILL.md for format rules.
  Generate the skill, write it to ~/.claude/skills/auto-generated/[skill-name]/SKILL.md.
  Validate per the guide. Report DONE or FAILED."""
)
```

Token budget: skill creation costs ~1500-2000 tokens. Only trigger if skill saves ~500+ tokens per future use AND used 3+ times.

---

## State File Template: `/tmp/solve_state.md`

```
## Iteration N
**ROLLBACK_BASE**: <git hash at start>
**Checkpoint**: <commit hash after this iteration, if successful>
**Complexity**: simple | medium | hard
**Iteration budget**: N / max M
**Tried**: <what — specific enough to detect same-approach spirals>
**Approach category**: <one phrase>
**Learned**: <verified facts with citations>
**Dead ends**: <what failed and why>
**Health check**: files modified, tests before/after, worse? Y/N
**Pre-edit checks**: grounding Y/N, duplication Y/N, guardian Y/N
**Skill-tracker-update**: pattern=[name], count=[N], action=[none|increment|AUTO_CREATE]
**Next**: <plan>
**Status**: IN_PROGRESS | SOLVED | BLOCKED | REVERTING | DEAD_END
```

---

## Persistent Memory Template: `.claude/solve-history/`

After solving (Status: SOLVED), save to `.claude/solve-history/<date>-<problem-slug>.md`:
```
---
date: YYYY-MM-DD
problem: <one line>
root_cause: <one line>
files_changed: [list]
iterations: N
complexity: simple | medium | hard
---
<Non-obvious insight that solved it. What would you tell a future agent facing a similar problem?>
```

---

## Kill-and-Reassign Template

```
Agent(name="fresh-solver", model="sonnet", prompt="Previous approach failed. Read /tmp/solve_state.md for dead ends to avoid.
Verified facts: [list only confirmed facts with citations].
Find a NEW approach to: [problem]. Do not retry: [dead end approaches].")
```

---

## Pre-Edit Gate — Guardian Validation Template

For changes affecting shared code (3+ dependents) or core logic:

```
Agent(model="haiku", prompt="Validate this change is correct.
File: [path], Lines: [range]
Change: [description]
Check: 1) Does function X still exist at the cited location? 2) Does the change match the stated intent? 3) Are there obvious errors?
Reply: VALID or INVALID with reason.")
```
