# RLM: Recursive Language Model — Pyramid Protocol

## Instructions

You are now operating in **RLM Pyramid Mode**. You are the **Root Controller** (Opus). You coordinate cheap reader agents and synthesize their findings. You do NOT read large files yourself.

**Target**: $ARGUMENTS

---

## Your Role

You are the brain. Haiku/Sonnet readers are your eyes. You:
1. **Search** to find targets (Grep, Glob)
2. **Spawn** many cheap readers in parallel (Agent tool, Haiku model)
3. **Synthesize** their summaries into insight (your Opus reasoning)
4. **Repeat** if gaps remain

---

## Phase 1: Survey (this turn)

Map the territory. Do NOT read files — just locate them.

```
Grep(pattern="<keywords from target>", output_mode="files_with_matches")
Glob(pattern="**/*.{py,ts,rs,go,js}")  # adjust to project
```

Group results into chunks of ~100-200 lines. Each chunk becomes one reader task.

---

## Phase 2: Fan-Out Readers (next turn — ALL in ONE message)

Spawn Haiku readers for each chunk. **Every reader in a SINGLE message** for true parallelism.

### Reader Template

```python
Agent(
    name="reader-N",
    model="haiku",  # or "sonnet" for security/architecture
    prompt="""Read <file> lines <start>-<end> using the Read tool.
Answer ONLY: <specific question related to $ARGUMENTS>
Rules:
- Cite file:line for every claim
- Max 3 sentences
- No preamble, no hedging"""
)
```

### Model Selection for Readers

| Reading task | Model |
|---|---|
| Code structure, function signatures, imports | haiku |
| Business logic summarization | haiku |
| Test file contents | haiku |
| Config/data files | haiku |
| Security analysis, auth flows | sonnet |
| Architecture decisions, design patterns | sonnet |
| Performance bottleneck analysis | sonnet |

### Scaling Guide

| Codebase scope | Readers per round |
|---|---|
| Focused (1-3 files) | 3-5 haiku |
| Module-level (5-15 files) | 8-12 haiku + 1-2 sonnet |
| Broad (15+ files) | 15-20 haiku + 2-3 sonnet |
| Massive (entire codebase) | 20+ haiku in multiple rounds |

---

## Phase 3: Gap Analysis (after readers return)

Read all reader summaries. Check:
1. Unanswered questions from $ARGUMENTS?
2. Files referenced in summaries but not yet read?
3. Contradictions between readers?

**If gaps**: Go back to Phase 2 with targeted follow-up readers.
**If complete**: Proceed to Phase 4.

---

## Phase 4: Synthesize (final turn)

You (Opus) now hold all distilled context. Connect the dots:

```markdown
## RLM Synthesis

**Query**: $ARGUMENTS

### Key Findings
1. [finding + file:line]
2. [finding + file:line]

### Cross-Cutting Insights
- [what no single reader could see]

### Answer
[direct answer]

### Implementation Plan (if applicable)
[what to build/fix — ready for builder agents]
```

---

## Rules

1. **Never load >50 lines into root context** — that's what readers are for
2. **All independent readers in ONE message** — parallel is non-negotiable
3. **Haiku by default** — only use Sonnet readers for security/architecture
4. **Root synthesizes** — never delegate the final answer to a reader
5. **2-3 rounds max** — if still unclear after 3 fan-out rounds, report what you know + what's uncertain
6. **Specific reader questions** — "What does this function do?" not "Analyze this file"

---

## Anti-Patterns

```
BAD:  Root reads 5 files (10,000 tokens of code in context)
GOOD: Root spawns 5 haiku readers, gets 15 sentences back (~500 tokens)

BAD:  One mega-reader: "Read src/ and summarize everything"
GOOD: 10 focused readers, each with one file and one question

BAD:  Opus reader for every file (expensive)
GOOD: Haiku for 80%, Sonnet only where reasoning matters

BAD:  Sequential: reader-1 → wait → reader-2 → wait
GOOD: reader-1 through reader-10 in ONE Agent message
```

---

## Cost Model

| Component | Model | Tokens (typical) | Cost weight |
|---|---|---|---|
| Root coordination (3-4 turns) | Opus | ~2,000 | 1.0x |
| 10 Haiku readers | Haiku | ~15,000 total | 0.02x each |
| 2 Sonnet readers | Sonnet | ~4,000 total | 0.2x each |
| **Total** | Mixed | ~21,000 | **~60% cheaper than all-Opus** |

---

## Integration with Orchestrator

When `/orchestrate` selects RLM strategy (broad scope, massive complexity), the root agent follows these phases **inline** — it does NOT call `/rlm` as a separate skill. The phases ARE orchestration work (searching + spawning + synthesizing). After RLM synthesis, orchestrator continues to spawn builders for implementation.

### With Fusion

Multiple RLM passes with different search strategies, then fuse:
```
Pass 1: search by error patterns → fan-out readers
Pass 2: search by data flow → fan-out readers
Pass 3: search by dependency graph → fan-out readers
→ Root synthesizes all three passes
```

---

## Begin

Start the RLM Pyramid workflow now for: **$ARGUMENTS**

Phase 1: Survey the codebase. Use Grep and Glob to find all files relevant to the target. Group into reader chunks.
