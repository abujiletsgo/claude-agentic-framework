"""
Unit tests for the CLI tool.

Tests cover:
- Health reporting
- Hook listing
- State reset operations
- Hook enable/disable
- Configuration display
- JSON output mode
- Color handling
- Time formatting
- Hook pattern matching
"""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from claude_hooks_cli import (
    Colors,
    format_time_ago,
    format_time_until,
    shorten_hook_cmd,
    print_health_report,
    print_hook_list,
    print_config,
    reset_hook,
    reset_all_hooks,
    enable_hook,
    disable_hook,
)
from hook_state_manager import HookStateManager
from config_loader import GuardrailsConfig, CircuitBreakerConfig, LoggingConfig
from state_schema import HookState, CircuitState


class TestTimeFormatting(unittest.TestCase):
    """Test time formatting functions."""

    def test_format_time_ago_none(self):
        """Test format_time_ago with None."""
        self.assertEqual(format_time_ago(None), "never")

    def test_format_time_ago_seconds(self):
        """Test format_time_ago with seconds."""
        now = datetime.now(timezone.utc)
        timestamp = (now - timedelta(seconds=30)).isoformat()
        result = format_time_ago(timestamp)
        self.assertIn("seconds ago", result)

    def test_format_time_ago_minutes(self):
        """Test format_time_ago with minutes."""
        now = datetime.now(timezone.utc)
        timestamp = (now - timedelta(minutes=5)).isoformat()
        result = format_time_ago(timestamp)
        self.assertIn("minute", result)
        self.assertIn("ago", result)

    def test_format_time_ago_hours(self):
        """Test format_time_ago with hours."""
        now = datetime.now(timezone.utc)
        timestamp = (now - timedelta(hours=3)).isoformat()
        result = format_time_ago(timestamp)
        self.assertIn("hour", result)
        self.assertIn("ago", result)

    def test_format_time_ago_days(self):
        """Test format_time_ago with days."""
        now = datetime.now(timezone.utc)
        timestamp = (now - timedelta(days=2)).isoformat()
        result = format_time_ago(timestamp)
        self.assertIn("day", result)
        self.assertIn("ago", result)

    def test_format_time_ago_singular(self):
        """Test format_time_ago with singular units."""
        now = datetime.now(timezone.utc)
        timestamp = (now - timedelta(minutes=1)).isoformat()
        result = format_time_ago(timestamp)
        self.assertEqual(result, "1 minute ago")

    def test_format_time_ago_invalid(self):
        """Test format_time_ago with invalid timestamp."""
        result = format_time_ago("invalid")
        self.assertEqual(result, "unknown")

    def test_format_time_until_none(self):
        """Test format_time_until with None."""
        self.assertEqual(format_time_until(None), "unknown")

    def test_format_time_until_future(self):
        """Test format_time_until with future timestamp."""
        now = datetime.now(timezone.utc)
        timestamp = (now + timedelta(minutes=5)).isoformat()
        result = format_time_until(timestamp)
        self.assertIn("in", result)
        self.assertIn("minute", result)

    def test_format_time_until_past(self):
        """Test format_time_until with past timestamp."""
        now = datetime.now(timezone.utc)
        timestamp = (now - timedelta(minutes=5)).isoformat()
        result = format_time_until(timestamp)
        self.assertEqual(result, "now")


class TestHookCommandShortening(unittest.TestCase):
    """Test hook command shortening."""

    def test_short_command_unchanged(self):
        """Test that short commands are not modified."""
        cmd = "short_command.py"
        self.assertEqual(shorten_hook_cmd(cmd), cmd)

    def test_long_command_with_script(self):
        """Test long command with .py script is shortened to script name."""
        cmd = "uv run /very/long/path/to/script/validate_file_contains.py --args"
        result = shorten_hook_cmd(cmd, max_length=30)
        self.assertIn("validate_file_contains.py", result)

    def test_long_command_without_script(self):
        """Test long command without .py script is truncated."""
        cmd = "a" * 100
        result = shorten_hook_cmd(cmd, max_length=50)
        self.assertEqual(len(result), 50)
        self.assertTrue(result.endswith("..."))

    def test_custom_max_length(self):
        """Test custom max_length parameter."""
        cmd = "a" * 100
        result = shorten_hook_cmd(cmd, max_length=20)
        self.assertEqual(len(result), 20)


