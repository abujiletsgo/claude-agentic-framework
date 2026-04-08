#!/usr/bin/env bash
# CAF Hooks Benchmark Harness: Python vs Rust
# Usage: ./run_benchmarks.sh [N]           (N = iterations, default 20)
#        ./run_benchmarks.sh --quick       (3 iterations, fast test)
set -euo pipefail

# ---------------------------------------------------------------------------
# Iteration count
# ---------------------------------------------------------------------------
ITERATIONS=20
if [[ "${1:-}" == "--quick" ]]; then
    ITERATIONS=3
elif [[ -n "${1:-}" ]]; then
    ITERATIONS="$1"
fi

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CAF_HOOKS_DIR="${REPO_ROOT}/caf-hooks"
RUST_BIN="${CAF_HOOKS_DIR}/target/release/caf-hooks"
GLOBAL_HOOKS="${REPO_ROOT}/global-hooks"
OUTPUT_FILE="/tmp/caf_rust_benchmark_results.md"

# ---------------------------------------------------------------------------
# Guard: Rust binary must exist
# ---------------------------------------------------------------------------
if [[ ! -f "${RUST_BIN}" ]]; then
    echo "ERROR: Rust binary not found at ${RUST_BIN}" >&2
    echo "Run 'cargo build --release' inside ${CAF_HOOKS_DIR} first." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Millisecond timer — macOS has no date +%N, use python3
# ---------------------------------------------------------------------------
ms_now() {
    python3 -c "import time; print(int(time.time()*1000))"
}

# ---------------------------------------------------------------------------
# RSS measurement via /usr/bin/time -l (macOS)
# Returns resident set size in KB, or 0 if unavailable.
# ---------------------------------------------------------------------------
rss_of_cmd() {
    local tmp
    tmp=$(mktemp)
    # /usr/bin/time -l writes stats to stderr
    { /usr/bin/time -l "$@" > /dev/null; } 2>"${tmp}" || true
    local bytes
    bytes=$(grep -i "maximum resident set size" "${tmp}" | awk '{print $1}' || echo "0")
    rm -f "${tmp}"
    if [[ -z "${bytes}" || "${bytes}" == "0" ]]; then
        echo "0"
    else
        echo $(( bytes / 1024 ))
    fi
}

# ---------------------------------------------------------------------------
# Statistics: space-separated ms values -> "mean median p95 min max"
# ---------------------------------------------------------------------------
calc_stats() {
    python3 - "$@" <<'PYEOF'
import sys, statistics
vals = [float(x) for x in sys.argv[1:] if x]
if not vals:
    print("0 0 0 0 0")
    sys.exit(0)
vs = sorted(vals)
mean   = statistics.mean(vs)
median = statistics.median(vs)
n      = len(vs)
p95    = vs[min(int(n * 0.95), n - 1)]
print(f"{mean:.2f} {median:.2f} {p95:.2f} {vs[0]:.2f} {vs[-1]:.2f}")
PYEOF
}

# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------
PAYLOAD_SIMPLE='{"session_id":"bench-test","hook_event_name":"Stop","cwd":"/tmp"}'

PAYLOAD_MEDIUM='{"session_id":"bench-test","hook_event_name":"PostToolUse","tool_name":"Bash","tool_input":{"command":"ls -la /tmp"},"tool_response":{"output":"total 123\ndrwxrwxrwt  15 root  wheel  480 Apr  8 12:00 .\ndrwxr-xr-x  20 root  wheel  640 Mar 15 10:00 ..\n-rw-r--r--   1 user  staff  1234 Apr  8 11:59 test.txt","isError":false},"cwd":"/tmp"}'

# Generate ~10 KB output string for COMPLEX payload
BIG_OUTPUT=$(python3 - <<'PYEOF'
import json
block = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
         "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
         "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris "
         "nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in "
         "reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla "
         "pariatur. Excepteur sint occaecat cupidatat non proident, sunt in "
         "culpa qui officia deserunt mollit anim id est laborum. ")
s = (block * 50)[:10240]
# Emit as a JSON string value (without outer quotes) so it is safe to embed
print(json.dumps(s)[1:-1])
PYEOF
)

