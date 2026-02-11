---
name: Task Decomposition
version: 0.1.0
description: "This skill should be used when facing a large feature, multi-step implementation, or when the user asks to 'break this down', 'decompose', 'plan the steps', or 'estimate effort'. It breaks down complex tasks into atomic, time-estimated micro-tasks with parallel execution markers."
---

# Task Decomposition Skill

Systematic breakdown of complex tasks into small, executable units with time estimates and dependency tracking. Each micro-task should be completable in a single focused session. Marks tasks that can run in parallel.

## When to Use

- User asks: "break this down", "decompose", "plan the steps", "estimate effort"
- Task will take more than 30 minutes of implementation
- Multiple files, modules, or systems need to be modified
- Task has unclear boundaries or hidden complexity
- Before delegating work to builder/validator subagents
- When creating TaskList entries for the framework

## Task Size Categories

| Size | Duration | Description | Examples |
|------|----------|-------------|----------|
| **Atomic** | 2-5 min | Single focused change, no context switching | Add a function, fix a typo, update a constant, add an import |
| **Small** | 5-15 min | One logical unit, minimal dependencies | Implement an endpoint, write tests for a function, add a config option |
| **Medium** | 15-30 min | Multiple related changes, some coordination | Complete a module, integrate a feature, refactor a class |
| **Large** | 30-60 min | Should be decomposed further | If you have a "large" task, break it into small/medium tasks |
| **Epic** | > 60 min | Must be decomposed | Break into medium tasks, group into milestones |

**Rule**: No task should exceed 30 minutes. If it does, decompose further.

## Workflow

### Step 1: Understand the Full Scope

Before decomposing, understand the complete picture:

1. **Read relevant code** to understand the current state
2. **Identify all files** that will need changes
3. **Map dependencies** between components
4. **List unknowns** that need investigation

```bash
# Find relevant files
grep -r "keyword" --include="*.py" --include="*.ts" -l | head -20

# Understand module structure
find src/ -name "*.py" -o -name "*.ts" | head -30

# Check existing tests
find tests/ -name "*.py" -o -name "*.spec.ts" | head -20
```

### Step 2: Identify Natural Boundaries

Break the task along these natural seams:

**By Layer**:
- Data model / Schema changes
- Business logic / Service layer
- API / Interface layer
- Tests for each layer
- Documentation

**By Feature**:
- Core functionality (happy path)
- Error handling
- Edge cases
- Performance optimization
- Logging / Observability

**By File**:
- Each file modification is a potential task boundary
- New files are natural task units

### Step 3: Create the Task List

Format each task with:

```markdown
## Task Decomposition: [Feature Name]

### Overview
- **Total estimated time**: [sum of all tasks]
- **Total tasks**: [count]
- **Parallel lanes**: [number of independent streams]
- **Critical path**: [longest sequential chain]

### Tasks

#### Lane A: [Name -- e.g., "Data Layer"]

| # | Task | Size | Est. | Depends On | Parallel |
|---|------|------|------|------------|----------|
| 1 | Create User model with fields | Small | 10 min | -- | Yes (with #4) |
| 2 | Add migration for users table | Atomic | 5 min | #1 | No |
| 3 | Write User model tests | Small | 10 min | #1 | Yes (with #2) |

#### Lane B: [Name -- e.g., "API Layer"]

| # | Task | Size | Est. | Depends On | Parallel |
|---|------|------|------|------------|----------|
| 4 | Define API schema/types | Atomic | 5 min | -- | Yes (with #1) |
| 5 | Implement POST /users endpoint | Small | 15 min | #1, #4 | No |
| 6 | Implement GET /users endpoint | Small | 10 min | #1, #4 | Yes (with #5) |
| 7 | Write API integration tests | Medium | 20 min | #5, #6 | No |

#### Lane C: [Name -- e.g., "Infrastructure"]

| # | Task | Size | Est. | Depends On | Parallel |
|---|------|------|------|------------|----------|
| 8 | Add input validation middleware | Small | 10 min | #4 | Yes (with #5) |
| 9 | Add error response formatting | Atomic | 5 min | -- | Yes (with any) |

### Execution Order
1. **Parallel start**: #1 + #4 + #9 (3 tasks, ~10 min)
2. **After #1**: #2 + #3 in parallel (~10 min)
3. **After #1 + #4**: #5 + #6 + #8 in parallel (~15 min)
4. **After #5 + #6**: #7 (~20 min)
5. **Total wall-clock time**: ~55 min (vs ~90 min sequential)
```

### Step 4: Validate the Decomposition

