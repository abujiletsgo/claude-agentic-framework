---
name: Brainstorm Before Code
version: 0.1.0
description: "This skill should be used when starting a new feature, tackling a complex problem, or when the user says 'brainstorm', 'design first', 'think before code', or 'plan this out'. It enforces a design-thinking phase before writing any code to prevent premature implementation."
---

# Brainstorm Before Code Skill

Structured ideation and design process that must complete before any code is written. Uses Socratic questioning, multi-option design exploration, and explicit user validation to prevent jumping straight to implementation.

## When to Use

- User asks: "brainstorm", "design first", "think before code", "plan this"
- Starting a new feature or module from scratch
- Facing a complex problem with multiple valid approaches
- When requirements are ambiguous or underspecified
- Before any task estimated at more than 30 minutes of implementation

## Workflow

### Phase 1: Socratic Questioning -- Clarify Requirements

**Goal**: Expose hidden assumptions and missing requirements before any design work.

Ask these questions (adapt to context, do not ask all mechanically):

**Scope Questions**:
- What is the MINIMUM viable version of this feature?
- What is explicitly OUT of scope?
- Who are the users/consumers of this code?

**Constraint Questions**:
- Are there performance requirements (latency, throughput, memory)?
- Are there compatibility constraints (browsers, OS, API versions)?
- Are there security or compliance requirements?

**Integration Questions**:
- What existing code does this interact with?
- What interfaces/contracts must be maintained?
- Are there upstream or downstream dependencies?

**Clarification Questions**:
- "You mentioned X -- does that mean Y or Z?"
- "What should happen when [edge case]?"
- "Is [assumption] correct?"

**Rules**:
- Ask 3-5 focused questions, not 20 generic ones
- Wait for the user's answers before proceeding
- Capture answers as design constraints for Phase 2
- If the user says "just do it", ask the 2 most critical questions only

### Phase 2: Design Options -- Present 2-3 Approaches

**Goal**: Explore the solution space before committing to one path.

For each approach, provide:

```markdown
## Design Options

### Option A: [Name -- e.g., "Event-Driven Architecture"]
**Approach**: [1-2 sentence description]
**Pros**:
- [Advantage 1]
- [Advantage 2]
**Cons**:
- [Disadvantage 1]
- [Disadvantage 2]
**Effort**: [Low/Medium/High]
**Risk**: [Low/Medium/High]
**Best when**: [Scenario where this option shines]

### Option B: [Name -- e.g., "Direct Service Calls"]
...

### Option C: [Name -- e.g., "Hybrid Approach"]
...

### Recommendation
I recommend **Option [X]** because [reasoning tied to constraints from Phase 1].
```

**Rules for good design options**:
- Options must be genuinely different (not minor variations)
- Include at least one simple/conservative option
- Include at least one option that the user might not have considered
- Be honest about trade-offs -- no option is perfect
- Tie pros/cons to the specific constraints identified in Phase 1

### Phase 3: User Validation -- Get Explicit Approval

**Goal**: Confirm the chosen approach before writing any code.

Present the chosen design for approval:

```markdown
## Design Decision

**Chosen approach**: [Option X]
**Key design decisions**:
1. [Decision 1 -- e.g., "Use SQLite instead of PostgreSQL for local-first"]
2. [Decision 2 -- e.g., "Event sourcing for audit trail"]
3. [Decision 3 -- e.g., "REST API with versioning"]

**File structure**:
```
src/
  feature/
    module_a.py    -- [purpose]
    module_b.py    -- [purpose]
    types.py       -- [purpose]
tests/
  test_feature/
    test_module_a.py
    test_module_b.py
```

**Dependencies**: [New packages needed, if any]
**Breaking changes**: [None / List of breaking changes]

Shall I proceed with this design?
```

**Rules**:
- Do NOT start coding until the user explicitly approves
- If the user modifies the design, update the document before proceeding
- "Sounds good", "go ahead", "yes" count as approval
- Silence or ambiguity does NOT count as approval -- ask again

