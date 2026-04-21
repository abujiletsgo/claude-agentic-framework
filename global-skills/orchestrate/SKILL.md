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
      prompt="Read ~/.caf/orch/<orch_id>/spec.md section: Frontend. Implement exactly what the spec says. Write build log to ~/.caf/orch/<orch_id>/results/builder-frontend.md when done. Time budget: complete your assigned work within ~10 minutes. If you reach a blocking decision (missing file, ambiguous spec, external dependency), stop immediately, write what you have to your results file, and append BLOCKED: <one sentence reason>. Do not keep retrying silently.")
Agent(name="builder-backend", subagent_type="builder", model="haiku",  # haiku if spec has exact replacements
      prompt="Read ~/.caf/orch/<orch_id>/spec.md section: Backend. Implement exactly what the spec says. Write build log to ~/.caf/orch/<orch_id>/results/builder-backend.md when done. Time budget: complete your assigned work within ~10 minutes. If you reach a blocking decision (missing file, ambiguous spec, external dependency), stop immediately, write what you have to your results file, and append BLOCKED: <one sentence reason>. Do not keep retrying silently.")
Agent(name="builder-config", subagent_type="builder", model="haiku",
      prompt="Read ~/.caf/orch/<orch_id>/spec.md section: Config. Make the exact changes specified. Write build log to ~/.caf/orch/<orch_id>/results/builder-config.md when done. Time budget: complete your assigned work within ~10 minutes. If you reach a blocking decision (missing file, ambiguous spec, external dependency), stop immediately, write what you have to your results file, and append BLOCKED: <one sentence reason>. Do not keep retrying silently.")
```

Write event: `bin/orch-shared broadcast <orch_id> orchestrator "build" "builders complete"`

---

## Wave 2: QA Loop

### First pass

```python
Agent(name="validator", subagent_type="validator", model="haiku",
      prompt="Read ~/.caf/orch/<orch_id>/spec.md. Verify the implementation matches. Run tests if available. Write PASS or FAIL + details to ~/.caf/orch/<orch_id>/qa-report.md.")
```

### On PASS → optional evaluator (opt-in only)

The evaluator is **not** run by default. To opt in, include `--evaluate` anywhere in the original task prompt.

If `--evaluate` was present:

```python
Agent(name="evaluator", subagent_type="critical-analyst", model="sonnet",
      prompt="Post-build quality review. Read spec, build logs, validator results, and git diff. Does this actually solve the problem? Edge cases? Simpler approach? Blast radius? Write APPROVE / CONCERNS / REJECT to ~/.caf/orch/<orch_id>/evaluation_report.md.")
```

On APPROVE: proceed to Final Report.
On CONCERNS: follow the CONCERNS protocol below.
On REJECT: treat as FAIL — spawn debugger, then re-run builders with evaluation as context.

If `--evaluate` was not present: proceed directly to Final Report on PASS.

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

### On CONCERNS (evaluator opt-in path only)

Read `~/.caf/orch/<orch_id>/concerns_count` (default 0). If already `1`, escalate to user with `rework.md` — do not loop.

If `concerns_count` is 0: write `1` to `concerns_count`, then:

1. Spawn the relevant domain consultant (no new user questions):

```python
Agent(name="<domain>-consultant", subagent_type="<domain>-consultant", model="sonnet",
      prompt="""Evaluator returned CONCERNS. No user questions — analyze only.
Original spec: ~/.caf/orch/<orch_id>/spec.md
Evaluation: ~/.caf/orch/<orch_id>/evaluation_report.md
QA report: ~/.caf/orch/<orch_id>/qa-report.md
Determine: spec gap, wrong approach, or build error? Write updated spec section or diagnosis to ~/.caf/orch/<orch_id>/rework.md.""")
```

2. Simultaneously, run Gemini CLI for a second opinion. Use whichever method is available:

```python
import subprocess, os, sys, time

orch_id = "<orch_id>"
prompt_file = os.path.expanduser(f"~/.caf/orch/{orch_id}/gemini_prompt.txt")
opinion_file = os.path.expanduser(f"~/.caf/orch/{orch_id}/gemini_opinion.md")
sentinel_file = os.path.expanduser(f"~/.caf/orch/{orch_id}/gemini_sentinel")

with open(prompt_file, "w") as f:
    f.write(f"""IMPORTANT: Do NOT read files under ~/.claude/, ~/.agents/, .claude/skills/, or agents/.
Review these evaluation concerns. Are they valid? Is the recommended fix sound?
See ~/.caf/orch/{orch_id}/evaluation_report.md and ~/.caf/orch/{orch_id}/spec.md""")

# Try cmux first (if available), fall back to direct subprocess
_lib = os.path.expanduser("~/.claude/lib")
if _lib not in sys.path:
    sys.path.insert(0, _lib)
_used_cmux = False
try:
    import cmux_client as cmux
    if cmux.is_available():
        sid = cmux.new_split("right")
        cmux.send_surface(sid,
            f'gemini -p "$(cat {prompt_file})" -y -o text > {opinion_file} && touch {sentinel_file}\n')
        for _ in range(24):  # poll up to 120s
            time.sleep(5)
            if os.path.exists(sentinel_file):
                break
        cmux.focus_surface(os.environ["CMUX_SURFACE_ID"])
        _used_cmux = True
except Exception:
    pass

if not _used_cmux:
    # Direct subprocess — works without cmux/tmux
    result = subprocess.run(
        f'gemini -p "$(cat {prompt_file})" -y -o text > {opinion_file} && touch {sentinel_file}',
        shell=True, capture_output=True
    )
    if result.returncode != 0:
        with open(opinion_file, "w") as f:
            f.write(f"GEMINI_UNAVAILABLE: {result.stderr.decode() or 'gemini not installed'}\n")
```

3. Verify Gemini ran: check `gemini_sentinel` exists. If absent, log "Gemini CLI verification failed" to `report.md` and continue without the second opinion.

4. Read `rework.md`. Re-run affected builders with it injected → re-run validator.

5. On re-validator PASS → Final Report. On FAIL or CONCERNS again → escalate to user.

**CONCERNS counter is independent of the FAIL counter. Only FAIL consumes from the 2-failure cap.**

---

### [EXPERIMENTAL] Self-healing for Simple tasks

> **EXPERIMENTAL**: Simple task self-healing is not yet validated in production.
> Monitor `~/.caf/logs/experimental_log.jsonl` for activation events.
> If it adds latency without improving outcomes, remove this block and revert to direct escalation.

For Simple tasks: on 1st QA failure, apply the same consultant self-healing as Standard/Complex, but:
- Spawn ONE consultant (most relevant domain — backend, frontend, or architecture)
- No new user questions
- Max **1** rework iteration (not 2)
- Log the activation:

```bash
echo '{"timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","orch_id":"<orch_id>","complexity":"simple","event":"experimental_self_heal_triggered"}' >> ~/.caf/logs/experimental_log.jsonl
```

Then spawn the relevant consultant:

```python
Agent(name="<domain>-consultant", subagent_type="<domain>-consultant", model="sonnet",
      prompt="""QA failed on a Simple task. No user questions — analyze only.
Spec: ~/.caf/orch/<orch_id>/spec.md
QA report: ~/.caf/orch/<orch_id>/qa-report.md
Determine root cause. Write updated spec section or diagnosis to ~/.caf/orch/<orch_id>/rework.md.""")
```

Re-spawn builder with `rework.md` injected → re-run validator. On 2nd failure → escalate to user.

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
