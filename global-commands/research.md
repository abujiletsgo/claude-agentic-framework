---
description: Delegate heavy research tasks to sub-agents to preserve primary context
---

# Research & Summarize

**Purpose:** Offload heavy research, file reading, and analysis to sub-agents. Keeps your primary agent's context clean while gathering comprehensive information.

---

## Core Principle

**DO NOT** consume primary context tokens on heavy tasks. Instead:
- Spawn specialized sub-agents with the `Task` tool
- Let them burn their own tokens reading files, searching code, analyzing patterns
- Receive only clean, synthesized summaries back
- Primary context stays lean and efficient

---

## Workflow

### Step 1: Analyze the Request
Understand what information is needed:
- What files need to be read?
- What patterns need to be searched?
- What level of detail is required?

### Step 2: Spawn Sub-Agents

Use the `Task` tool to create specialized research agents:

```
Task tool with subagent_type="Explore":
- Description: "Research [specific topic]"
- Prompt: "Read [Target Files] and extract [Specific Info]. Focus on [Key Areas]. Report findings in structured format with key insights only."
```

**Critical**: Be explicit about what the sub-agent should:
- ✅ Read and analyze
- ✅ Extract and summarize
- ❌ Include in raw form (no file dumps)

### Step 3: Synthesize Reports

When sub-agents complete:
1. Read their summary reports
2. Identify patterns across findings
3. Fill any gaps if needed (spawn more sub-agents)
4. Synthesize into coherent narrative

### Step 4: Report to User

Provide concise, actionable summary:
- **Key Findings**: 3-5 main discoveries
- **Architecture Insights**: How components interact
- **Recommendations**: Next steps or important context
- **Source References**: Which files contain details

---

## Delegation Rules

### DO ✅
- Spawn sub-agents for file-heavy tasks
- Spawn sub-agents for codebase searches
- Request structured summaries from sub-agents
- Keep primary context focused on synthesis
- Use multiple sub-agents in parallel for speed

### DON'T ❌
- Read all files in primary context
- Run heavy searches in primary context
- Ask sub-agents for raw data dumps
- Wait sequentially when tasks can run in parallel
- Include full file contents in reports

---

## Example Delegations

### Authentication Research
```
User: "/research how authentication is handled in this repo"

Your Response:
1. Spawn Explore agent: "Search for authentication patterns (login, auth, jwt, session) across the codebase. Read relevant files and summarize the authentication flow, middleware used, and security measures."

2. Receive summary (2k tokens instead of 50k)

3. Report to user: "Authentication uses JWT tokens with... [synthesized findings]"
```

### Architecture Analysis
```
User: "/research the database layer architecture"

Your Response:
1. Spawn Explore agent: "Find all database-related files (models, migrations, queries). Analyze the ORM used, schema structure, and data access patterns. Summarize the architecture."

2. Receive summary

3. Report findings with architecture diagram
```

### Hook System Investigation
```
User: "/research what hooks are configured in this project"

Your Response:
1. Spawn Explore agent: "Read .claude/settings.json and all hook scripts. Document which hooks are configured, what they do, and their execution order."

2. Receive summary

3. Report comprehensive hook inventory
```

---

## Token Efficiency

**Target for Primary Context**: < 5,000 tokens consumed on research tasks

**How**:
- Sub-agent reads 100 files = 100k tokens (in sub-agent context)
- Sub-agent summarizes = 3k tokens sent back
- Primary agent processes = 3k tokens consumed
- **Savings**: 97% token reduction

---

## Sub-Agent Communication Pattern

When spawning, be explicit:

**Good** ✅:
```
"Read all files in src/auth/ directory. Extract:
1. Authentication methods used
2. Session management approach
3. Security measures implemented
Report findings in structured bullet points, max 2000 tokens."
```

**Bad** ❌:
```
"Read all auth files and tell me everything"
(This results in file dumps and bloated responses)
```

---

## Advanced: Parallel Delegation

For complex research, spawn multiple sub-agents in parallel:

```
Task 1: "Research authentication (src/auth/)"
Task 2: "Research database layer (src/models/)"
Task 3: "Research API endpoints (src/routes/)"

All run simultaneously, each in isolated context.
Synthesize all three reports when complete.
```

---

## Success Metrics

After using `/research`:
- Primary context consumption: < 5k tokens
- Quality of information: High (synthesized, not raw)
- Time to insight: Fast (parallel sub-agents)
- Context remaining: > 95% available

---

## When to Use This Command

✅ **Use /research when**:
- Task requires reading > 5 files
- Codebase search across multiple directories
- Deep analysis of architecture or patterns
- Unfamiliar with code structure
- Need comprehensive documentation review

❌ **Don't use /research when**:
- Single file needs reading (just use Read tool)
- Quick grep search (use Grep tool)
- Information already in context
- Simple clarification questions

---

## Compound Effect

This command embodies "build the thing that builds the thing":
- You built `/prime` to load context efficiently
- Now you build `/research` to delegate heavy tasks
- Next: Build `/analyze`, `/search`, `/explore` for specialized delegation
- Result: Primary context stays pristine no matter the workload

**Your agent becomes infinitely scalable because it knows when to delegate.**
