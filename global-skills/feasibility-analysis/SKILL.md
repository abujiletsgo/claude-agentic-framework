---
name: Feasibility Analysis
version: 0.1.0
description: "This skill should be used when evaluating whether a feature, architecture, or approach is practical given the current codebase, team, and constraints. It scores the feasibility of a proposed implementation before committing to it, preventing investment in impractical solutions."
---

# Feasibility Analysis Skill

Quantitative feasibility scoring (0-100%) for proposed implementations. Evaluates technical stack compatibility, codebase patterns, dependencies, team experience, and implementation clarity. Only proceed with implementations scoring 80% or higher.

## When to Use

- Before starting any non-trivial implementation
- When evaluating multiple design options (score each)
- When a proposed approach feels risky or unfamiliar
- User asks: "is this feasible?", "can we do this?", "feasibility check"
- Before adopting a new library, framework, or architecture pattern
- When estimating effort for a feature request

## Scoring Formula

Total feasibility score is a weighted average of 5 dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| Technical Stack Match | 30% | How well the approach fits the existing tech stack |
| Existing Patterns | 25% | Presence of similar patterns already in the codebase |
| External Dependencies | 20% | Risk and overhead of required external dependencies |
| Team Experience | 15% | Familiarity with the technologies involved |
| Implementation Path | 10% | Clarity and concreteness of the implementation steps |

**Decision thresholds**:
- 80-100%: **Proceed** -- Strong feasibility, implementation is well-supported
- 60-79%: **Proceed with caution** -- Address gaps before starting
- 40-59%: **Reconsider** -- Significant risks, consider alternatives
- 0-39%: **Do not proceed** -- Fundamental feasibility issues

## Workflow

### Step 1: Gather Context

Before scoring, collect essential information:

```bash
# Identify the tech stack
cat package.json 2>/dev/null || cat pyproject.toml 2>/dev/null || cat go.mod 2>/dev/null || cat Cargo.toml 2>/dev/null

# Check existing patterns (search for similar implementations)
grep -r "pattern_keyword" --include="*.py" --include="*.ts" --include="*.js" -l | head -10

# Check current dependencies
cat package-lock.json 2>/dev/null | jq '.dependencies | keys' | head -20
pip list 2>/dev/null | head -20
```

### Step 2: Score Each Dimension

#### Dimension 1: Technical Stack Match (30%)

Evaluate how well the proposed approach aligns with the current technology:

| Score | Criteria |
|-------|----------|
| 90-100 | Uses only technologies already in the stack |
| 70-89 | Minor additions to existing stack (e.g., new library in same ecosystem) |
| 50-69 | New technology but same language/runtime |
| 30-49 | Different language/runtime but compatible (e.g., Python calling Rust via FFI) |
| 0-29 | Fundamentally different stack requiring major migration |

**How to assess**: Read the project's package manifest and compare against the proposed approach's requirements.

#### Dimension 2: Existing Patterns in Codebase (25%)

Search for similar patterns already implemented:

| Score | Criteria |
|-------|----------|
| 90-100 | Nearly identical pattern exists, just needs extension |
| 70-89 | Similar pattern exists, moderate adaptation needed |
| 50-69 | Related patterns exist, significant adaptation needed |
| 30-49 | No similar patterns, but codebase architecture supports it |
| 0-29 | Conflicts with existing architecture, requires restructuring |

**How to assess**: Use Grep to search for similar implementations, data flows, or architectural patterns in the existing code.

#### Dimension 3: External Dependencies (20%)

Evaluate the risk profile of required external dependencies:

| Score | Criteria |
|-------|----------|
| 90-100 | No new dependencies required |
| 70-89 | Well-maintained, popular dependencies (>10K GitHub stars, recent commits) |
| 50-69 | Moderately popular dependencies with active maintenance |
| 30-49 | Niche dependencies or dependencies with infrequent updates |
| 0-29 | Unmaintained, deprecated, or license-incompatible dependencies |

**How to assess**: For each new dependency, check:
- Last commit date (stale if > 6 months)
- Open issues count and response time
- License compatibility
- Bundle size impact
- Security vulnerability history

#### Dimension 4: Team Experience (15%)

Assess familiarity with the technologies involved:

| Score | Criteria |
|-------|----------|
| 90-100 | Team has production experience with all technologies |
| 70-89 | Team has experience with most; minor learning curve for some |
| 50-69 | Team has conceptual familiarity, needs hands-on practice |
| 30-49 | Team has minimal experience, significant learning investment |
| 0-29 | Completely new territory for the entire team |

**How to assess**: Look at git log for patterns of technology usage, check existing code quality in related areas, and ask the user about team background.

#### Dimension 5: Clear Implementation Path (10%)

Evaluate whether concrete implementation steps can be defined:

