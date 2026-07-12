# Research Routing Reference

Internal routing guide for dispatching research questions to the right tools and model tier. Consolidates what were previously four separate internal routing-guide skills (research-academic, research-code, research-docs, research-news) into one reference. Used by the researcher agent and by orchestrate's Wave 0b research step.

## Routing table

| Category | Trigger | Tools (priority order) | Model |
|---|---|---|---|
| Academic | papers, studies, citations, literature review, "state of the art", scientific findings, arXiv, PubMed, or any academic topic | 1. `mcp__papers__search_papers` — keyword search across 26+ sources 2. `mcp__papers__search_by_author` — author-specific search 3. `mcp__papersflow` — citation graph, verification, systematic reviews 4. `WebFetch` — only for reading specific paper URLs not in databases | Sonnet (search + synthesis); Haiku for formatting step only |
| Code | code patterns, implementations, "how does X library handle Y", firmware, API usage, open source projects, or any code-related investigation | 1. `mcp__github__search_code` — cross-repo code search (free, requires GITHUB_TOKEN) 2. `mcp__github__get_file_contents` — read specific files from repos 3. `mcp__github__search_repositories` — find repos by topic/language 4. `WebFetch` — for documentation pages 5. `WebSearch` — fallback for blog posts, tutorials | Sonnet. No two-step needed (code results are already structured) |
| Docs | library docs, API references, framework documentation, "how to use X", configuration reference, or any official documentation lookup | 1. `mcp__plugin_context7_context7__query-docs` — ALWAYS try first for library/SDK/API/framework docs; ~5x better token efficiency than WebFetch. Use `mcp__plugin_context7_context7__resolve-library-id` first if the library id is unknown. 2. `WebFetch` — direct URL fetch when context7 has no coverage (niche/internal docs) 3. `WebSearch` — to find the right docs page 4. `Grep`/`Glob` — if docs are local (node_modules, vendor, etc.) | Haiku (docs extraction is simple, no deep reasoning needed) |
| News | recent events, news, announcements, product launches, industry trends, "what happened with X", or any time-sensitive information | 1. `WebSearch` — primary for news queries 2. `WebFetch` — to read full articles (extract key points, don't dump HTML) | Sonnet for search + synthesis; Haiku for multi-article summarization |

## Process per category

**Academic**: Parse query → extract keywords, authors, date range. Search via paper-search-mcp (primary) + papersflow (citation graph if needed). Filter results by relevance (discard <2/5 relevance). Synthesize findings (free reasoning, no JSON constraint). Format output (Haiku, strict schema).

**Code**: Parse query → extract language, pattern, library/framework. Construct GitHub code search query with qualifiers (`language:X`, `repo:org/name`, `path:src/`, `org:orgname`). Search, retrieve top 5 results with code context. For each result: extract relevant snippet (max 20 lines), note repo + file + line. Return structured comparison.

**Docs**: Identify the documentation source URL. Fetch the specific page (not the whole site). Extract the relevant section only. Return structured reference.

**News**: Search with date-scoped queries (include year/month). Fetch top 3-5 most relevant articles. Extract key facts from each (do not dump full article text). Synthesize across sources, noting agreement/disagreement. Format output.

## Output schemas

Academic:
```json
{
  "query": "original research question",
  "papers_found": 12,
  "papers_relevant": 5,
  "synthesis": "free-text analysis of findings",
  "papers": [
    {
      "title": "...", "authors": "...", "year": 2025,
      "abstract_summary": "1-2 sentence summary",
      "relevance": 4, "doi": "...", "key_finding": "..."
    }
  ],
  "gaps": ["identified gap 1"],
  "recommendations": ["next step 1"]
}
```

Code:
```json
{
  "query": "original code research question",
  "language": "python",
  "results_found": 8,
  "results_relevant": 5,
  "patterns": [
    {
      "repo": "github.com/org/project", "file": "src/module.py", "line": 142,
      "snippet": "relevant code (max 20 lines)",
      "approach": "1-sentence description of the pattern",
      "pros": "...", "cons": "..."
    }
  ],
  "recommendation": "which pattern best fits your use case and why"
}
```

Docs:
```json
{
  "library": "...", "version": "...", "topic": "...",
  "reference": "extracted relevant section",
  "code_example": "if available",
  "url": "source URL",
  "related_pages": []
}
```

News:
```json
{
  "query": "original question",
  "as_of": "2026-04-08",
  "summary": "2-3 sentence synthesis",
  "sources": [
    {
      "title": "...", "publication": "...", "date": "...", "url": "...",
      "key_facts": ["fact 1", "fact 2"]
    }
  ],
  "confidence": "high|medium|low",
  "conflicting_reports": []
}
```

## Token budgets

| Category | Budget |
|---|---|
| Academic | Search phase: max 5,000 tokens input; synthesis phase: max 3,000 tokens output; total target <15,000 tokens |
| Code | Search phase: max 4,000 tokens input; results: max 2,000 tokens output; total target <10,000 tokens |
| Docs | Total target <5,000 tokens (should be fast and cheap) |
| News | Search: max 3,000 tokens; article extraction: max 2,000 tokens per article; total target <20,000 tokens |
