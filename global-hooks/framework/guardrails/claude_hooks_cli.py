#!/usr/bin/env python3
"""
claude-hooks - CLI tool for monitoring and managing the circuit breaker system.

This tool provides health monitoring, hook management, and status reporting
for the guardrails circuit breaker system.

Usage:
    claude-hooks health              Show hook health status
    claude-hooks reset <hook>        Reset specific hook state
    claude-hooks reset --all         Reset all hook states
    claude-hooks enable <hook>       Enable a disabled hook
    claude-hooks disable <hook>      Manually disable a hook
    claude-hooks config              Show current configuration
    claude-hooks list                List all tracked hooks
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

# Import our guardrails modules
try:
    from hook_state_manager import HookStateManager
    from config_loader import load_config, GuardrailsConfig
    from state_schema import CircuitState
except ImportError:
    # If running as standalone, try to import from current directory
    sys.path.insert(0, str(Path(__file__).parent))
    from hook_state_manager import HookStateManager
    from config_loader import load_config, GuardrailsConfig
    from state_schema import CircuitState


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""
    # Basic colors
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

    # Styles
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    # Reset
    RESET = '\033[0m'

    @staticmethod
    def is_terminal() -> bool:
        """Check if stdout is a terminal (supports colors)."""
        return sys.stdout.isatty()

    @classmethod
    def disable(cls):
        """Disable colors (for non-terminal output)."""
        cls.RED = ''
        cls.GREEN = ''
        cls.YELLOW = ''
        cls.BLUE = ''
        cls.MAGENTA = ''
        cls.CYAN = ''
        cls.WHITE = ''
        cls.BOLD = ''
        cls.UNDERLINE = ''
        cls.RESET = ''


# Initialize colors based on terminal detection
if not Colors.is_terminal():
    Colors.disable()


def format_time_ago(timestamp_str: Optional[str]) -> str:
    """
    Format timestamp as human-readable "X time ago" string.

    Args:
        timestamp_str: ISO 8601 timestamp string

    Returns:
        Human-readable time string (e.g., "5 minutes ago")
    """
    if not timestamp_str:
        return "never"

    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        now = datetime.now(timezone.utc)

        # Handle timezone-naive timestamps
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        delta = now - timestamp
        seconds = delta.total_seconds()

        if seconds < 0:
            return "in the future"
        elif seconds < 60:
            return f"{int(seconds)} seconds ago"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
    except (ValueError, AttributeError):
        return "unknown"


def format_time_until(timestamp_str: Optional[str]) -> str:
    """
    Format timestamp as "in X time" string.

    Args:
        timestamp_str: ISO 8601 timestamp string

    Returns:
        Human-readable time string (e.g., "in 5 minutes")
    """
    if not timestamp_str:
        return "unknown"

    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        now = datetime.now(timezone.utc)

        # Handle timezone-naive timestamps
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        delta = timestamp - now
        seconds = delta.total_seconds()

        if seconds < 0:
            return "now"
        elif seconds < 60:
            return f"in {int(seconds)} seconds"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"in {minutes} minute{'s' if minutes != 1 else ''}"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"in {hours} hour{'s' if hours != 1 else ''}"
        else:
            days = int(seconds / 86400)
            return f"in {days} day{'s' if days != 1 else ''}"
    except (ValueError, AttributeError):
        return "unknown"


def shorten_hook_cmd(cmd: str, max_length: int = 60) -> str:
    """
    Shorten hook command for display.

    Args:
        cmd: Full hook command string
        max_length: Maximum length for display

    Returns:
        Shortened command string
    """
    if len(cmd) <= max_length:
        return cmd

    # Try to extract meaningful part (script name)
    parts = cmd.split()
    script_parts = [p for p in parts if p.endswith('.py')]
    if script_parts:
        script_name = Path(script_parts[0]).name
        return f"...{script_name}"

    # Fallback: truncate with ellipsis
    return cmd[:max_length-3] + "..."


def print_health_report(state_manager: HookStateManager, config: GuardrailsConfig, json_output: bool = False):
    """
    Print health report for all hooks.

    Args:
        state_manager: State manager instance
        config: Configuration object
        json_output: If True, output JSON instead of formatted text
    """
    report = state_manager.get_health_report()

    if json_output:
        # JSON output mode
        print(json.dumps(report, indent=2))
        return

    # Formatted text output
    total_hooks = report['total_hooks']
    active_hooks = report['active_hooks']
    disabled_hooks = report['disabled_hooks']
    disabled_details = report['disabled_hook_details']
    global_stats = report['global_stats']

    # Header
    print(f"\n{Colors.BOLD}Hook Health Report{Colors.RESET}")
    print("=" * 60)

    # Summary
    print(f"Total Hooks: {Colors.BOLD}{total_hooks}{Colors.RESET}")
    print(f"Active: {Colors.GREEN}{active_hooks}{Colors.RESET}")
    print(f"Disabled: {Colors.RED if disabled_hooks > 0 else Colors.GREEN}{disabled_hooks}{Colors.RESET}")

    # Global stats
    print(f"\n{Colors.BOLD}Global Statistics{Colors.RESET}")
    print(f"Total Executions: {global_stats['total_executions']}")
    print(f"Total Failures: {global_stats['total_failures']}")
    if global_stats['total_executions'] > 0:
        failure_rate = (global_stats['total_failures'] / global_stats['total_executions']) * 100
        color = Colors.RED if failure_rate > 10 else Colors.YELLOW if failure_rate > 5 else Colors.GREEN
        print(f"Failure Rate: {color}{failure_rate:.2f}%{Colors.RESET}")
    print(f"Last Updated: {format_time_ago(global_stats['last_updated'])}")

    # Disabled hooks details
    if disabled_details:
        print(f"\n{Colors.BOLD}{Colors.RED}DISABLED HOOKS:{Colors.RESET}")
        for detail in disabled_details:
            cmd = detail['command']
            state = detail['state']
            failure_count = detail['failure_count']
            consecutive_failures = detail['consecutive_failures']
            last_error = detail['last_error']
            disabled_at = detail['disabled_at']
            retry_after = detail['retry_after']

            print(f"\n  {Colors.BOLD}[{state.upper()}] {shorten_hook_cmd(cmd)}{Colors.RESET}")
            print(f"    Full Command: {Colors.CYAN}{cmd}{Colors.RESET}")
            print(f"    Failures: {Colors.RED}{consecutive_failures} consecutive, {failure_count} total{Colors.RESET}")
            if last_error:
                # Truncate long errors
                error_display = last_error[:100] + "..." if len(last_error) > 100 else last_error
                print(f"    Last Error: {Colors.YELLOW}{error_display}{Colors.RESET}")
            print(f"    Disabled Since: {format_time_ago(disabled_at)}")
            print(f"    Retry After: {format_time_until(retry_after)}")
    else:
        print(f"\n{Colors.GREEN}All hooks are healthy!{Colors.RESET}")

    # Commands section
    if disabled_details:
        print(f"\n{Colors.BOLD}COMMANDS:{Colors.RESET}")
        print(f"  Reset single hook:  {Colors.CYAN}claude-hooks reset <hook_name>{Colors.RESET}")
        print(f"  Reset all:          {Colors.CYAN}claude-hooks reset --all{Colors.RESET}")
        print(f"  Enable hook:        {Colors.CYAN}claude-hooks enable <hook_name>{Colors.RESET}")
        print(f"  Show all hooks:     {Colors.CYAN}claude-hooks list{Colors.RESET}")

    print()  # Empty line at end


def print_hook_list(state_manager: HookStateManager, json_output: bool = False):
    """
    Print list of all tracked hooks.

    Args:
        state_manager: State manager instance
        json_output: If True, output JSON instead of formatted text
    """
    all_hooks = state_manager.get_all_hooks()

    if json_output:
        # JSON output mode
        hook_list = [
            {
                "command": cmd,
                "state": hook_state.state,
                "failure_count": hook_state.failure_count,
                "consecutive_failures": hook_state.consecutive_failures,
                "consecutive_successes": hook_state.consecutive_successes,
                "last_success": hook_state.last_success,
                "last_failure": hook_state.last_failure,
            }
            for cmd, hook_state in all_hooks.items()
        ]
        print(json.dumps(hook_list, indent=2))
        return

    # Formatted text output
    if not all_hooks:
        print(f"\n{Colors.YELLOW}No hooks tracked yet.{Colors.RESET}\n")
        return

    print(f"\n{Colors.BOLD}All Tracked Hooks ({len(all_hooks)}){Colors.RESET}")
    print("=" * 80)

    # Sort by state (OPEN first, then by command)
    sorted_hooks = sorted(
        all_hooks.items(),
        key=lambda x: (0 if x[1].state == CircuitState.OPEN.value else 1, x[0])
    )

    for cmd, hook_state in sorted_hooks:
        state = hook_state.state

        # Color based on state
        if state == CircuitState.OPEN.value:
            state_color = Colors.RED
            state_text = "OPEN"
        elif state == CircuitState.HALF_OPEN.value:
            state_color = Colors.YELLOW
            state_text = "HALF-OPEN"
        else:
            state_color = Colors.GREEN
            state_text = "CLOSED"

        print(f"\n{state_color}[{state_text}]{Colors.RESET} {Colors.BOLD}{shorten_hook_cmd(cmd, 70)}{Colors.RESET}")
        print(f"  Full: {Colors.CYAN}{cmd}{Colors.RESET}")
        print(f"  Failures: {hook_state.failure_count} total, {hook_state.consecutive_failures} consecutive")
        print(f"  Successes: {hook_state.consecutive_successes} consecutive")
        if hook_state.last_success:
            print(f"  Last Success: {format_time_ago(hook_state.last_success)}")
        if hook_state.last_failure:
            print(f"  Last Failure: {format_time_ago(hook_state.last_failure)}")

    print()


def print_config(config: GuardrailsConfig, json_output: bool = False):
    """
    Print current configuration.

    Args:
        config: Configuration object
        json_output: If True, output JSON instead of formatted text
    """
    if json_output:
        # JSON output mode
        print(json.dumps(config.model_dump(), indent=2))
        return

    # Formatted text output
    print(f"\n{Colors.BOLD}Guardrails Configuration{Colors.RESET}")
    print("=" * 60)

    print(f"\n{Colors.BOLD}Circuit Breaker{Colors.RESET}")
    print(f"  Enabled: {Colors.GREEN if config.circuit_breaker.enabled else Colors.RED}{config.circuit_breaker.enabled}{Colors.RESET}")
    print(f"  Failure Threshold: {config.circuit_breaker.failure_threshold}")
    print(f"  Cooldown: {config.circuit_breaker.cooldown_seconds} seconds")
    print(f"  Success Threshold: {config.circuit_breaker.success_threshold}")
    if config.circuit_breaker.exclude:
        print(f"  Excluded Hooks:")
        for pattern in config.circuit_breaker.exclude:
            print(f"    - {pattern}")

    print(f"\n{Colors.BOLD}Logging{Colors.RESET}")
    print(f"  File: {config.logging.file}")
    print(f"  Level: {config.logging.level}")

    print(f"\n{Colors.BOLD}State{Colors.RESET}")
    print(f"  State File: {config.state_file}")

    print()


def reset_hook(state_manager: HookStateManager, hook_pattern: str) -> int:
    """
    Reset specific hook(s) matching pattern.

    Args:
        state_manager: State manager instance
        hook_pattern: Pattern to match hook commands

    Returns:
        Exit code (0 for success, 1 for no matches)
    """
    all_hooks = state_manager.get_all_hooks()

    # Find matching hooks
    matches = [cmd for cmd in all_hooks.keys() if hook_pattern in cmd]

    if not matches:
        print(f"{Colors.RED}Error: No hooks found matching '{hook_pattern}'{Colors.RESET}")
        print(f"\nAvailable hooks:")
        for cmd in all_hooks.keys():
            print(f"  {shorten_hook_cmd(cmd)}")
        return 1

    if len(matches) > 1:
        print(f"{Colors.YELLOW}Warning: Multiple hooks match pattern '{hook_pattern}':{Colors.RESET}")
        for cmd in matches:
            print(f"  - {shorten_hook_cmd(cmd)}")
        print(f"\nPlease be more specific, or reset all with: claude-hooks reset --all")
        return 1

    # Reset the single match
    hook_cmd = matches[0]
    success = state_manager.reset_hook(hook_cmd)

    if success:
        print(f"{Colors.GREEN}Successfully reset hook:{Colors.RESET}")
        print(f"  {shorten_hook_cmd(hook_cmd)}")
        return 0
    else:
        print(f"{Colors.RED}Failed to reset hook (not found in state).{Colors.RESET}")
        return 1


def reset_all_hooks(state_manager: HookStateManager) -> int:
    """
    Reset all hook states.

    Args:
        state_manager: State manager instance

    Returns:
        Exit code (0 for success)
    """
    count = state_manager.reset_all()
    print(f"{Colors.GREEN}Successfully reset {count} hook(s).{Colors.RESET}")
    return 0


def enable_hook(state_manager: HookStateManager, hook_pattern: str, force: bool = False) -> int:
    """
    Enable a disabled hook by resetting its state.

    Args:
        state_manager: State manager instance
        hook_pattern: Pattern to match hook commands
        force: If True, reset even if not disabled

    Returns:
        Exit code (0 for success, 1 for error)
    """
    all_hooks = state_manager.get_all_hooks()

    # Find matching hooks
    matches = [cmd for cmd in all_hooks.keys() if hook_pattern in cmd]

    if not matches:
        print(f"{Colors.RED}Error: No hooks found matching '{hook_pattern}'{Colors.RESET}")
        return 1

    if len(matches) > 1:
        print(f"{Colors.YELLOW}Warning: Multiple hooks match pattern '{hook_pattern}':{Colors.RESET}")
        for cmd in matches:
            print(f"  - {shorten_hook_cmd(cmd)}")
        print(f"\nPlease be more specific.")
        return 1

    hook_cmd = matches[0]
    hook_state = all_hooks[hook_cmd]

    # Check if hook is actually disabled
    if hook_state.state != CircuitState.OPEN.value and not force:
        print(f"{Colors.YELLOW}Hook is not disabled (state: {hook_state.state}).{Colors.RESET}")
        print(f"Use --force to reset anyway.")
        return 1

    # Reset to enable
    success = state_manager.reset_hook(hook_cmd)

    if success:
        print(f"{Colors.GREEN}Successfully enabled hook:{Colors.RESET}")
        print(f"  {shorten_hook_cmd(hook_cmd)}")
        return 0
    else:
        print(f"{Colors.RED}Failed to enable hook.{Colors.RESET}")
        return 1


def disable_hook(state_manager: HookStateManager, config: GuardrailsConfig, hook_pattern: str) -> int:
    """
    Manually disable a hook by opening its circuit.

    Args:
        state_manager: State manager instance
        config: Configuration object
        hook_pattern: Pattern to match hook commands

    Returns:
        Exit code (0 for success, 1 for error)
    """
    all_hooks = state_manager.get_all_hooks()

    # Find matching hooks
    matches = [cmd for cmd in all_hooks.keys() if hook_pattern in cmd]

    # If no matches found in existing hooks, treat pattern as exact hook name
    if not matches:
        # Check if pattern looks like a hook command (contains .py or similar extension)
        if '.' in hook_pattern or '/' in hook_pattern:
            matches = [hook_pattern]
        else:
            print(f"{Colors.RED}Error: No hooks found matching '{hook_pattern}'{Colors.RESET}")
            return 1

    if len(matches) > 1:
        print(f"{Colors.YELLOW}Warning: Multiple hooks match pattern '{hook_pattern}':{Colors.RESET}")
        for cmd in matches:
            print(f"  - {shorten_hook_cmd(cmd)}")
        print(f"\nPlease be more specific.")
        return 1

    hook_cmd = matches[0]

    # Record enough failures to open circuit
    threshold = config.circuit_breaker.failure_threshold
    for _ in range(threshold):
        state_manager.record_failure(hook_cmd, "Manually disabled via CLI")

    print(f"{Colors.GREEN}Successfully disabled hook:{Colors.RESET}")
    print(f"  {shorten_hook_cmd(hook_cmd)}")
    print(f"\nTo re-enable: claude-hooks enable {hook_pattern}")
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='claude-hooks',
        description='CLI tool for monitoring and managing the circuit breaker system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  claude-hooks health                    Show hook health status
  claude-hooks health --json             Output health as JSON
  claude-hooks list                      List all tracked hooks
  claude-hooks reset validate_file       Reset specific hook
  claude-hooks reset --all               Reset all hooks
  claude-hooks enable validate_file      Enable a disabled hook
  claude-hooks disable validate_file     Manually disable a hook
  claude-hooks config                    Show current configuration

For more information, see the documentation in CIRCUIT_BREAKER_README.md
        """
    )

    # Global options
    parser.add_argument(
        '--config',
        type=Path,
        help='Path to configuration file (default: ~/.claude/guardrails.yaml)'
    )
    parser.add_argument(
        '--state-file',
        type=Path,
        help='Path to state file (default: ~/.claude/hook_state.json)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # health command
    health_parser = subparsers.add_parser('health', help='Show hook health status')

    # list command
    list_parser = subparsers.add_parser('list', help='List all tracked hooks')

    # reset command
    reset_parser = subparsers.add_parser('reset', help='Reset hook state')
    reset_parser.add_argument('hook_pattern', nargs='?', help='Pattern to match hook command')
    reset_parser.add_argument('--all', action='store_true', help='Reset all hooks')

    # enable command
    enable_parser = subparsers.add_parser('enable', help='Enable a disabled hook')
    enable_parser.add_argument('hook_pattern', help='Pattern to match hook command')
    enable_parser.add_argument('--force', action='store_true', help='Force enable even if not disabled')

    # disable command
    disable_parser = subparsers.add_parser('disable', help='Manually disable a hook')
    disable_parser.add_argument('hook_pattern', help='Pattern to match hook command')

    # config command
    config_parser = subparsers.add_parser('config', help='Show current configuration')

    # Parse args
    args = parser.parse_args()

    # Disable colors if requested or not a terminal
    if args.no_color or not sys.stdout.isatty():
        Colors.disable()

    # Load configuration
    try:
        config = load_config(args.config)

        # Override state file if specified
        if args.state_file:
            config.state_file = str(args.state_file)
    except Exception as e:
        print(f"{Colors.RED}Error loading configuration: {e}{Colors.RESET}", file=sys.stderr)
        return 1

    # Initialize state manager
    try:
        state_manager = HookStateManager(config.get_state_file_path())
    except Exception as e:
        print(f"{Colors.RED}Error initializing state manager: {e}{Colors.RESET}", file=sys.stderr)
        return 1

    # Execute command
    if args.command == 'health':
        print_health_report(state_manager, config, args.json)
        return 0

    elif args.command == 'list':
        print_hook_list(state_manager, args.json)
        return 0

    elif args.command == 'reset':
        if args.all:
            return reset_all_hooks(state_manager)
        elif args.hook_pattern:
            return reset_hook(state_manager, args.hook_pattern)
        else:
            print(f"{Colors.RED}Error: Either provide a hook pattern or use --all{Colors.RESET}")
            return 1

    elif args.command == 'enable':
        return enable_hook(state_manager, args.hook_pattern, args.force)

    elif args.command == 'disable':
        return disable_hook(state_manager, config, args.hook_pattern)

    elif args.command == 'config':
        print_config(config, args.json)
        return 0

    else:
        # No command specified, show help
        parser.print_help()
        return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrupted by user{Colors.RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"{Colors.RED}Unexpected error: {e}{Colors.RESET}", file=sys.stderr)
        sys.exit(1)
