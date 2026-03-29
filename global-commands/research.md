---
description: Delegate heavy research tasks to sub-agents to preserve primary context
---

# Research & Summarize (v2 — Layered Token-Efficient)

**Purpose:** Offload heavy research to sub-agents using a layered approach that reduces token consumption by ~97% while maintaining quality.

---

## Architecture: 3-Layer Research Pipeline

```
Layer 1: INDEX SCAN (Haiku-speed, ~500 tokens)
  → Glob + Grep only — no file reads
  → Returns: file paths + line numbers + 1-line match context

Layer 2: TARGETED READ (Opus, ~2000 tokens)
  → Read ONLY specific line ranges from Layer 1
  → Return: 2-3 sentence summary per finding, max 3000 tokens total

Layer 3: SYNTHESIS (Primary context, ~1000 tokens)
  → Receive only summaries — zero raw code
  → Synthesize into actionable answer
```

**Token budget**: < 5,000 tokens total in primary context (vs 100K+ in v1)

---

## Execution Protocol

### Step 1: Parse the Research Question
Identify what information is needed:
- **Internal** (codebase): which files, patterns, functions?
- **External** (web): which docs, APIs, frameworks?
- **Hybrid**: both internal and external?

### Step 2: Layer 1 — Index Scan

Spawn a **single fast sub-agent** with ONLY search tools:

```
Agent(subagent_type="Explore", description="Index scan for [topic]")
Prompt: "Using ONLY Glob and Grep (NO file reads), find:
  1. Files matching [patterns] — return paths only
  2. Lines matching [keywords] — return file:line:match
  3. Rank by relevance (most matches first)
  Return a structured list: PATH:LINE — one-line context
  Maximum 30 results. No file contents."
```

For **external research**, use WebSearch directly (it's cheap):
```
WebSearch("Claude Code [specific feature] documentation 2026")
```

### Step 3: Layer 2 — Targeted Read

From Layer 1 results, spawn sub-agent(s) to read ONLY the relevant sections:

```
Agent(subagent_type="researcher", description="Deep read [topic]")
Prompt: "Read these specific file ranges and summarize:
  - file_a.py lines 45-80: extract [specific info]
  - file_b.ts lines 120-150: extract [specific info]

  For each file, return a 2-3 sentence summary of the finding.
  DO NOT include raw code. DO NOT read beyond the specified lines.
  Maximum 3000 tokens total response."
```

**For large research (10+ files)**: Spawn 2-3 parallel sub-agents, each reading 3-5 files.

### Step 4: Layer 3 — Synthesis

In primary context, synthesize sub-agent summaries:
1. **Key Findings**: 3-5 main discoveries
2. **Connections**: How findings relate to each other
3. **Recommendations**: Next steps or decisions needed
4. **Source References**: file:line for details (user can Read if needed)

---

## Rules

### DO
- Spawn sub-agents for ALL file reading
- Cap sub-agent responses to 3000 tokens via prompt instructions
- Use Glob/Grep before Read (index before content)
- Run sub-agents in parallel when researching multiple topics
- Use WebSearch for external docs (it returns summaries)
- Save large findings to `/tmp/claude/research_[topic].md` and reference by path

### DON'T
- Read files in primary context (delegate ALL reads)
- Ask sub-agents for raw code dumps
- Let sub-agents exceed 3000 token responses
- Wait sequentially when parallel is possible
- Include full file contents in reports to user

---

## External Research Pattern

For web research (docs, APIs, frameworks):

```
# Step 1: Search (cheap, returns summaries)
WebSearch("Claude Code hooks documentation 2026")

# Step 2: If specific page needed, fetch with focused prompt
WebFetch(url, "Extract ONLY: [specific fields]. Max 2000 tokens.")

# Step 3: Synthesize in primary context
```

**Never** fetch a full page without a focused extraction prompt.

---

## Hybrid Pattern (Internal + External)

For questions that span codebase and docs:

```
# Parallel launch:
Agent 1 (Explore): "Index scan for [feature] in codebase"
Agent 2 (researcher): "WebSearch + WebFetch for [feature] in official docs"

# Both return summaries → synthesize together
```

---

## Token Budget

| Layer | Tokens in Primary | What Happens |
|-------|-------------------|-------------|
| Layer 1 (Index) | ~200 (file list) | Sub-agent does Glob/Grep |
| Layer 2 (Read) | ~2000 (summaries) | Sub-agent reads specific lines |
| Layer 3 (Synthesis) | ~1000 (your output) | You synthesize + report |
| **Total** | **~3200** | **vs 100K+ in v1** |

---

## When to Use

**Use /research when:**
- Task requires reading > 5 files
- Codebase search across multiple directories
- External documentation lookup
- Unfamiliar with code structure
- Deep analysis of architecture or patterns

**Don't use /research when:**
- Single file needs reading (just use Read)
- Quick grep search (use Grep directly)
- Information already in primed context
- Simple yes/no question

---

## Examples

### Example 1: Internal Research
```
User: /research how authentication works in this repo

You:
  Layer 1: Explore agent → Grep for auth|jwt|session|login → returns 12 files
  Layer 2: Researcher agent → Read top 5 files' relevant sections → 2500 tokens
  Layer 3: "Auth uses JWT with refresh tokens. Middleware at src/auth/middleware.ts
           validates on every request. Tokens stored in httpOnly cookies. PKCE flow
           for mobile clients implemented in src/auth/pkce.ts."

Primary context cost: ~3000 tokens (not 80K)
```

### Example 2: External Research
```
User: /research what hook events does Claude Code support

You:
  WebSearch("Claude Code hooks documentation 2026") → summaries
  WebFetch(official docs URL, "Extract all hook event types and descriptions")
  Synthesize into structured table

Primary context cost: ~2000 tokens
```

### Example 3: Hybrid
```
User: /research are we using all available Claude Code features

You:
  Parallel:
    Agent 1: "Index scan our settings.json.template for hook events"
    Agent 2: "WebSearch for complete Claude Code hook event list 2026"
  Compare: what we use vs what exists → gap analysis

Primary context cost: ~4000 tokens
```
