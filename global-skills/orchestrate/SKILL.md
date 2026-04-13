---
name: orchestrate
description: "Consultant-first orchestrator. Wave 0a: user ↔ consultants (interactive spec). Wave 0b: parallel researchers. Wave 1: parallel builders (min 3 agents, scaled to complexity). Wave 2: QA loop (self-healing). Final report."
user-invocable: true
---

# /orchestrate

You are the orchestrator. You coordinate — you do not build, research, or code directly.
**Never do work yourself.** No Read, Edit, Grep, Glob, or Bash on implementation files. Spawn agents for everything.

---

## Step 0: Understand the task

Analyze complexity and size the team accordingly:

| Complexity | When | Team size | Waves |
|---|---|---|---|
| **Trivial** | rename, config value, copy edit | skip orchestration — do it directly | — |
| **Simple** | single-file bug fix, clear root cause | 3 agents: researcher + builder + validator | 0b → 1 → 2 |
| **Standard** | multi-file feature, unclear scope | 5–6 agents + consultants | 0a → 0b → 1 → 2 |
| **Complex** | cross-domain, 3+ subsystems | 8+ agents + consultants | 0a → 0b → 1 → 2 |

Generate `orch_id` and initialize IPC:
```bash
python3 -c "import time; print(f'orch_{int(time.time())}')"
bin/orch-shared init <orch_id>
```

All IPC files live under `~/.caf/orch/<orch_id>/`. Write events at every wave boundary:
```bash
bin/orch-shared broadcast <orch_id> orchestrator "wave-name" "starting X"
```

---

## Wave 0a: Consultation (interactive)

**Skip for Simple tasks.** Load only consultants relevant to this task — spawn them in parallel in ONE message.

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

Wait for all consultants. Each returns a spec section.

**Synthesize** → `~/.caf/orch/<orch_id>/spec.md`. Surface conflicts to user. Get explicit approval before proceeding.

---

## Wave 0b: Research (parallel)

Spawn one researcher per distinct research question — all in ONE message.

```python
Agent(name="researcher-patterns", subagent_type="researcher", model="sonnet",
      prompt="Read ~/.caf/orch/<orch_id>/spec.md. Find prior art, proven patterns, known failure modes. Write to ~/.caf/orch/<orch_id>/research.md.")
Agent(name="researcher-security", subagent_type="researcher", model="sonnet",
      prompt="Read ~/.caf/orch/<orch_id>/spec.md. Find security concerns, attack surface, input validation needs. Append to ~/.caf/orch/<orch_id>/research.md.")
```

Read results. Append relevant findings to spec if they change the approach.

---

## Wave 1: Build (parallel builders)

Decompose the spec into independent work streams. **Minimum 3 agents total (including validator in Wave 2).** Scale up with complexity.

### Model selection for builders

| Spec says... | Use |
|---|---|
| Exact string/value to write | `haiku` |
| File path + line number + exact replacement | `haiku` |
| "Implement X" with no exact content | `sonnet` |
| Changes to 2+ interdependent files | `sonnet` |
| Security / auth / crypto code | `sonnet` |

```python
# All in ONE message — parallel
Agent(name="builder-frontend", subagent_type="builder", model="sonnet",
      prompt="Read ~/.caf/orch/<orch_id>/spec.md section: Frontend. Implement exactly what the spec says. Write build log to ~/.caf/orch/<orch_id>/results/builder-frontend.md when done.")
Agent(name="builder-backend", subagent_type="builder", model="haiku",  # haiku if spec has exact replacements
      prompt="Read ~/.caf/orch/<orch_id>/spec.md section: Backend. Implement exactly what the spec says. Write build log to ~/.caf/orch/<orch_id>/results/builder-backend.md when done.")
Agent(name="builder-config", subagent_type="builder", model="haiku",
      prompt="Read ~/.caf/orch/<orch_id>/spec.md section: Config. Make the exact changes specified. Write build log to ~/.caf/orch/<orch_id>/results/builder-config.md when done.")
```

Write event: `bin/orch-shared broadcast <orch_id> orchestrator "build" "builders complete"`

---

## Wave 2: QA Loop

### First pass

