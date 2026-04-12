---
name: research-news
description: "Internal routing guide for news and current events research — recent events, announcements, industry trends"
user-invocable: false
---

# News & Current Events Research Skill

## Trigger
Use when the research query involves: recent events, news, announcements,
product launches, industry trends, "what happened with X", or any
time-sensitive information.

## Tools (priority order)
1. WebSearch — primary for news queries
2. WebFetch — to read full articles (extract key points, don't dump HTML)

## Model
Sonnet for search + synthesis. Haiku for multi-article summarization.

## Process
1. Search with date-scoped queries (include year/month)
2. Fetch top 3-5 most relevant articles
3. Extract key facts from each (DO NOT dump full article text)
4. Synthesize across sources, noting agreement/disagreement
5. Format output

## Output schema
```json
{
  "query": "original question",
  "as_of": "2026-04-08",
  "summary": "2-3 sentence synthesis",
  "sources": [
    {
      "title": "...",
      "publication": "...",
      "date": "...",
      "url": "...",
      "key_facts": ["fact 1", "fact 2"]
    }
  ],
  "confidence": "high|medium|low",
  "conflicting_reports": []
}
```

## Token budget
- Search: max 3,000 tokens
- Article extraction: max 2,000 tokens per article
- Total: target <20,000 tokens
