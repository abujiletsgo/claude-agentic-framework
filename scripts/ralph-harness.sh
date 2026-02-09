#!/bin/bash
# ==============================================================================
# Ralph Loop Harness ("Principal Skinner" Supervisor)
#
# Runs Claude in a deterministic loop with:
# - Stateless resampling (fresh context each iteration)
# - Completion Promise verification
# - Circuit breakers (detect spinning)
# - Progress file persistence (only memory between loops)
#
# Usage:
#   ralph-harness.sh <goal> [--max-loops N] [--progress-file FILE] [--test-cmd CMD]
#
# Examples:
#   ralph-harness.sh "Fix all bugs in /src"
#   ralph-harness.sh "Add OAuth2 to the API" --max-loops 10 --test-cmd "npm test"
#   ralph-harness.sh "Refactor auth module" --progress-file auth_progress.txt
# ==============================================================================

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
MAX_LOOPS=20
PROMISE="<promise>COMPLETE</promise>"
PROGRESS_FILE="progress.txt"
TEST_CMD=""
GOAL=""
MAX_TURNS=30
WORKING_DIR="$(pwd)"

# ── Parse Arguments ───────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --max-loops)    MAX_LOOPS="$2"; shift 2 ;;
        --progress-file) PROGRESS_FILE="$2"; shift 2 ;;
        --test-cmd)     TEST_CMD="$2"; shift 2 ;;
        --max-turns)    MAX_TURNS="$2"; shift 2 ;;
        --working-dir)  WORKING_DIR="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: ralph-harness.sh <goal> [options]"
            echo ""
            echo "Options:"
            echo "  --max-loops N       Maximum iterations (default: 20)"
            echo "  --progress-file F   State file path (default: progress.txt)"
            echo "  --test-cmd CMD      Verification command (e.g., 'npm test')"
            echo "  --max-turns N       Max agent turns per iteration (default: 30)"
            echo "  --working-dir DIR   Working directory (default: current)"
            exit 0
            ;;
        *)
            if [ -z "$GOAL" ]; then
                GOAL="$1"
            fi
            shift
            ;;
    esac
done

if [ -z "$GOAL" ]; then
    echo "Error: No goal specified."
    echo "Usage: ralph-harness.sh \"<goal>\" [options]"
    exit 1
fi

# ── Initialize ────────────────────────────────────────────────────────────────
cd "$WORKING_DIR"

# Create progress file if it doesn't exist
if [ ! -f "$PROGRESS_FILE" ]; then
    echo "# Ralph Loop Progress File" > "$PROGRESS_FILE"
    echo "# Goal: $GOAL" >> "$PROGRESS_FILE"
    echo "# Started: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$PROGRESS_FILE"
    echo "---" >> "$PROGRESS_FILE"
fi

PREV_HASH=""
STALL_COUNT=0
MAX_STALLS=3

echo "============================================"
echo "  Ralph Loop: Starting"
echo "  Goal: $GOAL"
echo "  Max Loops: $MAX_LOOPS"
echo "  Progress: $PROGRESS_FILE"
echo "  Test Cmd: ${TEST_CMD:-none}"
echo "============================================"
echo ""

# ── Main Loop ─────────────────────────────────────────────────────────────────
for ((i=1; i<=MAX_LOOPS; i++)); do
    echo "──────────────────────────────────────────"
    echo "  Iteration $i / $MAX_LOOPS"
    echo "  $(date -u +%H:%M:%S)"
    echo "──────────────────────────────────────────"

    # ── Build the Prompt ──────────────────────────────────────────────────────
    # The prompt includes the progress file content so the agent has state
    PROGRESS_CONTENT=$(cat "$PROGRESS_FILE")

    PROMPT="Goal: $GOAL