### Phase 4: Document -- Save Design Before Implementation

**Goal**: Create a persistent design record that survives context compaction.

Save the design decision to a file:

```bash
# Create design doc in project root or docs/ directory
mkdir -p docs/designs
```

Write the design document:

```markdown
# Design: [Feature Name]
Date: [YYYY-MM-DD]
Status: Approved

## Context
[Why this feature is being built]

## Constraints
[From Phase 1 questioning]

## Decision
[Chosen option and rationale]

## Alternatives Considered
[Brief summary of rejected options and why]

## Implementation Plan
[Ordered list of implementation steps]
```

Then proceed to implementation (ideally using TDD Workflow skill).

## Brainstorm Depth Levels

Adapt the depth of brainstorming to the task size:

| Task Size | Questioning | Options | Documentation |
|-----------|------------|---------|--------------|
| **Small** (< 30 min) | 1-2 key questions | 2 quick options, verbal | Inline comment |
| **Medium** (30 min - 2 hr) | 3-5 questions | 2-3 options with pros/cons | Design section in PR |
| **Large** (> 2 hr) | Full Socratic phase | 3+ detailed options | Dedicated design doc |
| **Architecture** (multi-day) | Multiple rounds | ADR (Architecture Decision Record) format | Permanent docs/adr/ |

## Examples

### Example 1: New API Endpoint

**Phase 1 -- Questions**:
- "What data does this endpoint return? Full objects or summaries?"
- "What authentication is required? Same as existing endpoints?"
- "Expected request volume? Caching needed?"

**Phase 2 -- Options**:
- Option A: REST endpoint with pagination
- Option B: GraphQL query (if GraphQL already in use)
- Option C: REST with cursor-based pagination

**Phase 3**: User approves Option A with 50-item default page size.

**Phase 4**: Design doc saved, proceed to TDD implementation.

### Example 2: Database Schema Change

**Phase 1 -- Questions**:
- "Is this additive (new columns) or destructive (removing/renaming)?"
- "Do we need a data migration for existing records?"
- "What is the rollback strategy?"

**Phase 2 -- Options**:
- Option A: Add nullable columns (backward compatible)
- Option B: New table with foreign key (normalized)
- Option C: JSON column for flexible schema

**Phase 3**: User approves Option A for simplicity.

### Example 3: Quick Brainstorm (Small Task)

User: "Add retry logic to the API client"

**Quick questions**: "Should we use exponential backoff? What is the max retry count?"
User: "Yes, 3 retries with exponential backoff"

**Quick options**:
- A: Manual retry loop with sleep
- B: Use tenacity/retry library

**Approval**: User picks B. Proceed immediately.

## Anti-Patterns

### What to Avoid

1. **Analysis paralysis** -- Brainstorming is time-boxed. For small tasks, spend 2-5 minutes. For large tasks, cap at 30 minutes. If stuck between two good options, pick the simpler one.

2. **Asking too many questions** -- 3-5 focused questions, not an interrogation. If the user seems impatient, compress to the top 2 questions.

3. **Presenting fake options** -- All options must be genuinely viable. Do not include a straw man just to make your preferred option look better.

4. **Designing in a vacuum** -- Always ground the design in the existing codebase. Read relevant code before proposing options.

5. **Skipping validation** -- Even if the design seems obvious, confirm with the user. Their mental model may differ from yours.

6. **Over-documenting small tasks** -- A 10-minute fix does not need an Architecture Decision Record. Scale documentation to task size.

7. **Brainstorming after coding** -- If you catch yourself already writing code, STOP. Go back to Phase 1. Retrofitting a design to existing code is worse than no design.

## Integration with Other Skills

- **Feasibility Analysis**: Run feasibility scoring on each design option
- **Task Decomposition**: After design approval, decompose into TDD-sized tasks
- **TDD Workflow**: Use the approved design to drive test-first implementation
- **Verification Checklist**: Include design conformance in final verification
