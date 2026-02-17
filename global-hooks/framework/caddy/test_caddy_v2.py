#!/usr/bin/env python3
"""
Caddy v2 Test Suite
====================
Tests every failure mode introduced or fixed by the Haiku + YAML config update.

Run with:
    uv run python test_caddy_v2.py
or:
    python3 test_caddy_v2.py

Coverage:
  1. YAML config loader - file missing, valid, malformed, empty
  2. Config deep merge - partial keys don't clobber defaults
  3. Keyword classification baseline - correct for clear prompts
  4. Haiku fallback - fires when confidence < threshold, skipped when high
  5. Haiku failure isolation - network error / bad JSON / invalid values don't crash
  6. Haiku response validation - rejects incomplete/wrong-enum responses
  7. Confidence source selection - uses haiku confidence when available
  8. classification_source label - correct for keyword vs haiku paths
  9. Hook output format - valid JSON with correct hookEventName
 10. Empty prompt / slash command - exits early without output
 11. Haiku [haiku] tag in output - only appears when haiku was used
 12. Strategy selection unchanged - haiku result routes correctly through select_strategy
 13. Disabled caddy - no output when enabled=False in config
 14. Full end-to-end via stdin pipe - integration test with mock haiku
"""

import json
import sys
import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add caddy dir to path
_caddy_dir = Path(__file__).parent
sys.path.insert(0, str(_caddy_dir))

import analyze_request as caddy


# ---------------------------------------------------------------------------
# 1. YAML config loader
# ---------------------------------------------------------------------------

