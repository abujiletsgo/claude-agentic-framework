# Multi-Agent Orchestration - The Endgame

> **2026 Update**: Orchestration now uses multi-model tiers (Opus for orchestrator, Sonnet for builders, Haiku for validators). 33 agents available across 3 tiers. See [../docs/2026_UPGRADE_GUIDE.md](../docs/2026_UPGRADE_GUIDE.md).

## What You've Achieved So Far

✅ **Steps 1-5: Elite Context Engineering**
- Context Reduction, Priming, Delegation, Bundles
- 95% token savings, resilient intelligence

Now: **Step 8: Multi-Agent Orchestration** - Scale compute to scale impact

---

## The Evolution

```
Single Agent
    ↓
Agent with Sub-Agents (delegation)
    ↓
Fleet of Sandboxed Agents (orchestration)
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│    YOU (Human) - Give high-level objectives    │
└─────────────────┬───────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────┐
│   Orchestrator Agent ("O" Agent)                │
│   - Breaks down objectives into tasks           │
│   - Spawns specialized agents                   │
│   - Coordinates parallel execution              │
│   - Aggregates results                          │
└─────────────────┬───────────────────────────────┘
                  ↓
        ┌─────────┼─────────┬─────────┐
        ▼         ▼         ▼         ▼
    ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
    │Agent 1│ │Agent 2│ │Agent 3│ │Agent N│
    │Builder│ │Tester │ │Docs   │ │...    │
    └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘
        │         │         │         │
        ▼         ▼         ▼         ▼
    [E2B]     [E2B]     [E2B]     [E2B]
    Sandbox   Sandbox   Sandbox   Sandbox
```

---

## Why Sandboxes?

**The Problem Without Sandboxes** ❌:
- Agent 1 deletes files Agent 2 is reading
- Conflicting package versions
- Agents crash your local machine
- Security risks from untrusted code

**With Sandboxes** ✅:
- Each agent gets **isolated ephemeral computer**
- Full filesystem, package management, networking
- Auto-cleanup after task completion
- 100% local machine protection

---

## Setup Instructions

### Step 1: Get E2B API Key

1. Visit: https://e2b.dev/
2. Sign up (free tier available)
3. Go to Dashboard → API Keys
4. Generate key (starts with `sbx_`)

### Step 2: Configure Environment

The skill is already cloned at: `~/.claude/skills/agent-sandboxes/`

Create `.env` file:

```bash
cd ~/.claude/skills/agent-sandboxes
cp .env.sample .env

# Edit .env and add your key:
E2B_API_KEY=sbx_your_key_here
ELEVENLABS_API_KEY=your_key_here  # Optional for TTS
```

### Step 3: Verify Installation

The skill provides these commands:

#### Simple Sandbox Operations
```bash
\sandbox <prompt>
```
Example: `\sandbox "create a hello world express app"`

#### Full Orchestration (Plan → Build → Host → Test)
```bash
\agent-sandboxes:plan-build-host-test "<prompt>" "<workflow_id>"
```

---

## Usage Patterns

### Pattern 1: Simple Task Execution

```bash
\sandbox "Write a Python script that analyzes CSV data and generates charts"
```

**What happens**:
1. Orchestrator spawns agent in E2B sandbox
2. Agent writes code, installs packages, executes
3. Returns results to you
4. Sandbox cleaned up automatically

### Pattern 2: Full-Stack Application

```bash
cd ~/.claude/skills/agent-sandboxes

# Very Easy - Counter App
\agent-sandboxes:plan-build-host-test "$(cat prompts/full_stack/sonnet/very_easy_counter.md)" "counter_v1"
```

**What happens**:
1. **Plan**: Agent designs Vue + FastAPI + SQLite architecture
2. **Build**: Agent implements in isolated sandbox
3. **Host**: Agent exposes public URL (e.g., `https://abc123.e2b.dev`)
4. **Test**: Agent validates with browser automation

**Result**: Live, publicly-accessible web app in ~5 minutes

### Pattern 3: "Best of N" - Parallel Execution

```bash
# Generate 3 landing page variations in parallel
\agent-sandboxes:plan-build-host-test "$(cat prompts/full_stack/sonnet/very_easy_greeter.md)" "landing_v1"
\agent-sandboxes:plan-build-host-test "$(cat prompts/full_stack/sonnet/very_easy_greeter.md)" "landing_v2"
\agent-sandboxes:plan-build-host-test "$(cat prompts/full_stack/sonnet/very_easy_greeter.md)" "landing_v3"
```

**What happens**:
- 3 agents spawn simultaneously in separate sandboxes
- Each implements the same requirement differently
- You get 3 public URLs to compare
- Pick the best implementation

---

## Available Example Prompts

Located in: `~/.claude/skills/agent-sandboxes/prompts/full_stack/sonnet/`

### Very Easy (Start Here)
- `very_easy_calculator.md` - Basic calculator app
- `very_easy_counter.md` - Counter with increment/decrement
- `very_easy_greeter.md` - Personalized greeting app

### Easy
- `easy_api_mock_studio.md` - API mocking tool
- `easy_code_snippet_manager.md` - Code snippet library
- `easy_markdown_knowledge_base.md` - Markdown wiki