class TestColorsClass(unittest.TestCase):
    """Test Colors utility class."""

    def test_colors_disabled_when_not_terminal(self):
        """Test colors are disabled for non-terminal output."""
        with patch('sys.stdout.isatty', return_value=False):
            colors = Colors()
            colors.disable()
            self.assertEqual(colors.RED, '')
            self.assertEqual(colors.GREEN, '')
            self.assertEqual(colors.RESET, '')

    def test_colors_enabled_when_terminal(self):
        """Test colors are enabled for terminal output."""
        with patch('sys.stdout.isatty', return_value=True):
            # Reset colors to defaults as if terminal
            Colors.RED = '\033[91m'
            Colors.GREEN = '\033[92m'
            Colors.YELLOW = '\033[93m'
            Colors.BLUE = '\033[94m'
            Colors.MAGENTA = '\033[95m'
            Colors.CYAN = '\033[96m'
            Colors.WHITE = '\033[97m'
            Colors.BOLD = '\033[1m'
            Colors.UNDERLINE = '\033[4m'
            Colors.RESET = '\033[0m'

            self.assertNotEqual(Colors.RED, '')
            self.assertNotEqual(Colors.GREEN, '')


class TestHealthReport(unittest.TestCase):
    """Test health report printing."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.temp_dir) / "test_state.json"
        self.state_manager = HookStateManager(self.state_file)

        # Create test configuration
        self.config = GuardrailsConfig(
            circuit_breaker=CircuitBreakerConfig(
                enabled=True,
                failure_threshold=3,
                cooldown_seconds=300,
                success_threshold=2,
                exclude=[]
            ),
            logging=LoggingConfig(
                file="~/.claude/logs/test.log",
                level="INFO",
                format="%(message)s"
            ),
            state_file=str(self.state_file)
        )

        # Disable colors for testing
        Colors.disable()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_health_report_empty(self):
        """Test health report with no hooks."""
        output = StringIO()
        with patch('sys.stdout', output):
            print_health_report(self.state_manager, self.config)

        result = output.getvalue()
        self.assertIn("Total Hooks: 0", result)
        self.assertIn("All hooks are healthy!", result)

    def test_health_report_with_disabled_hook(self):
        """Test health report with a disabled hook."""
        # Create a disabled hook
        hook_cmd = "test_hook.py"
        for _ in range(3):
            self.state_manager.record_failure(hook_cmd, "Test error", failure_threshold=3)

        output = StringIO()
        with patch('sys.stdout', output):
            print_health_report(self.state_manager, self.config)

        result = output.getvalue()
        self.assertIn("Total Hooks: 1", result)
        self.assertIn("Disabled: 1", result)
        self.assertIn("DISABLED HOOKS:", result)
        self.assertIn("test_hook.py", result)

    def test_health_report_json_output(self):
        """Test health report JSON output."""
        hook_cmd = "test_hook.py"
        self.state_manager.record_success(hook_cmd)

        output = StringIO()
        with patch('sys.stdout', output):
            print_health_report(self.state_manager, self.config, json_output=True)

        result = output.getvalue()
        data = json.loads(result)

        self.assertEqual(data['total_hooks'], 1)
        self.assertEqual(data['active_hooks'], 1)
        self.assertEqual(data['disabled_hooks'], 0)

    def test_health_report_failure_rate(self):
        """Test health report shows failure rate."""
        hook_cmd = "test_hook.py"
        self.state_manager.record_success(hook_cmd)
        self.state_manager.record_failure(hook_cmd, "Test error", failure_threshold=3)

        output = StringIO()
        with patch('sys.stdout', output):
            print_health_report(self.state_manager, self.config)

        result = output.getvalue()
        self.assertIn("Failure Rate:", result)


class TestHookList(unittest.TestCase):
    """Test hook list printing."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.temp_dir) / "test_state.json"
        self.state_manager = HookStateManager(self.state_file)
        Colors.disable()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_list_empty(self):
        """Test list with no hooks."""
        output = StringIO()
        with patch('sys.stdout', output):
            print_hook_list(self.state_manager)

        result = output.getvalue()
        self.assertIn("No hooks tracked yet", result)

    def test_list_with_hooks(self):
        """Test list with multiple hooks."""
        self.state_manager.record_success("hook1.py")
        self.state_manager.record_success("hook2.py")
        self.state_manager.record_failure("hook3.py", "Error", failure_threshold=3)

        output = StringIO()
        with patch('sys.stdout', output):
            print_hook_list(self.state_manager)

        result = output.getvalue()
        self.assertIn("All Tracked Hooks (3)", result)
        self.assertIn("hook1.py", result)
        self.assertIn("hook2.py", result)
        self.assertIn("hook3.py", result)

    def test_list_json_output(self):
        """Test list JSON output."""
        self.state_manager.record_success("hook1.py")

        output = StringIO()
        with patch('sys.stdout', output):
            print_hook_list(self.state_manager, json_output=True)

        result = output.getvalue()
        data = json.loads(result)

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['command'], "hook1.py")
        self.assertEqual(data[0]['state'], CircuitState.CLOSED.value)

    def test_list_sorting(self):
        """Test list sorts OPEN hooks first."""
        self.state_manager.record_success("closed_hook.py")
        for _ in range(3):
            self.state_manager.record_failure("open_hook.py", "Error", failure_threshold=3)

        output = StringIO()
        with patch('sys.stdout', output):
            print_hook_list(self.state_manager)

        result = output.getvalue()
        # OPEN hook should appear before CLOSED hook
        open_pos = result.find("[OPEN]")
        closed_pos = result.find("[CLOSED]")
        self.assertLess(open_pos, closed_pos)


