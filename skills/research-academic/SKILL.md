---
name: research-academic
description: "Academic paper research: search papers, trace citations, synthesize
  literature. Dispatches to academic-researcher agent with mcp__papers and mcp__papersflow."
user-invocable: true
---

# /research-academic — Academic Paper Research

Search papers, trace citations, and synthesize literature using structured MCP tools.

## Protocol

1. Identify query type: simple lookup vs synthesis task
2. For simple lookup: call mcp__papers directly, return TOON-encoded results
3. For synthesis: use two-step reasoning (reason freely, then format)
4. Encode uniform result lists (5+ papers) as TOON before returning
5. Token budget: <15K total

## Tool Routing

| Query | Tool |
|---|---|
| Paper search by title/author/keyword | mcp__papers |
| Citation graph, "who cited this" | mcp__papersflow |
| Literature review, systematic coverage | mcp__papersflow |

## Two-Step Reasoning (Synthesis Only)

**Step 1**: Reason freely about findings, themes, contradictions, gaps.
**Step 2**: Format into structured output.

Skip two-step for simple lookups (single paper, citation count).

## Output

- Uniform search results (5+ papers) → TOON encoding
- Synthesis → plain text (Consensus / Contradictions / Gaps / Key papers)
- Citation graphs → JSON

## Fallback

mcp__papers unavailable → mcp__papersflow.
Both unavailable → report gap to orchestrator. Do NOT WebFetch paper URLs.
