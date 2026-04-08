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

### 2. Spawn research agents — ALL in ONE message

```python
Agent(name="researcher-1", model="sonnet", prompt="...")  # \
Agent(name="researcher-2", model="sonnet", prompt="...")  #  } ONE message = parallel
```

### 3. Synthesize research, write plan, spawn builders — ALL in ONE message

```python
Write("/tmp/caf_plan.md", plan_content)
Agent(name="builder-1", model="sonnet", prompt="Read /tmp/caf_plan.md section 1...")  # \
Agent(name="builder-2", model="haiku", prompt="Read /tmp/caf_plan.md section 2...")   # } parallel
```

### 4. Validate — MANDATORY after every build

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

See `global-agents/orchestrator.md` for the full reference protocol (if using Claude Agentic Framework).
