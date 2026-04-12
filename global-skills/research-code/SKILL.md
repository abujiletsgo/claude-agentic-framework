---
name: research-code
description: "Internal routing guide for code pattern research — GitHub search, implementation patterns, library usage"
user-invocable: false
---

# Code Research Skill

## Trigger
Use when the research query involves: code patterns, implementations,
"how does X library handle Y", firmware, API usage, open source
projects, or any code-related investigation.

## Tools (priority order)
1. mcp__github__search_code — cross-repo code search (free, requires GITHUB_TOKEN)
2. mcp__github__get_file_contents — read specific files from repos
3. mcp__github__search_repositories — find repos by topic/language
4. WebFetch — for documentation pages
5. WebSearch — fallback for blog posts, tutorials

## Model
Sonnet. No two-step needed (code results are already structured).

## Process
1. Parse query → extract language, pattern, library/framework
2. Construct GitHub code search query with appropriate qualifiers:
   - language:X for language filter
   - repo:org/name for specific repo
   - path:src/ for path filtering
   - org:orgname for org-scoped search
3. Search, retrieve top 5 results with code context
4. For each result: extract relevant snippet (max 20 lines), note repo + file + line
5. Return structured comparison

## Output schema
```json
{
  "query": "original code research question",
  "language": "python",
  "results_found": 8,
  "results_relevant": 5,
  "patterns": [
    {
      "repo": "github.com/org/project",
      "file": "src/module.py",
      "line": 142,
      "snippet": "relevant code (max 20 lines)",
      "approach": "1-sentence description of the pattern",
      "pros": "...",
      "cons": "..."
    }
  ],
  "recommendation": "which pattern best fits your use case and why"
}
```

## Token budget
- Search phase: max 4,000 tokens input
- Results: max 2,000 tokens output
- Total: target <10,000 tokens
