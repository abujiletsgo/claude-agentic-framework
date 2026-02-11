# Agent Teams - Quick Setup Guide

> **2026 Update**: The framework now includes 33 agents across 3 model tiers (Opus/Sonnet/Haiku). Builder + Validator team pattern is the recommended approach for implementation tasks. See [../docs/2026_UPGRADE_GUIDE.md](../docs/2026_UPGRADE_GUIDE.md).

This guide will get you up and running with Agent Teams in 5 minutes.

---

## Step 1: Enable Agent Teams (Experimental Feature)

### Option A: Add to Shell Configuration

**For Zsh (macOS default)**:
```bash
echo 'export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1' >> ~/.zshrc
source ~/.zshrc
```

**For Bash**:
```bash
echo 'export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1' >> ~/.bashrc
source ~/.bashrc
```

### Option B: Temporary (This Session Only)

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
claude
```

### Verify

```bash
echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS
# Should output: 1
```

---

## Step 2: Test Native Agent Teams (If Available)

Start Claude Code:
```bash
claude
```

Try this in conversation:
```
"Create an agent team. Spawn a researcher to check OAuth2
best practices, and a builder to implement the auth flow."
```

**Expected Behavior**: Claude spawns multiple agents and coordinates them.

**If this works**: You have native agent teams! Skip to Step 4.

**If this doesn't work**: The experimental feature may not be released yet. Use the custom Orchestrator instead (Step 3).

---

## Step 3: Use Custom Orchestrator

We've built a custom Orchestrator agent that provides agent team functionality.

### How It Works

The Orchestrator is a "Lead Agent" that:
1. Receives your high-level goal
2. Plans the agent team composition
3. Spawns specialized sub-agents
4. Coordinates their execution (parallel/sequential)
5. Aggregates results
6. Reports back with synthesis

### Test the Orchestrator

```bash
claude
```

In conversation:
```
/orchestrate "Implement OAuth2 authentication with comprehensive security"
```

**What Happens**:
1. Orchestrator analyzes your goal
2. Spawns Researcher agent (OAuth2 best practices)
3. Spawns Security Analyst agent (vulnerabilities)
4. Spawns Builder agent (implementation)
5. Spawns Tester agent (test generation)
6. Synthesizes all results
7. Reports back: "OAuth2 implemented securely"

**Time**: 15-20 minutes (vs 4-6 hours manually)

---

## Step 4: Example Workflows

### Example 1: Feature Implementation

**Command**:
```
/orchestrate "Add password reset functionality"
```

**Agent Team**:
- Researcher (best practices)
- Security Analyst (vulnerabilities)
- Builder (implementation)
- Tester (test generation)
- Documenter (API docs)

**Result**: Complete password reset feature with tests and docs

---

### Example 2: Codebase Audit

**Command**:
```
/orchestrate "Audit codebase for security vulnerabilities"
```

**Agent Team**:
- Directory Analyzer (finds all files)
- 10x Security Auditors (parallel, 5 files each)
- Prioritizer (ranks issues by severity)

**Result**: Comprehensive security report with prioritized fixes

**Time**: 10-15 minutes (vs 8 hours manually)

---

### Example 3: Performance Optimization

**Command**:
```
/orchestrate "Optimize all API endpoints to respond under 300ms"
```

**Agent Team**:
- Metrics Analyzer (finds slow endpoints)
- 5x Profilers (parallel, one per endpoint)
- 5x Optimizers (parallel, implement fixes)
- 5x Validators (parallel, verify improvements)

**Result**: All endpoints optimized with before/after metrics

**Time**: 20 minutes (vs 6 hours manually)

---

## Step 5: Combine with Other Tools

### With Context Priming

```bash
/prime
/orchestrate "Implement feature X"
```

The Orchestrator benefits from primed context for better planning.

---

### With Context Bundles

```bash
/loadbundle latest
/orchestrate "Continue implementing feature Y"
```

Orchestrator restores previous session intelligence before planning.

---

### With E2B Sandboxes

```bash
/orchestrate "Build and deploy full-stack app"
```

Orchestrator automatically uses E2B sandboxes for Builder agents (safe execution).

---

## Understanding the Orchestrator

### What It Does

✅ **Plans**: Analyzes your goal and designs agent team
✅ **Delegates**: Spawns specialized sub-agents
✅ **Coordinates**: Manages parallel/sequential execution
✅ **Synthesizes**: Aggregates results into executive summary

### What It Doesn't Do

❌ **No Reading**: Delegates to Researcher agents
❌ **No Writing**: Delegates to Builder agents
❌ **No Commands**: Delegates to appropriate agents

**Key**: Orchestrator keeps YOUR context lean (<10k tokens) while distributing heavy work to isolated sub-agent contexts.

---

## Token Economics

### Without Orchestrator
```
Your context: 80k tokens (reading all files, writing code)
Total cost: $2.40
Time: 6 hours
```

### With Orchestrator
```
Your context: 7k tokens (just the plan + synthesis)
Sub-agent contexts: 60k tokens (isolated)
Total cost: $2.10
Time: 20 minutes