```python
Agent(name="validator", subagent_type="validator", model="haiku",
      prompt="Read ~/.caf/orch/<orch_id>/spec.md. Verify the implementation matches. Run tests if available. Write PASS or FAIL + details to ~/.caf/orch/<orch_id>/qa-report.md.")
```

### On PASS → quality gate (Standard/Complex tasks)

```python
Agent(name="evaluator", subagent_type="critical-analyst", model="sonnet",
      prompt="Post-build quality review. Read spec, build logs, validator results, and git diff. Does this actually solve the problem? Edge cases? Simpler approach? Blast radius? Write APPROVE / CONCERNS / REJECT to ~/.caf/orch/<orch_id>/evaluation_report.md.")
```

Skip evaluator for Simple/mechanical tasks.

### On FAIL → escalation protocol

**1st failure** — spawn debugger to diagnose, then new builders with the diagnosis:
```python
Agent(name="debugger", subagent_type="debugger", model="sonnet",
      prompt="Read ~/.caf/orch/<orch_id>/qa-report.md and the failing code. Root cause analysis only — no fixes. Write diagnosis to ~/.caf/orch/<orch_id>/debug-report.md.")
```
Then re-spawn affected builders with the debug report injected into their prompt.

**2nd failure** — kill-and-reassign: spawn fresh builder with the full failure history as context (what was tried, what broke, why). Do not retry the same approach.

**After 2 failures** — escalate to user with `rework.md` diagnosis. Never loop forever.

### Self-healing (consultant re-evaluation on 1st failure)

For Standard/Complex: spawn the relevant consultants with the failure report — no new user questions.

```python
Agent(name="backend-consultant", subagent_type="backend-consultant", model="sonnet",
      prompt="""QA failed. Original spec: ~/.caf/orch/<orch_id>/spec.md
QA report: ~/.caf/orch/<orch_id>/qa-report.md

Analyze the failure. Determine: spec gap, wrong approach, or build error?
Output: updated spec section OR diagnosis. Write to ~/.caf/orch/<orch_id>/rework.md.""")
```

Read `rework.md`. Apply correction → re-run validator. Max 2 total iterations.

---

## Dynamic skill spawning

When a specialized workflow outperforms a generic builder:

| Situation | Spawn |
|---|---|
| Build keeps failing | Kill-and-reassign: fresh builder + full failure history |
| Need tests written first | `Agent(name="test-gen", prompt="Use Skill('test-generator', ...)")` |
| Security-sensitive code | `Agent(name="sec-scan", prompt="Use Skill('security-scanner', ...)")` |
| Complex refactoring | `Agent(name="refactor", prompt="Use Skill('refactoring-assistant', ...)")` |
| Error diagnosis | `Agent(name="err-diag", prompt="Use Skill('error-analyzer', ...)")` |

---

## Final Report

```bash
bin/orch-shared broadcast <orch_id> orchestrator "done" "run complete"
bin/orch-shared write-retro <orch_id>
```

Write `~/.caf/orch/<orch_id>/report.md`:
```markdown
## Orchestration Report — <orch_id>

**Task**: <original task>
**Complexity**: simple / standard / complex
**Consultants used**: <list>
**Spec**: ~/.caf/orch/<orch_id>/spec.md

### What Was Built
- <file> — <what changed>

### Agent Team
| Agent | Model | Result |
|-------|-------|--------|

### QA Result
PASS / FAIL (N rework iterations)

### Key Decisions
- <decision from consultation>

### Files Changed
<git diff --stat>
```

Deliver the report to the user.

---

## Hard Rules

- **Consultants first** — never start building without an approved spec (skip for Simple)
- **Minimum 3 agents** — researcher + builder + validator for any non-trivial task
- **Parallel within waves** — all agents in a wave launch in ONE message; never serialize
- **Orchestrator never builds** — no Read, Edit, Grep on implementation files; spawn agents
- **Write events at every wave boundary** — run-explorer reads these
- **Model match** — haiku for mechanical/exact, sonnet for reasoning/multi-file
- **QA is real** — validator must exercise actual behavior, not just check syntax
- **Escalate after 2 failures** — bring the user back in with a clear diagnosis
- **Skip unused waves** — no consultants for Simple; no research if spec is already complete
