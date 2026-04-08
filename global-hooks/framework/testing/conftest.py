# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest", "pyyaml"]
# ///
"""
Shared pytest configuration and fixtures for the testing framework.
"""

import sys
from pathlib import Path

# Add framework paths for imports
TESTING_DIR = Path(__file__).parent
FRAMEWORK_DIR = TESTING_DIR.parent
HOOKS_DIR = FRAMEWORK_DIR.parent

# Add all framework modules to sys.path
sys.path.insert(0, str(FRAMEWORK_DIR / "knowledge"))
sys.path.insert(0, str(FRAMEWORK_DIR / "guardrails"))
sys.path.insert(0, str(FRAMEWORK_DIR / "review"))
sys.path.insert(0, str(FRAMEWORK_DIR / "review" / "analyzers"))

import pytest
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# benchmark fixture
# ---------------------------------------------------------------------------
#
# Provides evidence-based timing measurement to any pytest test.
# Philosophy: measure P99, never guess at thresholds.
#
# Usage:
#
#   def test_parser_is_fast(benchmark):
#       result = benchmark(lambda: parse_config("big.yaml"), runs=20)
#       result.assert_p99_under(0.050)        # hard SLA: must be < 50ms
#       # OR: just print the recommendation
#       print(result.report())
#
#   def test_db_query_budget(benchmark):
#       result = benchmark(lambda: db.search("python"), runs=15)
#       # No assertion — just documents what the real cost is
#       print(f"Recommended timeout: {result.recommended_limit():.3f}s")
#
# ---------------------------------------------------------------------------

@pytest.fixture
def benchmark():
    """
    Pytest fixture: measure execution time of a callable.

    Returns a callable that accepts (fn, runs=10, label=None) and returns
    a BenchmarkResult with P50/P95/P99 and recommendation helpers.

    Example:
        def test_something_fast(benchmark):
            result = benchmark(lambda: my_fn(), runs=20)
            result.assert_p99_under(0.1)
    """
    from test_utils import Benchmarker

    def _run(fn: Callable, runs: int = 10, label: Optional[str] = None):
        return Benchmarker(fn, runs=runs, label=label).run()

    return _run
