# F-Threads: Fusion Threads (Best of N)

## The Principle

Language models are non-deterministic. One agent gives you one roll of the dice. **N agents in parallel** makes the probability of finding the optimal solution approach 100%.

F-Threads exploit this by running **multiple agents on the same task**, then **fusing** the best results into a final output that's better than any individual attempt.

---

## Why F-Threads Work

### The Math

```
Single agent accuracy on complex task:     ~60-70%
Best of 3 agents (independent attempts):   ~90-95%
Best of 5 agents:                          ~97-99%
```

Each agent explores a different region of the solution space. With enough diversity, at least one will find the optimal path.

### The Diversity Problem

If all agents think the same way, you get 3 copies of the same answer. F-Threads solve this by assigning **different personas** that force divergent approaches:

| Persona | Approach | Strength |
|---------|----------|----------|
| Pragmatist | Ship fast, KISS | Simplicity, readability |
| Architect | Scale and maintain | Abstractions, extensibility |
| Optimizer | Performance first | Speed, efficiency |
| Security | Defense in depth | Safety, edge cases |
| Minimalist | Least code possible | Conciseness |

---

## Implementation

### Level 1: Slash Command (Immediate)

**File**: `~/.claude/commands/fusion.md`

**Usage**:
```
/fusion "Implement a rate limiter for the API"
```

**What happens**:
1. 3 sub-agents spawn in parallel (Pragmatist, Architect, Optimizer)
2. Each solves the task independently
3. Fusion Judge scores all solutions (correctness, simplicity, robustness, performance, maintainability)
4. Winner selected, improvements cherry-picked from losers
5. Final fused solution applied to codebase

**Cost**: ~3x a single agent (but solution quality approaches optimal)

---

### Level 2: Custom N and Personas

For critical tasks, increase N or customize personas.

**Example**: Security-critical feature

```
/fusion "Implement OAuth2 authentication" --personas security,architect,pragmatist,pentester --n 4
```

**Custom persona definitions** (in the prompt):

```markdown
### Agent 1: "The Security Engineer"
Solve with defense-in-depth. Assume all inputs are hostile.
Validate every boundary. Use established crypto libraries only.

### Agent 2: "The Architect"
Design for maintainability. Clean interfaces.
Dependency injection for testing. Clear separation of concerns.

### Agent 3: "The Pragmatist"
Ship it. Use battle-tested libraries (passport.js, etc).
Minimal custom code. Follow the framework's happy path.

### Agent 4: "The Pentester"
Write the solution, then try to break it.
Include the attack vectors you tested in your response.
```

---

### Level 3: P-Threads (Parallel Sandbox Environments)

**Prerequisite**: E2B Sandboxes (Step 8)

Instead of just generating code, spin up **N separate sandbox environments**. Each agent builds the **full running application** independently.

**Workflow**:

```
┌──────────────────────────────────────────────┐
│  Orchestrator (F-Thread Controller)          │
├──────────────────────────────────────────────┤
│                                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │Sandbox 1│ │Sandbox 2│ │Sandbox 3│       │
│  │Pragmatst│ │Architect│ │Optimizer│       │
│  │         │ │         │ │         │       │
│  │ Build   │ │ Build   │ │ Build   │       │
│  │ Test    │ │ Test    │ │ Test    │       │
│  │ Deploy  │ │ Deploy  │ │ Deploy  │       │
│  │         │ │         │ │         │       │
│  │ URL: A  │ │ URL: B  │ │ URL: C  │       │
│  └─────────┘ └─────────┘ └─────────┘       │
│                                              │
│  ┌─────────────────────────────────┐        │
│  │  Reviewer Agent                 │        │
│  │  Visit URL A, B, C             │        │
│  │  Run test suite against each   │        │
│  │  Score and select winner       │        │
│  │  Copy winning code to repo     │        │
│  └─────────────────────────────────┘        │
└──────────────────────────────────────────────┘
```

**Implementation**:

```markdown
# P-Thread: Parallel Sandbox Fusion

## Step 1: Spawn Sandboxes
Launch 3 sandboxes in parallel using E2B:

### Sandbox 1 (Pragmatist)
\sandbox "Build a rate limiter API with the simplest approach. Use Express.js. Deploy on port 3000."

### Sandbox 2 (Architect)
\sandbox "Build a rate limiter API with clean architecture. Use dependency injection, repository pattern. Express.js. Port 3000."

### Sandbox 3 (Optimizer)
\sandbox "Build a rate limiter API optimized for throughput. Use sliding window algorithm, Redis backing. Express.js. Port 3000."

## Step 2: Test All
Run the same test suite against each deployed URL:
- Functional tests (correct rate limiting behavior)
- Load tests (requests/sec before degradation)
- Edge case tests (concurrent requests, clock skew)

## Step 3: Score
| Sandbox | Functional | Load (req/s) | Edge Cases | Winner? |
|---------|-----------|--------------|------------|---------|
| 1       | 10/10     | 5,000        | 7/10       | No      |
| 2       | 10/10     | 3,000        | 9/10       | No      |
| 3       | 10/10     | 12,000       | 8/10       | Yes     |

## Step 4: Fuse
Copy Sandbox 3's code to repo, cherry-pick Sandbox 2's error handling.
```