### Medium
- `medium_habit_tracker.md` - Daily habit tracking
- `medium_job_board_aggregator.md` - Job listing aggregator
- `medium_recipe_remix_engine.md` - Recipe variation generator

### Hard
- `hard_collaborative_code_editor.md` - Real-time code editor
- `hard_distributed_rate_limiter.md` - API rate limiting system
- `hard_feature_flag_orchestrator.md` - Feature flag management

### Very Hard
- `very_hard_api_gateway_router.md` - API gateway with routing
- `very_hard_event_sourcing_framework.md` - Event sourcing system
- `very_hard_realtime_collaborative_whiteboard.md` - Collaborative whiteboard

---

## The Orchestrator Pattern

### What Makes a Good Orchestrator?

```markdown
## Orchestrator Responsibilities

1. **Task Decomposition**
   - Break complex objectives into subtasks
   - Identify dependencies between tasks

2. **Agent Spawning**
   - Create specialized agents for each subtask
   - Assign appropriate sandboxes

3. **Coordination**
   - Manage task execution order
   - Handle parallel vs sequential execution

4. **Result Aggregation**
   - Collect outputs from all agents
   - Synthesize into coherent result

5. **Error Handling**
   - Retry failed tasks
   - Spawn replacement agents if needed
```

---

## CRUD Operations for Agent Lifecycle

The `sandbox_cli` provides these operations:

```bash
# Navigate to CLI
cd ~/.claude/skills/agent-sandboxes/sandbox_cli

# CREATE - Initialize new sandbox
uv run sbx init --timeout 1800

# READ - List files in sandbox
uv run sbx files ls <sandbox_id> /home/user

# UPDATE - Execute commands
uv run sbx exec <sandbox_id> "echo hello world"

# DELETE - Auto-cleanup via timeout
# (Sandboxes auto-delete after timeout expires)

# BROWSER - Start browser automation
uv run sbx browser start <sandbox_id>
```

---

## Token Economics

### Single Agent Approach
```
Task: Build full-stack app
Tokens: 50,000 (all in one context)
Risk: Context overflow, lost work if crash
```

### Orchestrated Multi-Agent Approach
```
Task: Build full-stack app

Orchestrator (5k tokens):
- Plans architecture
- Spawns 3 agents:

Agent 1 - Frontend (15k tokens in sandbox):
- Builds Vue UI
- Returns: "Frontend complete at /frontend"

Agent 2 - Backend (15k tokens in sandbox):
- Builds FastAPI
- Returns: "API complete at /backend"

Agent 3 - Tests (10k tokens in sandbox):
- Writes + runs tests
- Returns: "All tests passing"

Orchestrator aggregates:
- "App complete at https://abc.e2b.dev"

Your context: 5k tokens (orchestrator only)
Total work: 45k tokens (distributed across agents)
Result: 90% context savings + parallelization
```

---

## Best Practices

### DO ✅
- Start with "very_easy" prompts to understand flow
- Use descriptive workflow_ids for tracking
- Run parallel agents for "Best of N" experiments
- Let sandboxes auto-cleanup (don't manually manage)
- Use browser testing for UI validation

### DON'T ❌
- Try hard prompts without testing easy ones first
- Forget to set E2B_API_KEY in .env
- Manually manage sandbox lifecycle (let E2B handle it)
- Run too many parallel agents (start with 2-3)
- Skip the Plan step (always plan first)

---

## Integration with Elite Context Engineering

**The Complete Stack**:

1. **Strip Global Context** → 10-20% permanent savings
2. **On-Demand Priming** → `/prime` with git-aware caching (90% faster repeats)
3. **Sub-Agent Delegation** → `/research` for heavy tasks
4. **Context Bundles** → `/loadbundle` for resilience
5. **Multi-Agent Orchestration** → Scale compute infinitely

**Result**: You can coordinate fleets of agents building full-stack apps while your primary context stays under 5k tokens.

---

## Success Metrics

After implementing orchestration:
- ✅ Can build full-stack apps without local environment pollution
- ✅ Primary context usage: < 5k tokens (orchestrator only)
- ✅ Parallel execution: 3+ agents simultaneously
- ✅ Public hosting: Apps accessible via https://
- ✅ Safety: Zero risk to local filesystem
- ✅ Scalability: Infinite agent spawning capability

---

## Try It Now

```bash
# 1. Test basic sandbox
\sandbox "create a simple python calculator script"

# 2. Build a full-stack app
cd ~/.claude/skills/agent-sandboxes
\agent-sandboxes:plan-build-host-test "$(cat prompts/full_stack/sonnet/very_easy_counter.md)" "my_first_app"

# 3. Watch the magic happen:
# - Agent plans the architecture
# - Agent builds Vue frontend + FastAPI backend + SQLite DB
# - Agent hosts at public URL
# - Agent tests with browser automation
# - You get: "App live at https://xyz.e2b.dev"
```

---

## The Endgame Achievement

You've mastered:
- ✅ Context Engineering (95% token savings)
- ✅ Agent Delegation (isolated heavy workloads)
- ✅ Context Persistence (resilient intelligence)
- ✅ Multi-Agent Orchestration (infinite scale)

**You can now coordinate fleets of specialized agents to build production-grade applications while maintaining pristine context efficiency.**

Welcome to **Agentic Engineering at Scale**. 🚀