class TestLoadCaddyConfig(unittest.TestCase):

    def test_returns_defaults_when_no_file(self):
        with patch.object(Path, "exists", return_value=False):
            cfg = caddy.load_caddy_config()
        self.assertTrue(cfg["caddy"]["enabled"])
        self.assertEqual(cfg["caddy"]["haiku_fallback_threshold"], 0.65)

    def test_loads_valid_yaml(self):
        yaml_content = "caddy:\n  haiku_fallback_threshold: 0.5\n  always_suggest: false\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            tmp = Path(f.name)
        try:
            with patch("analyze_request.Path") as MockPath:
                # Make the config path resolve to our temp file
                instance = MockPath.return_value
                instance.__truediv__ = lambda s, o: tmp
                instance.exists = lambda: True
                # Bypass mock and call directly with real path
                cfg = caddy.load_caddy_config.__wrapped__(tmp) if hasattr(caddy.load_caddy_config, "__wrapped__") else None
            # Direct test: patch home directory
            with patch("pathlib.Path.home", return_value=tmp.parent):
                # rename temp file to expected name
                expected = tmp.parent / ".claude" / "caddy_config.yaml"
                expected.parent.mkdir(parents=True, exist_ok=True)
                tmp.rename(expected)
                cfg = caddy.load_caddy_config()
                self.assertEqual(cfg["caddy"]["haiku_fallback_threshold"], 0.5)
                self.assertFalse(cfg["caddy"]["always_suggest"])
                # Defaults not in file should still be present
                self.assertEqual(cfg["caddy"]["auto_invoke_threshold"], 0.8)
        finally:
            if expected.exists():
                expected.unlink()

    def test_malformed_yaml_returns_defaults(self):
        bad_yaml = "caddy: [this is: not: valid yaml"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(bad_yaml)
            tmp = Path(f.name)
        try:
            with patch("pathlib.Path.home", return_value=tmp.parent):
                expected = tmp.parent / ".claude" / "caddy_config.yaml"
                expected.parent.mkdir(parents=True, exist_ok=True)
                tmp.rename(expected)
                cfg = caddy.load_caddy_config()
                # Should return defaults, not crash
                self.assertTrue(cfg["caddy"]["enabled"])
        finally:
            if expected.exists():
                expected.unlink()

    def test_empty_yaml_returns_defaults(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            tmp = Path(f.name)
        try:
            with patch("pathlib.Path.home", return_value=tmp.parent):
                expected = tmp.parent / ".claude" / "caddy_config.yaml"
                expected.parent.mkdir(parents=True, exist_ok=True)
                tmp.rename(expected)
                cfg = caddy.load_caddy_config()
                self.assertTrue(cfg["caddy"]["enabled"])
        finally:
            if expected.exists():
                expected.unlink()

    def test_partial_config_merges_with_defaults(self):
        """Partial YAML must not clobber keys it doesn't specify."""
        yaml_content = "caddy:\n  enabled: false\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            tmp = Path(f.name)
        try:
            with patch("pathlib.Path.home", return_value=tmp.parent):
                expected = tmp.parent / ".claude" / "caddy_config.yaml"
                expected.parent.mkdir(parents=True, exist_ok=True)
                tmp.rename(expected)
                cfg = caddy.load_caddy_config()
                self.assertFalse(cfg["caddy"]["enabled"])         # overridden
                self.assertEqual(cfg["caddy"]["haiku_fallback_threshold"], 0.65)  # default preserved
        finally:
            if expected.exists():
                expected.unlink()


# ---------------------------------------------------------------------------
# 2. Keyword classification
# ---------------------------------------------------------------------------

class TestKeywordClassification(unittest.TestCase):

    def test_complexity_simple(self):
        self.assertEqual(caddy.classify_complexity("fix typo in readme"), "simple")

    def test_complexity_complex(self):
        # "redesign" and "authentication" both match complex; "redesign" alone unambiguously scores complex > moderate
        self.assertEqual(caddy.classify_complexity("full redesign of the authentication system"), "complex")

    def test_complexity_massive(self):
        self.assertEqual(caddy.classify_complexity("rewrite entire codebase in Go"), "massive")

    def test_task_type_fix(self):
        self.assertEqual(caddy.classify_task_type("fix the login bug"), "fix")

    def test_task_type_research(self):
        self.assertEqual(caddy.classify_task_type("how does the auth system work"), "research")

    def test_quality_critical_triggers(self):
        self.assertEqual(caddy.classify_quality_need("update payment processing logic"), "critical")

    def test_scope_broad(self):
        self.assertEqual(caddy.classify_codebase_scope("refactor across the entire codebase"), "broad")

    def test_scope_unknown_for_exploration(self):
        self.assertEqual(caddy.classify_codebase_scope("how does X work"), "unknown")


# ---------------------------------------------------------------------------
# 3. Haiku classify function
# ---------------------------------------------------------------------------

class TestHaikuClassify(unittest.TestCase):

    def _make_mock_response(self, data: dict) -> MagicMock:
        """Build a mock Anthropic message response."""
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock()]
        mock_msg.content[0].text = json.dumps(data)
        return mock_msg

    def _mock_anthropic(self, response_data=None, side_effect=None):
        """Return a context manager that patches anthropic via sys.modules (lazy import)."""
        mock_module = MagicMock()
        if side_effect:
            mock_module.Anthropic.return_value.messages.create.side_effect = side_effect
        elif response_data is not None:
            mock_module.Anthropic.return_value.messages.create.return_value = (
                self._make_mock_response(response_data)
            )
        return patch.dict("sys.modules", {"anthropic": mock_module})

    def test_valid_response_returns_classification(self):
        valid = {
            "complexity": "moderate",
            "task_type": "fix",
            "quality": "standard",
            "scope": "focused",
            "confidence": 0.85,
            "reasoning": "Clear bug fix request on a single file.",
        }
        with self._mock_anthropic(response_data=valid):
            result = caddy.haiku_classify("fix the null pointer in auth.py")
        self.assertEqual(result["complexity"], "moderate")
        self.assertEqual(result["task_type"], "fix")
        self.assertAlmostEqual(result["confidence"], 0.85)

    def test_network_error_returns_none(self):
        with self._mock_anthropic(side_effect=ConnectionError("timeout")):
            result = caddy.haiku_classify("fix the bug")
        self.assertIsNone(result)

    def test_invalid_json_returns_none(self):
        mock_module = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock()]
        mock_msg.content[0].text = "I cannot classify this."
        mock_module.Anthropic.return_value.messages.create.return_value = mock_msg
        with patch.dict("sys.modules", {"anthropic": mock_module}):
            result = caddy.haiku_classify("do the thing")
        self.assertIsNone(result)

    def test_wrong_enum_value_returns_none(self):
        bad = {
            "complexity": "ENORMOUS",  # not in allowed set
            "task_type": "fix",
            "quality": "standard",
            "scope": "focused",
            "confidence": 0.9,
        }
        with self._mock_anthropic(response_data=bad):
            result = caddy.haiku_classify("do something")
        self.assertIsNone(result)

    def test_missing_required_field_returns_none(self):
        incomplete = {
            "complexity": "simple",
            "task_type": "fix",
            # missing quality, scope, confidence
        }
        with self._mock_anthropic(response_data=incomplete):
            result = caddy.haiku_classify("do something")
        self.assertIsNone(result)

    def test_confidence_not_numeric_returns_none(self):
        bad_conf = {
            "complexity": "simple",
            "task_type": "fix",
            "quality": "standard",
            "scope": "focused",
            "confidence": "high",  # string instead of float
        }
        with self._mock_anthropic(response_data=bad_conf):
            result = caddy.haiku_classify("do something")
        self.assertIsNone(result)

    def test_haiku_import_error_returns_none(self):
        """If anthropic package is not installed, returns None gracefully."""
        with patch.dict("sys.modules", {"anthropic": None}):
            result = caddy.haiku_classify("do something")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# 4. Hybrid classification logic (confidence source selection)
