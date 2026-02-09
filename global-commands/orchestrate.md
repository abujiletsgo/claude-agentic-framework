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

## Examples

### Example 1: Feature Implementation
```
/orchestrate "Implement OAuth2 authentication with comprehensive security"
```

**What Happens**:
1. Orchestrator spawns Researcher agent
2. Orchestrator spawns Security Analyst agent
3. Orchestrator spawns Builder agent (with context from 1 & 2)
4. Orchestrator spawns Tester agent
5. Orchestrator synthesizes results and reports back

**Time**: 15-20 minutes (vs 4-6 hours manually)

---

### Example 2: Codebase Audit
```
/orchestrate "Audit entire codebase for security vulnerabilities"
```

**What Happens**:
1. Orchestrator spawns Directory Analyzer
2. Orchestrator spawns 10 Security Auditor agents (parallel)
3. Orchestrator spawns Prioritizer agent
4. Orchestrator synthesizes consolidated security report

**Time**: 10-15 minutes (vs 8 hours manually)

---

### Example 3: Performance Optimization
```
/orchestrate "Optimize all API endpoints to respond under 300ms"
```

**What Happens**:
1. Orchestrator spawns Metrics Analyzer
2. Orchestrator spawns Profiler agents (parallel, one per slow endpoint)
3. Orchestrator spawns Optimizer agents (parallel)
4. Orchestrator spawns Validator agents (parallel)
5. Orchestrator synthesizes performance improvement report

**Time**: 20 minutes (vs 6 hours manually)

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

## Token Economics

### Traditional Approach (No Orchestrator)
```
You manually coordinate:
  - Read 50 files: 50k tokens (your context)
  - Write code: 20k tokens (your context)
  - Write tests: 10k tokens (your context)
  - Total: 80k tokens in YOUR context
```

### With Orchestrator
```
Orchestrator coordinates:
  - Your context: 5k tokens (just the plan)
  - Sub-agent 1 (Research): 20k tokens (isolated)
  - Sub-agent 2 (Build): 30k tokens (isolated)
  - Sub-agent 3 (Test): 10k tokens (isolated)
  - Sub-agent contexts: 60k tokens (ISOLATED)
  - Orchestrator synthesis: 2k tokens
  - Total YOUR context: 7k tokens (93% reduction)
```

**Key**: Orchestrator keeps YOUR context pristine while distributing work.

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

### With E2B Sandboxes
```
/orchestrate "Build and deploy full-stack app"
```

Orchestrator automatically uses E2B sandboxes for Builder agents.

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

## Monitoring Progress

While the Orchestrator works, you'll see:

```
🤖 Orchestrator: Planning agent team...
   ├─ Identified 3 sub-tasks
   ├─ Spawning Researcher agent...
   ├─ Spawning Security Analyst agent...
   └─ Waiting for research phase...

🤖 Orchestrator: Research complete. Building...
   ├─ Spawning Builder agent (E2B sandbox)...
   └─ Waiting for implementation...

🤖 Orchestrator: Implementation complete. Testing...
   ├─ Spawning Tester agent...
   └─ Running test suite...

🤖 Orchestrator: All agents complete. Synthesizing...
   └─ Generating executive summary...

✅ Orchestrator: Task complete!
```

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

## Cost Analysis

### Traditional Development
```
Engineer: 6 hours @ $75/hr = $450
Context overhead: 80k tokens = $2.40
Total: $452.40
```

### With Orchestrator
```
Engineer: 5 minutes @ $75/hr = $6.25
Orchestrator context: 7k tokens = $0.21
Sub-agent contexts: 60k tokens = $1.80
Total: $8.26

Savings: 98% cost reduction
Time: 6 hours → 20 minutes
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

---

**You're now operating at the Executive level. Welcome to Living Software.** 🚀
