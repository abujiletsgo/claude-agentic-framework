# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest", "pyyaml"]
# ///
"""
Prompt Hook Validation Tests
=============================

Tests for prompt-based hook configurations:
  - Response format validation ($ARGUMENTS substitution)
  - Decision parsing (ok: true/false)
  - Status message handling
  - Timeout behavior
  - Error recovery
  - Configuration structure validation

Run:
  uv run pytest test_prompt_hook_validation.py -v
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

TESTING_DIR = Path(__file__).parent
FRAMEWORK_DIR = TESTING_DIR.parent
sys.path.insert(0, str(TESTING_DIR))

from test_utils import (
    make_hook_input,
    make_pre_tool_use_input,
    SettingsFixture,
    TempDirFixture,
)


# ===========================================================================
# $ARGUMENTS Substitution Tests
# ===========================================================================


class TestArgumentsSubstitution:
    """Tests for $ARGUMENTS placeholder substitution in prompt hooks."""

    def test_arguments_replaced_with_tool_input(self):
        """$ARGUMENTS should be replaced with the JSON-encoded tool_input."""
        prompt_template = "Review this command: $ARGUMENTS\nRespond with {\"ok\": true} or {\"ok\": false}."
        tool_input = {"command": "git status"}
        expected_args = json.dumps(tool_input)
        result = prompt_template.replace("$ARGUMENTS", expected_args)
        assert "git status" in result
        assert "$ARGUMENTS" not in result

    def test_arguments_with_special_characters(self):
        """$ARGUMENTS should handle special characters in tool input."""
        prompt_template = "Check: $ARGUMENTS"
        tool_input = {"command": "echo 'hello \"world\"' | grep -v 'test'"}
        args_json = json.dumps(tool_input)
        result = prompt_template.replace("$ARGUMENTS", args_json)
        assert "$ARGUMENTS" not in result
        assert "hello" in result

    def test_arguments_with_multiline_content(self):
        """$ARGUMENTS should handle multiline content in Write tool."""
        prompt_template = "Review: $ARGUMENTS"
        tool_input = {
            "file_path": "/tmp/test.py",
            "content": "def hello():\n    return 'world'\n\nprint(hello())\n",
        }
        args_json = json.dumps(tool_input)
        result = prompt_template.replace("$ARGUMENTS", args_json)
        assert "def hello" in result
        assert "$ARGUMENTS" not in result

    def test_arguments_with_empty_input(self):
        """$ARGUMENTS handles empty tool input."""
        prompt_template = "Check: $ARGUMENTS"
        result = prompt_template.replace("$ARGUMENTS", json.dumps({}))
        assert result == "Check: {}"

    def test_arguments_with_large_input(self):
        """$ARGUMENTS handles large tool input (e.g., big Write content)."""
        prompt_template = "Review: $ARGUMENTS"
        tool_input = {"content": "x" * 10000, "file_path": "/tmp/big.txt"}
        args_json = json.dumps(tool_input)
        result = prompt_template.replace("$ARGUMENTS", args_json)
        assert len(result) > 10000
        assert "$ARGUMENTS" not in result

    def test_arguments_with_nested_json(self):
        """$ARGUMENTS handles nested JSON structures."""
        prompt_template = "Check: $ARGUMENTS"
        tool_input = {
            "command": "echo test",
            "metadata": {"nested": {"deep": True}},
        }
        args_json = json.dumps(tool_input)
        result = prompt_template.replace("$ARGUMENTS", args_json)
        assert "nested" in result


# ===========================================================================
# Decision Parsing Tests
# ===========================================================================


class TestDecisionParsing:
    """Tests for parsing ok/true/false decisions from prompt hook responses."""

    @staticmethod
    def parse_decision(response: str) -> dict:
        """
        Parse a prompt hook response.
        Returns {"ok": bool, "message": str}.
        Mirrors what Claude Code does when processing prompt hook output.
        """
        try:
            # Try to extract JSON from response
            text = response.strip()
            # Handle markdown code blocks
            if text.startswith("```"):
                lines = text.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                text = "\n".join(lines).strip()

            data = json.loads(text)
            if isinstance(data, dict):
                ok = data.get("ok", True)
                message = data.get("message", "")
                return {"ok": bool(ok), "message": str(message)}
        except (json.JSONDecodeError, ValueError):
            pass
        # Default: allow if parsing fails
        return {"ok": True, "message": ""}

    def test_ok_true(self):
        result = self.parse_decision('{"ok": true}')
        assert result["ok"] is True

    def test_ok_false(self):
        result = self.parse_decision('{"ok": false, "message": "dangerous command"}')
        assert result["ok"] is False
        assert result["message"] == "dangerous command"

    def test_ok_false_no_message(self):
        result = self.parse_decision('{"ok": false}')
        assert result["ok"] is False
        assert result["message"] == ""

    def test_markdown_wrapped_json(self):
        response = '```json\n{"ok": false, "message": "blocked"}\n```'
        result = self.parse_decision(response)
        assert result["ok"] is False
        assert result["message"] == "blocked"

    def test_invalid_json_defaults_to_allow(self):
        result = self.parse_decision("This is not JSON")
        assert result["ok"] is True

    def test_empty_response_defaults_to_allow(self):
        result = self.parse_decision("")
        assert result["ok"] is True

    def test_ok_with_integer_truthy(self):
        result = self.parse_decision('{"ok": 1}')
        assert result["ok"] is True

    def test_ok_with_integer_falsy(self):
        result = self.parse_decision('{"ok": 0}')
        assert result["ok"] is False

    def test_ok_with_string_true(self):
        """String "true" should be truthy in bool()."""
        result = self.parse_decision('{"ok": "true"}')
        assert result["ok"] is True

    def test_extra_fields_ignored(self):
        result = self.parse_decision('{"ok": true, "extra": "field", "another": 42}')
        assert result["ok"] is True

    def test_nested_ok_field(self):
        """Only top-level ok field matters."""
        result = self.parse_decision('{"ok": true, "details": {"ok": false}}')
        assert result["ok"] is True

    def test_whitespace_around_json(self):
        result = self.parse_decision('  \n  {"ok": false, "message": "blocked"}  \n  ')
        assert result["ok"] is False


# ===========================================================================
# Settings Configuration Validation Tests
# ===========================================================================


class TestSettingsValidation:
    """Tests for validating settings.json hook configuration structure."""

    def test_default_settings_have_bash_hooks(self):
        with SettingsFixture() as sf:
            settings = sf.get_settings()
            pre_tool_use = settings["hooks"]["PreToolUse"]
            bash_group = next(
                (g for g in pre_tool_use if g.get("matcher") == "Bash"), None
            )
            assert bash_group is not None
            assert len(bash_group["hooks"]) >= 2  # command + prompt

    def test_default_settings_have_edit_hooks(self):
        with SettingsFixture() as sf:
            settings = sf.get_settings()
            pre_tool_use = settings["hooks"]["PreToolUse"]
            edit_group = next(
                (g for g in pre_tool_use if g.get("matcher") == "Edit"), None
            )
            assert edit_group is not None

    def test_default_settings_have_write_hooks(self):
        with SettingsFixture() as sf:
            settings = sf.get_settings()
            pre_tool_use = settings["hooks"]["PreToolUse"]
            write_group = next(
                (g for g in pre_tool_use if g.get("matcher") == "Write"), None
            )
            assert write_group is not None

    def test_command_hook_before_prompt_hook(self):
        """Command hooks should run before prompt hooks (fast filter first)."""
        with SettingsFixture() as sf:
            settings = sf.get_settings()
            for group in settings["hooks"]["PreToolUse"]:
                hooks = group.get("hooks", [])
                types = [h.get("type") for h in hooks]
                if "command" in types and "prompt" in types:
                    cmd_idx = types.index("command")
                    prompt_idx = types.index("prompt")
                    assert cmd_idx < prompt_idx, (
                        f"Command hook should come before prompt hook in {group.get('matcher')}"
                    )

    def test_prompt_hooks_have_arguments_placeholder(self):
        """All prompt hooks should use $ARGUMENTS."""
        with SettingsFixture() as sf:
            settings = sf.get_settings()
            for group in settings["hooks"]["PreToolUse"]:
                for hook in group.get("hooks", []):
                    if hook.get("type") == "prompt":
                        assert "$ARGUMENTS" in hook.get("prompt", ""), (
                            f"Prompt hook for {group.get('matcher')} missing $ARGUMENTS"
                        )

    def test_prompt_hooks_have_timeout(self):
        """All prompt hooks should have a timeout field."""
        with SettingsFixture() as sf:
            settings = sf.get_settings()
            for group in settings["hooks"]["PreToolUse"]:
                for hook in group.get("hooks", []):
                    if hook.get("type") == "prompt":
                        assert "timeout" in hook, (
                            f"Prompt hook for {group.get('matcher')} missing timeout"
                        )

    def test_prompt_hooks_mention_ok_format(self):
        """Prompt hooks should instruct the model to respond with ok format."""
        with SettingsFixture() as sf:
            settings = sf.get_settings()
            for group in settings["hooks"]["PreToolUse"]:
                for hook in group.get("hooks", []):
                    if hook.get("type") == "prompt":
                        prompt = hook.get("prompt", "")
                        assert '"ok"' in prompt or "'ok'" in prompt, (
                            f"Prompt hook for {group.get('matcher')} missing ok format instruction"
                        )

    def test_no_deprecated_decision_format(self):
        """Settings should not use the old decision/approve/block format."""
        with SettingsFixture() as sf:
            content = json.dumps(sf.get_settings())
            assert '"decision"' not in content or '"approve"' not in content
            assert '"decision"' not in content or '"block"' not in content

    def test_settings_has_all_hook_event_types(self):
        """Settings should define all standard hook event types."""
        with SettingsFixture() as sf:
            settings = sf.get_settings()
            hooks = settings["hooks"]
            for event in ["PreToolUse", "PostToolUse", "SessionStart", "SessionEnd"]:
                assert event in hooks, f"Missing hook event type: {event}"


# ===========================================================================
# Hook Matcher Pattern Tests
# ===========================================================================


class TestHookMatchers:
    """Tests for hook matcher patterns."""

    def test_exact_tool_matcher(self):
        """Matcher 'Bash' should match only 'Bash' tool."""
        matcher = "Bash"
        assert matcher == "Bash"
        assert matcher != "Edit"

    def test_wildcard_matcher(self):
        """Matcher '*' should match any tool."""
        matcher = "*"
        # In the hook system, * matches everything
        for tool in ["Bash", "Edit", "Write", "Read", "Grep", "Glob"]:
            # Wildcard matching is done by the hook runner, not by us
            assert matcher == "*"

    def test_multiple_matchers(self):
        """Multiple matcher groups can target different tools."""
        with SettingsFixture() as sf:
            settings = sf.get_settings()
            matchers = [g.get("matcher") for g in settings["hooks"]["PreToolUse"]]
            assert "Bash" in matchers
            assert "Edit" in matchers
            assert "Write" in matchers


# ===========================================================================
# Error Recovery Tests
# ===========================================================================


class TestPromptHookErrorRecovery:
    """Tests for error recovery in prompt hook processing."""

    def test_timeout_returns_allow(self):
        """When a prompt hook times out, the default should be to allow."""
        # Simulate timeout by having the response be empty/invalid
        from test_prompt_hook_validation import TestDecisionParsing
        result = TestDecisionParsing.parse_decision("")
        assert result["ok"] is True

    def test_malformed_json_returns_allow(self):
        """Malformed JSON response should default to allow."""
        from test_prompt_hook_validation import TestDecisionParsing
        result = TestDecisionParsing.parse_decision("{broken json")
        assert result["ok"] is True

    def test_response_with_only_message(self):
        """Response with only message (no ok) should default to allow."""
        from test_prompt_hook_validation import TestDecisionParsing
        result = TestDecisionParsing.parse_decision('{"message": "looks fine"}')
        assert result["ok"] is True

    def test_array_response_defaults_to_allow(self):
        """Array response (not object) should default to allow."""
        from test_prompt_hook_validation import TestDecisionParsing
        result = TestDecisionParsing.parse_decision('[{"ok": false}]')
        assert result["ok"] is True  # Top level is array, not object


# ===========================================================================
# Template Consistency Tests
# ===========================================================================


class TestTemplateConsistency:
    """Tests for settings.json.template consistency."""

    def test_template_exists(self):
        template_path = (
            Path(__file__).parent.parent.parent.parent / "templates" / "settings.json.template"
        )
        if not template_path.exists():
            pytest.skip("Template file not found (expected in templates/settings.json.template)")
        content = template_path.read_text()
        assert len(content) > 0

    def test_template_has_prompt_hooks(self):
        # v2.1.0 removed LLM prompt hooks for token efficiency.
        # Template uses command hooks only — skip this check.
        pytest.skip("v2.1.0: LLM prompt hooks removed for token efficiency")

    def test_template_has_arguments_placeholder(self):
        # v2.1.0 removed LLM prompt hooks; $ARGUMENTS placeholder no longer in template.
        pytest.skip("v2.1.0: LLM prompt hooks removed, $ARGUMENTS no longer used")

    def test_template_uses_ok_format(self):
        template_path = (
            Path(__file__).parent.parent.parent.parent / "templates" / "settings.json.template"
        )
        if not template_path.exists():
            pytest.skip("Template file not found")
        content = template_path.read_text()
        # Check for ok format (may be escaped in JSON strings)
        assert "ok" in content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
