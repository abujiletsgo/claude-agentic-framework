#!/usr/bin/env python3
"""
CAF Comprehensive Audit Test Suite
====================================
Usage:
  uv run python tests/audit/run_audit.py                    # run all modules
  uv run python tests/audit/run_audit.py --module caddy     # run one module
  uv run python tests/audit/run_audit.py --skip-slow        # skip @pytest.mark.slow
  uv run python tests/audit/run_audit.py --format json      # JSON output only
  uv run python tests/audit/run_audit.py --format html      # HTML output (default)
  uv run python tests/audit/run_audit.py --list             # list available modules

Modules:
  caddy              Caddy classifier accuracy + latency
  circuit_breaker    Circuit breaker state machine
  damage_control     Pattern matching accuracy
  knowledge_db       FTS5 speed + search accuracy
  hooks              All hook files existence + JSON I/O
  context_pipeline   Context compaction pipeline
  memory_system      Fact extraction + MEMORY.md writes
  rust_hooks         Rust binary speed vs Python (slow)
  e2e                Full simulated session (slow)

Output:
  /tmp/caf_audit_report.html  (HTML, default)
  /tmp/caf_audit_report.json  (JSON)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent.parent
MODULES_DIR = Path(__file__).parent / "modules"
REPORT_DIR = Path(__file__).parent / "report"
sys.path.insert(0, str(REPORT_DIR))

MODULES = {
    "caddy":            MODULES_DIR / "test_caddy.py",
    "circuit_breaker":  MODULES_DIR / "test_circuit_breaker.py",
    "damage_control":   MODULES_DIR / "test_damage_control.py",
    "knowledge_db":     MODULES_DIR / "test_knowledge_db.py",
    "hooks":            MODULES_DIR / "test_hooks.py",
    "context_pipeline": MODULES_DIR / "test_context_pipeline.py",
    "memory_system":    MODULES_DIR / "test_memory_system.py",
    "rust_hooks":       MODULES_DIR / "test_rust_hooks.py",
    "e2e":              MODULES_DIR / "test_e2e_session.py",
}

SLOW_MODULES = {"rust_hooks", "e2e"}


def run_module(name: str, path: Path, skip_slow: bool) -> dict:
    """Run a single audit module via pytest and parse results."""
    if skip_slow and name in SLOW_MODULES:
        return {
            "module": name,
            "status": "SKIP",
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_error": 0,
            "duration_ms": 0,
            "metrics": {},
            "failures": [],
            "skip_reason": "slow test skipped (--skip-slow)",
        }

    if not path.exists():
        return {
            "module": name,
            "status": "ERROR",
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_error": 1,
            "duration_ms": 0,
            "metrics": {},
            "failures": [{"test": "module_load", "reason": f"File not found: {path}"}],
        }

    print(f"\n{'─'*60}")
    print(f"  Running: {name}")
    print(f"{'─'*60}")

    t0 = time.perf_counter()
    extra_args = ["-m", "not slow"] if skip_slow else []

    cmd = [
        "uv", "run", "--no-project", "-m", "pytest",
        str(path),
        "--tb=short",
        "--json-report",
        f"--json-report-file=/tmp/caf_pytest_{name}.json",
        "-q",
        *extra_args,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            cwd=str(REPO_ROOT), timeout=120
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
        if result.stderr:
            print(result.stderr[-1000:], file=sys.stderr)
    except subprocess.TimeoutExpired:
        return {
            "module": name,
            "status": "ERROR",
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_error": 1,
            "duration_ms": 120_000,
            "metrics": {},
            "failures": [{"test": "timeout", "reason": "Module timed out after 120s"}],
        }

    # Parse pytest JSON report if available
    report_file = Path(f"/tmp/caf_pytest_{name}.json")
    if report_file.exists():
        try:
            pytest_data = json.loads(report_file.read_text())
            summary = pytest_data.get("summary", {})
            tests_run = summary.get("total", 0)
            tests_passed = summary.get("passed", 0)
            tests_failed = summary.get("failed", 0)
            tests_error = summary.get("error", 0)
            failures = []
            for test in pytest_data.get("tests", []):
                if test.get("outcome") in ("failed", "error"):
                    failures.append({
                        "test": test.get("nodeid", "?"),
                        "reason": (test.get("call", {}) or {}).get("longrepr", "")[:200],
                    })
            status = "PASS" if tests_failed == 0 and tests_error == 0 else "FAIL"
            return {
                "module": name,
                "status": status,
                "tests_run": tests_run,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "tests_error": tests_error,
                "duration_ms": round(elapsed_ms),
                "metrics": extract_metrics(pytest_data),
                "failures": failures,
            }
        except Exception:
            pass

    # Fallback: parse from exit code + stdout
    status = "PASS" if result.returncode == 0 else "FAIL"
    passed = result.stdout.count(" passed")
    failed = result.stdout.count(" failed")
    return {
        "module": name,
        "status": status,
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": int(failed > 0),
        "tests_error": 0,
        "duration_ms": round(elapsed_ms),
        "metrics": {},
        "failures": [],
    }


def extract_metrics(pytest_data: dict) -> dict:
    """Extract custom metrics from pytest JSON report (stored as test properties)."""
    metrics = {}
    for test in pytest_data.get("tests", []):
        props = (test.get("metadata") or {})
        for k, v in props.items():
            if k in ("accuracy_pct", "avg_latency_ms", "p99_latency_ms", "memory_rss_mb", "speedup_ratio"):
                metrics[k] = v
    return metrics


def print_summary(results: list[dict]) -> None:
    total = sum(r.get("tests_run", 0) for r in results)
    passed = sum(r.get("tests_passed", 0) for r in results)
    failed = sum(r.get("tests_failed", 0) for r in results)
    duration = sum(r.get("duration_ms", 0) for r in results) / 1000

    print(f"\n{'='*60}")
    print(f"  CAF AUDIT SUMMARY")
    print(f"{'='*60}")
    for r in results:
        icon = "v" if r["status"] == "PASS" else ("o" if r["status"] == "SKIP" else "x")
        print(f"  {icon} {r['module']:<20} {r['status']:<6}  {r.get('tests_passed',0)}/{r.get('tests_run',0)} passed  {r.get('duration_ms',0):.0f}ms")
    print(f"{'─'*60}")
    print(f"  Total: {passed}/{total} passed · {failed} failed · {duration:.1f}s")
    overall = "PASS" if failed == 0 else "FAIL"
    print(f"  Overall: {overall}")
    print(f"{'='*60}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="CAF Audit Test Suite")
    parser.add_argument("--module", choices=list(MODULES.keys()), help="Run a specific module only")
    parser.add_argument("--skip-slow", action="store_true", help="Skip slow tests (rust_hooks, e2e)")
    parser.add_argument("--format", choices=["html", "json", "both"], default="html")
    parser.add_argument("--list", action="store_true", help="List available modules and exit")
    args = parser.parse_args()

    if args.list:
        print("Available modules:")
        for name, path in MODULES.items():
            slow = " [slow]" if name in SLOW_MODULES else ""
            exists = "v" if path.exists() else "x"
            print(f"  {exists} {name:<20}{slow}")
        return 0

    # Select modules to run
    to_run = {args.module: MODULES[args.module]} if args.module else MODULES

    print(f"\nCAF Audit Test Suite")
    print(f"Modules: {', '.join(to_run.keys())}")
    print(f"Skip slow: {args.skip_slow}")

    results = []
    for name, path in to_run.items():
        module_result = run_module(name, path, args.skip_slow)
        results.append(module_result)

    print_summary(results)

    # Build report
    report = {
        "report_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "framework": "claude-agentic-framework",
        "overall_status": "PASS" if all(r["status"] in ("PASS", "SKIP") for r in results) else "FAIL",
        "summary": {
            "total_tests": sum(r.get("tests_run", 0) for r in results),
            "total_passed": sum(r.get("tests_passed", 0) for r in results),
            "total_failed": sum(r.get("tests_failed", 0) for r in results),
            "total_errors": sum(r.get("tests_error", 0) for r in results),
            "total_duration_ms": sum(r.get("duration_ms", 0) for r in results),
            "pass_rate_pct": 0,
        },
        "modules": results,
    }
    total = report["summary"]["total_tests"]
    report["summary"]["pass_rate_pct"] = round(
        (report["summary"]["total_passed"] / total * 100) if total else 0, 1
    )

    # Save reports
    import html_reporter, json_reporter  # noqa: E402 — loaded from report/
    if args.format in ("json", "both"):
        json_reporter.save(report, Path("/tmp/caf_audit_report.json"))
    if args.format in ("html", "both"):
        html_reporter.save(report, Path("/tmp/caf_audit_report.html"))
    if args.format == "html":
        html_reporter.save(report, Path("/tmp/caf_audit_report.html"))

    # Exit code: 0 if all pass, 1 if any fail
    failed = sum(r.get("tests_failed", 0) for r in results)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
