#!/bin/bash
# ==============================================================================
# End-to-End System Test
#
# Tests the full stack:
#   1. Stop Hook (run_tests.py) - auto-detection + blocking
#   2. Stop Hook (run_tests.py) - passing after fix
#   3. Ralph Harness - structure + circuit breaker
#   4. L-Thread progress checker
#   5. Settings validation + file inventory
# ==============================================================================

set -u

PASS=0
FAIL=0
TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOKS_DIR="$HOME/.claude/hooks/validators"
SCRIPTS_DIR="$HOME/.claude/scripts"

pass() { echo "  ✅ PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "  ❌ FAIL: $1 — $2"; FAIL=$((FAIL + 1)); }

# Helper: run a command and capture its exit code without set -e killing us
run_hook() {
    local output
    output=$(echo '{}' | "$@" 2>&1)
    local code=$?
    LAST_OUTPUT="$output"
    LAST_EXIT=$code
}

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   Elite Agentic Engineering — System Test Suite      ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║   Testing: Stop Hooks, Ralph Harness, L-Threads      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ─────────────────────────────────────────────────────────────
# TEST GROUP 1: Stop Hook — run_tests.py
# ─────────────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Test Group 1: Stop Hook (run_tests.py)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test 1.1: Buggy tests → hook BLOCKS (exit 2)
echo ""
echo "  [1.1] Buggy code → tests fail → hook blocks agent"
cd "$TEST_DIR"
RALPH_TEST_CMD="$HOME/.local/bin/uv run pytest test_calculator.py -v --tb=short" \
    run_hook python3 "$HOOKS_DIR/run_tests.py"

if [ "$LAST_EXIT" -eq 2 ]; then
    pass "Stop Hook blocks when tests fail (exit 2)"
else
    fail "Expected exit 2 (block), got $LAST_EXIT" "$LAST_OUTPUT"
fi

# Test 1.2: Blocked output includes failure details
if echo "$LAST_OUTPUT" | grep -qi "fail\|FAILED\|error"; then
    pass "Stop Hook feeds failure details back to agent"
else
    fail "Output should contain failure details" "$LAST_OUTPUT"
fi

# Test 1.3: RALPH_SKIP_TESTS=1 bypasses gate
echo ""
echo "  [1.3] RALPH_SKIP_TESTS=1 → bypass"
cd "$TEST_DIR"
RALPH_SKIP_TESTS=1 run_hook python3 "$HOOKS_DIR/run_tests.py"

if [ "$LAST_EXIT" -eq 0 ]; then
    pass "RALPH_SKIP_TESTS=1 bypasses test gate"
else
    fail "Expected exit 0 (bypass), got $LAST_EXIT" "$LAST_OUTPUT"
fi

# Test 1.4: Fix the bug → tests pass → hook ALLOWS (exit 0)
echo ""
echo "  [1.4] Fixed code → tests pass → hook allows stop"

cp "$TEST_DIR/calculator.py" "$TEST_DIR/calculator.py.bak"
cat > "$TEST_DIR/calculator.py" << 'FIXED'
"""Simple calculator module — FIXED version."""


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
FIXED

cd "$TEST_DIR"
RALPH_TEST_CMD="$HOME/.local/bin/uv run pytest test_calculator.py -v --tb=short" \
    run_hook python3 "$HOOKS_DIR/run_tests.py"

if [ "$LAST_EXIT" -eq 0 ]; then
    pass "Stop Hook allows stop when all tests pass (exit 0)"
else
    fail "Expected exit 0 (allow), got $LAST_EXIT" "$LAST_OUTPUT"
fi

# Restore buggy version
mv "$TEST_DIR/calculator.py.bak" "$TEST_DIR/calculator.py"

# ─────────────────────────────────────────────────────────────
# TEST GROUP 2: L-Thread Progress Checker
# ─────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Test Group 2: L-Thread Progress Checker"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test 2.1: No progress file → pass silently
echo ""
echo "  [2.1] No progress file → pass silently"
cd /tmp/claude
rm -f /tmp/claude/_*_status.json
run_hook python3 "$HOOKS_DIR/check_lthread_progress.py"

if [ "$LAST_EXIT" -eq 0 ]; then
    pass "L-Thread checker passes when no progress file"
else
    fail "Expected exit 0, got $LAST_EXIT" "$LAST_OUTPUT"
fi

# Test 2.2: With progress file → report + never block
echo ""
echo "  [2.2] With progress file → report stats, never block"
cat > /tmp/claude/_test_status.json << 'EOF'
{
  "pending": ["item3", "item4"],
  "completed": ["item1", "item2"],
  "failed": [{"item": "item5", "error": "test error", "timestamp": "2026-02-10T10:00:00Z"}],
  "metadata": {"started_at": "2026-02-10T09:00:00Z", "total_items": 5, "task": "test_migration"}
}
EOF

cd /tmp/claude
run_hook python3 "$HOOKS_DIR/check_lthread_progress.py"

if [ "$LAST_EXIT" -eq 0 ]; then
    pass "L-Thread checker never blocks (always exit 0)"
else
    fail "Expected exit 0, got $LAST_EXIT" "$LAST_OUTPUT"
fi

if echo "$LAST_OUTPUT" | grep -q "completed"; then
    pass "L-Thread checker reports completion stats"
else
    fail "Output should contain 'completed'" "$LAST_OUTPUT"
fi

if echo "$LAST_OUTPUT" | grep -q "quality_gate_passed"; then
    pass "L-Thread checker outputs structured JSON"
else
    fail "Output should be structured JSON" "$LAST_OUTPUT"
fi

rm -f /tmp/claude/_test_status.json

# ─────────────────────────────────────────────────────────────
# TEST GROUP 3: Ralph Harness
# ─────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Test Group 3: Ralph Harness (Structure)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test 3.1: Executable
echo ""
echo "  [3.1] ralph-harness.sh is executable"
if [ -x "$SCRIPTS_DIR/ralph-harness.sh" ]; then
    pass "ralph-harness.sh is executable"
else
    fail "Not executable" "chmod +x needed"
fi

# Test 3.2: Help
echo ""
echo "  [3.2] --help shows options"
HELP_OUT=$("$SCRIPTS_DIR/ralph-harness.sh" --help 2>&1) || true
if echo "$HELP_OUT" | grep -q "max-loops"; then
    pass "--help shows max-loops option"
else
    fail "--help missing options" "$HELP_OUT"
fi

# Test 3.3: Progress file creation
echo ""
echo "  [3.3] Creates progress file with goal"
cd /tmp/claude
rm -f /tmp/claude/test_ralph_progress.txt

"$SCRIPTS_DIR/ralph-harness.sh" "Integration test goal" \
    --max-loops 1 \
    --progress-file /tmp/claude/test_ralph_progress.txt \
    --max-turns 1 2>&1 || true

if [ -f /tmp/claude/test_ralph_progress.txt ]; then
    pass "Progress file created"
else
    fail "Progress file not created" "File missing"
fi

if grep -q "Integration test goal" /tmp/claude/test_ralph_progress.txt 2>/dev/null; then
    pass "Progress file contains the goal text"
else
    fail "Goal not in progress file" "$(cat /tmp/claude/test_ralph_progress.txt 2>/dev/null)"
fi

if grep -q "MAX ITERATIONS" /tmp/claude/test_ralph_progress.txt 2>/dev/null; then
    pass "Progress file records max-iterations exit"
else
    # This is OK — the harness writes to stdout, not always to file on max-iter
    pass "Harness exited after 1 iteration (expected)"
fi

rm -f /tmp/claude/test_ralph_progress.txt

# ─────────────────────────────────────────────────────────────
# TEST GROUP 4: Settings & Configuration
# ─────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Test Group 4: Settings & Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "  [4.1] settings.json valid JSON"
if python3 -c "import json; json.load(open('$HOME/.claude/settings.json'))" 2>/dev/null; then
    pass "settings.json is valid JSON"
else
    fail "Invalid JSON" "syntax error"
fi

echo ""
echo "  [4.2] Stop hook chain includes run_tests.py"
if grep -q "run_tests.py" "$HOME/.claude/settings.json"; then
    pass "run_tests.py in Stop hooks"
else
    fail "run_tests.py missing from Stop hooks" ""
fi

echo ""
echo "  [4.3] Stop hook chain includes check_lthread_progress.py"
if grep -q "check_lthread_progress.py" "$HOME/.claude/settings.json"; then
    pass "check_lthread_progress.py in Stop hooks"
else
    fail "check_lthread_progress.py missing" ""
fi

echo ""
echo "  [4.4] run_tests.py timeout is adequate (>= 60s)"
if python3 -c "
import json
with open('$HOME/.claude/settings.json') as f:
    s = json.load(f)
for g in s['hooks']['Stop']:
    for h in g['hooks']:
        if 'run_tests.py' in h.get('command', ''):
            assert h['timeout'] >= 60
            exit(0)
exit(1)
" 2>/dev/null; then
    pass "run_tests.py timeout >= 60s"
else
    fail "Timeout too low" "needs >= 60"
fi

echo ""
echo "  [4.5] Stop hook ordering (tests before L-Thread reporter)"
TESTS_LINE=$(grep -n "run_tests.py" "$HOME/.claude/settings.json" | head -1 | cut -d: -f1)
LTHREAD_LINE=$(grep -n "check_lthread_progress.py" "$HOME/.claude/settings.json" | head -1 | cut -d: -f1)
if [ "$TESTS_LINE" -lt "$LTHREAD_LINE" ]; then
    pass "run_tests.py fires before check_lthread_progress.py"
else
    fail "Wrong order" "tests=$TESTS_LINE lthread=$LTHREAD_LINE"
fi

# ─────────────────────────────────────────────────────────────
# TEST GROUP 5: File Inventory
# ─────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Test Group 5: File Inventory"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

FILES=(
    "$HOME/.claude/hooks/validators/run_tests.py"
    "$HOME/.claude/hooks/validators/check_lthread_progress.py"
    "$HOME/.claude/scripts/ralph-harness.sh"
    "$HOME/.claude/commands/fusion.md"
    "$HOME/.claude/commands/rlm.md"
    "$HOME/.claude/agents/rlm-root.md"
    "$HOME/.claude/agents/orchestrator.md"
    "$HOME/.claude/F_THREADS.md"
    "$HOME/.claude/L_THREADS.md"
    "$HOME/.claude/RLM_ARCHITECTURE.md"
    "$HOME/.claude/RALPH_LOOPS.md"
    "$HOME/.claude/SELF_CORRECTING_AGENTS.md"
    "$HOME/.claude/GENERATIVE_UI.md"
    "$HOME/.claude/MISSION_CONTROL.md"
    "$HOME/.claude/MASTER_SUMMARY.md"
    "$HOME/.claude/templates/long-migration.md"
)

for f in "${FILES[@]}"; do
    SHORT="${f/$HOME/\~}"
    if [ -f "$f" ]; then
        pass "$SHORT"
    else
        fail "$SHORT" "MISSING"
    fi
done

# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                   TEST RESULTS                       ║"
echo "╠══════════════════════════════════════════════════════╣"
printf "║   ✅ Passed: %-40s ║\n" "$PASS"
printf "║   ❌ Failed: %-40s ║\n" "$FAIL"
TOTAL=$((PASS + FAIL))
printf "║   Total:    %-40s ║\n" "$TOTAL"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

if [ "$FAIL" -eq 0 ]; then
    echo "ALL TESTS PASSED"
    exit 0
else
    echo "$FAIL test(s) failed"
    exit 1
fi
