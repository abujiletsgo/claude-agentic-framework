# Ralph Loops: Stateless Resampling with Completion Promises

> **2026 Update**: Ralph Loops now integrate with anti-loop guardrails and the knowledge pipeline. Learnings from failed iterations are stored automatically. See [../docs/2026_UPGRADE_GUIDE.md](../docs/2026_UPGRADE_GUIDE.md).

## The Problem: Context Rot in Long Tasks

Standard agent threads accumulate context over time. After 20+ turns:
- Context fills with old attempts, failed approaches, error messages
- Attention dilutes across 100k+ tokens of history
- Agent starts repeating the same mistakes
- Quality degrades until timeout

**Result**: Agent burns tokens spinning in circles within a single context window.

---

## The Solution: Stateless Resampling

**Ralph Loop**: Reset the context window on every iteration. The agent maintains state ONLY through the file system.

```
Iteration 1: Fresh context → Read progress.txt → Attempt fix → Update progress.txt → Stop
Iteration 2: Fresh context → Read progress.txt → See what failed → Try different approach → Update → Stop
Iteration 3: Fresh context → Read progress.txt → Continue → Tests pass → Output PROMISE → Exit
```

**Key Insight**: Each iteration gets a FRESH context window (no rot), but reads the progress file to know what was tried before.

---

## Architecture

### The Three Components

```
┌──────────────────────────────────────────────┐
│  1. Principal Skinner (External Harness)     │
│  ralph-harness.sh                            │
│  - Runs Claude in loop                       │
│  - Checks Completion Promise                 │
│  - Enforces circuit breakers                 │
│  - Manages progress file                     │
└──────────────┬───────────────────────────────┘
               │
               ▼ (each iteration)
┌──────────────────────────────────────────────┐
│  2. Ralph (The Agent)                        │
│  claude -p "<prompt with progress.txt>"      │
│  - Fresh context every iteration             │
│  - Reads progress file for state             │
│  - Attempts task                             │
│  - Updates progress file                     │
│  - Outputs <promise>COMPLETE</promise>       │
└──────────────┬───────────────────────────────┘
               │
               ▼ (on exit attempt)
┌──────────────────────────────────────────────┐
│  3. Stop Hook (Verification Gate)            │
│  npm test / pytest / custom verification     │
│  - PASS → Allow exit (promise valid)         │
│  - FAIL → Block exit (force retry)           │
└──────────────────────────────────────────────┘
```

### Data Flow

```
Iteration 1:
  progress.txt: (empty)
  Agent: Reads file → No history → Tries approach A → Fails → Writes "Approach A: failed (reason)"
  Harness: No PROMISE found → Continue loop

Iteration 2:
  progress.txt: "Approach A: failed (reason)"
  Agent: Reads file → Sees A failed → Tries approach B → Fails → Writes "Approach B: failed (reason)"
  Harness: No PROMISE found → Continue loop

Iteration 3:
  progress.txt: "Approach A: failed\nApproach B: failed"
  Agent: Reads file → Sees A,B failed → Tries approach C → Works! → Writes "Approach C: SUCCESS"
  Agent: Outputs <promise>COMPLETE</promise>
  Harness: PROMISE found → Runs tests → Tests pass → EXIT SUCCESS
```

---

## Implementation

### Level 1: The Ralph Harness Script

**File**: `~/.claude/scripts/ralph-harness.sh`

**Usage**:
```bash
# Basic
~/.claude/scripts/ralph-harness.sh "Fix all bugs in /src"

# With test verification
~/.claude/scripts/ralph-harness.sh "Fix all bugs in /src" --test-cmd "npm test"

# With options
~/.claude/scripts/ralph-harness.sh "Add OAuth2" \
  --max-loops 10 \
  --progress-file oauth_progress.txt \
  --test-cmd "pytest tests/ -v" \
  --max-turns 30
```

**What happens**:
1. Creates `progress.txt` if it doesn't exist
2. Runs `claude -p` with the goal + progress file content (headless mode)
3. Checks for `<promise>COMPLETE</promise>` in output
4. If promise found + tests pass → EXIT SUCCESS
5. If promise found + tests fail → Log failure, continue loop
6. If no promise → Check circuit breaker → Continue loop
7. Circuit breaker triggers after 3 stalls (no progress file changes)

