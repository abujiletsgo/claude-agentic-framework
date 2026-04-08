---
name: research-code
description: "Code pattern research: find how real projects implement patterns,
  compare implementations across repos. Uses sourcegraph-mcp for source code search."
user-invocable: true
---

# /research-code — Code Pattern Research

Find how real projects implement patterns using cross-repo source code search.

## Protocol

1. Parse query: extract language hint, pattern name, repo/org constraints
2. Build Sourcegraph query with appropriate filters (lang:, repo:, file:, type:symbol)
3. Execute via mcp__sourcegraph
4. Return structured comparison (TOON for 5+ uniform results)
5. Token budget: <10K total

## Sourcegraph Query Building

- Always add `lang:` filter when language is known
- Use `repo:` filter to narrow scope (e.g., `repo:^github.com/pallets/`)
- Use `type:symbol` for function/class/interface search
- Use `file:` for file pattern matching

## Output

Structured code pattern comparison. TOON for 5+ uniform results.

## Fallback

mcp__sourcegraph unavailable → WebSearch with `site:github.com <query>`,
then WebFetch top 2-3 results.

No two-step reasoning — this is structured extraction, not synthesis.