PAYLOAD_COMPLEX='{"session_id":"bench-test","hook_event_name":"PostToolUse","tool_name":"Bash","tool_input":{"command":"ls -la /tmp"},"tool_response":{"output":"'"${BIG_OUTPUT}"'","isError":false},"cwd":"/tmp"}'

# ---------------------------------------------------------------------------
# Hook map: name -> relative python path (relative to GLOBAL_HOOKS)
# ---------------------------------------------------------------------------
declare -A HOOK_PYTHON_PATH
HOOK_PYTHON_PATH["post-compact-verify"]="framework/context/post_compact_verify.py"
HOOK_PYTHON_PATH["file-watcher"]="framework/automation/file_watcher.py"
HOOK_PYTHON_PATH["voice-done"]="framework/notifications/voice_done.py"
HOOK_PYTHON_PATH["stop-failure-recovery"]="framework/automation/stop_failure_recovery.py"
HOOK_PYTHON_PATH["task-quality-gate"]="framework/automation/task_quality_gate.py"
HOOK_PYTHON_PATH["enforce-orchestrate"]="framework/guardrails/enforce_orchestrate.py"
HOOK_PYTHON_PATH["epistemic-guard"]="framework/guardrails/epistemic_guard.py"
HOOK_PYTHON_PATH["auto-refine"]="framework/automation/auto_refine.py"
HOOK_PYTHON_PATH["auto-error-analyzer"]="framework/automation/auto_error_analyzer.py"
HOOK_PYTHON_PATH["context-bundle-logger"]="framework/context-bundle-logger.py"
HOOK_PYTHON_PATH["damage-control"]="damage-control/unified-damage-control.py"
HOOK_PYTHON_PATH["auto-memory-writer"]="framework/memory/auto_memory_writer.py"

# Hooks that are normally CB-wrapped
declare -A CB_WRAPPED
CB_WRAPPED["enforce-orchestrate"]=1
CB_WRAPPED["epistemic-guard"]=1
CB_WRAPPED["auto-refine"]=1
CB_WRAPPED["auto-error-analyzer"]=1
CB_WRAPPED["auto-memory-writer"]=1

CB_WRAPPER="${GLOBAL_HOOKS}/framework/guardrails/circuit_breaker_wrapper.py"

# ---------------------------------------------------------------------------
# Main benchmark loop
# ---------------------------------------------------------------------------
echo "=== CAF Hooks Benchmark ==="
echo "Iterations: ${ITERATIONS}"
echo "Output: ${OUTPUT_FILE}"
echo ""

declare -a TABLE_ROWS=()
declare -A EVENT_PYTHON_TOTAL
declare -A EVENT_RUST_TOTAL
EVENT_PYTHON_TOTAL["Stop"]=0
EVENT_PYTHON_TOTAL["PostToolUse"]=0
EVENT_RUST_TOTAL["Stop"]=0
EVENT_RUST_TOTAL["PostToolUse"]=0

ALL_PYTHON_MEANS=()
ALL_RUST_MEANS=()