Savings: 93% token reduction in YOUR context
         96% time reduction
```

---

## When to Use /orchestrate

### ✅ Use Orchestrator For:

- **Multi-step workflows** (research + build + test)
- **Large-scale operations** (audit 50 files)
- **Parallel execution** (optimize 10 endpoints)
- **Complex features** (OAuth, payments, dashboards)

### ❌ Don't Use Orchestrator For:

- **Simple tasks** ("fix typo in README")
- **Single-agent tasks** ("/research OAuth2")
- **Interactive tasks** ("explain how X works")

---

## Monitoring Progress

While Orchestrator works, you'll see:

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

## The Executive Shift

### Before Agent Teams

```
You: "Research OAuth2"
You: [wait for result]
You: "Now implement it"
You: [wait for result]
You: "Now test it"
You: [coordinate everything]
```

**Role**: Lead Engineer (tactical execution)

### After Agent Teams

```
You: "Implement OAuth2 authentication"
Orchestrator: [spawns Researcher, Builder, Tester]
Orchestrator: [coordinates everything]
Orchestrator: [reports back]
You: [receive complete implementation]
```

**Role**: Executive (strategic direction)

---

## Next Steps

### 1. Test Basic Orchestration

```bash
/orchestrate "Audit this codebase for security issues"
```

### 2. Test Complex Workflow

```bash
/orchestrate "Implement user authentication with email verification"
```

### 3. Combine with Drop Zones

Set up a Drop Zone that triggers orchestration:

**drops.yaml**:
```yaml
- name: "Feature Request Zone"
  file_patterns: ["*.txt"]
  reusable_prompt: ".claude/commands/orchestrate_feature.md"
  zone_dirs: ["agentic_drop_zone/feature_requests"]
  agent: "claude_code"
```

**Result**: Drop feature request file → Orchestrator builds it automatically

---

## Living Software (Advanced)

The ultimate goal: **agents that run 24/7, improving your codebase while you sleep**.

### Always-On Agents (Step 10)

See: `~/.claude/AGENTIC_LAYER.md`

Set up agents that run continuously:
- **Refactorer** (nightly): Improves code quality
- **Tester** (on commit): Ensures test coverage
- **Documenter** (weekly): Updates documentation
- **Performance** (continuous): Monitors and optimizes
- **Security** (on commit): Scans for vulnerabilities

### Z-Threads (Zero Touch)

Goal: **Prompt → Production with zero human intervention**

Requirements:
1. Comprehensive testing (80%+ coverage)
2. Automatic rollback (on failure)
3. Gradual rollout (1% → 100%)
4. Post-deploy validation

**Result**: You write high-level goals, agents handle everything from research to production deployment.

---

## Documentation Reference

- **Agent Teams Guide**: `~/.claude/AGENT_TEAMS.md`
- **Orchestrator Agent**: `~/.claude/agents/orchestrator.md`
- **Orchestrate Command**: `~/.claude/commands/orchestrate.md`
- **Agentic Layer (Step 10)**: `~/.claude/AGENTIC_LAYER.md`
- **Master Summary**: `~/.claude/MASTER_SUMMARY.md`

---

## Summary

You've implemented **Agent Teams** - the Executive Shift:

✅ **Shift**: Engineer → Executive
✅ **Pattern**: High-level goals → Orchestrator coordinates fleet
✅ **Benefit**: 10x productivity via parallel agent coordination
✅ **Token Efficiency**: 93% reduction in YOUR context
✅ **Time Efficiency**: 96% reduction vs manual work

**You now operate at the Executive level. Welcome to Living Software.** 🚀
