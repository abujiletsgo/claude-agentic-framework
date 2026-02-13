# Orchestrate Command

**Purpose**: Invoke the Orchestrator Agent for complex multi-agent workflows.

---

## When to Use

Use the Orchestrator when you need:
- **Multi-step workflows** requiring coordination
- **Parallel execution** of independent tasks
- **Complex features** needing research + implementation + testing
- **Large-scale operations** (audits, refactoring, optimization)

---

## Usage

```bash
/orchestrate "high-level goal"
```

---

## Example

```
/orchestrate "Implement OAuth2 authentication with comprehensive security"
```

**What Happens**:
1. Orchestrator spawns Researcher agent
2. Orchestrator spawns Security Analyst agent
3. Orchestrator spawns Builder agent (with context from 1 & 2)
4. Orchestrator spawns Tester agent
5. Orchestrator synthesizes results and reports back

---

## How It Works

### Step 1: Load Orchestrator Agent

The system loads the Orchestrator agent from:
```
~/.claude/agents/orchestrator.md
```

### Step 2: Orchestrator Plans

The Orchestrator:
1. Analyzes your high-level goal
2. Breaks it into specialized sub-tasks
3. Identifies required agent types
4. Plans execution order (parallel vs sequential)

### Step 3: Orchestrator Executes

The Orchestrator:
1. Spawns sub-agents using `Task` tool
2. Provides context to each agent
3. Coordinates parallel/sequential execution
4. Waits for all agents to complete

### Step 4: Orchestrator Synthesizes

The Orchestrator:
1. Collects all agent reports
2. Synthesizes into executive summary
3. Reports back to you with:
   - What was done
   - Results achieved
   - Time saved
   - Next steps (if any)

---

## Combining with Other Tools

### With Context Priming
```
/prime
/orchestrate "Implement new feature X"
```

Orchestrator benefits from primed context for better planning.

---

### With Context Bundles
```
/loadbundle latest
/orchestrate "Continue implementing feature Y"
```

Orchestrator restores previous session intelligence before planning.

---

## When NOT to Use

### Simple Tasks
If the task is straightforward and doesn't need coordination:
```
❌ /orchestrate "Fix typo in README"
✅ Just fix it directly
```

### Single-Agent Tasks
If only one specialized agent is needed:
```
❌ /orchestrate "Research OAuth2 best practices"
✅ /research "OAuth2 best practices"
```

### Interactive Tasks
If you need back-and-forth conversation:
```
❌ /orchestrate "Help me understand how authentication works"
✅ Ask directly for explanation
```

---

## Advanced Usage

### Specify Agent Team Composition

```
/orchestrate "Optimize database queries. Use 5 profiler agents in parallel."
```

The Orchestrator will follow your guidance on team composition.

---

### Provide Constraints

```
/orchestrate "Refactor codebase, but keep changes under 100 lines per file."
```

The Orchestrator passes constraints to sub-agents.

---

### Request Specific Outputs

```
/orchestrate "Audit security. Provide JSON report with severity ratings."
```

The Orchestrator ensures sub-agents generate requested format.

---

## Troubleshooting

### Issue: Orchestrator seems slow

**Cause**: Large number of agents spawned

**Solution**: This is expected. Orchestrator coordinates complex workflows. The time saved vs manual work is significant.

---

### Issue: Sub-agent failed

**What Happens**: Orchestrator automatically handles failures:
1. Analyzes failure
2. Spawns debugger/fixer agent
3. Retries operation
4. If still fails: Reports to you with details

---

### Issue: Need to cancel orchestration

**Solution**:
```bash
# Stop the orchestrator
Ctrl+C

# Or use stop command
/stop
```

---

## Summary

The `/orchestrate` command transforms you from **Lead Engineer** to **Executive**:

**Before**: You coordinate everything manually
**After**: Orchestrator coordinates, you provide high-level goals

**Before**: Your context bloats with every task
**After**: Orchestrator keeps your context pristine

**Before**: Serial execution (one thing at a time)
**After**: Parallel execution (many agents simultaneously)
