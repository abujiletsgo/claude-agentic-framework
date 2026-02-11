---
name: Downstream Correction
version: 0.1.0
description: "This skill should be used when an implementation reveals that initial assumptions were wrong, requirements need revision, or a technical decision should be reversed. It applies the A3 principle: later roles can override earlier decisions when better information emerges, preventing cascading errors from early mistakes."
---

# Downstream Correction Skill (A3 Principle)

Later stages in the development process can and should correct decisions made in earlier stages when new information makes those decisions suboptimal. This prevents cascading errors where one wrong assumption contaminates all subsequent work.

## When to Use

- During implementation, you discover an earlier design decision was wrong
- A technical constraint invalidates a product requirement
- Testing reveals that the chosen approach has fundamental issues
- A dependency assumption proves incorrect
- Performance profiling shows the architecture cannot meet requirements
- User asks: "should we change direction?", "this isn't working", "revisit the plan"

## Core Principle

**Traditional (rigid, waterfall-style) flow**:
```
PM decides -> Architect designs -> Dev implements -> QA tests
     |              |                    |              |
     v              v                    v              v
  No one questions earlier stages. Mistakes cascade.
```

**A3 Corrective flow**:
```
PM decides -> Architect designs -> Dev implements -> QA tests
     ^              ^                    |              |
     |              |                    v              v
  Earlier decisions can be revised when downstream finds issues.
```

The person closest to the problem has the best information. A developer who discovers that PostgreSQL is overkill for the actual data volume should be empowered to propose SQLite. A QA engineer who finds the API design makes testing impossible should be empowered to request API changes.

## Workflow

### Step 1: Detect the Correction Trigger

Recognize when downstream correction is needed:

| Trigger | Signal | Example |
|---------|--------|---------|
| **Assumption invalidated** | Code reveals constraint not visible during design | "The API doesn't support batch operations like we assumed" |
| **Performance mismatch** | Measured performance contradicts estimates | "PostgreSQL queries take 200ms, need < 50ms for this volume" |
| **Complexity explosion** | Implementation is 3x more complex than designed | "The event sourcing design requires 5 new services for what should be simple CRUD" |
| **Dependency problem** | Required library is unmaintained, incompatible, or missing features | "The recommended library hasn't been updated in 2 years" |
| **Requirements conflict** | Two requirements are mutually exclusive | "Real-time sync AND offline-first are incompatible with current architecture" |
| **Better alternative found** | Simpler approach discovered during implementation | "We can use the existing queue instead of building a new pub/sub system" |

### Step 2: Document the Correction

Before making changes, document what is being corrected and why:

```markdown
## Downstream Correction Record

### Original Decision
- **Made by**: [Role/stage -- e.g., "Design phase", "Architecture review"]
- **Decision**: [What was decided]
- **Rationale**: [Why it was decided that way]

### Correction
- **Detected by**: [Role/stage -- e.g., "During implementation", "During testing"]
- **Issue**: [What was discovered that invalidates the original decision]
- **Evidence**: [Concrete data -- benchmarks, code examples, error messages]

### Proposed Change
- **New decision**: [What should replace the original decision]
- **Impact**: [What needs to change -- code, tests, docs, timeline]
- **Risk**: [Risks of the correction itself]

### Approval
- **Status**: [Proposed / Approved / Rejected]
- **Approved by**: [User/lead]
- **Date**: [YYYY-MM-DD]
```

### Step 3: Present the Correction to the User

Frame the correction constructively:

```markdown
## Course Correction Needed

I discovered an issue with our current approach while [implementing/testing/profiling].

**Current plan**: [Brief description of the current approach]

**Problem found**: [What doesn't work and why, with evidence]

**Proposed correction**: [New approach]

**Impact**:
- Code changes: [Files affected]
- Timeline: [Faster/same/slower]
- Risk: [Lower/same/higher]

**Why this is better**: [Concrete benefits with evidence]

Do you approve this correction?
```

### Step 4: Apply or Escalate

Based on the correction's scope:

| Scope | Action |
|-------|--------|
| **Minor** (same approach, different detail) | Apply and inform: "I used X instead of Y because..." |
| **Moderate** (different approach, same outcome) | Propose and get approval before proceeding |
| **Major** (different outcome or timeline) | Full correction document, explicit approval required |
| **Fundamental** (invalidates the entire plan) | Stop work, present findings, brainstorm alternatives |