---

### Level 2: Stop Hook Integration

For agents running inside Claude Code (not headless), use the Stop hook as the verification gate.

**How it works**:
- Agent tries to finish (stop event fires)
- Stop hook runs verification (tests, linter, etc.)
- If verification FAILS → Hook returns exit code 2 → Agent gets feedback → Retries
- If verification PASSES → Hook returns exit code 0 → Agent stops

This is already configured via your Self-Correcting Agents system (Step 14). The Stop hooks in `settings.json` run:
- `run_tests.py` (blocks if tests fail)
- `check_coverage.py` (blocks if coverage < 80%)
- `check_lthread_progress.py` (reports L-Thread progress)

**The Ralph integration**: Stop hooks act as the "Skinner" within a single session, while the harness script acts as the "Skinner" across sessions.

---

### Level 3: The Completion Promise

**Pattern**: Agent must output an exact string to signal completion.

```
<promise>COMPLETE</promise>
```

**Rules**:
1. Agent MUST NOT output the promise until ALL verification passes
2. Harness checks for the exact string (grep)
3. Even after promise, harness can run external verification
4. If external verification fails, promise is rejected and loop continues

**Why this works**: The promise is deterministic. No ambiguity about whether the agent "thinks" it's done vs actually done. The promise is verified externally.

---

### Level 4: Circuit Breakers

**Problem**: Agent might spin without making progress (updating progress file but not actually fixing anything).

**Solution**: Three circuit breaker mechanisms:

#### 1. Stall Detection
```bash
# If progress file hash unchanged for 3 iterations → break
CURRENT_HASH=$(md5sum progress.txt)
if [ "$CURRENT_HASH" = "$PREV_HASH" ]; then
    STALL_COUNT=$((STALL_COUNT + 1))
fi
```

#### 2. Max Iterations
```bash
MAX_LOOPS=20  # Hard limit
```

#### 3. Cost Budget (Advanced)
```bash
# Track API cost per iteration
# Break if total exceeds budget
if [ "$TOTAL_COST" -gt "$MAX_COST" ]; then
    echo "Cost budget exceeded"
    exit 1
fi
```

---

## The Progress File

### Structure

```
# Ralph Loop Progress File
# Goal: Fix all bugs in /src
# Started: 2026-02-10T10:00:00Z
---

### Iteration 1: 2026-02-10T10:01:00Z
Approach: Fixed TypeError in auth.py:45 by adding null check
Result: PARTIAL - auth tests pass, but checkout tests still fail
Remaining: checkout.py:89 has undefined variable 'total'

### Iteration 2: 2026-02-10T10:05:00Z
Approach: Fixed undefined 'total' in checkout.py:89, added import
Result: PARTIAL - checkout tests pass, but payment gateway timeout in test_payment.py
Remaining: payment.py:120 needs retry logic for gateway timeouts

### Iteration 3: 2026-02-10T10:10:00Z
Approach: Added retry logic with exponential backoff to payment.py:120
Result: SUCCESS - all 45 tests pass
Verification: npm test → 45/45 passed

## COMPLETED (Iteration 3)
Timestamp: 2026-02-10T10:12:00Z
Verification: PASSED (npm test)
```

### Why This Works

1. **State persistence**: Agent reads file to know what was tried
2. **No repetition**: Failed approaches documented, agent skips them
3. **Crash-safe**: File survives crashes, can resume
4. **Auditable**: Full history of what was attempted

---

## Integration with Living System

### With Drop Zones (Step 9)

Create a Ralph-specific drop zone:

```yaml
# drops.yaml
- name: "Ralph Tasks"
  path: "~/drops/ralph-tasks"
  handler: "~/.claude/scripts/ralph-harness.sh '{file_content}' --test-cmd 'npm test'"
  events: ["created"]
```

**Usage**: Drop a spec file into `~/drops/ralph-tasks/` → Ralph Loop executes automatically.

---

### With L-Threads (Step 15)

Ralph Loops and L-Threads are complementary:

| | L-Threads | Ralph Loops |
|---|---|---|
| **State** | `_status.json` (structured) | `progress.txt` (free-form) |
| **Context** | Single long session | Fresh context each iteration |
| **Failure** | Skip failed items | Try different approach |
| **Use case** | Bulk operations (100s of items) | Single complex goal |
| **Loop type** | Items loop (for each item) | Retry loop (until done) |

