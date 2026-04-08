---
name: research-news
description: "Current events and news research: recent developments, trends,
  announcements. Uses WebSearch + WebFetch for up-to-date information."
user-invocable: true
---

# /research-news — Current Events Research

Find recent developments, trends, and announcements via web search.

## Protocol

1. Run WebSearch with date-scoped query (append year to anchor recency)
2. Identify top 3-5 most relevant results
3. WebFetch full content of key results (be selective — not all)
4. Synthesize into bulleted summary with source attribution
5. Token budget: <20K total

## Query Construction

- Append year: `<topic> 2026` or `<topic> site:techcrunch.com`
- Use news-specific domains when appropriate: site:reuters.com, site:techcrunch.com
- Avoid academic sites for news queries

## Output

```
## Recent: <topic>
- <finding> — [Source](url)
- <finding> — [Source](url)
**Date range covered**: <oldest to newest result>
```

No TOON — news summaries are non-uniform prose.
No two-step — straightforward aggregation.