### Step 5: Update All Artifacts

After a correction is approved:

1. **Update design docs** with the correction and rationale
2. **Update task decomposition** if tasks changed
3. **Update tests** to reflect the new approach
4. **Add a note** to the correction log for project history
5. **Notify** anyone working on dependent tasks

## Correction Authority Matrix

Who can correct what:

| Stage | Can Correct | Must Escalate |
|-------|------------|---------------|
| **Planning** | Requirements ambiguity, scope clarification | Budget changes, deadline changes |
| **Design** | Technology choices, architecture patterns | Fundamental requirement changes |
| **Implementation** | Library choices, data structures, algorithms | Architecture changes, API contract changes |
| **Testing** | Test strategy, coverage targets | Feature behavior changes, acceptance criteria |
| **Review** | Code style, naming, minor refactoring | Algorithmic changes, public API changes |

## Examples

### Example 1: Database Technology Correction

**Original decision** (Design phase): "Use PostgreSQL for all data storage"
**Downstream finding** (Implementation): The data is simple key-value pairs, total volume < 10MB, single user.

```markdown
## Course Correction: Database Technology

**Problem**: PostgreSQL requires a separate server process, connection pooling,
and migration tooling for what is essentially a 10MB key-value store.

**Evidence**:
- Data model has 3 tables, all simple key-value
- Maximum dataset: ~5,000 records, ~10MB total
- Single user, no concurrent access
- Application is a CLI tool that runs locally

**Proposed correction**: Use SQLite instead of PostgreSQL.

**Benefits**:
- Zero infrastructure (no server, no Docker, no connection string)
- Simpler deployment (single file database)
- Faster for this workload (no network roundtrip)
- Reduces dependencies from 3 packages to 1

**Impact**:
- Rewrite: 2 files (db.py, models.py)
- Timeline: Saves ~2 hours of PostgreSQL setup
- Tests: Simpler (no test database provisioning)

Approved -> Implemented -> Tests pass.
```

### Example 2: API Design Correction

**Original decision** (PM): "REST API with JSON responses"
**Downstream finding** (Frontend dev): The UI needs to display partial results as they stream in.

```markdown
## Course Correction: API Response Format

**Problem**: REST with JSON requires the full response to be assembled
before sending. The LLM processing takes 10-30 seconds, leaving
users staring at a spinner.

**Proposed correction**: Add Server-Sent Events (SSE) for the
generation endpoint while keeping REST for all other endpoints.

**Impact**: One endpoint changes from POST returning JSON to POST
returning an SSE stream. All other endpoints unchanged.
```

### Example 3: Minor Self-Correction (No Approval Needed)

```
Original plan: Use lodash.debounce for input handling
Finding: The project already has a custom debounce utility in utils/timing.ts
Correction: Use existing utility instead of adding a dependency

[Applied automatically, noted in commit message]
```

## Anti-Patterns

### What to Avoid

1. **Silently changing the plan** -- Always document corrections, even minor ones. Future you (or other developers) need to know why the implementation differs from the design.

2. **Refusing to correct out of sunk cost** -- "We already spent 3 days on this approach" is not a reason to continue if the approach is wrong. Cut losses early.

3. **Correcting without evidence** -- "I think X would be better" is not a correction. "I benchmarked X and it's 5x faster for our workload" is a correction.

4. **Over-correcting** -- Not every imperfection needs correction. If the current approach works and meets requirements, minor aesthetic preferences are not worth the disruption.

5. **Correction ping-pong** -- Changing direction more than twice on the same decision indicates the problem is not well understood. Stop and brainstorm (use Brainstorm Before Code skill).

6. **Blaming upstream** -- Corrections are collaborative, not adversarial. "The design was wrong" is less productive than "New information suggests a different approach."

7. **Not updating artifacts** -- A correction that lives only in someone's memory will be lost. Update all design docs, task lists, and tests.

## Integration with Other Skills

- **Brainstorm Before Code**: When a fundamental correction is needed, re-enter the brainstorm phase
- **Feasibility Analysis**: Re-run feasibility scoring after correction to validate the new approach
- **Task Decomposition**: Update the task breakdown to reflect corrected approach
- **Verification Checklist**: Add "correction assumptions validated" to the checklist
