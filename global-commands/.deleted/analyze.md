---
description: Delegate deep code analysis to sub-agents
---

# Analyze & Evaluate

**Purpose:** Offload deep analysis tasks (architecture review, code quality, performance patterns) to sub-agents.

## When to Use

✅ Use `/analyze` when:
- Reviewing code architecture
- Evaluating code quality across modules
- Finding performance bottlenecks
- Assessing security patterns
- Understanding complex interactions

## Usage Pattern

```
/analyze "Review the security of the authentication system"
/analyze "Evaluate the database query patterns for N+1 issues"
/analyze "Assess the error handling strategy across the API"
```

## Delegation Strategy

Spawn Explore sub-agent with analytical focus:

```
Task tool (subagent_type="Explore"):
"Analyze [target area]. Read relevant files, evaluate patterns, identify issues and best practices. Report findings with specific examples and recommendations."
```

## Report Format Expected

```markdown
### Analysis Report: [Topic]

**Overall Assessment**: [Summary rating/evaluation]

**Strengths**:
- [Good patterns found]

**Concerns**:
- [Issues identified with severity]

**Recommendations**:
1. [Actionable suggestion]
2. [Another suggestion]

**Examples**:
- [file:line] - [specific example]
```

## Token Efficiency

- Sub-agent analysis: 30k+ tokens (deep reading)
- Report back: 2-3k tokens
- Primary context: Preserved ✅