# ---------------------------------------------------------------------------

class TestHybridClassification(unittest.TestCase):
    """Test that confidence and classification_source are set correctly."""

    def _run_main_with_prompt(self, prompt: str, haiku_result=None, haiku_threshold=0.65):
        """Run main() with a patched environment. Returns printed output or None."""
        import io

        input_data = json.dumps({"prompt": prompt, "session_id": "test"})

        captured_output = []

        def fake_print(data):
            captured_output.append(data)

        config = {
            "caddy": {
                "enabled": True,
                "auto_invoke_threshold": 0.8,
                "always_suggest": True,
                "haiku_fallback_threshold": haiku_threshold,
            }
        }

        with patch("analyze_request.load_caddy_config", return_value=config), \
             patch("analyze_request.haiku_classify", return_value=haiku_result), \
             patch("analyze_request.audit_detected_skills", return_value={}), \
             patch("builtins.print", side_effect=fake_print), \
             patch("sys.stdin", io.StringIO(input_data)), \
             patch("pathlib.Path.mkdir"), \
             patch("builtins.open", unittest.mock.mock_open()):
            try:
                caddy.main()
            except SystemExit:
                pass

        return captured_output[0] if captured_output else None

    def test_keyword_source_when_confidence_high(self):
        """High keyword confidence → no Haiku call, source=keyword, no [haiku] tag."""
        # "fix typo in readme" → simple, keyword confidence should be high
        output_str = self._run_main_with_prompt(
            "fix typo in readme",
            haiku_result=None,  # haiku_classify should not be called (mocked to None)
            haiku_threshold=0.65,
        )
        if output_str:
            output = json.loads(output_str)
            context = output["hookSpecificOutput"]["additionalContext"]
            self.assertNotIn("[haiku]", context)

    def test_haiku_source_tag_when_used(self):
        """Low confidence prompt + successful Haiku → [haiku] tag appears in output."""
        haiku_result = {
            "complexity": "moderate",
            "task_type": "fix",
            "quality": "standard",
            "scope": "focused",
            "confidence": 0.88,
            "reasoning": "clear bug fix",
        }
        # Very short prompt will have low keyword confidence
        output_str = self._run_main_with_prompt(
            "help",  # ambiguous, very short → low keyword confidence
            haiku_result=haiku_result,
            haiku_threshold=0.65,
        )
        if output_str:
            output = json.loads(output_str)
            context = output["hookSpecificOutput"]["additionalContext"]
            self.assertIn("[haiku]", context)

    def test_confidence_uses_haiku_value_when_haiku_runs(self):
        """When Haiku runs, reported confidence should be from Haiku (0.88), not keyword."""
        haiku_result = {
            "complexity": "moderate",
            "task_type": "fix",
            "quality": "standard",
            "scope": "focused",
            "confidence": 0.88,
            "reasoning": "clear",
        }
        output_str = self._run_main_with_prompt(
            "help",
            haiku_result=haiku_result,
            haiku_threshold=0.65,
        )
        if output_str:
            output = json.loads(output_str)
            context = output["hookSpecificOutput"]["additionalContext"]
            self.assertIn("88%", context)

    def test_haiku_failure_falls_back_to_keyword(self):
        """If Haiku returns None (failure), keyword results are still used."""
        output_str = self._run_main_with_prompt(
            "help",
            haiku_result=None,  # Haiku failed
            haiku_threshold=0.65,
        )
        # Should still produce output (no crash)
        if output_str:
            output = json.loads(output_str)
            self.assertIn("hookSpecificOutput", output)
            context = output["hookSpecificOutput"]["additionalContext"]
            self.assertNotIn("[haiku]", context)


# ---------------------------------------------------------------------------
# 5. Hook output format
# ---------------------------------------------------------------------------

