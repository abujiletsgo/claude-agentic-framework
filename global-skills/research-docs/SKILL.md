# Documentation Research Skill

## Trigger
Use when the research query involves: library docs, API references,
framework documentation, "how to use X", configuration reference,
or any official documentation lookup.

## Tools (priority order)
1. WebFetch — direct URL fetch on known docs sites
2. WebSearch — to find the right docs page
3. Grep/Glob — if docs are local (node_modules, vendor, etc.)

## Model
Haiku (docs extraction is simple, no deep reasoning needed).

## Process
1. Identify the documentation source URL
2. Fetch the specific page (NOT the whole site)
3. Extract the relevant section only
4. Return structured reference

## Output schema
```json
{
  "library": "...",
  "version": "...",
  "topic": "...",
  "reference": "extracted relevant section",
  "code_example": "if available",
  "url": "source URL",
  "related_pages": []
}
```

## Token budget
- Total: target <5,000 tokens (this should be fast and cheap)