## Progress File (Your ONLY memory from previous iterations)
\`\`\`
$PROGRESS_CONTENT
\`\`\`

## Instructions
1. Read the progress above carefully. It shows what was tried before.
2. Do NOT repeat approaches that already failed (listed above).
3. Attempt a fix or continue from where the last iteration left off.
4. Run verification: ${TEST_CMD:-"check your work manually"}
5. Append your results to $PROGRESS_FILE (what you tried, what happened).
6. If the goal is FULLY achieved and ALL verification passes, output exactly:
   $PROMISE

## Rules
- You MUST update $PROGRESS_FILE before finishing (success or failure).
- You MUST NOT output $PROMISE unless verification passes.
- If you encounter a new error, log it in $PROGRESS_FILE and stop.
- If you cannot make progress, log WHY in $PROGRESS_FILE and stop."

    # ── Run Claude (Headless / Print Mode) ────────────────────────────────────
    # Fresh context each iteration (stateless resampling)
    OUTPUT=$(claude -p "$PROMPT" --max-turns "$MAX_TURNS" 2>&1) || true

    # ── Check Completion Promise ──────────────────────────────────────────────
    if echo "$OUTPUT" | grep -q "$PROMISE"; then
        echo ""
        echo "============================================"
        echo "  PROMISE MET on iteration $i"
        echo "============================================"

        # ── Run external verification if configured ───────────────────────────
        if [ -n "$TEST_CMD" ]; then
            echo "  Running verification: $TEST_CMD"
            if eval "$TEST_CMD" 2>&1; then
                echo "  Verification PASSED"
                echo "" >> "$PROGRESS_FILE"
                echo "## COMPLETED (Iteration $i)" >> "$PROGRESS_FILE"
                echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$PROGRESS_FILE"
                echo "Verification: PASSED ($TEST_CMD)" >> "$PROGRESS_FILE"
                echo ""
                echo "  Ralph Loop: SUCCESS"
                exit 0
            else
                echo "  Verification FAILED - continuing loop"
                echo "" >> "$PROGRESS_FILE"
                echo "### Iteration $i: Promise claimed but verification FAILED" >> "$PROGRESS_FILE"
                echo "Test command: $TEST_CMD" >> "$PROGRESS_FILE"
                echo "Result: FAILED" >> "$PROGRESS_FILE"
            fi
        else
            # No test command - trust the agent's promise
            echo "" >> "$PROGRESS_FILE"
            echo "## COMPLETED (Iteration $i)" >> "$PROGRESS_FILE"
            echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$PROGRESS_FILE"
            echo ""
            echo "  Ralph Loop: SUCCESS (unverified)"
            exit 0
        fi
    fi

    # ── Circuit Breaker: Detect Spinning ──────────────────────────────────────
    CURRENT_HASH=$(md5sum "$PROGRESS_FILE" 2>/dev/null | cut -d' ' -f1 || md5 -q "$PROGRESS_FILE" 2>/dev/null || echo "unknown")

    if [ "$CURRENT_HASH" = "$PREV_HASH" ]; then
        STALL_COUNT=$((STALL_COUNT + 1))
        echo "  WARNING: Progress file unchanged ($STALL_COUNT/$MAX_STALLS stalls)"

        if [ "$STALL_COUNT" -ge "$MAX_STALLS" ]; then
            echo ""
            echo "============================================"
            echo "  CIRCUIT BROKEN: Agent is spinning"
            echo "  No progress for $MAX_STALLS iterations"
            echo "============================================"
            echo "" >> "$PROGRESS_FILE"
            echo "## CIRCUIT BROKEN (Iteration $i)" >> "$PROGRESS_FILE"
            echo "Reason: No progress detected for $MAX_STALLS consecutive iterations" >> "$PROGRESS_FILE"
            echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$PROGRESS_FILE"
            exit 1
        fi
    else
        STALL_COUNT=0
    fi

    PREV_HASH="$CURRENT_HASH"

    # ── Brief pause between iterations ────────────────────────────────────────
    sleep 2
done

# ── Max Iterations Reached ────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  MAX ITERATIONS ($MAX_LOOPS) REACHED"
echo "  Goal not fully achieved"
echo "============================================"
echo "" >> "$PROGRESS_FILE"
echo "## MAX ITERATIONS REACHED (Loop $MAX_LOOPS)" >> "$PROGRESS_FILE"
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$PROGRESS_FILE"
exit 1