for hook_name in "${!HOOK_PYTHON_PATH[@]}"; do
    py_rel="${HOOK_PYTHON_PATH[${hook_name}]}"
    py_abs="${GLOBAL_HOOKS}/${py_rel}"

    if [[ ! -f "${py_abs}" ]]; then
        echo "  SKIP ${hook_name}: Python source not found at ${py_abs}"
        continue
    fi

    for complexity in SIMPLE MEDIUM COMPLEX; do
        case "${complexity}" in
            SIMPLE)  payload="${PAYLOAD_SIMPLE}"  ;;
            MEDIUM)  payload="${PAYLOAD_MEDIUM}"  ;;
            COMPLEX) payload="${PAYLOAD_COMPLEX}" ;;
        esac

        echo -n "  [${hook_name}/${complexity}] Rust..."

        # --- Rust timings ---
        rust_timings=()
        for (( i=0; i<ITERATIONS; i++ )); do
            t0=$(ms_now)
            printf '%s' "${payload}" | "${RUST_BIN}" "${hook_name}" > /dev/null 2>&1 || true
            t1=$(ms_now)
            rust_timings+=("$(( t1 - t0 ))")
        done
        read -r rust_mean rust_median rust_p95 rust_min rust_max \
            <<< "$(calc_stats "${rust_timings[@]}")"

        # Rust RSS (single measurement, raw args — no shell eval)
        rust_rss=$(rss_of_cmd bash -c "printf '%s' \"\${1}\" | \"\${2}\" \"\${3}\"" \
            _ "${payload}" "${RUST_BIN}" "${hook_name}") || rust_rss=0

        echo -n " Python..."

        # --- Python (bare) timings ---
        py_timings=()
        for (( i=0; i<ITERATIONS; i++ )); do
            t0=$(ms_now)
            printf '%s' "${payload}" | uv run --no-project "${py_abs}" > /dev/null 2>&1 || true
            t1=$(ms_now)
            py_timings+=("$(( t1 - t0 ))")
        done
        read -r py_mean py_median py_p95 py_min py_max \
            <<< "$(calc_stats "${py_timings[@]}")"

        # Python RSS (single measurement)
        py_rss=$(rss_of_cmd bash -c "printf '%s' \"\${1}\" | uv run --no-project \"\${2}\"" \
            _ "${payload}" "${py_abs}") || py_rss=0

        echo -n " done"

        # --- CB-wrapped Python timings (if applicable) ---
        cb_mean="N/A"
        if [[ -n "${CB_WRAPPED[${hook_name}]+x}" && -f "${CB_WRAPPER}" ]]; then
            echo -n " CB..."
            cb_timings=()
            for (( i=0; i<ITERATIONS; i++ )); do
                t0=$(ms_now)
                printf '%s' "${payload}" | uv run --no-project "${CB_WRAPPER}" \
                    -- uv run --no-project "${py_abs}" > /dev/null 2>&1 || true
                t1=$(ms_now)
                cb_timings+=("$(( t1 - t0 ))")
            done
            read -r cb_mean cb_median cb_p95 cb_min cb_max \
                <<< "$(calc_stats "${cb_timings[@]}")"
            echo -n " done"
        fi

        echo ""

        # Speedup
        speedup=$(python3 -c "
rm = float('${rust_mean}')
pm = float('${py_mean}')
print(f'{pm/rm:.1f}x' if rm > 0 else 'N/A')
")

        # Accumulate per-event totals (use SIMPLE complexity for aggregate, avoid triple-counting)
        if [[ "${complexity}" == "SIMPLE" ]]; then
            case "${hook_name}" in
                post-compact-verify|stop-failure-recovery|task-quality-gate|voice-done|auto-memory-writer)
                    ev="Stop" ;;
                *)
                    ev="PostToolUse" ;;
            esac
            py_mean_int=$(python3 -c "print(int(float('${py_mean}')))")
            rust_mean_int=$(python3 -c "print(int(float('${rust_mean}')))")
            EVENT_PYTHON_TOTAL["${ev}"]=$(( EVENT_PYTHON_TOTAL["${ev}"] + py_mean_int ))
            EVENT_RUST_TOTAL["${ev}"]=$(( EVENT_RUST_TOTAL["${ev}"] + rust_mean_int ))
        fi

        ALL_PYTHON_MEANS+=("${py_mean}")
        ALL_RUST_MEANS+=("${rust_mean}")

        TABLE_ROWS+=("| ${hook_name} | ${complexity} | ${py_mean} | ${rust_mean} | ${speedup} | ${py_rss} | ${rust_rss} | ${cb_mean} |")
    done
done

# ---------------------------------------------------------------------------
# Overall averages
# ---------------------------------------------------------------------------
read -r overall_py_mean _ _ _ _ <<< "$(calc_stats "${ALL_PYTHON_MEANS[@]}")"
read -r overall_rust_mean _ _ _ _ <<< "$(calc_stats "${ALL_RUST_MEANS[@]}")"

