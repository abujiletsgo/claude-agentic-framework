---
name: research-docs
description: "Library documentation and API reference lookup. Direct WebFetch to
  official docs URLs. Fastest and cheapest research skill."
user-invocable: true
---

# /research-docs — Documentation Lookup

Fast library documentation and API reference lookup via direct URL fetch.

## Protocol

1. If docs URL is known or can be inferred: WebFetch directly
2. If URL unknown: WebSearch "<library> official documentation" → extract URL → WebFetch
3. Return relevant excerpt with source URL
4. Token budget: <5K total — be concise

## URL Inference Rules

- Python: docs.python.org or <pkg>.readthedocs.io
- npm: npmjs.com/package/<pkg> or package homepage
- GitHub: github.com/<org>/<repo>#readme
- Major frameworks: well-known URLs (nextjs.org/docs, docs.djangoproject.com, etc.)

## Output

```
**Source**: <url>
**Relevant section**: <section title>
---
<relevant docs content>
```

Model: Haiku — this is extraction, not reasoning.
No two-step. No TOON — docs content is non-uniform.
