---
description: Delegate heavy research tasks to sub-agents to preserve primary context
---

# Research & Summarize (v3 -- Context-Aware Token-Efficient)

**Purpose:** Offload heavy research to sub-agents using a context-first approach that checks existing knowledge layers before reading any code. Targets <5,000 tokens in primary context.

---

## Architecture: Context-First Research Pipeline

```
Layer 0: CONTEXT CHECK (~200 tokens, instant)
  --> Use inherited PROJECT_CONTEXT.md + Grep FACTS.md & ARCHITECTURE.md
  --> If answer is already there: report it, DONE
  --> If partially answered: note gaps, proceed to Layer 1

Layer 1: INDEX SCAN (Glob + Grep only -- no file reads, ~500 tokens)
  --> Search ONLY for gaps not covered by context layers
  --> Returns: file paths + line numbers + 1-line match context

Layer 2: TARGETED READ (Sonnet researcher, ~2000 tokens)
  --> Read ONLY specific line ranges from Layer 1
  --> Researcher receives pre-digested context so it doesn't re-read known files
  --> Return: 2-3 sentence summary per finding, max 3000 tokens total

Layer 3: SYNTHESIS (Primary context, ~1000 tokens)
  --> Receive only summaries -- zero raw code
  --> Synthesize into actionable answer
```

**Token budget**: < 5,000 tokens total in primary context

---

## Execution Protocol

### Step 0: Check Context Layers (MANDATORY -- do this BEFORE anything else)

Check if the answer is already available — but do NOT read full files into your context:

1. **PROJECT_CONTEXT.md** -- already in your context via auto-prime `<system-reminder>`. Check what you already have. Do NOT re-read it.
2. `/tmp/caf_project_context.md` -- Read ONLY if it exists and you need test commands or conventions not in auto-prime.
3. `.claude/FACTS.md` -- **Grep** for keywords related to the question. Do NOT read the whole file (~4KB).
4. `.claude/ARCHITECTURE.md` -- **Grep** for the specific module/area. Do NOT read the whole file (~22KB).
5. `.claude/MEMORY.md` -- **Grep** for topic keywords. Do NOT read unless the topic was recently researched.

**Decision gate:**
- If the answer is FULLY in context layers: report it directly. No sub-agents needed. DONE.
- If PARTIALLY answered: extract what's known, identify specific gaps, proceed to Step 1 with gaps only.
- If NOT in context layers: proceed to Step 1 with full research question.

### Step 1: Parse the Research Question
Identify what information is needed:
- **Internal** (codebase): which files, patterns, functions?
- **External** (web): which docs, APIs, frameworks?
- **Hybrid**: both internal and external?

**Scope narrowing**: Convert the user's question into specific, searchable sub-questions. "How does auth work?" becomes:
1. Where are the auth files? (check ARCHITECTURE.md first)
2. What auth strategy is used? (check FACTS.md first)
3. How do auth middleware and routes connect? (this is likely the actual gap)

### Step 2: Layer 1 -- Index Scan

Spawn a **single fast sub-agent** with ONLY search tools:

```
Agent(subagent_type="Explore", description="Index scan for [topic]")
Prompt: "Using ONLY Glob and Grep (NO file reads), find:
  1. Files matching [patterns] -- return paths only
  2. Lines matching [keywords] -- return file:line:match
  3. Rank by relevance (most matches first)
  Return a structured list: PATH:LINE -- one-line context
  Maximum 15 results. No file contents."
```

