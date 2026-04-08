# Academic Research Skill

## Trigger
Use when the research query involves: papers, studies, citations,
literature review, "state of the art", scientific findings, arXiv,
PubMed, or any academic topic.

## Tools (priority order)
1. mcp__papers__search_papers — keyword search across 26+ sources
2. mcp__papers__search_by_author — author-specific search
3. mcp__papersflow — citation graph, verification, systematic reviews
4. WebFetch — only for reading specific paper URLs not in databases

## Model
Sonnet (search + synthesis). Haiku for formatting step only.

## Process
1. Parse query → extract keywords, authors, date range
2. Search via paper-search-mcp (primary) + papersflow (citation graph if needed)
3. Filter results by relevance (discard <2/5 relevance)
4. Synthesize findings (free reasoning, NO JSON constraint)
5. Format output (Haiku, strict schema)

## Output schema
```json
{
  "query": "original research question",
  "papers_found": 12,
  "papers_relevant": 5,
  "synthesis": "free-text analysis of findings",
  "papers": [
    {
      "title": "...",
      "authors": "...",
      "year": 2025,
      "abstract_summary": "1-2 sentence summary",
      "relevance": 4,
      "doi": "...",
      "key_finding": "..."
    }
  ],
  "gaps": ["identified gap 1"],
  "recommendations": ["next step 1"]
}
```

## Token budget
- Search phase: max 5,000 tokens input
- Synthesis phase: max 3,000 tokens output
- Total skill execution: target <15,000 tokens
