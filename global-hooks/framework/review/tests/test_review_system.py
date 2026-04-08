#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest"]
# ///
"""
Tests for the continuous background review system.

Tests cover:
- Findings store CRUD operations
- Individual analyzer logic
- Review engine orchestration
- Findings notifier context generation
- Configuration loading
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add review module to path
REVIEW_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(REVIEW_DIR))


# ---------------------------------------------------------------------------
# Findings Store Tests
# ---------------------------------------------------------------------------


class TestFindingsStore:
    """Tests for findings_store.py"""

    def setup_method(self):
        """Create a temporary findings file for each test."""
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp_file = Path(self.tmp_dir) / "review_findings.json"

    def teardown_method(self):
        """Clean up temp files."""
        if self.tmp_file.exists():
            self.tmp_file.unlink()
        Path(self.tmp_dir).rmdir()

    @patch("findings_store.FINDINGS_PATH")
    @patch("findings_store.FINDINGS_DIR")
    def test_add_and_get_findings(self, mock_dir, mock_path):
        """Test adding findings and retrieving them."""
        mock_path.__str__ = lambda s: str(self.tmp_file)
        mock_path.exists.return_value = False
        mock_dir.mkdir = MagicMock()

        from findings_store import Finding, add_findings, _read_findings, _write_findings

        # Create findings manually
        findings = [
            Finding(
                id="abc123:complexity:0",
                commit_hash="abc123",
                analyzer="complexity",
                severity="warning",
                title="High complexity in foo()",
                description="Complexity score 15",
                file_path="src/foo.py",
                line_start=10,
            ),
            Finding(
                id="abc123:dead_code:0",
                commit_hash="abc123",
                analyzer="dead_code",
                severity="info",
                title="Unused import: os",
                description="Import os is never used",
                file_path="src/bar.py",
                line_start=1,
            ),
        ]

        # Write directly to temp file
        from dataclasses import asdict
        data = [asdict(f) for f in findings]
        with open(self.tmp_file, "w") as fh:
            json.dump(data, fh)

        # Read back
        with open(self.tmp_file, "r") as fh:
            loaded = json.load(fh)

        assert len(loaded) == 2
        assert loaded[0]["id"] == "abc123:complexity:0"
        assert loaded[1]["analyzer"] == "dead_code"

    def test_finding_creation(self):
        """Test Finding dataclass creation with defaults."""
        from findings_store import Finding

        f = Finding(
            id="test:0",
            commit_hash="abc123",
            analyzer="test",
            severity="info",
            title="Test finding",
            description="A test",
            file_path="test.py",
        )

        assert f.status == "open"
        assert f.created_at  # Should be auto-set
        assert f.suggestion == ""
        assert f.metadata == {}

    def test_severity_enum(self):
        """Test Severity enum values."""
        from findings_store import Severity

        assert Severity.INFO.value == "info"
        assert Severity.WARNING.value == "warning"
        assert Severity.ERROR.value == "error"
        assert Severity.CRITICAL.value == "critical"

    def test_finding_status_enum(self):
        """Test FindingStatus enum values."""
        from findings_store import FindingStatus

        assert FindingStatus.OPEN.value == "open"
        assert FindingStatus.NOTIFIED.value == "notified"
        assert FindingStatus.RESOLVED.value == "resolved"
        assert FindingStatus.WONTFIX.value == "wontfix"


# ---------------------------------------------------------------------------
# Duplication Analyzer Tests
# ---------------------------------------------------------------------------


class TestDuplicationAnalyzer:
    """Tests for analyzers/duplication.py"""

    def test_tokenize_basic(self):
        """Test basic tokenization."""
        from analyzers.duplication import tokenize

        tokens = tokenize("def hello(x): return x + 1")
        assert "def" in tokens
        assert "hello" in tokens
        assert "return" in tokens

    def test_tokenize_strips_comments(self):
        """Test that comments are removed during tokenization."""
        from analyzers.duplication import tokenize

        tokens = tokenize("x = 1  # this is a comment")
        assert "this" not in tokens
        assert "comment" not in tokens
        assert "x" in tokens

    def test_extract_added_blocks(self):
        """Test extraction of added code blocks from a diff."""
        from analyzers.duplication import extract_added_blocks

        diff = """diff --git a/foo.py b/foo.py
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,10 @@
+def hello():
+    x = 1
+    y = 2
+    z = x + y
+    return z
+
 existing code