| Score | Criteria |
|-------|----------|
| 90-100 | Step-by-step plan with no unknowns |
| 70-89 | Clear plan with 1-2 areas needing investigation |
| 50-69 | General approach is clear but several unknowns remain |
| 30-49 | High-level direction only, many unknowns |
| 0-29 | No clear path, requires significant R&D or prototyping |

**How to assess**: Try to write a concrete implementation plan. Count the number of steps that include "figure out how to..." or "investigate whether...".

### Step 3: Generate Feasibility Report

```markdown
## Feasibility Analysis Report

### Proposal
[Brief description of what is being evaluated]

### Scores

| Dimension | Weight | Score | Weighted |
|-----------|--------|-------|----------|
| Technical Stack Match | 30% | XX/100 | XX |
| Existing Patterns | 25% | XX/100 | XX |
| External Dependencies | 20% | XX/100 | XX |
| Team Experience | 15% | XX/100 | XX |
| Implementation Path | 10% | XX/100 | XX |
| **TOTAL** | **100%** | | **XX/100** |

### Decision: [PROCEED / PROCEED WITH CAUTION / RECONSIDER / DO NOT PROCEED]

### Dimension Details

**Technical Stack Match (XX/100)**:
[Explanation of score with specific evidence]

**Existing Patterns (XX/100)**:
[Files/patterns found or not found]

**External Dependencies (XX/100)**:
[List of dependencies with risk assessment]

**Team Experience (XX/100)**:
[Evidence from codebase or user input]

**Implementation Path (XX/100)**:
[Steps identified, unknowns flagged]

### Risk Mitigation
[For scores below 70, suggest specific actions to improve feasibility]

### Alternatives
[If total score < 60, suggest alternative approaches with estimated scores]
```

### Step 4: Decision Gate

Based on the total score:

- **>= 80%**: Present the report and proceed to implementation
- **60-79%**: Present the report, highlight risks, ask user whether to proceed or address gaps first
- **40-59%**: Present the report, recommend alternative approaches, ask user for direction
- **< 40%**: Present the report, strongly recommend against proceeding, propose alternatives

## Examples

### Example 1: Adding Real-Time WebSocket Support

**Proposal**: Add WebSocket support to an Express.js REST API.

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Stack Match | 85 | Express.js + Socket.io is standard pairing |
| Existing Patterns | 60 | REST only currently, but middleware pattern transfers |
| Dependencies | 80 | Socket.io is well-maintained and widely used |
| Team Experience | 70 | Team knows Express, Socket.io is new but documented |
| Implementation Path | 75 | Clear steps, unknown around scaling WebSocket connections |

**Total**: 85 * 0.30 + 60 * 0.25 + 80 * 0.20 + 70 * 0.15 + 75 * 0.10 = 74.0

**Decision**: PROCEED WITH CAUTION. Address WebSocket scaling unknowns first.

### Example 2: Migrating from REST to GraphQL

**Proposal**: Replace REST API with GraphQL.

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Stack Match | 50 | Same language, entirely different API paradigm |
| Existing Patterns | 20 | Zero GraphQL patterns, requires full rewrite of API layer |
| Dependencies | 70 | Apollo/graphql-yoga are mature |
| Team Experience | 30 | No GraphQL experience on team |
| Implementation Path | 40 | Many unknowns around schema design, N+1, auth |

**Total**: 50 * 0.30 + 20 * 0.25 + 70 * 0.20 + 30 * 0.15 + 40 * 0.10 = 42.5

**Decision**: RECONSIDER. Suggest incremental approach: add GraphQL alongside REST for one endpoint as a pilot.

### Example 3: Quick Feasibility (Small Feature)

For small features, run a mental checklist (no formal report needed):
- Stack match? Yes / No
- Similar pattern exists? Yes / No
- New dependencies? None / Some / Many
- Know how to do it? Yes / Mostly / No
- Can I outline the steps? Yes / Roughly / No

If all "Yes" or "Mostly" -- proceed. Otherwise, run the full analysis.

## Anti-Patterns

### What to Avoid

1. **Skipping feasibility for "obvious" tasks** -- Even experienced developers misjudge complexity. A 2-minute feasibility check can save hours.

2. **Inflating scores to justify a preferred approach** -- Be honest. If the score is low, that is valuable information, not a failure.

3. **Ignoring low dimension scores** -- A total of 75% with one dimension at 20% is a red flag. Address the weak dimension specifically.

4. **Analysis without action** -- Feasibility analysis should lead to a decision. Do not just generate a report and move on.

5. **Scoring without evidence** -- Every score must be backed by concrete evidence (files found, dependencies checked, patterns searched). Gut feelings are starting points, not scores.

6. **One-time assessment** -- Revisit feasibility if significant new information emerges during implementation.

## Integration with Other Skills

- **Brainstorm Before Code**: Score each design option during brainstorming
- **Task Decomposition**: Use feasibility to estimate task complexity and time
- **Downstream Correction**: If feasibility drops during implementation, trigger course correction
- **Verification Checklist**: Include "feasibility assumptions still hold" in verification