overall_speedup=$(python3 -c "
rm = float('${overall_rust_mean}')
pm = float('${overall_py_mean}')
print(f'{pm/rm:.1f}x' if rm > 0 else 'N/A')
")

# ---------------------------------------------------------------------------
# Projections (100 tool calls per session)
# ---------------------------------------------------------------------------
avg_tool_calls=100
read -r py_session_ms py_session_s rust_session_ms rust_session_s net_savings_ms net_savings_s <<< "$(python3 -c "
pm = float('${overall_py_mean}')
rm = float('${overall_rust_mean}')
n  = ${avg_tool_calls}
py_ms   = pm * n
ru_ms   = rm * n
net_ms  = (pm - rm) * n
print(f'{py_ms:.0f} {py_ms/1000:.2f} {ru_ms:.0f} {ru_ms/1000:.2f} {net_ms:.0f} {net_ms/1000:.2f}')
")"

# ---------------------------------------------------------------------------
# Environment info
# ---------------------------------------------------------------------------
OS_INFO=$(uname -srm)
RUSTC_VER=$(rustc --version 2>/dev/null || echo "not found")
PYTHON_VER=$(python3 --version 2>/dev/null || echo "not found")
BIN_SIZE=$(ls -lh "${RUST_BIN}" 2>/dev/null | awk '{print $5}' || echo "n/a")

# ---------------------------------------------------------------------------
# Write markdown report
# ---------------------------------------------------------------------------
{
printf '%s\n' "# CAF Hooks Benchmark: Python vs Rust"
printf '%s\n' ""
printf '%s\n' "## Environment"
printf '%s\n' "- OS: ${OS_INFO}"
printf '%s\n' "- Rust: ${RUSTC_VER}"
printf '%s\n' "- Python: ${PYTHON_VER}"
printf '%s\n' "- Binary size: ${BIN_SIZE}"
printf '%s\n' "- Iterations per combination: ${ITERATIONS}"
printf '%s\n' "- Generated: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
printf '%s\n' ""
printf '%s\n' "## Per-Hook Results"
printf '%s\n' ""
printf '%s\n' "| Hook | Complexity | Python Mean (ms) | Rust Mean (ms) | Speedup | Python RSS (KB) | Rust RSS (KB) | CB-Wrapped Mean (ms) |"
printf '%s\n' "|------|-----------|-----------------|---------------|---------|----------------|--------------|----------------------|"

for row in "${TABLE_ROWS[@]}"; do
    printf '%s\n' "${row}"
done

printf '%s\n' ""
printf '%s\n' "## Per-Event Aggregate"
printf '%s\n' ""
printf '%s\n' "| Event | Python Total (ms) | Rust Total (ms) | Savings (ms) | Speedup |"
printf '%s\n' "|-------|------------------|----------------|-------------|---------|"

for ev in Stop PostToolUse; do
    py_tot="${EVENT_PYTHON_TOTAL[${ev}]}"
    ru_tot="${EVENT_RUST_TOTAL[${ev}]}"
    savings=$(( py_tot - ru_tot ))
    ev_speedup=$(python3 -c "
rt = int('${ru_tot}')
pt = int('${py_tot}')
print(f'{pt/rt:.1f}x' if rt > 0 else 'N/A')
")
    printf '%s\n' "| ${ev} | ${py_tot} | ${ru_tot} | ${savings} | ${ev_speedup} |"
done

printf '%s\n' ""
printf '%s\n' "## Projection"
printf '%s\n' ""
printf '%s\n' "- Avg tool calls per session: ~${avg_tool_calls}"
printf '%s\n' "- Python overhead per session: ${py_session_s} seconds (${py_session_ms} ms)"
printf '%s\n' "- Rust overhead per session: ${rust_session_s} seconds (${rust_session_ms} ms)"
printf '%s\n' "- Net savings: ${net_savings_s} seconds per session (${net_savings_ms} ms)"
printf '%s\n' "- Overall speedup: ${overall_speedup}"
printf '%s\n' ""
printf '%s\n' "> Note: RSS measurements use /usr/bin/time -l (macOS). Values are 0 if unavailable."
printf '%s\n' "> CB-Wrapped column shows N/A for hooks not in the circuit-breaker-wrapped set."

} > "${OUTPUT_FILE}"

echo ""
echo "=== Benchmark complete ==="
echo "Results written to: ${OUTPUT_FILE}"