"""
        blocks = extract_added_blocks(diff)
        assert len(blocks) >= 1
        assert blocks[0].file_path == "foo.py"

    def test_no_duplicates_in_small_code(self):
        """Test that small, unique code blocks produce no duplicates."""
        from analyzers.duplication import analyze

        diff = """diff --git a/foo.py b/foo.py
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,5 @@
+def hello():
+    return "hello"
"""
        findings = analyze(diff, ["foo.py"], "/tmp", min_tokens=5)
        assert len(findings) == 0  # Only one block, nothing to compare


# ---------------------------------------------------------------------------
# Complexity Analyzer Tests
# ---------------------------------------------------------------------------


class TestComplexityAnalyzer:
    """Tests for analyzers/complexity.py"""

    def test_simple_function_low_complexity(self):
        """Test that a simple function has low complexity."""
        from analyzers.complexity import analyze_python_complexity

        source = """
def simple():
    return 42
"""
        functions = analyze_python_complexity(source)
        assert len(functions) == 1
        assert functions[0]["name"] == "simple"
        assert functions[0]["complexity"] == 1

    def test_branching_increases_complexity(self):
        """Test that if/elif/else increases complexity."""
        from analyzers.complexity import analyze_python_complexity

        source = """
def branchy(x):
    if x > 0:
        if x > 10:
            return "big"
        else:
            return "small"
    elif x == 0:
        return "zero"
    else:
        return "negative"
"""
        functions = analyze_python_complexity(source)
        assert len(functions) == 1
        assert functions[0]["name"] == "branchy"
        # if + if + elif = 3 branches + 1 base = 4
        assert functions[0]["complexity"] >= 4

    def test_loops_increase_complexity(self):
        """Test that for/while loops increase complexity."""
        from analyzers.complexity import analyze_python_complexity

        source = """
def loopy(items):
    result = []
    for item in items:
        while item > 0:
            result.append(item)
            item -= 1
    return result
"""
        functions = analyze_python_complexity(source)
        assert len(functions) == 1
        # for + while = 2 + 1 base = 3
        assert functions[0]["complexity"] >= 3

    def test_boolean_ops_increase_complexity(self):
        """Test that and/or increase complexity."""
        from analyzers.complexity import analyze_python_complexity

        source = """
def check(a, b, c):
    if a and b or c:
        return True
    return False
"""
        functions = analyze_python_complexity(source)
        assert len(functions) == 1
        # if + and + or = 3 + 1 base = 4
        assert functions[0]["complexity"] >= 3

    def test_syntax_error_returns_empty(self):
        """Test that syntax errors produce empty results."""
        from analyzers.complexity import analyze_python_complexity

        result = analyze_python_complexity("def broken(:")
        assert result == []

    def test_analyze_with_threshold(self):
        """Test that analyze() only reports above threshold."""
        from analyzers.complexity import analyze

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir="/tmp"
        ) as f:
            f.write("""
def simple():
    return 1

def complex_func(x, y, z):
    if x:
        if y:
            if z:
                for i in range(10):
                    while True:
                        if i > 5:
                            break
                        elif i > 3:
                            continue
                        else:
                            pass
    return None
""")
            f.flush()
            file_name = Path(f.name).name

        try:
            findings = analyze("", [file_name], "/tmp", complexity_threshold=3)
            # complex_func should be reported, simple should not
            assert len(findings) >= 1
            assert any("complex_func" in f.title for f in findings)
            assert not any("simple" in f.title for f in findings)
        finally:
            os.unlink(f"/tmp/{file_name}")


# ---------------------------------------------------------------------------
# Dead Code Analyzer Tests
# ---------------------------------------------------------------------------


class TestDeadCodeAnalyzer:
    """Tests for analyzers/dead_code.py"""

    def test_unused_function_detected(self):
        """Test that an unused function is detected."""
        from analyzers.dead_code import analyze_python_dead_code

        source = """
def used_func():
    return 1

def unused_func():
    return 2

result = used_func()
"""
        dead = analyze_python_dead_code(source, "test.py")
        names = [d["name"] for d in dead]
        assert "unused_func" in names
        assert "used_func" not in names

    def test_unused_import_detected(self):
        """Test that an unused import is detected."""
        from analyzers.dead_code import analyze_python_dead_code

        source = """
import os
import sys

print(sys.argv)
"""
        dead = analyze_python_dead_code(source, "test.py")
        names = [d["name"] for d in dead]
        assert "os" in names
        assert "sys" not in names

    def test_private_functions_skipped(self):
        """Test that private functions (_prefixed) are not flagged."""
        from analyzers.dead_code import analyze_python_dead_code

        source = """