---

## Fusion Strategies

### Strategy 1: Winner Takes All

**When**: Solutions are fundamentally different architectures (can't merge)

```
Pick highest-scoring solution. Apply as-is.
```

**Best for**: Architecture decisions, framework choices, algorithm selection

---

### Strategy 2: Cherry-Pick Merge

**When**: Solutions share structure but differ in details

```
Start with winning solution.
Cherry-pick specific improvements from losers:
- Better error handling from Solution B
- Performance optimization from Solution C
- Edge case coverage from Solution A
```

**Best for**: Feature implementations, API designs, most coding tasks

---

### Strategy 3: Ensemble Voting

**When**: Multiple solutions claim different correct answers

```
If 2/3 agents agree on approach X, go with X.
If all 3 disagree, escalate to human review.
```

**Best for**: Debugging (which fix is correct?), code review, architecture decisions

---

### Strategy 4: Staged Fusion

**When**: Task has distinct phases

```
Phase 1 (Design): Use Architect's solution
Phase 2 (Implementation): Use Pragmatist's solution
Phase 3 (Optimization): Use Optimizer's solution
```

**Best for**: Large features, multi-file changes, end-to-end features

---

## Scoring Rubric

### Default Rubric (General Tasks)

| Criteria | Weight | Description |
|----------|--------|-------------|
| Correctness | 3x | Does it solve the task correctly? |
| Simplicity | 2x | Is the code easy to understand? |
| Robustness | 2x | Does it handle edge cases? |
| Performance | 1x | Is it efficient? |
| Maintainability | 1x | Is it easy to modify? |

### Security Rubric

| Criteria | Weight | Description |
|----------|--------|-------------|
| Security | 3x | Is it resistant to attacks? |
| Correctness | 3x | Does it work correctly? |
| Robustness | 2x | Does it handle edge cases? |
| Simplicity | 1x | Less code = less attack surface |
| Performance | 1x | Is it efficient? |

### Performance Rubric

| Criteria | Weight | Description |
|----------|--------|-------------|
| Performance | 3x | Throughput, latency, memory |
| Correctness | 3x | Does it work correctly? |
| Scalability | 2x | Does it scale with load? |
| Maintainability | 1x | Can it be tuned later? |
| Simplicity | 1x | Is it understandable? |

---

## When to Use F-Threads

### High-Value Scenarios

| Scenario | N | Why |
|----------|---|-----|
| Security-critical auth | 4-5 | One miss = vulnerability |
| Core algorithm | 3 | Performance matters |
| Architecture decision | 3 | Hard to change later |
| Production bug fix | 3 | Must be correct |
| Interview prep | 5 | Multiple valid approaches |

### Skip F-Threads When

| Scenario | Why |
|----------|-----|
| Simple bug fix | One agent sufficient |
| Trivial feature | Not worth 3x cost |
| Well-defined task | Little room for variation |
| Time-critical | Latency of N agents |

---

## Cost Economics

### Single Agent
```
Task: Implement rate limiter
Tokens: 15,000
Cost: $0.50
Quality: ~65% optimal
```

### F-Thread (N=3)
```
Task: Implement rate limiter
Tokens: 45,000 (3 agents) + 5,000 (fusion)
Cost: $1.50
Quality: ~95% optimal
```

### F-Thread (N=5)
```
Task: Implement rate limiter
Tokens: 75,000 (5 agents) + 8,000 (fusion)
Cost: $2.50
Quality: ~99% optimal
```

### ROI Analysis
```
3x cost → 30% quality improvement
5x cost → 34% quality improvement

For critical code: 3x cost is almost always worth it
For routine code: Single agent is fine
```

---

## Integration with Steps 1-15

### With Agent Teams (Step 11)

The Orchestrator can trigger F-Threads for critical sub-tasks:

```
/orchestrate "Implement OAuth2"

Orchestrator plan:
1. Research (single agent) - well-defined task
2. Security analysis (single agent) - well-defined task
3. Auth implementation (F-THREAD, N=3) - critical, benefits from diversity
4. Test generation (single agent) - well-defined task
5. Security scan (single agent) - well-defined task
```

---

### With Z-Threads (Step 12)

Z-Thread workflows can specify F-Thread stages:

```yaml
stages:
  - name: implementation
    type: f-thread        # Fusion Thread
    n: 3
    personas:
      - pragmatist
      - architect
      - optimizer
    fusion_strategy: cherry-pick
    rubric: default
```

---

### With L-Threads (Step 15)

For bulk operations, use F-Threads on the **critical items** only:

```python
for item in state['pending']:
    if item in critical_items:
        # F-Thread: 3 parallel attempts, fuse best
        result = f_thread(task=f"Migrate {item}", n=3)
    else:
        # Single agent: routine migration
        result = single_agent(task=f"Migrate {item}")
```

---

### With Mission Control (Step 13)

F-Thread execution visible in dashboard:

```
┌──────────────────────────────────────────────────┐
│ F-Thread: Rate Limiter Implementation            │
│                                                  │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────┐ │
│ │ Pragmatist   │ │ Architect    │ │ Optimizer │ │
│ │ ▓▓▓▓▓▓▓▓ ✅  │ │ ▓▓▓▓▓░░ 71% │ │ ▓▓▓▓▓▓ ✅│ │
│ │ Score: 78    │ │ Score: --    │ │ Score: 85│ │
│ └──────────────┘ └──────────────┘ └──────────┘ │
│                                                  │
│ Fusion: Pending (waiting for all agents)         │
└──────────────────────────────────────────────────┘
```

---

### With Generative UI (Step 14)

F-Thread results as HTML comparison dashboard:

```html
<div class="fthread-results">
  <h1>F-Thread: Rate Limiter</h1>

  <div class="solutions">
    <div class="solution winner">
      <h2>Optimizer (Winner)</h2>
      <div class="score">85/100</div>
      <pre><code>// Sliding window implementation...</code></pre>
    </div>

    <div class="solution">
      <h2>Pragmatist</h2>
      <div class="score">78/100</div>
      <pre><code>// Fixed window implementation...</code></pre>
    </div>

    <div class="solution">
      <h2>Architect</h2>
      <div class="score">82/100</div>
      <pre><code>// Token bucket implementation...</code></pre>
    </div>
  </div>

  <div class="cherry-picks">
    <h2>Cherry-Picked Enhancements</h2>
    <ul>
      <li>From Architect: Repository pattern for storage backend</li>
      <li>From Pragmatist: Simplified configuration API</li>
    </ul>
  </div>
</div>
```

---

## Advanced Patterns

### Pattern 1: Iterative F-Threads

Run F-Thread → Apply → Run F-Thread again on the result:

```
Round 1: 3 agents implement feature
         → Fuse best solution (Score: 85)

Round 2: 3 agents improve the Round 1 winner
         → Fuse improvements (Score: 92)

Round 3: 3 agents polish the Round 2 winner
         → Fuse final version (Score: 96)
```

Each round has diminishing returns. Usually 2 rounds is sufficient.

---

### Pattern 2: Competitive F-Threads

Agents can see each other's solutions and try to beat them:

```
Round 1: 3 agents solve independently → Agent C wins (Score: 85)

Round 2: 3 agents receive Agent C's solution + scores
         "Here is the current best solution (Score: 85). Beat it."
         → Agent A produces Score: 91

Round 3: 3 agents receive Agent A's solution (Score: 91)
         → Agent B produces Score: 94
```

---

### Pattern 3: Specialist F-Threads

Instead of general personas, use domain specialists:

```
Task: "Implement real-time notifications"

Agent 1: WebSocket expert
Agent 2: Server-Sent Events expert
Agent 3: Long-polling expert

Fusion: Compare approaches, pick best for the specific use case
```

---

### Pattern 4: F-Thread with Automated Testing

Fuse based on **test results** not subjective scoring:

```
1. All agents write code + tests
2. Run each agent's code against ALL agents' tests
3. Solution that passes the most tests wins
4. Cherry-pick tests that only losing solutions thought of
```

This removes subjective bias from fusion entirely.

---

## Summary

**F-Threads = Multiple agents + Same task + Fusion of best results**

### Core Pattern
1. **Spawn N agents** in parallel with different personas
2. **Collect all solutions** independently
3. **Score against rubric** (correctness, simplicity, robustness, etc.)
4. **Fuse the best** - winner + cherry-picked improvements from losers
5. **Apply to codebase** - final fused solution

### Benefits
- ✅ Near-optimal solutions (~95% with N=3)
- ✅ Exploits model non-determinism
- ✅ Diversity via personas
- ✅ Cherry-picking captures best of all worlds
- ✅ Parallelized (no extra wall-clock time)

### Cost
- 3x tokens for N=3 (worth it for critical code)
- 5x tokens for N=5 (for security-critical paths)
- Not worth it for trivial tasks

### When to Use
- Security-critical implementations
- Core algorithms and architecture decisions
- Production bug fixes
- Anything hard to change later

---

**F-Threads turn model non-determinism from a weakness into a superpower.**

---

**Guide Version**: 1.0.0
**Last Updated**: 2026-02-10
**Status**: COMPLETE
