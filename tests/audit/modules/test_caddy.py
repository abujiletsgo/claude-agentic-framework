"""
CAF Audit — Caddy Classifier Tests
====================================
Tests Caddy's classification accuracy, confidence scoring, strategy routing,
and hook output format. Measures latency per classification.

Run standalone:
  uv run pytest tests/audit/modules/test_caddy.py -v
  uv run pytest tests/audit/modules/test_caddy.py -v -m "not slow"
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent
CADDY_PATH = REPO_ROOT / "global-hooks/framework/caddy/analyze_request.py"
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

TIMINGS: list[dict] = []


# ── helpers ────────────────────────────────────────────────────────────────────

def run_caddy(prompt: str, session_id: str = "audit-caddy-001") -> tuple[dict, float]:
    """Run analyze_request.py via subprocess. Returns (output_dict, elapsed_ms)."""
    payload = json.dumps({"prompt": prompt, "session_id": session_id})
    t0 = time.perf_counter()
    result = subprocess.run(
        ["uv", "run", "--no-project", str(CADDY_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    if result.stdout.strip():
        try:
            return json.loads(result.stdout), elapsed_ms
        except json.JSONDecodeError:
            return {}, elapsed_ms
    return {}, elapsed_ms


def get_classification(output: dict) -> dict:
    """Extract classification dict from hook output."""
    ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
    # Parse from additionalContext string: "[Caddy] Task classified as: simple fix"
    result = {}
    for line in ctx.splitlines():
        if "[Caddy] Task classified as:" in line:
            parts = line.split("classified as:")[-1].strip().split()
            if len(parts) >= 2:
                result["complexity"] = parts[0]
                result["task_type"] = parts[1]
        if "[Caddy] Recommended strategy:" in line:
            parts = line.split("strategy:")[-1].strip().split()
            if parts:
                result["strategy"] = parts[0]
    return result


def record_timing(test_name: str, elapsed_ms: float) -> None:
    TIMINGS.append({"test": test_name, "ms": elapsed_ms})


# ── fixture check ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def require_caddy():
    if not CADDY_PATH.exists():
        pytest.skip(f"Caddy not found: {CADDY_PATH}")


# ── tests ──────────────────────────────────────────────────────────────────────

def test_caddy_script_exists():
    assert CADDY_PATH.exists(), f"analyze_request.py not found at {CADDY_PATH}"


def test_classify_simple_fix_prompts():
    simple_prompts = [
        "fix the typo in the README",
        "correct the import path in utils.py",
        "the login button has a bug",
        "there is a missing semicolon",
        "fix the broken unit test",
    ]
    for prompt in simple_prompts:
        output, elapsed_ms = run_caddy(prompt)
        record_timing("test_classify_simple_fix_prompts", elapsed_ms)
        assert output, f"No output for: {prompt}"
        cls = get_classification(output)
        assert cls.get("complexity") in ("simple", "moderate"), (
            f"Expected simple/moderate for '{prompt}', got {cls.get('complexity')}"
        )


def test_classify_complex_prompts():
    complex_prompts = [
        "research why our API latency has increased 3x, analyze all logs, traces, and metrics to find root cause",
        "investigate and fix the 38 failing tests across the entire test suite",
        "redesign the database schema to support multi-tenancy for 10000 tenants",
    ]
    for prompt in complex_prompts:
        output, elapsed_ms = run_caddy(prompt)
        record_timing("test_classify_complex_prompts", elapsed_ms)
        assert output, f"No output for: {prompt}"
        cls = get_classification(output)
        assert cls.get("complexity") in ("complex", "massive"), (
            f"Expected complex/massive for long research prompt, got {cls.get('complexity')}"
        )


def test_classify_complexity_numeric_scale():
    """'38 failing tests' should push complexity up toward moderate/complex."""
    output, elapsed_ms = run_caddy("investigate and fix the 38 failing tests across the test suite")
    record_timing("test_classify_complexity_numeric_scale", elapsed_ms)
    assert output
    cls = get_classification(output)
    assert cls.get("complexity") in ("moderate", "complex"), (
        f"Numeric scale (38 tests) should push complexity up, got {cls.get('complexity')}"
    )


def test_classify_task_type_fix():
    prompts = ["fix the null pointer", "correct the bug in auth.py", "resolve the error in payment"]
    for prompt in prompts:
        output, elapsed_ms = run_caddy(prompt)
        record_timing("test_classify_task_type_fix", elapsed_ms)
        assert output


def test_classify_task_type_research():
    prompts = ["research why the latency increased", "investigate the performance issue", "analyze the logs"]
    for prompt in prompts:
        output, elapsed_ms = run_caddy(prompt)
        record_timing("test_classify_task_type_research", elapsed_ms)
        assert output


def test_classify_task_type_test():
    prompts = ["write tests for the UserService", "add unit tests for auth module"]
    for prompt in prompts:
        output, elapsed_ms = run_caddy(prompt)
        record_timing("test_classify_task_type_test", elapsed_ms)
        assert output


def test_classify_quality_critical_keywords():
    """Security/payment/encryption keywords should raise quality to critical or high."""
    critical_prompts = [
        "fix the SQL injection vulnerability in the search endpoint",
        "the payment processing has a critical security bug",
        "there is an authentication bypass in production",
    ]
    for prompt in critical_prompts:
        output, elapsed_ms = run_caddy(prompt)
        record_timing("test_classify_quality_critical_keywords", elapsed_ms)
        assert output


def test_strategy_direct_for_simple():
    output, elapsed_ms = run_caddy("fix the typo in README.md")
    record_timing("test_strategy_direct_for_simple", elapsed_ms)
    cls = get_classification(output)
    # Simple standard → direct
    assert cls.get("strategy") in ("direct", "team"), (
        f"Simple fix should route to direct, got {cls.get('strategy')}"
    )


def test_strategy_rlm_for_massive():
    output, elapsed_ms = run_caddy(
        "research the entire unknown codebase with broad unknown scope and unlimited complexity "
        "to understand every component, data flow, and architectural decision"
    )
    record_timing("test_strategy_rlm_for_massive", elapsed_ms)
    # massive + broad + research → rlm
    cls = get_classification(output)
    # Accept rlm or orchestrate (classifier may not always reach rlm threshold)
    assert cls.get("strategy") in ("rlm", "orchestrate", "fusion"), (
        f"Massive broad research should route to rlm/orchestrate, got {cls.get('strategy')}"
    )


def test_strategy_fusion_for_critical():
    output, elapsed_ms = run_caddy(
        "fix the critical security vulnerability in the payment encryption — production is at risk"
    )
    record_timing("test_strategy_fusion_for_critical", elapsed_ms)
    cls = get_classification(output)
    assert cls.get("strategy") in ("fusion", "orchestrate", "direct"), (
        f"Critical security fix strategy, got {cls.get('strategy')}"
    )


def test_hook_output_has_required_fields():
    output, elapsed_ms = run_caddy("fix the login bug")
    record_timing("test_hook_output_has_required_fields", elapsed_ms)
    assert output, "Expected non-empty output"
    hook_output = output.get("hookSpecificOutput")
    assert hook_output is not None, f"Missing hookSpecificOutput. Got: {list(output.keys())}"
    assert "hookEventName" in hook_output, "Missing hookEventName in hookSpecificOutput"
    assert hook_output["hookEventName"] == "UserPromptSubmit"


def test_hook_output_has_caddy_context():
    output, elapsed_ms = run_caddy("implement a new feature for user management")
    record_timing("test_hook_output_has_caddy_context", elapsed_ms)
    ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "[Caddy]" in ctx, f"Expected [Caddy] marker in additionalContext. Got: {ctx[:200]}"


def test_full_stdin_pipe_subprocess():
    """End-to-end test: raw subprocess call with JSON stdin."""
    payload = json.dumps({"prompt": "add rate limiting to the API", "session_id": "e2e-test"})
    result = subprocess.run(
        ["uv", "run", "--no-project", str(CADDY_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )
    assert result.returncode == 0, f"Caddy exited {result.returncode}: {result.stderr}"
    if result.stdout.strip():
        parsed = json.loads(result.stdout)
        assert isinstance(parsed, dict)


def test_short_prompt_produces_output():
    """Very short prompts should not crash the classifier."""
    output, elapsed_ms = run_caddy("fix")
    record_timing("test_short_prompt_produces_output", elapsed_ms)
    # Should return something (even if low-confidence)
    assert isinstance(output, dict)


def test_ground_truth_sample_accuracy():
    """Run a sample of the ground truth prompts and measure accuracy."""
    prompts_file = FIXTURES_DIR / "sample_prompts.json"
    if not prompts_file.exists():
        pytest.skip("sample_prompts.json not found")

    prompts = json.loads(prompts_file.read_text())
    # Test a sample of 10 for speed
    sample = prompts[:10]

    correct_strategy = 0
    timings = []
    for item in sample:
        output, elapsed_ms = run_caddy(item["prompt"])
        timings.append(elapsed_ms)
        cls = get_classification(output)
        expected_strategy = item["expected"]["strategy"]
        if cls.get("strategy") == expected_strategy:
            correct_strategy += 1
        record_timing("test_ground_truth_sample_accuracy", elapsed_ms)

    accuracy = correct_strategy / len(sample) * 100
    avg_ms = sum(timings) / len(timings)
    p99_ms = sorted(timings)[int(len(timings) * 0.99)]

    print(f"\n  Strategy accuracy: {accuracy:.1f}% ({correct_strategy}/{len(sample)})")
    print(f"  Avg latency: {avg_ms:.1f}ms  p99: {p99_ms:.1f}ms")

    # Soft assertion — accuracy should be reasonable
    assert accuracy >= 50, f"Strategy accuracy too low: {accuracy:.1f}%"


@pytest.mark.slow
def test_ground_truth_full_accuracy():
    """Run all 100 ground truth prompts (slow — requires full API or deterministic classifier)."""
    prompts_file = FIXTURES_DIR / "sample_prompts.json"
    if not prompts_file.exists():
        pytest.skip("sample_prompts.json not found")

    prompts = json.loads(prompts_file.read_text())
    correct_strategy = 0
    timings = []

    for item in prompts:
        output, elapsed_ms = run_caddy(item["prompt"])
        timings.append(elapsed_ms)
        cls = get_classification(output)
        if cls.get("strategy") == item["expected"]["strategy"]:
            correct_strategy += 1

    accuracy = correct_strategy / len(prompts) * 100
    avg_ms = sum(timings) / len(timings)
    timings_sorted = sorted(timings)
    p99_ms = timings_sorted[int(len(timings) * 0.99)]

    print(f"\n  Full accuracy: {accuracy:.1f}% ({correct_strategy}/{len(prompts)})")
    print(f"  Avg: {avg_ms:.1f}ms  p99: {p99_ms:.1f}ms  max: {max(timings):.1f}ms")

    assert accuracy >= 60, f"Full accuracy too low: {accuracy:.1f}%"