For **external research**, use WebSearch directly (it's cheap):
```
WebSearch("Claude Code [specific feature] documentation 2026")
```

### Step 3: Layer 2 -- Targeted Read

From Layer 1 results, spawn sub-agent(s) to read ONLY the relevant sections.

**CRITICAL: Include pre-digested context so the researcher doesn't re-read known files:**

```
Agent(subagent_type="researcher", name="researcher-1", maxTurns=25,
  description="Deep read [topic]")
Prompt: "
  ## Already Known (from context layers -- DO NOT re-read these files)
  [Summary of relevant facts from Step 0]

  ## Read These Specific Ranges and Summarize the GAPS:
  - file_a.py lines 45-80: extract [specific info not in context]
  - file_b.ts lines 120-150: extract [specific info not in context]

  For each file, return a 2-3 sentence summary of the finding.
  DO NOT include raw code. DO NOT read beyond the specified lines.
  DO NOT re-read files already summarized in 'Already Known' above.
  Maximum 3000 tokens total response."
```

**For large research (10+ files)**: Spawn 2 parallel sub-agents, each reading 5-7 files. Cap at 2 researchers.

### Step 4: Layer 3 -- Synthesis

In primary context, synthesize sub-agent summaries:
1. **Key Findings**: 3-5 main discoveries
2. **Connections**: How findings relate to each other
3. **Recommendations**: Next steps or decisions needed
4. **Source References**: file:line for details (user can Read if needed)

---

## Rules

### DO
- Check context layers BEFORE spawning any sub-agent
- Inject pre-digested context into every researcher prompt
- Scope research questions narrowly -- specific gaps, not "explore everything"
- Cap sub-agent responses to 3000 tokens via prompt instructions
- Cap researchers at maxTurns=25
- Use Glob/Grep before Read (index before content)
- Run sub-agents in parallel when researching multiple topics (max 2)
- Save large findings to `/tmp/claude/research_[topic].md` and reference by path

### DON'T
- Skip the context layer check (Step 0 is MANDATORY)
- Spawn researchers without telling them what's already known
- Let researchers re-read PROJECT_CONTEXT.md, FACTS.md, or ARCHITECTURE.md
- Read files in primary context (delegate ALL reads)
- Ask sub-agents for raw code dumps
- Spawn more than 2 parallel researchers
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
Agent 1 (researcher): "What do context layers say + index scan for [feature] in codebase"
Agent 2 (researcher): "WebSearch + WebFetch for [feature] in official docs"

# Both return summaries --> synthesize together
```

---

## Token Budget

| Layer | Tokens in Primary | What Happens |
|-------|-------------------|-------------|
| Layer 0 (Context) | ~300 (gap list) | You read context layers, identify gaps |
| Layer 1 (Index) | ~200 (file list) | Sub-agent does Glob/Grep |
| Layer 2 (Read) | ~2000 (summaries) | Sub-agent reads specific lines |
| Layer 3 (Synthesis) | ~1000 (your output) | You synthesize + report |
| **Total** | **~3500** | **vs 50K+ without context-first** |

---

## When to Use

**Use /research when:**
- Task requires reading > 5 files not covered by context layers
- Codebase search across multiple directories
- External documentation lookup
- Deep analysis of patterns not in ARCHITECTURE.md

**Don't use /research when:**
- Single file needs reading (just use Read)
- Quick grep search (use Grep directly)
- Information already in PROJECT_CONTEXT.md or FACTS.md (just read those)
- Simple yes/no question answerable from context layers
- Architecture question already covered by ARCHITECTURE.md

---

## Examples

### Example 1: Context Layers Have the Answer (no sub-agents!)
```
User: /research how are hooks organized in this repo

You:
  Step 0: Read PROJECT_CONTEXT.md → has full hook table with counts by event
  Step 0: Read ARCHITECTURE.md → has module import graph showing all hooks
  → Answer directly from context. Zero sub-agents. ~300 tokens total.
```

### Example 2: Partially Known (focused research)
```
User: /research how authentication works in this repo

You:
  Step 0: FACTS.md says "JWT-based auth, middleware at src/auth/middleware.ts"
  Step 0: ARCHITECTURE.md shows auth module dependencies
  Gap: How refresh tokens work, PKCE flow details
  Layer 1: Grep for "refresh|pkce" → 3 files found
  Layer 2: Researcher reads 3 specific sections → 1500 tokens
  Layer 3: Combine known facts + new findings → report

Primary context cost: ~2500 tokens (vs 50K+ without context-first)
```

### Example 3: External Research
```
User: /research what hook events does Claude Code support

You:
  Step 0: PROJECT_CONTEXT.md already lists our 9 events with hook counts
  Gap: What events exist that we DON'T use?
  WebSearch("Claude Code hooks documentation 2026") → gap analysis
  Compare: what we use vs what exists

Primary context cost: ~2000 tokens
```