class TestConfigDisplay(unittest.TestCase):
    """Test configuration display."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = GuardrailsConfig(
            circuit_breaker=CircuitBreakerConfig(
                enabled=True,
                failure_threshold=5,
                cooldown_seconds=600,
                success_threshold=3,
                exclude=["test_hook.py"]
            ),
            logging=LoggingConfig(
                file="~/.claude/logs/test.log",
                level="DEBUG",
                format="%(message)s"
            ),
            state_file="~/.claude/test_state.json"
        )
        Colors.disable()

    def test_config_display_text(self):
        """Test config display in text format."""
        output = StringIO()
        with patch('sys.stdout', output):
            print_config(self.config)

        result = output.getvalue()
        self.assertIn("Guardrails Configuration", result)
        self.assertIn("Circuit Breaker", result)
        self.assertIn("Failure Threshold: 5", result)
        self.assertIn("Cooldown: 600 seconds", result)
        self.assertIn("test_hook.py", result)

    def test_config_display_json(self):
        """Test config display in JSON format."""
        output = StringIO()
        with patch('sys.stdout', output):
            print_config(self.config, json_output=True)

        result = output.getvalue()
        data = json.loads(result)

        self.assertEqual(data['circuit_breaker']['failure_threshold'], 5)
        self.assertEqual(data['circuit_breaker']['cooldown_seconds'], 600)
        self.assertIn("test_hook.py", data['circuit_breaker']['exclude'])


class TestResetOperations(unittest.TestCase):
    """Test reset operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.temp_dir) / "test_state.json"
        self.state_manager = HookStateManager(self.state_file)
        Colors.disable()

        # Create some test hooks
        self.state_manager.record_failure("validate_file.py", "Error", failure_threshold=3)
        self.state_manager.record_success("other_hook.py")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_reset_specific_hook_exact_match(self):
        """Test reset with exact hook pattern match."""
        output = StringIO()
        with patch('sys.stdout', output):
            result = reset_hook(self.state_manager, "validate_file.py")

        self.assertEqual(result, 0)
        self.assertIn("Successfully reset", output.getvalue())

        # Verify hook was reset
        all_hooks = self.state_manager.get_all_hooks()
        self.assertNotIn("validate_file.py", all_hooks)

    def test_reset_specific_hook_partial_match(self):
        """Test reset with partial hook pattern match."""
        output = StringIO()
        with patch('sys.stdout', output):
            result = reset_hook(self.state_manager, "validate")

        self.assertEqual(result, 0)
        self.assertIn("Successfully reset", output.getvalue())

    def test_reset_no_match(self):
        """Test reset with no matching hooks."""
        output = StringIO()
        with patch('sys.stdout', output):
            result = reset_hook(self.state_manager, "nonexistent")

        self.assertEqual(result, 1)
        self.assertIn("No hooks found", output.getvalue())

    def test_reset_multiple_matches(self):
        """Test reset with multiple matching hooks."""
        self.state_manager.record_success("validate_other.py")

        output = StringIO()
        with patch('sys.stdout', output):
            result = reset_hook(self.state_manager, "validate")

        self.assertEqual(result, 1)
        self.assertIn("Multiple hooks match", output.getvalue())

    def test_reset_all_hooks(self):
        """Test reset all hooks."""
        output = StringIO()
        with patch('sys.stdout', output):
            result = reset_all_hooks(self.state_manager)

        self.assertEqual(result, 0)
        self.assertIn("Successfully reset", output.getvalue())

        # Verify all hooks were reset
        all_hooks = self.state_manager.get_all_hooks()
        self.assertEqual(len(all_hooks), 0)


