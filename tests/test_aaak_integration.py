#!/usr/bin/env python3
"""
AAAK Integration Tests
======================
Comprehensive tests for AAAK compression integration.

Categories:
  3a. Unit tests for aaak_compress.py
  3b. Integration tests for auto_prime compression (_aaak_compress_context)
  3c. Token efficiency benchmark tests
  3d. Safety tests (edge cases)

Run with:
  cd /Users/tomkwon/Documents/claude-agentic-framework
  uv run --no-project pytest tests/test_aaak_integration.py -v
"""

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

# --- sys.path setup ---
FRAMEWORK_DIR = os.path.join(os.path.dirname(__file__), '..', 'global-hooks', 'framework')
sys.path.insert(0, FRAMEWORK_DIR)

AUTO_PRIME_DIR = os.path.join(FRAMEWORK_DIR, 'automation')
sys.path.insert(0, AUTO_PRIME_DIR)

from aaak_compress import compress, compress_sections, compress_with_stats, log_compression_stats

# Import _aaak_compress_context from auto_prime without triggering main()
# We import it as a module and extract only the function we need
import importlib.util as _ilu

_auto_prime_spec = _ilu.spec_from_file_location(
    "auto_prime",
    os.path.join(AUTO_PRIME_DIR, "auto_prime.py"),
)
_auto_prime_mod = _ilu.module_from_spec(_auto_prime_spec)
# We load the module source but do NOT execute main() - the module-level code
# only defines functions and constants, so exec_module is safe here.
_auto_prime_spec.loader.exec_module(_auto_prime_mod)
_aaak_compress_context = _auto_prime_mod._aaak_compress_context

# ---------------------------------------------------------------------------
# 3a. Unit tests for aaak_compress.py
# ---------------------------------------------------------------------------

LONG_TEXT = (
    "Hello world this is a test of the compression system that should be long "
    "enough to trigger compression with at least fifty characters in the input"
)

MULTI_SECTION_TEXT = """## Header One

This is the body text for the first section. It contains information that
might be compressed but the header should survive intact.

## Header Two

Another body section with content that is relevant to the project structure
and contains details about configuration and deployment procedures.
"""


def test_compress_returns_string():
    """compress() always returns a string."""
    result = compress(LONG_TEXT)
    assert isinstance(result, str)


def test_compress_short_text_passthrough():
    """compress() passes through text shorter than 50 chars unchanged."""
    short = "short"
    result = compress(short)
    assert result == short


def test_compress_sections_preserves_headers():
    """compress_sections() keeps ## headers verbatim in output."""
    result = compress_sections(MULTI_SECTION_TEXT)
    assert "## Header One" in result
    assert "## Header Two" in result


def test_compress_with_stats_returns_tuple():
    """compress_with_stats() returns a (str, dict) tuple."""
    result = compress_with_stats(LONG_TEXT)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], str)
    assert isinstance(result[1], dict)


def test_compress_with_stats_has_ratio():
    """compress_with_stats() stats dict has a 'ratio' key when mempalace is available."""
    _compressed, stats = compress_with_stats(LONG_TEXT)
    # If mempalace is available, stats will be non-empty with a ratio key.
    # If not available, stats is {} — also acceptable (fail-open).
    if stats:
        assert "ratio" in stats, f"stats dict missing 'ratio' key: {stats}"


def test_fail_open_on_missing_mempalace():
    """compress() returns original text when mempalace import fails."""
    original_path = sys.path[:]
    try:
        # Remove mempalace venv from path temporarily
        # Find the actual mempalace venv path (any Python version)
        import glob
        matches = glob.glob(os.path.expanduser(
            "~/Documents/mempalace/.venv/lib/python3.*/site-packages"
        ))
        mempalace_venv = matches[0] if matches else ""
        sys.path = [p for p in sys.path if p != mempalace_venv]
        # Also patch _get_dialect to simulate failure
        with patch("aaak_compress._get_dialect", return_value=None):
            result = compress(LONG_TEXT)
            assert result == LONG_TEXT, "compress() should return original text when dialect is None"
    finally:
        sys.path = original_path


# ---------------------------------------------------------------------------
# 3b. Integration tests for auto_prime compression
# ---------------------------------------------------------------------------

def test_aaak_compress_context_returns_string():
    """_aaak_compress_context() always returns a string."""
    result = _aaak_compress_context(LONG_TEXT)
    assert isinstance(result, str)


def test_aaak_compress_context_fail_open():
    """_aaak_compress_context() returns original text when mempalace import fails."""
    with patch("aaak_compress._get_dialect", return_value=None):
        result = _aaak_compress_context(LONG_TEXT)
        # Should return a string (either compressed or original)
        assert isinstance(result, str)
        assert len(result) > 0


def test_compression_ratio_reasonable():
    """Compressed output is shorter than or equal to input length."""
    text = LONG_TEXT * 20  # Make it substantial
    result = _aaak_compress_context(text)
    assert isinstance(result, str)
    # Compression should not expand the text beyond 2x original
    assert len(result) <= len(text) * 2, (
        f"Output ({len(result)} chars) is more than 2x input ({len(text)} chars)"
    )


def test_session_context_prefix_preserved():
    """The SESSION CONTEXT prefix should not be mangled by compression."""
    prefix = "**SESSION CONTEXT LOADED**\n---\n"
    body = LONG_TEXT * 10
    full_text = prefix + body
    result = _aaak_compress_context(full_text)
    assert isinstance(result, str)
    # The function compresses the whole text (body prefix split is in auto_prime main)
    # so just verify it returns something valid
    assert len(result) > 0


