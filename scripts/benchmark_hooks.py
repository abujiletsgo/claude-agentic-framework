#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Hook Timeout Benchmarker
========================

Measures actual cold-start and warm-start execution times for every hook
registered in settings.json and outputs evidence-based timeout recommendations.

Run:
    uv run scripts/benchmark_hooks.py
    uv run scripts/benchmark_hooks.py --cold    # simulate cold uv start
    uv run scripts/benchmark_hooks.py --runs 10  # more samples per hook
    uv run scripts/benchmark_hooks.py --event SessionStart  # filter by event

Output includes:
    - P50 / P95 / P99 timing per hook
    - Current timeout from settings.json
    - Recommended timeout (P99 * 2.0, minimum 5s)
    - Whether current timeout is safe (current >= recommended)

Why P99 * 2.0?
    - P99 captures outliers (GC pause, disk cache miss, process contention)
    - 2x multiplier adds breathing room without being reckless
    - If your P99 is 800ms, recommended = 1.6s (not 30s)
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from statistics import mean, median, quantiles
from typing import Optional

SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
REPO_DIR = Path(__file__).resolve().parent.parent

# Mock SessionStart input (used for hooks that don't care about tool events)
MOCK_SESSION_INPUT = json.dumps({
    "hook_event_name": "SessionStart",
    "session_id": "benchmark-session",
    "cwd": str(REPO_DIR),
    "transcript_path": "/tmp/benchmark-transcript.jsonl",
    "permission_mode": "default",
})

MOCK_INPUTS = {
    "PreToolUse": json.dumps({
        "hook_event_name": "PreToolUse",
        "session_id": "benchmark-session",
        "cwd": str(REPO_DIR),
        "transcript_path": "/tmp/benchmark-transcript.jsonl",
        "permission_mode": "default",
        "tool_name": "Bash",
        "tool_input": {"command": "echo benchmark"},
    }),
    "PostToolUse": json.dumps({
        "hook_event_name": "PostToolUse",
        "session_id": "benchmark-session",
        "cwd": str(REPO_DIR),
        "transcript_path": "/tmp/benchmark-transcript.jsonl",
        "permission_mode": "default",
        "tool_name": "Bash",
        "tool_input": {"command": "echo benchmark"},
        "tool_output": "benchmark",
    }),
    "Stop": json.dumps({
        "hook_event_name": "Stop",
        "session_id": "benchmark-session",
        "cwd": str(REPO_DIR),
        "transcript_path": "/tmp/benchmark-transcript.jsonl",
        "permission_mode": "default",
    }),
    "SessionStart": MOCK_SESSION_INPUT,
    "UserPromptSubmit": json.dumps({
        "hook_event_name": "UserPromptSubmit",
        "session_id": "benchmark-session",
        "cwd": str(REPO_DIR),
        "transcript_path": "/tmp/benchmark-transcript.jsonl",
        "permission_mode": "default",
        "prompt": "benchmark test prompt",
    }),
    "PreCompact": json.dumps({
        "hook_event_name": "PreCompact",
        "session_id": "benchmark-session",
        "cwd": str(REPO_DIR),
        "transcript_path": "/tmp/benchmark-transcript.jsonl",
        "permission_mode": "default",
    }),
}


def load_settings() -> Optional[dict]:
    if not SETTINGS_PATH.exists():
        print(f"ERROR: settings.json not found at {SETTINGS_PATH}", file=sys.stderr)
        return None
    with open(SETTINGS_PATH) as f:
        return json.load(f)


def extract_hooks(settings: dict, event_filter: Optional[str] = None) -> list[dict]:
    """Extract all command hooks from settings, returning flat list of dicts."""
    results = []
    hooks_section = settings.get("hooks", {})

    for event, groups in hooks_section.items():
        if event_filter and event != event_filter:
            continue
        for group in groups:
            matcher = group.get("matcher", "*")
            for hook in group.get("hooks", []):
                if hook.get("type") != "command":
                    continue
                cmd = hook.get("command", "")
                if not cmd:
                    continue
                results.append({
                    "event": event,
                    "matcher": matcher,
                    "command": cmd,
                    "current_timeout": hook.get("timeout", 30),
                })

    return results


def run_once(command: str, event: str) -> tuple[float, bool]:
    """
    Run a hook command once with mock input.

    Returns:
        (elapsed_seconds, success)
    """
    mock_input = MOCK_INPUTS.get(event, MOCK_SESSION_INPUT)

    start = time.perf_counter()
    try:
        result = subprocess.run(
            command,
            shell=True,
            input=mock_input,
            capture_output=True,
            text=True,
            timeout=60,  # hard ceiling for benchmark
        )
        elapsed = time.perf_counter() - start
        success = result.returncode == 0
        return elapsed, success
    except subprocess.TimeoutExpired:
        return 60.0, False
    except Exception:
        elapsed = time.perf_counter() - start
        return elapsed, False


def shorten_command(command: str) -> str:
    """Extract the script name from a uv run command for display."""
    # Match last path component (the script filename)
    m = re.search(r'([^/\s]+\.py)(?:\s|$)', command)
    if m:
        return m.group(1)
    # Fall back to last word
    return command.split()[-1] if command.split() else command