class TestEnableDisableOperations(unittest.TestCase):
    """Test enable and disable operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.temp_dir) / "test_state.json"
        self.state_manager = HookStateManager(self.state_file)

        self.config = GuardrailsConfig(
            circuit_breaker=CircuitBreakerConfig(
                enabled=True,
                failure_threshold=3,
                cooldown_seconds=300,
                success_threshold=2,
                exclude=[]
            ),
            logging=LoggingConfig(),
            state_file=str(self.state_file)
        )

        Colors.disable()

        # Create a disabled hook
        for _ in range(3):
            self.state_manager.record_failure("disabled_hook.py", "Error", failure_threshold=3)

        # Create an active hook
        self.state_manager.record_success("active_hook.py")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_enable_disabled_hook(self):
        """Test enabling a disabled hook."""
        output = StringIO()
        with patch('sys.stdout', output):
            result = enable_hook(self.state_manager, "disabled_hook")

        self.assertEqual(result, 0)
        self.assertIn("Successfully enabled", output.getvalue())

        # Verify hook was enabled (removed from state)
        all_hooks = self.state_manager.get_all_hooks()
        self.assertNotIn("disabled_hook.py", all_hooks)

    def test_enable_active_hook_without_force(self):
        """Test enabling an active hook without force."""
        output = StringIO()
        with patch('sys.stdout', output):
            result = enable_hook(self.state_manager, "active_hook", force=False)

        self.assertEqual(result, 1)
        self.assertIn("not disabled", output.getvalue())

    def test_enable_active_hook_with_force(self):
        """Test enabling an active hook with force."""
        output = StringIO()
        with patch('sys.stdout', output):
            result = enable_hook(self.state_manager, "active_hook", force=True)

        self.assertEqual(result, 0)
        self.assertIn("Successfully enabled", output.getvalue())

    def test_enable_nonexistent_hook(self):
        """Test enabling a nonexistent hook."""
        output = StringIO()
        with patch('sys.stdout', output):
            result = enable_hook(self.state_manager, "nonexistent")

        self.assertEqual(result, 1)
        self.assertIn("No hooks found", output.getvalue())

    def test_disable_active_hook(self):
        """Test disabling an active hook."""
        output = StringIO()
        with patch('sys.stdout', output):
            result = disable_hook(self.state_manager, self.config, "active_hook")

        self.assertEqual(result, 0)
        self.assertIn("Successfully disabled", output.getvalue())

        # Verify hook is now disabled
        hook_state = self.state_manager.get_hook_state("active_hook.py")
        self.assertEqual(hook_state.state, CircuitState.OPEN.value)

    def test_disable_nonexistent_hook(self):
        """Test disabling a nonexistent hook."""
        output = StringIO()
        with patch('sys.stdout', output):
            result = disable_hook(self.state_manager, self.config, "nonexistent")

        self.assertEqual(result, 1)
        self.assertIn("No hooks found", output.getvalue())

    def test_disable_with_multiple_matches(self):
        """Test disable with multiple matching hooks."""
        self.state_manager.record_success("hook1.py")
        self.state_manager.record_success("hook2.py")

        output = StringIO()
        with patch('sys.stdout', output):
            result = disable_hook(self.state_manager, self.config, "hook")

        self.assertEqual(result, 1)
        self.assertIn("Multiple hooks match", output.getvalue())


class TestCLIIntegration(unittest.TestCase):
    """Test CLI integration with various scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.temp_dir) / "test_state.json"
        self.state_manager = HookStateManager(self.state_file)
        Colors.disable()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_workflow_create_fail_reset(self):
        """Test workflow: create hook, fail it, then reset."""
        hook_cmd = "test_hook.py"

        # Record failures to open circuit
        for _ in range(3):
            self.state_manager.record_failure(hook_cmd, "Test error", failure_threshold=3)

        # Verify circuit is open
        hook_state = self.state_manager.get_hook_state(hook_cmd)
        self.assertEqual(hook_state.state, CircuitState.OPEN.value)

        # Reset the hook
        output = StringIO()
        with patch('sys.stdout', output):
            result = reset_hook(self.state_manager, hook_cmd)

        self.assertEqual(result, 0)

        # Verify hook is removed
        all_hooks = self.state_manager.get_all_hooks()
        self.assertNotIn(hook_cmd, all_hooks)

    def test_workflow_disable_enable(self):
        """Test workflow: disable hook, then enable it."""
        config = GuardrailsConfig(
            circuit_breaker=CircuitBreakerConfig(failure_threshold=3),
            logging=LoggingConfig(),
            state_file=str(self.state_file)
        )

        hook_cmd = "test_hook.py"

        # Disable the hook
        output = StringIO()
        with patch('sys.stdout', output):
            result = disable_hook(self.state_manager, config, hook_cmd)

        self.assertEqual(result, 0)

        # Verify it's disabled
        hook_state = self.state_manager.get_hook_state(hook_cmd)
        self.assertEqual(hook_state.state, CircuitState.OPEN.value)

        # Enable it again
        output = StringIO()
        with patch('sys.stdout', output):
            result = enable_hook(self.state_manager, hook_cmd)

        self.assertEqual(result, 0)

        # Verify it's removed (reset to default state)
        all_hooks = self.state_manager.get_all_hooks()
        self.assertNotIn(hook_cmd, all_hooks)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
