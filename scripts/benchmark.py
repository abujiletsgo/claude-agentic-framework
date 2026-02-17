#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
General-Purpose Benchmarker
============================

Measures real execution time of any shell command or Python script and
produces evidence-based threshold recommendations using P99 * 2.0.

Use this when you need to set a timeout, budget, or performance limit for
ANYTHING — a hook, a script, a database query, a CLI tool — and you don't
want to pull a number out of thin air.

Usage:
    # Benchmark a specific script with a mock JSON input
    uv run scripts/benchmark.py --cmd "uv run path/to/script.py" --input '{...}'

    # Benchmark all hooks in settings.json (delegates to benchmark_hooks.py logic)
    uv run scripts/benchmark.py --hooks
    uv run scripts/benchmark.py --hooks --event SessionStart

    # Benchmark an arbitrary shell command (no stdin)
    uv run scripts/benchmark.py --cmd "python3 -c 'import json; json.loads(\\"{}\\")'\"

    # More samples for tighter P99
    uv run scripts/benchmark.py --cmd "..." --runs 20

    # Cold-start simulation (warns that uv cache clear affects all hooks)
    uv run scripts/benchmark.py --hooks --cold

Methodology:
    - P50  : typical case
    - P95  : busy-system case (GC pause, disk cache miss)
    - P99  : outlier — USE THIS for threshold recommendations
    - Rec. : P99 * 2.0, rounded to nearest 5s, floor 5s
             (2x gives breathing room without over-provisioning)

Why not P100 (max)?
    Max is dominated by one-off OS events (process scheduling, laptop sleep).
    P99 over 10+ runs is stable and representative of real conditions.

Why 2x margin?
    Thresholds set at P99 with no margin will fail ~1% of the time by
    definition. 2x gives enough room for sustained load while keeping
    timeouts honest. Adjust with --margin if your use case warrants it.
"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from statistics import mean, quantiles
from typing import Optional

REPO_DIR = Path(__file__).resolve().parent.parent
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

MOCK_INPUTS = {
    "PreToolUse": {
        "hook_event_name": "PreToolUse",
        "session_id": "benchmark-session",
        "cwd": str(REPO_DIR),
        "transcript_path": "/tmp/benchmark-transcript.jsonl",
        "permission_mode": "default",
        "tool_name": "Bash",
        "tool_input": {"command": "echo benchmark"},
    },
    "PostToolUse": {
        "hook_event_name": "PostToolUse",
        "session_id": "benchmark-session",
        "cwd": str(REPO_DIR),
        "transcript_path": "/tmp/benchmark-transcript.jsonl",
        "permission_mode": "default",
        "tool_name": "Bash",
        "tool_input": {"command": "echo benchmark"},
        "tool_output": "benchmark",
    },
    "Stop": {
        "hook_event_name": "Stop",
        "session_id": "benchmark-session",
        "cwd": str(REPO_DIR),
        "transcript_path": "/tmp/benchmark-transcript.jsonl",
        "permission_mode": "default",
    },
    "SessionStart": {
        "hook_event_name": "SessionStart",
        "session_id": "benchmark-session",
        "cwd": str(REPO_DIR),
        "transcript_path": "/tmp/benchmark-transcript.jsonl",
        "permission_mode": "default",
    },
    "UserPromptSubmit": {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "benchmark-session",
        "cwd": str(REPO_DIR),
        "transcript_path": "/tmp/benchmark-transcript.jsonl",
        "permission_mode": "default",
        "prompt": "benchmark test prompt",
    },
    "PreCompact": {
        "hook_event_name": "PreCompact",
        "session_id": "benchmark-session",
        "cwd": str(REPO_DIR),
        "transcript_path": "/tmp/benchmark-transcript.jsonl",
        "permission_mode": "default",
    },
}


# ---------------------------------------------------------------------------
# Core timing logic (shared with benchmark_hooks.py)
# ---------------------------------------------------------------------------