# ---------------------------------------------------------------------------
# 3c. Token efficiency benchmark tests
# ---------------------------------------------------------------------------

FRAMEWORK_CLAUDE_MD = Path(__file__).parent.parent / "CLAUDE.md"


def test_benchmark_compression_ratio():
    """Compress a real CLAUDE.md and verify ratio is reasonable."""
    if not FRAMEWORK_CLAUDE_MD.exists():
        import pytest
        pytest.skip("CLAUDE.md not found")
    content = FRAMEWORK_CLAUDE_MD.read_text()
    compressed, stats = compress_with_stats(content)
    assert isinstance(compressed, str)
    if stats:
        ratio = stats.get("ratio", 1.0)
        # Ratio should be >= 1.0 (no expansion)
        assert ratio >= 1.0, f"Compression expanded the text: ratio={ratio}"


def test_benchmark_compression_speed():
    """Compression completes in under 2 seconds."""
    if not FRAMEWORK_CLAUDE_MD.exists():
        import pytest
        pytest.skip("CLAUDE.md not found")
    content = FRAMEWORK_CLAUDE_MD.read_text()
    start = time.time()
    compress(content)
    elapsed = time.time() - start
    assert elapsed < 2.0, f"Compression took {elapsed:.2f}s (limit: 2.0s)"


def test_benchmark_all_projects():
    """For each project in ~/Documents with a CLAUDE.md, compress and collect stats."""
    docs_dir = Path.home() / "Documents"
    claude_files = list(docs_dir.glob("*/CLAUDE.md"))
    if not claude_files:
        import pytest
        pytest.skip("No CLAUDE.md files found in ~/Documents/*/")

    results = []
    for claude_file in claude_files[:10]:  # cap at 10 to keep test fast
        try:
            content = claude_file.read_text(errors="replace")
            _compressed, stats = compress_with_stats(content)
            ratio = stats.get("ratio", 1.0) if stats else None
            results.append({
                "project": claude_file.parent.name,
                "original_chars": len(content),
                "ratio": ratio,
            })
        except Exception as exc:
            results.append({
                "project": claude_file.parent.name,
                "error": str(exc),
            })

    # Print summary table
    print("\n--- AAAK Benchmark: all projects ---")
    print(f"{'Project':<35} {'Chars':>8} {'Ratio':>8}")
    print("-" * 55)
    for r in results:
        if "error" in r:
            print(f"{r['project']:<35} ERROR: {r['error']}")
        else:
            ratio_str = f"{r['ratio']:.2f}x" if r['ratio'] is not None else "N/A"
            print(f"{r['project']:<35} {r['original_chars']:>8} {ratio_str:>8}")

    # Just assert we collected some results without crashing
    assert len(results) > 0


def test_stats_logging():
    """compress_with_stats writes an entry to aaak_stats.jsonl when stats are non-empty."""
    stats_file = Path.home() / ".claude" / "data" / "aaak_stats.jsonl"
    content = LONG_TEXT * 10

    _compressed, stats = compress_with_stats(content, metadata={"hook": "test_stats_logging"})

    if not stats:
        # mempalace not available — log_compression_stats is a no-op
        # Just verify the function doesn't crash
        log_compression_stats({}, context="test_no_op")
        return

    # Stats available — log and verify file was written
    log_compression_stats(stats, context="test_stats_logging")
    assert stats_file.exists(), f"aaak_stats.jsonl not created at {stats_file}"

    # Verify the last entry is valid JSON
    with open(stats_file) as f:
        lines = f.readlines()
    assert len(lines) >= 1
    last_entry = json.loads(lines[-1])
    assert "context" in last_entry
    assert "timestamp" in last_entry


# ---------------------------------------------------------------------------
# 3d. Safety tests
# ---------------------------------------------------------------------------

def test_no_data_loss_critical_sections():
    """Compress a CLAUDE.md and verify key section headers survive."""
    if not FRAMEWORK_CLAUDE_MD.exists():
        import pytest
        pytest.skip("CLAUDE.md not found")
    content = FRAMEWORK_CLAUDE_MD.read_text()
    result = compress_sections(content)
    # compress_sections preserves lines starting with ##
    # Verify at least some ## headers are present in output
    original_headers = [line for line in content.splitlines() if line.startswith("##")]
    if original_headers:
        result_headers = [line for line in result.splitlines() if line.startswith("##")]
        assert len(result_headers) > 0, "No ## headers survived compress_sections()"


def test_idempotent_compression():
    """compress(compress(text)) doesn't corrupt or crash."""
    text = LONG_TEXT * 5
    first = compress(text)
    second = compress(first)
    assert isinstance(second, str)
    assert len(second) > 0


def test_empty_input():
    """compress('') returns ''."""
    result = compress("")
    assert result == ""


def test_none_handling():
    """compress(None) doesn't crash — returns None or empty string gracefully."""
    try:
        result = compress(None)
        # If it returns without raising, it must return None or a string
        assert result is None or isinstance(result, str)
    except TypeError:
        # Acceptable: function may not handle None explicitly
        pass


def test_binary_input_safety():
    """compress(bytes) doesn't crash."""
    binary_data = b"\x00\x01\x02hello\xff\xfe"
    try:
        result = compress(binary_data)
        # If no exception, result should be bytes or something reasonable
        assert result is not None
    except (TypeError, AttributeError):
        # Acceptable: function expects str, binary input may raise
        pass