def recommend_timeout(p99: float) -> int:
    """Calculate recommended timeout from P99 measurement."""
    raw = p99 * 2.0
    # Round up to nearest 5s, minimum 5s
    rounded = max(5, int((raw + 4) // 5) * 5)
    return rounded


def benchmark_hook(hook: dict, runs: int, verbose: bool = False) -> dict:
    """Run a hook N times and return timing statistics."""
    command = hook["command"]
    event = hook["event"]
    name = shorten_command(command)

    if verbose:
        print(f"  Benchmarking {name} ({runs} runs)...", end="", flush=True)

    times = []
    failures = 0

    for i in range(runs):
        elapsed, success = run_once(command, event)
        times.append(elapsed)
        if not success:
            failures += 1
        if verbose:
            print(".", end="", flush=True)

    if verbose:
        print()

    times.sort()

    # Compute percentiles (need at least 2 data points for quantiles())
    if len(times) >= 2:
        qs = quantiles(times, n=100)
        p50 = qs[49]
        p95 = qs[94]
        p99 = qs[98]
    else:
        p50 = p95 = p99 = times[0] if times else 0.0

    return {
        "name": name,
        "event": event,
        "command": command,
        "current_timeout": hook["current_timeout"],
        "runs": runs,
        "failures": failures,
        "min": times[0] if times else 0,
        "max": times[-1] if times else 0,
        "mean": mean(times) if times else 0,
        "p50": p50,
        "p95": p95,
        "p99": p99,
        "recommended_timeout": recommend_timeout(p99),
    }


def format_table(results: list[dict]) -> str:
    """Format benchmark results as an aligned table."""
    header = (
        f"{'Hook':<35} {'Event':<18} {'P50':>6} {'P95':>6} {'P99':>6} "
        f"{'Current':>8} {'Rec.':>6} {'Safe?':>6} {'Fails':>5}"
    )
    separator = "-" * len(header)
    rows = [header, separator]

    for r in results:
        safe = r["current_timeout"] >= r["recommended_timeout"]
        safe_str = "✓" if safe else "✗ LOW"
        fail_str = f"{r['failures']}/{r['runs']}"
        row = (
            f"{r['name']:<35} {r['event']:<18} "
            f"{r['p50']*1000:>5.0f}ms "
            f"{r['p95']*1000:>5.0f}ms "
            f"{r['p99']*1000:>5.0f}ms "
            f"{r['current_timeout']:>7}s "
            f"{r['recommended_timeout']:>5}s "
            f"{safe_str:>6} "
            f"{fail_str:>5}"
        )
        rows.append(row)

    return "\n".join(rows)


def print_recommendations(results: list[dict]) -> None:
    """Print actionable fixes for hooks with unsafe timeouts."""
    unsafe = [r for r in results if r["current_timeout"] < r["recommended_timeout"]]
    if not unsafe:
        print("\n✓ All timeouts are safe based on measured P99 timings.")
        return

    print(f"\n⚠ {len(unsafe)} hook(s) have timeouts below P99*2.0 recommendation:")
    for r in unsafe:
        margin = r["recommended_timeout"] - r["current_timeout"]
        print(
            f"  {r['name']} ({r['event']}): "
            f"current={r['current_timeout']}s, "
            f"P99={r['p99']*1000:.0f}ms, "
            f"recommended={r['recommended_timeout']}s "
            f"(+{margin}s)"
        )
    print(
        "\nTo fix: update templates/settings.json.template and run bash install.sh"
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Benchmark hook execution times and recommend timeouts"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of runs per hook (default: 5)",
    )
    parser.add_argument(
        "--event",
        type=str,
        default=None,
        help="Filter to a specific event type (e.g. SessionStart)",
    )
    parser.add_argument(
        "--cold",
        action="store_true",
        help="Attempt cold-start simulation by clearing uv script cache before first run",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show progress dots per run",
    )
    args = parser.parse_args()

    settings = load_settings()
    if not settings:
        sys.exit(1)

    hooks = extract_hooks(settings, event_filter=args.event)
    if not hooks:
        print("No command hooks found" + (f" for event '{args.event}'" if args.event else "") + ".")
        sys.exit(0)

    print(f"Benchmarking {len(hooks)} hook(s) × {args.runs} run(s) each...")
    if args.cold:
        print("Cold-start mode: clearing uv script cache before first run of each hook")
    print()

    results = []
    for hook in hooks:
        if args.cold:
            # Clear uv script cache to force re-resolution on first run
            script_path = re.search(r'uv run (\S+\.py)', hook["command"])
            if script_path:
                cache_clear = subprocess.run(
                    ["uv", "cache", "clean", "--quiet"],
                    capture_output=True,
                )

        result = benchmark_hook(hook, runs=args.runs, verbose=args.verbose)
        results.append(result)

        # Quick live feedback
        safe = result["current_timeout"] >= result["recommended_timeout"]
        status = "✓" if safe else f"✗ (rec. {result['recommended_timeout']}s)"
        print(
            f"  {result['name']:<35} P99={result['p99']*1000:5.0f}ms  "
            f"timeout={result['current_timeout']}s  {status}"
        )

    print()
    print(format_table(results))
    print_recommendations(results)


if __name__ == "__main__":
    main()