**Combined**: Use L-Thread for the outer loop (items), Ralph Loop for each item:
```
L-Thread: for each table in migration
  Ralph Loop: fix this specific table until tests pass
```

---

### With Self-Correcting Agents (Step 14)

Ralph Loops ARE self-correcting agents at the session level:

```
Self-Correcting (within session):
  Agent tries → Stop hook blocks → Agent retries → Stop hook passes
  Problem: Context accumulates, rots after 20+ turns

Ralph Loop (across sessions):
  Agent tries → Fails → Session ends → NEW session → Reads progress → Tries differently
  Benefit: Zero context rot (fresh window each time)
```

---

### With F-Threads (Step 16)

Run multiple Ralph Loops in parallel with different strategies:

```bash
# F-Thread + Ralph: 3 parallel Ralph Loops
ralph-harness.sh "Fix auth bugs" --progress-file ralph_a.txt &
ralph-harness.sh "Fix auth bugs" --progress-file ralph_b.txt &
ralph-harness.sh "Fix auth bugs" --progress-file ralph_c.txt &
wait

# First one to produce PROMISE wins
```

---

### With Mission Control (Step 13)

Ralph Loop progress visible in dashboard:

```
┌──────────────────────────────────────────────────┐
│ Ralph Loop: Fix auth bugs                        │
│                                                  │
│ Iteration: 3 / 20                                │
│ Status: Running                                  │
│                                                  │
│ History:                                         │
│  1. Fixed TypeError in auth.py       ❌ PARTIAL  │
│  2. Fixed undefined var in checkout  ❌ PARTIAL  │
│  3. Adding retry logic to payment    🔄 RUNNING │
│                                                  │
│ Circuit Breaker: 0/3 stalls                      │
│ Estimated: 1-2 more iterations                   │
└──────────────────────────────────────────────────┘
```

---

## When to Use Ralph Loops

### Use Ralph Loops For

| Scenario | Why |
|----------|-----|
| Bug fixing (complex) | Multiple approaches may be needed |
| Feature implementation with tests | Clear verification (tests pass) |
| Refactoring with CI | CI pipeline as verification gate |
| UI tasks with screenshots | Visual verification possible |
| Any task with deterministic verification | PROMISE can be verified externally |

### Don't Use Ralph Loops For

| Scenario | Better Alternative |
|----------|-------------------|
| Bulk operations (100s of items) | L-Threads |
| Research / exploration | RLM Architecture |
| Simple one-shot tasks | Single agent call |
| Tasks without verification | No way to validate PROMISE |

---

## Advanced: Screenshot Protocol

For UI tasks, force visual verification:

```markdown
## Verification Protocol
1. After making changes, take a screenshot: `screenshot.png`
2. On the NEXT iteration, the agent sees the screenshot
3. Agent cannot output PROMISE until screenshot matches expectations

Progress file entry:
"Iteration 3: Changed button color. Screenshot taken. Visual check needed."
"Iteration 4: Screenshot confirmed - button is now blue. PROMISE valid."
```

---

## Summary

**Ralph Loop = Fresh context each iteration + Progress file + Completion Promise + Circuit breakers**

### Core Pattern
1. **Harness** (`ralph-harness.sh`) runs Claude in a loop
2. **Agent** gets fresh context + progress file each iteration
3. **Agent** attempts task, updates progress file
4. **Agent** outputs `<promise>COMPLETE</promise>` when done
5. **Harness** verifies promise (external tests)
6. **Circuit breaker** stops spinning agents

### Benefits
- ✅ Zero context rot (fresh window each iteration)
- ✅ Deterministic verification (external test suite)
- ✅ Crash-safe (progress file persists)
- ✅ Anti-spinning (circuit breakers)
- ✅ Auditable (full history in progress file)

### Key Difference from L-Threads
- L-Threads: "Process each item, skip failures"
- Ralph Loops: "Keep trying until this ONE goal is achieved"

---

**Ralph Loops turn complex, multi-attempt tasks into deterministic, verifiable workflows.**

**The agent can fail 19 times. It only needs to succeed once.**

---

**Guide Version**: 1.0.0
**Last Updated**: 2026-02-10
**Status**: COMPLETE
