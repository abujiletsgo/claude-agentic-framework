---
name: orchestrate
description: "Unified Smart Orchestrator — single entry point for all complex work. Always spawns multiple parallel subagents: researchers, builders, validators, dynamic specialists. Never does work in a single agent."
user-invocable: true
---

# /orchestrate — You ARE the orchestrator

**Do NOT spawn a separate orchestrator agent. You (the root agent) follow the orchestrator protocol directly.**

Why: spawned subagents do not have the Agent tool — they cannot spawn further agents. Only the root agent can spawn agents. So you must coordinate directly.

## Protocol

### 1. Analyze the task

```markdown
## Orchestrator Analysis

**Request**: [user's request]
**Complexity**: [simple/moderate/complex/massive]
**Strategy**: ORCHESTRATE
**Team**: [N agents — list roles]
**Waves**:
  Wave 0: researcher-1, researcher-2 (parallel)
  Wave 1: builder-1, builder-2 (parallel)
  Wave 2: validator-1
```

## Dashboard Integration (MANDATORY)

Before spawning each wave, call `orch-event` to stream live status to the dashboard panels:

```bash
# Before spawning Wave N agents — mark as running:
Bash("bin/orch-event <N> <agent-name> running '<one-line description of what it will do>'")

# After each agent returns — mark done or failed:
Bash("bin/orch-event <N> <agent-name> done '<one-line summary of what it found/built>'")
Bash("bin/orch-event <N> <agent-name> failed '<reason>'")
```

Also reset the status file at the start of each orchestration:
```bash
Bash("rm -f /tmp/caf_orch_status.jsonl")
```

Then, immediately after resetting the status file, register this task with the session tracker and open a dedicated report pane. Do this BEFORE spawning any agents:
```bash
# 1. Register task — this writes /tmp/caf_session/<session_id>/current_task_id
Bash("bin/session-event task_start '<task description>' orchestrate")

# 2. Read the task_id assigned by session-event:
#    task_id = int(open(f"/tmp/caf_session/{SESSION_ID}/current_task_id").read().strip())

# 3. Open a dedicated report pane for this task:
Bash("bin/open-task-pane <task_id> '<task description>' orchestrate")
```

The task_id is a monotonically increasing integer written to `/tmp/caf_session/<session_id>/current_task_id` by `session-event task_start`. Read it after calling task_start, before calling open-task-pane.

### 2. Spawn research agents — ALL in ONE message

Before spawning, call orch-event for each researcher (status: running). After results return, call orch-event (status: done/failed) with a one-line summary.

```python
Agent(name="researcher-1", model="sonnet", prompt="...")  # \
Agent(name="researcher-2", model="sonnet", prompt="...")  #  } ONE message = parallel
```

### 3. Synthesize research, write plan, spawn builders — ALL in ONE message

Before spawning builders, call orch-event (status: running). After results, call orch-event (done/failed).

```python
Write("/tmp/caf_plan.md", plan_content)
Agent(name="builder-1", model="sonnet", prompt="Read /tmp/caf_plan.md section 1...")  # \
Agent(name="builder-2", model="haiku", prompt="Read /tmp/caf_plan.md section 2...")   # } parallel
```

### 4. Validate — MANDATORY after every build

Call orch-event before and after validator.

```python
Agent(name="validator-1", model="haiku", prompt="Verify the changes match the plan...")
```

### 4b. Quality gate — after validator PASS on complex/critical tasks

```python
Agent(name="evaluator-1", subagent_type="critical-analyst", model="sonnet",
      prompt="Post-build quality review. Read plan, build output, validator results, and git diff. "
             "Does this actually solve the problem? Edge cases? Simpler approach? Blast radius? "
             "Output: APPROVE / CONCERNS / REJECT")
```
Skip for simple/mechanical tasks. Always run for: security, architecture, 3+ files, critical quality.

### 5. On failure — escalate dynamically

- 1st failure: spawn debugger, then new builder
- 2nd failure: kill-and-reassign — fresh builder with dead-end context
- Broad/unknown scope: follow RLM Pyramid phases inline (survey → fan-out Haiku readers → synthesize) — do NOT call Skill("rlm"), just do the phases directly