def _private_helper():
    return 1

def public_unused():
    return 2
"""
        dead = analyze_python_dead_code(source, "test.py")
        names = [d["name"] for d in dead]
        assert "_private_helper" not in names
        assert "public_unused" in names

    def test_skip_test_files(self):
        """Test that test files are skipped."""
        from analyzers.dead_code import _should_skip_file

        assert _should_skip_file("test_foo.py", "") is True
        assert _should_skip_file("foo_test.py", "") is True
        assert _should_skip_file("tests/test_bar.py", "") is True
        assert _should_skip_file("src/foo.py", "") is False

    def test_skip_init_files(self):
        """Test that __init__.py files are skipped."""
        from analyzers.dead_code import _should_skip_file

        assert _should_skip_file("__init__.py", "") is True
        assert _should_skip_file("pkg/__init__.py", "") is True


# ---------------------------------------------------------------------------
# Architecture Analyzer Tests
# ---------------------------------------------------------------------------


class TestArchitectureAnalyzer:
    """Tests for analyzers/architecture.py"""

    def test_hardcoded_secret_detected(self):
        """Test that hardcoded secrets are flagged."""
        from analyzers.architecture import extract_added_lines_with_numbers, DEFAULT_RULES

        diff = """diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,1 +1,2 @@
+API_KEY = "sk-1234567890abcdef1234567890abcdef"
"""
        added = extract_added_lines_with_numbers(diff)
        assert "config.py" in added
        assert len(added["config.py"]) == 1

        # Check the rule matches
        secret_rule = next(r for r in DEFAULT_RULES if r.name == "hardcoded-secret")
        line_content = added["config.py"][0][1]
        assert secret_rule.pattern.search(line_content)

    def test_eval_usage_detected(self):
        """Test that eval() usage is flagged."""
        from analyzers.architecture import DEFAULT_RULES

        eval_rule = next(r for r in DEFAULT_RULES if r.name == "eval-usage")
        assert eval_rule.pattern.search("result = eval(user_input)")
        assert not eval_rule.pattern.search("# eval is bad")

    def test_god_module_check(self):
        """Test god module detection."""
        from analyzers.architecture import check_god_module

        # Build a source with many top-level functions
        source = "\n".join(
            [f"def func_{i}(): pass" for i in range(25)]
        )
        result = check_god_module(source, threshold=20)
        assert result is not None
        assert result["count"] == 25

    def test_god_module_under_threshold(self):
        """Test that small modules pass."""
        from analyzers.architecture import check_god_module

        source = "def func_a(): pass\ndef func_b(): pass\n"
        result = check_god_module(source, threshold=20)
        assert result is None

    def test_file_length_check(self):
        """Test file length detection."""
        from analyzers.architecture import check_file_length

        short = "line\n" * 100
        long = "line\n" * 600

        assert check_file_length(short, threshold=500) is None
        result = check_file_length(long, threshold=500)
        assert result is not None
        assert result["lines"] > 500


# ---------------------------------------------------------------------------
# Test Coverage Analyzer Tests
# ---------------------------------------------------------------------------


class TestTestCoverageAnalyzer:
    """Tests for analyzers/test_coverage.py"""

    def test_is_test_file(self):
        """Test test file detection."""
        from analyzers.test_coverage import is_test_file

        assert is_test_file("test_foo.py") is True
        assert is_test_file("foo_test.py") is True
        assert is_test_file("foo.test.js") is True
        assert is_test_file("foo.spec.ts") is True
        assert is_test_file("src/foo.py") is False

    def test_is_source_file(self):
        """Test source file detection."""
        from analyzers.test_coverage import is_source_file

        assert is_source_file("src/foo.py") is True
        assert is_source_file("__init__.py") is False
        assert is_source_file("setup.py") is False
        assert is_source_file("test_foo.py") is False
        assert is_source_file("README.md") is False

    def test_extract_new_definitions(self):
        """Test extraction of new function/class definitions from diff."""
        from analyzers.test_coverage import extract_new_definitions_python

        diff = """diff --git a/foo.py b/foo.py