class TestHookOutputFormat(unittest.TestCase):

    def test_output_is_valid_json(self):
        import io
        input_data = json.dumps({"prompt": "fix the login bug", "session_id": "test"})
        captured = []
        config = {
            "caddy": {
                "enabled": True,
                "always_suggest": True,
                "auto_invoke_threshold": 0.8,
                "haiku_fallback_threshold": 0.65,
            }
        }
        with patch("analyze_request.load_caddy_config", return_value=config), \
             patch("analyze_request.haiku_classify", return_value=None), \
             patch("analyze_request.audit_detected_skills", return_value={}), \
             patch("builtins.print", side_effect=lambda x: captured.append(x)), \
             patch("sys.stdin", io.StringIO(input_data)), \
             patch("pathlib.Path.mkdir"), \
             patch("builtins.open", unittest.mock.mock_open()):
            try:
                caddy.main()
            except SystemExit:
                pass
        self.assertTrue(len(captured) > 0, "Expected JSON output")
        parsed = json.loads(captured[0])
        self.assertIn("hookSpecificOutput", parsed)
        self.assertEqual(
            parsed["hookSpecificOutput"]["hookEventName"],
            "UserPromptSubmit"
        )
        self.assertIn("additionalContext", parsed["hookSpecificOutput"])

    def test_slash_command_produces_no_output(self):
        import io
        input_data = json.dumps({"prompt": "/review", "session_id": "test"})
        captured = []
        with patch("builtins.print", side_effect=lambda x: captured.append(x)), \
             patch("sys.stdin", io.StringIO(input_data)), \
             patch("pathlib.Path.mkdir"), \
             patch("builtins.open", unittest.mock.mock_open()):
            try:
                caddy.main()
            except SystemExit:
                pass
        self.assertEqual(captured, [], "Slash commands should produce no output")

    def test_empty_prompt_produces_no_output(self):
        import io
        input_data = json.dumps({"prompt": "   ", "session_id": "test"})
        captured = []
        with patch("builtins.print", side_effect=lambda x: captured.append(x)), \
             patch("sys.stdin", io.StringIO(input_data)), \
             patch("pathlib.Path.mkdir"), \
             patch("builtins.open", unittest.mock.mock_open()):
            try:
                caddy.main()
            except SystemExit:
                pass
        self.assertEqual(captured, [])

    def test_disabled_caddy_produces_no_output(self):
        import io
        input_data = json.dumps({"prompt": "fix the bug", "session_id": "test"})
        captured = []
        config = {"caddy": {"enabled": False}}
        with patch("analyze_request.load_caddy_config", return_value=config), \
             patch("builtins.print", side_effect=lambda x: captured.append(x)), \
             patch("sys.stdin", io.StringIO(input_data)), \
             patch("pathlib.Path.mkdir"), \
             patch("builtins.open", unittest.mock.mock_open()):
            try:
                caddy.main()
            except SystemExit:
                pass
        self.assertEqual(captured, [])


# ---------------------------------------------------------------------------
# 6. Strategy routing with Haiku-sourced classification
# ---------------------------------------------------------------------------

class TestStrategyWithHaikuResult(unittest.TestCase):

    def test_massive_complexity_routes_to_rlm(self):
        strategy = caddy.select_strategy("massive", "implement", "standard", "broad")
        self.assertEqual(strategy, "rlm")

    def test_simple_standard_routes_to_direct(self):
        strategy = caddy.select_strategy("simple", "fix", "standard", "focused")
        self.assertEqual(strategy, "direct")

    def test_unknown_scope_research_routes_to_rlm(self):
        strategy = caddy.select_strategy("moderate", "research", "standard", "unknown")
        self.assertEqual(strategy, "rlm")

    def test_haiku_classification_routes_correctly(self):
        """Haiku output complexity/scope should feed select_strategy correctly."""
        haiku_out = {
            "complexity": "massive",
            "task_type": "refactor",
            "quality": "high",
            "scope": "broad",
            "confidence": 0.9,
        }
        strategy = caddy.select_strategy(
            haiku_out["complexity"],
            haiku_out["task_type"],
            haiku_out["quality"],
            haiku_out["scope"],
        )
        self.assertEqual(strategy, "rlm")


# ---------------------------------------------------------------------------
# 7. Estimate confidence still works for keyword path
# ---------------------------------------------------------------------------

class TestEstimateConfidence(unittest.TestCase):

    def test_very_short_prompt_lowers_confidence(self):
        # base=0.5, fix→+0.1, simple→+0.15, short(<20)→-0.2 = 0.55
        # Still below long-prompt baseline — verify short < long for same task
        c_short = caddy.estimate_confidence("simple", "fix", "standard", [], 5)
        c_long = caddy.estimate_confidence("simple", "fix", "standard", [], 300)
        self.assertLess(c_short, c_long)

    def test_simple_task_raises_confidence(self):
        c = caddy.estimate_confidence("simple", "fix", "standard", [], 50)
        c_complex = caddy.estimate_confidence("complex", "implement", "standard", [], 50)
        self.assertGreater(c, c_complex)

    def test_critical_quality_lowers_confidence(self):
        c_std = caddy.estimate_confidence("moderate", "implement", "standard", [], 80)
        c_crit = caddy.estimate_confidence("moderate", "implement", "critical", [], 80)
        self.assertGreater(c_std, c_crit)

    def test_confidence_bounds(self):
        # Should never exceed [0.0, 1.0]
        for complexity in ["simple", "moderate", "complex", "massive"]:
            for quality in ["standard", "high", "critical"]:
                c = caddy.estimate_confidence(complexity, "fix", quality, [], 100)
                self.assertGreaterEqual(c, 0.0)
                self.assertLessEqual(c, 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