## Hard rules

- **Parallel**: independent agents in ONE message. Never serialize.
- **Minimum 3 agents**: researcher + builder + validator for any task.
- **Match complexity**: simple=3 agents, moderate=5-6, complex=8+, massive=RLM+team.
- **Never do work yourself**: do not Read files, Edit code, or Bash commands. Spawn agents for everything.
- **Validate every build**: no exceptions. PASS -> report. FAIL -> debug loop (max 5).

## Model selection for builders

| Plan contains... | Model |
|---|---|
| Exact string/value to write | haiku |
| File path + line number + exact replacement | haiku |
| "Implement X" with no exact content | sonnet |
| Changes to 2+ interdependent files | sonnet |
| Security/auth/crypto code | sonnet |

## Dynamic skill spawning

When a specialized workflow outperforms a generic builder:

| Situation | Spawn |
|---|---|
| Build keeps failing | Kill-and-reassign: fresh builder with dead-end context |
| Need tests first | `Agent(name="test-gen", prompt="Use Skill('test-generator', ...)")` |
| Security-sensitive | `Agent(name="sec-scan", prompt="Use Skill('security-scanner', ...)")` |
| Complex refactoring | `Agent(name="refactor", prompt="Use Skill('refactoring-assistant', ...)")` |
| Error diagnosis | `Agent(name="err-diag", prompt="Use Skill('error-analyzer', ...)")` |

## Completion report

```markdown
## Orchestrator Report

**Request**: [original]
**Strategy**: [used]

### What Was Done
- [actions]

### Files Changed
- [file] — [what changed]

### Agent Team Performance
| Agent | Model | Turns | Result |
|-------|-------|-------|--------|

### Verification
[PASS/FAIL]
```

After the validator returns PASS, close out the session task record:
```bash
Bash("bin/session-event task_done '<task description>'")
```

See `global-agents/orchestrator.md` for the full reference protocol (if using Claude Agentic Framework).

## Sprint Strategy

When the task is **massive** (complexity score > 8, or user explicitly requests `/sprint`), escalate from ORCHESTRATE to SPRINT:

### When to Escalate

| Signal | Action |
|--------|--------|
| User says `/sprint` | Use sprint directly |
| Complexity > 8 AND tmux available | Recommend sprint |
| Complexity > 8 AND no tmux | Use agents-only sprint mode |
| Multiple workstreams (3+ independent tracks) | Recommend sprint |

### Sprint Dispatch

When escalating to sprint:
1. Hand off to `/sprint` skill — it handles PM → Lead → Worker hierarchy
2. The orchestrator becomes the PM role within the sprint
3. Each lead gets its own tmux pane (or Agent() in agents-only mode)
4. Waves: Plan(W0) → Build(W1) → Validate(W2) → Ship(W3)

See `global-skills/sprint/SKILL.md` for the full protocol.

### Staying in Orchestrate

For tasks below sprint threshold, continue with the standard ORCHESTRATE strategy (researcher → builder → validator waves).

## Research Dispatch

Route research queries to the correct tool/agent based on the domain:

| Query Domain | Primary Route | Fallback | Agent |
|-------------|--------------|----------|-------|
| Academic papers, citations | `mcp__papers__*` | `mcp__papersflow__*` | academic-researcher |
| Code patterns, cross-repo search | `mcp__sourcegraph__*` | WebSearch | code-researcher |
| Library docs, API reference | `mcp__context7__*` | WebFetch | (inline, haiku) |
| Current events, news | WebSearch | WebFetch | (inline) |

### Research Skills (user-invocable)

| Skill | Route |
|-------|-------|
| `/research-academic` | academic-researcher via papers MCP |
| `/research-code` | code-researcher via sourcegraph MCP |
| `/research-docs` | context7 MCP or WebFetch (haiku) |
| `/research-news` | WebSearch + WebFetch |

### Data Format

Research agents return results in **TOON encoding** (Token-Oriented Object Notation) for uniform lists — `[N,{fields}]` header + CSV rows. Falls back to compact JSON for nested/mixed data. See `lib/toon_utils.py`.