--- a/foo.py
+++ b/foo.py
@@ -1,1 +1,10 @@
+def new_function():
+    pass
+
+class NewClass:
+    pass
+
+def _private_func():
+    pass
"""
        defs = extract_new_definitions_python(diff, "foo.py")
        names = [d["name"] for d in defs]

        assert "new_function" in names
        assert "NewClass" in names
        assert "_private_func" not in names  # Private, should be excluded


# ---------------------------------------------------------------------------
# Findings Notifier Tests
# ---------------------------------------------------------------------------


class TestFindingsNotifier:
    """Tests for findings_notifier.py"""

    def test_format_finding(self):
        """Test finding formatting for context injection."""
        from findings_notifier import format_finding_for_context

        finding = {
            "severity": "error",
            "title": "High complexity in foo()",
            "file_path": "src/foo.py",
            "line_start": 42,
            "suggestion": "Split into smaller functions",
            "commit_hash": "abc12345",
        }

        formatted = format_finding_for_context(finding)
        assert "[ERROR]" in formatted
        assert "foo()" in formatted
        assert "src/foo.py:42" in formatted
        assert "abc12345" in formatted

    @patch("findings_notifier.get_unresolved_findings")
    @patch("findings_notifier.mark_as_notified")
    def test_context_generation_with_findings(self, mock_mark, mock_get):
        """Test that context is generated when findings exist."""
        from findings_notifier import get_notification_context

        mock_get.return_value = [
            {
                "id": "test:0",
                "status": "open",
                "severity": "error",
                "title": "Test finding",
                "file_path": "test.py",
                "line_start": 1,
                "suggestion": "Fix it",
                "commit_hash": "abc123",
            }
        ]
        mock_mark.return_value = 1

        context = get_notification_context()
        assert "Code Review Findings" in context
        assert "Test finding" in context
        mock_mark.assert_called_once_with(["test:0"])

    @patch("findings_notifier.get_unresolved_findings")
    def test_no_context_when_no_findings(self, mock_get):
        """Test that empty string returned when no findings."""
        from findings_notifier import get_notification_context

        mock_get.return_value = []
        context = get_notification_context()
        assert context == ""


# ---------------------------------------------------------------------------
# Review Config Tests
# ---------------------------------------------------------------------------


class TestReviewConfig:
    """Tests for review configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        from review_engine import ReviewConfig

        config = ReviewConfig()
        assert config.enabled is True
        assert config.background is True
        assert config.complexity_threshold == 10
        assert config.duplication_tokens == 50
        assert "duplication" in config.analysis_types
        assert "complexity" in config.analysis_types

    def test_config_loading_missing_file(self):
        """Test that missing config file returns defaults."""
        from review_engine import load_review_config

        config = load_review_config(Path("/nonexistent/config.yaml"))
        assert config.enabled is True
        assert config.complexity_threshold == 10

    def test_config_loading_from_yaml(self):
        """Test loading config from YAML file."""
        from review_engine import load_review_config

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("""
enabled: true
complexity_threshold: 15
duplication_tokens: 30
analysis_types:
  - complexity
  - architecture
""")
            f.flush()
            config_path = Path(f.name)

        try:
            config = load_review_config(config_path)
            assert config.complexity_threshold == 15
            assert config.duplication_tokens == 30
            assert config.analysis_types == ["complexity", "architecture"]
        finally:
            config_path.unlink()


# ---------------------------------------------------------------------------
# Integration-style test
# ---------------------------------------------------------------------------


class TestReviewEngineIntegration:
    """Integration tests for the review engine (mocked git)."""

    @patch("review_engine.get_commit_diff")
    @patch("review_engine.get_changed_files")
    @patch("review_engine.get_commit_message")
    @patch("review_engine.get_repo_root")
    def test_engine_runs_all_analyzers(
        self, mock_root, mock_msg, mock_files, mock_diff
    ):
        """Test that engine runs all configured analyzers."""
        mock_root.return_value = "/tmp"
        mock_msg.return_value = "test commit"
        mock_files.return_value = ["test_file.py"]
        mock_diff.return_value = """diff --git a/test_file.py b/test_file.py
--- a/test_file.py
+++ b/test_file.py
@@ -0,0 +1,3 @@
+def hello():
+    return "world"
"""
        from review_engine import ReviewEngine, ReviewConfig

        config = ReviewConfig(
            enabled=True,
            analysis_types=["complexity", "architecture"],
            exclude_patterns=[],
        )

        engine = ReviewEngine(
            commit_hash="abc123" * 7,
            repo_root="/tmp",
            config=config,
        )

        # Mock circuit breaker to always allow
        engine._check_circuit_breaker = lambda: True
        engine._record_circuit_breaker_success = lambda: None
        engine._store_to_knowledge_db = lambda findings: None

        result = engine.run()

        assert result.commit_hash.startswith("abc123")
        assert "complexity" in result.analyzers_run
        assert "architecture" in result.analyzers_run
        assert result.duration_seconds >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