Run these checks:

1. **Completeness**: Do all tasks together achieve the original goal?
2. **No gaps**: Is there anything needed that is not listed?
3. **No overlaps**: Do any tasks duplicate work?
4. **Size check**: Are all tasks under 30 minutes?
5. **Dependency check**: Are dependencies correctly identified?
6. **Parallel check**: Are parallel opportunities marked?
7. **Test coverage**: Does every functional task have a corresponding test task?

### Step 5: Create Framework Tasks

Convert the decomposition into TaskCreate calls:

```
For each task in the decomposition:
1. TaskCreate with subject, description, and activeForm
2. TaskUpdate to set dependencies (addBlockedBy)
3. Mark parallel-executable tasks in metadata
```

## Estimation Heuristics

When estimating task duration:

| Factor | Multiplier | Example |
|--------|-----------|---------|
| New code (greenfield) | 1x | Writing a new function |
| Modifying existing code | 1.3x | Changing a function's behavior |
| Integrating with external API | 1.5x | Adding a third-party service call |
| Unfamiliar codebase area | 1.5x | First time touching this module |
| Complex business logic | 1.5x | Multiple branching conditions |
| Database schema changes | 1.3x | Migrations, data backfill |
| Cross-module changes | 1.5x | Changes spanning 3+ modules |
| Has existing tests to update | 1.2x | Tests need modification too |

**Rule of thumb**: Take your initial estimate and multiply by 1.5 for safety. Developers consistently underestimate.

## Examples

### Example 1: Add User Authentication

```markdown
## Task Decomposition: User Authentication

### Overview
- **Total estimated time**: ~2.5 hours
- **Total tasks**: 10
- **Parallel lanes**: 3
- **Critical path**: #1 -> #3 -> #5 -> #7 -> #10 (90 min)

### Lane A: Data & Models
| # | Task | Size | Est. | Depends On |
|---|------|------|------|------------|
| 1 | Add password_hash field to User model | Atomic | 5 min | -- |
| 2 | Create Session model | Small | 10 min | -- |
| 3 | Implement password hashing utility | Small | 10 min | #1 |

### Lane B: Auth Logic
| # | Task | Size | Est. | Depends On |
|---|------|------|------|------------|
| 4 | Implement JWT token generation | Small | 15 min | -- |
| 5 | Implement login endpoint | Small | 15 min | #3, #4 |
| 6 | Implement logout endpoint | Small | 10 min | #2, #4 |
| 7 | Add auth middleware | Medium | 20 min | #4 |

### Lane C: Testing & Polish
| # | Task | Size | Est. | Depends On |
|---|------|------|------|------------|
| 8 | Write unit tests for password hashing | Small | 10 min | #3 |
| 9 | Write integration tests for login flow | Medium | 20 min | #5, #6 |
| 10 | Write middleware tests | Small | 15 min | #7 |
```

### Example 2: Quick Decomposition (Small Feature)

For simple features, use a flat list:

```markdown
## Task Decomposition: Add Rate Limiting

1. [Atomic, 5 min] Install rate-limiting package
2. [Small, 10 min] Configure rate limiter middleware
3. [Atomic, 5 min] Apply to API routes
4. [Small, 10 min] Write tests for rate limiting
5. [Atomic, 5 min] Update API documentation

Tasks 1-3 are sequential. Task 4 can start after task 3. Task 5 is independent.
Total: ~35 min wall-clock.
```

## Anti-Patterns

### What to Avoid

1. **Tasks too vague** -- "Implement feature" is not a task. "Add validateEmail function that checks format and uniqueness" is a task.

2. **Tasks too granular** -- "Add import statement" is not worth tracking. Group trivially small changes into their parent task.

3. **Missing dependencies** -- Failing to identify that task B needs task A's output leads to blocked work and wasted effort.

4. **Sequential bias** -- Not identifying parallel opportunities. Ask: "Can this task start before the previous one finishes?"

5. **Forgetting tests** -- Every functional task should have a corresponding test task. If testing is an afterthought, it will be skipped.

6. **Optimistic estimates** -- Always use the 1.5x safety multiplier. "It should only take 5 minutes" is famous last words.

7. **No critical path analysis** -- Without identifying the longest sequential chain, you cannot give an accurate total time estimate.

## Integration with Other Skills

- **Brainstorm Before Code**: Decompose after design approval, not before
- **TDD Workflow**: Each task maps to one or more TDD cycles
- **Feasibility Analysis**: Use feasibility scores to adjust time estimates
- **Verification Checklist**: Add verification as the final task in every decomposition
