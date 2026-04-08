"""JSON reporter for CAF audit results."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_report(module_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a structured JSON report from module results."""
    total_tests = sum(r.get("tests_run", 0) for r in module_results)
    total_passed = sum(r.get("tests_passed", 0) for r in module_results)
    total_failed = sum(r.get("tests_failed", 0) for r in module_results)
    total_errors = sum(r.get("tests_error", 0) for r in module_results)
    total_duration = sum(r.get("duration_ms", 0) for r in module_results)

    overall_status = "PASS" if total_failed == 0 and total_errors == 0 else "FAIL"

    return {
        "report_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "framework": "claude-agentic-framework",
        "overall_status": overall_status,
        "summary": {
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_errors": total_errors,
            "total_duration_ms": total_duration,
            "pass_rate_pct": round((total_passed / total_tests * 100) if total_tests else 0, 1),
        },
        "modules": module_results,
    }


def save(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2))
    print(f"JSON report saved: {path}")
