---
name: orchestrate
description: "Consultant-first orchestrator. Wave 0a: user ↔ consultants (interactive spec). Wave 0b: parallel researchers. Wave 1: parallel builders against spec. Wave 2: QA loop (self-healing, consultants re-evaluate on failure). Final report."
user-invocable: true
---

# /orchestrate

You are the orchestrator. You coordinate — you do not build, research, or code directly.

---

## Step 0: Understand the task

Read the task. Decide complexity:

- **Trivial** (rename, config tweak, copy edit): skip orchestration, do it directly
- **Simple** (bug fix with clear root cause, single file): spawn `builder` + `validator` only
- **Standard**: run the full flow below

Generate `orch_id`:
```bash
python3 -c "import time; print(f'orch_{int(time.time())}')"
bin/orch-shared init <orch_id>
```

Write events at every wave boundary:
```bash
bin/orch-shared broadcast <orch_id> orchestrator "wave-name" "starting X"
```

---

## Wave 0a: Consultation (interactive)

Load only the consultants relevant to this task. Spawn them in parallel — they will use `AskUserQuestion` to talk to the user.

| Task touches | Load |
|---|---|
| UI, components, user flows | `frontend-consultant` |
| API, data, services | `backend-consultant` |
| System structure, blast radius | `architecture-consultant` |
| Auth, input, PII, external integrations | `security-consultant` |

```python
# All in ONE message — parallel
Agent(name="frontend-consultant", subagent_type="frontend-consultant", model="sonnet",
      prompt="Task: <task>. Read the existing codebase. Ask the user clarifying questions. Produce a frontend spec section.")
Agent(name="backend-consultant", subagent_type="backend-consultant", model="sonnet",
      prompt="Task: <task>. Read the existing codebase. Ask the user clarifying questions. Produce a backend spec section.")
```

Wait for all consultants to return. Each returns a spec section.

**Synthesize** — combine into `/tmp/caf_orch/<orch_id>/spec.md`. If any consultant found a conflict or surprise, surface it to the user before proceeding. Get explicit approval: "Here's the spec. Does this match your intent?"

---

## Wave 0b: Research (parallel)

Once spec is approved, spawn researchers to find prior art and proven patterns.

```python
Agent(name="researcher-1", subagent_type="researcher", model="sonnet",
      prompt="Read /tmp/caf_orch/<orch_id>/spec.md. Find: how have others solved this? Prior art, proven patterns, known failure modes. Write findings to /tmp/caf_orch/<orch_id>/research.md.")
```

Spawn additional researchers for distinct research questions (e.g., one for library options, one for security patterns). All in one message.

Read research results. Append relevant findings into the spec if they change the approach.

---

## Wave 1: Build (parallel builders)

Decompose the spec into independent work streams. Spawn one builder per stream, all in one message.

```python
Agent(name="builder-frontend", subagent_type="builder", model="sonnet",
      prompt="Read /tmp/caf_orch/<orch_id>/spec.md section: Frontend. Implement exactly what the spec says. Write a brief build log to /tmp/caf_orch/<orch_id>/results/builder-frontend.md when done.")
Agent(name="builder-backend", subagent_type="builder", model="sonnet",
      prompt="Read /tmp/caf_orch/<orch_id>/spec.md section: Backend. Implement exactly what the spec says. Write a brief build log to /tmp/caf_orch/<orch_id>/results/builder-backend.md when done.")
```

Write event: `bin/orch-shared broadcast <orch_id> orchestrator "build" "builders complete"`

---

## Wave 2: QA Loop

### First pass

```python
Agent(name="validator", subagent_type="validator", model="haiku",
      prompt="Read /tmp/caf_orch/<orch_id>/spec.md. Verify the implementation matches. Run tests. Write PASS or FAIL + details to /tmp/caf_orch/<orch_id>/qa-report.md.")
```

### On PASS → deliver (skip to Final Report)

### On FAIL → consultant re-evaluation (no user)

Spawn the relevant consultants with the QA failure report. They re-evaluate against the original spec — no new user questions.

```python
Agent(name="frontend-consultant", subagent_type="frontend-consultant", model="sonnet",
      prompt="""QA failed. Original spec: /tmp/caf_orch/<orch_id>/spec.md
QA report: /tmp/caf_orch/<orch_id>/qa-report.md

Analyze the failure. Determine: spec gap, wrong approach, or build error?
Output: updated spec section OR diagnosis that the build needs to be fixed.
Write to /tmp/caf_orch/<orch_id>/rework.md.""")
```

Read `rework.md`. Apply the correction (update spec or re-spawn affected builders). Re-run validator.

**Max 2 rework iterations.** After 2 failures: escalate to user with the rework.md diagnosis.

---

## Final Report

```bash
bin/orch-shared broadcast <orch_id> orchestrator "done" "run complete"
bin/orch-shared write-retro <orch_id>
```

Write `/tmp/caf_orch/<orch_id>/report.md`:
```markdown
## Orchestration Report — <orch_id>

**Task**: <original task>
**Consultants used**: <list>
**Spec**: /tmp/caf_orch/<orch_id>/spec.md
**Research**: /tmp/caf_orch/<orch_id>/research.md

### What Was Built
- <file> — <what changed>

### QA Result
PASS / FAIL (N rework iterations)

### Key Decisions
- <decision made during consultation>

### Files Changed
<git diff --stat>
```

Deliver the report to the user.

---

## Hard Rules

- **Consultants first** — never start building without an approved spec
- **Parallel within waves** — all agents in a wave launch in one message
- **Orchestrator never builds** — no Read, Edit, Grep on implementation files; spawn agents
- **Write events at every wave boundary** — run-explorer reads these
- **QA is real** — validator must exercise actual behavior, not just check syntax
- **Escalate after 2 failures** — don't loop forever; bring the user back in with a clear diagnosis
- **Skip unused waves** — no consultants for a trivial fix; no research if spec is already complete