def run_once(command: str, stdin_data: Optional[str] = None) -> tuple[float, bool]:
    """Run a shell command once, return (elapsed_seconds, success)."""
    start = time.perf_counter()
    try:
        result = subprocess.run(
            command,
            shell=True,
            input=stdin_data or "",
            capture_output=True,
            text=True,
            timeout=120,
        )
        elapsed = time.perf_counter() - start
        return elapsed, result.returncode == 0
    except subprocess.TimeoutExpired:
        return 120.0, False
    except Exception:
        return time.perf_counter() - start, False


def compute_stats(times: list[float], failures: int, label: str, current_timeout: Optional[float], margin: float) -> dict:
    """Compute timing statistics from a list of elapsed times."""
    times = sorted(times)

    if len(times) >= 2:
        qs = quantiles(times, n=100)
        p50, p95, p99 = qs[49], qs[94], qs[98]
    else:
        p50 = p95 = p99 = times[0] if times else 0.0

    # Recommendation: P99 * margin, rounded to nearest 5s, floor 5s
    raw_rec = p99 * margin
    recommended = max(5, int((raw_rec + 4) // 5) * 5)

    return {
        "label": label,
        "runs": len(times),
        "failures": failures,
        "min": times[0] if times else 0,
        "max": times[-1] if times else 0,
        "mean": mean(times) if times else 0,
        "p50": p50,
        "p95": p95,
        "p99": p99,
        "recommended": recommended,
        "current_timeout": current_timeout,
        "safe": (current_timeout is None) or (current_timeout >= recommended),
    }


def benchmark_command(
    command: str,
    runs: int,
    stdin_data: Optional[str] = None,
    label: Optional[str] = None,
    current_timeout: Optional[float] = None,
    margin: float = 2.0,
) -> dict:
    """Benchmark a shell command and return stats dict."""
    name = label or _shorten(command)
    times = []
    failures = 0

    for _ in range(runs):
        elapsed, success = run_once(command, stdin_data)
        times.append(elapsed)
        if not success:
            failures += 1

    return compute_stats(times, failures, name, current_timeout, margin)


def _shorten(command: str) -> str:
    m = re.search(r'([^/\s]+\.py)(?:\s|$)', command)
    return m.group(1) if m else (command.split()[-1] if command.split() else command)


# ---------------------------------------------------------------------------
# Hooks mode (reads settings.json)
# ---------------------------------------------------------------------------

def load_hooks(event_filter: Optional[str] = None) -> list[dict]:
    if not SETTINGS_PATH.exists():
        print(f"ERROR: {SETTINGS_PATH} not found", file=sys.stderr)
        return []
    with open(SETTINGS_PATH) as f:
        settings = json.load(f)

    results = []
    for event, groups in settings.get("hooks", {}).items():
        if event_filter and event != event_filter:
            continue
        for group in groups:
            for hook in group.get("hooks", []):
                if hook.get("type") != "command" or not hook.get("command"):
                    continue
                results.append({
                    "event": event,
                    "command": hook["command"],
                    "current_timeout": hook.get("timeout"),
                })
    return results


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def print_table(results: list[dict]) -> None:
    header = (
        f"{'Target':<38} {'P50':>6} {'P95':>6} {'P99':>6} "
        f"{'Current':>8} {'Rec.':>6} {'Safe?':>6} {'Fails':>5}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        safe_str = "✓" if r["safe"] else "✗ LOW"
        cur_str = f"{r['current_timeout']}s" if r["current_timeout"] is not None else "  n/a"
        print(
            f"{r['label']:<38} "
            f"{r['p50']*1000:>5.0f}ms "
            f"{r['p95']*1000:>5.0f}ms "
            f"{r['p99']*1000:>5.0f}ms "
            f"{cur_str:>8} "
            f"{r['recommended']:>5}s "
            f"{safe_str:>6} "
            f"{r['failures']}/{r['runs']:>3}"
        )


def print_recommendations(results: list[dict]) -> None:
    unsafe = [r for r in results if not r["safe"]]
    if not unsafe:
        print("\n✓ All measured targets are within their current limits.")
        return

    print(f"\n⚠ {len(unsafe)} target(s) have limits below P99*2.0:")
    for r in unsafe:
        margin = r["recommended"] - (r["current_timeout"] or 0)
        print(
            f"  {r['label']}: current={r['current_timeout']}s, "
            f"P99={r['p99']*1000:.0f}ms, recommended={r['recommended']}s (+{margin}s)"
        )
    print("\nTo fix hooks: update templates/settings.json.template → bash install.sh")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Benchmark any command or all hooks — get evidence-based thresholds"
    )
    parser.add_argument(
        "--cmd",
        type=str,
        default=None,
        help="Shell command to benchmark (e.g. 'uv run path/to/script.py')",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="JSON string to pass via stdin (for hooks/scripts that read stdin)",
    )
    parser.add_argument(
        "--label",
        type=str,
        default=None,
        help="Display name for the command (default: script filename)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Current timeout/limit to compare against (shows ✓/✗)",
    )
    parser.add_argument(
        "--hooks",
        action="store_true",
        help="Benchmark all hooks registered in settings.json",
    )
    parser.add_argument(
        "--event",
        type=str,
        default=None,
        help="(with --hooks) Filter to a specific event type",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Samples per target (default: 5; use 20+ for tight P99)",
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=2.0,
        help="Multiplier on P99 for recommendation (default: 2.0)",
    )
    parser.add_argument(
        "--cold",
        action="store_true",
        help="Clear uv script cache before each first run (hooks mode only)",
    )
    args = parser.parse_args()

    if not args.hooks and not args.cmd:
        parser.print_help()
        sys.exit(1)

    if args.hooks:
        hooks = load_hooks(event_filter=args.event)
        if not hooks:
            print("No hooks found.")
            sys.exit(0)

        print(f"Benchmarking {len(hooks)} hook(s) × {args.runs} run(s) each...\n")
        results = []
        for hook in hooks:
            if args.cold:
                subprocess.run(["uv", "cache", "clean", "--quiet"], capture_output=True)
            stdin_data = json.dumps(MOCK_INPUTS.get(hook["event"], MOCK_INPUTS["SessionStart"]))
            r = benchmark_command(
                command=hook["command"],
                runs=args.runs,
                stdin_data=stdin_data,
                current_timeout=hook["current_timeout"],
                margin=args.margin,
            )
            results.append(r)
            safe = "✓" if r["safe"] else f"✗ (rec. {r['recommended']}s)"
            print(f"  {r['label']:<38} P99={r['p99']*1000:5.0f}ms  {safe}")

        print()
        print_table(results)
        print_recommendations(results)

    elif args.cmd:
        print(f"Benchmarking: {args.cmd}")
        print(f"Runs: {args.runs}  Margin: {args.margin}x\n")
        r = benchmark_command(
            command=args.cmd,
            runs=args.runs,
            stdin_data=args.input,
            label=args.label,
            current_timeout=args.timeout,
            margin=args.margin,
        )
        print(f"  Min    : {r['min']*1000:.1f}ms")
        print(f"  P50    : {r['p50']*1000:.1f}ms")
        print(f"  P95    : {r['p95']*1000:.1f}ms")
        print(f"  P99    : {r['p99']*1000:.1f}ms")
        print(f"  Max    : {r['max']*1000:.1f}ms")
        print(f"  Mean   : {r['mean']*1000:.1f}ms")
        print(f"  Rec.   : {r['recommended']}s  (P99 × {args.margin})")
        if args.timeout is not None:
            status = "✓ safe" if r["safe"] else f"✗ LOW — increase to {r['recommended']}s"
            print(f"  Current: {args.timeout}s  →  {status}")
        if r["failures"]:
            print(f"\n  ⚠ {r['failures']}/{r['runs']} runs failed")


if __name__ == "__main__":
    main()
