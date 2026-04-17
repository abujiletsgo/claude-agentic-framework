#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pyyaml>=6.0.0",
#   "pydantic>=2.0.0",
# ]
# ///
"""
Circuit breaker wrapper for hook commands.

Usage:
  # In settings.json, wrap any hook command:
  Before:  "uv run path/to/hook.py --args"
  After:   "uv run .../circuit_breaker_wrapper.py -- uv run path/to/hook.py --args"

Features:
  - Tracks failure counts per command
  - Auto-disables after threshold failures
  - Cooldown period before retry
  - Graceful degradation (returns success when disabled)
  - Detailed logging of state transitions
  - Returns Claude-compatible JSON output

Exit Codes:
  0: Success (hook succeeded or circuit open with graceful skip)
  1: Hook failed and circuit is closed/half-open
  2: Invalid usage or configuration error
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def normalize_hook_key(command: list) -> str:
    """Find the last meaningful .py filename or caf-hooks subcommand."""
    skip = {'uv', 'run', '--no-project', 'python', 'python3', '--',
            'circuit_breaker_wrapper.py', 'circuit-breaker-wrapper'}
    # Scan reversed to find the last meaningful script/subcommand
    for part in reversed(command):
        if part.endswith('.py') and 'circuit_breaker_wrapper' not in part:
            return os.path.splitext(os.path.basename(part))[0].replace('_', '-').lower()
        if (part and not part.startswith('-') and '/' not in part
                and part not in skip and not part.endswith('.py')):
            clean = part.replace('_', '-').lower()
            if clean not in skip:
                return clean
    return os.path.splitext(os.path.basename(command[-1]))[0].replace('_', '-').lower()

from circuit_breaker import CircuitBreaker, CircuitBreakerDecision
from hook_state_manager import HookStateManager
from config_loader import load_config


def parse_args() -> Optional[tuple]:
    """
    Parse command line arguments.

    Expected format: circuit_breaker_wrapper.py [--failure-threshold N] [--cooldown-seconds N] -- <command> [args...]

    Returns:
        Tuple of (command_args, failure_threshold, cooldown_seconds), or None if invalid
    """
    args = sys.argv[1:]

    if not args:
        print("Error: No command provided", file=sys.stderr)
        print_usage()
        return None

    # Parse our flags before the -- separator
    failure_threshold = None
    cooldown_seconds = None
    i = 0
    while i < len(args) and args[i] != '--':
        if args[i] == '--failure-threshold' and i + 1 < len(args):
            try:
                failure_threshold = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i] == '--cooldown-seconds' and i + 1 < len(args):
            try:
                cooldown_seconds = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            i += 1

    # Find the -- separator
    if "--" not in args:
        print("Error: Missing '--' separator", file=sys.stderr)
        print_usage()
        return None

    separator_idx = args.index("--")
    command_args = args[separator_idx + 1:]

    if not command_args:
        print("Error: No command after '--'", file=sys.stderr)
        print_usage()
        return None

    return command_args, failure_threshold, cooldown_seconds


def print_usage():
    """Print usage information."""
    print("""
Usage: circuit_breaker_wrapper.py -- <command> [args...]

Examples:
  circuit_breaker_wrapper.py -- uv run hooks/validator.py --file test.py
  circuit_breaker_wrapper.py -- python check_lint.py
  circuit_breaker_wrapper.py -- bash -c "echo hello"

The wrapper will:
  1. Check circuit breaker state
  2. Skip execution if circuit is open (returns success)
  3. Execute command if circuit is closed or half-open
  4. Update failure/success counters
  5. Open circuit after threshold failures
""", file=sys.stderr)


def execute_command(command: list[str]) -> tuple[int, str, str]:
    """
    Execute command and capture output.

    Args:
        command: Command to execute as list of strings

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out after 300 seconds"
    except FileNotFoundError as e:
        return 1, "", f"Command not found: {e}"
    except Exception as e:
        return 1, "", f"Failed to execute command: {e}"


def output_claude_json(result: str, message: str, success: bool = True):
    """
    Output JSON in Claude-compatible format.

    Args:
        result: Result status ("continue" or "stop")
        message: Message to display
        success: Whether operation was successful
    """
    output = {
        "result": result,
        "message": message,
        "success": success
    }
    print(json.dumps(output, indent=2))


def main() -> int:
    """
    Main wrapper logic.

    Returns:
        Exit code (0 = success, 1 = failure, 2 = usage error)
    """
    # Parse command
    parsed = parse_args()
    if parsed is None:
        return 2

    command, cli_failure_threshold, cli_cooldown_seconds = parsed

    # Build canonical CB key for state tracking
    hook_cmd = normalize_hook_key(command)

    try:
        # Load configuration
        config = load_config()

        # Apply CLI overrides if provided
        if cli_failure_threshold is not None:
            config.circuit_breaker.failure_threshold = cli_failure_threshold
        if cli_cooldown_seconds is not None:
            config.circuit_breaker.cooldown_seconds = cli_cooldown_seconds

        # Check if circuit breaker is enabled
        if not config.circuit_breaker.enabled:
            # Circuit breaker disabled, execute normally without tracking
            exit_code, stdout, stderr = execute_command(command)
            if stdout:
                print(stdout, end="")
            if stderr:
                print(stderr, end="", file=sys.stderr)
            return exit_code

        # Initialize circuit breaker
        state_manager = HookStateManager(config.get_state_file_path())
        breaker = CircuitBreaker(state_manager, config)

        # Check if we should execute
        result = breaker.should_execute(hook_cmd)

        if not result.should_execute:
            # Circuit is open, skip execution
            output_claude_json(
                "continue",
                f"Hook disabled due to repeated failures. {result.message}",
                success=True
            )
            return 0  # Return success to not block agent

        # Execute the command
        exit_code, stdout, stderr = execute_command(command)

        # Output command's stdout/stderr
        if stdout:
            print(stdout, end="")
        if stderr:
            print(stderr, end="", file=sys.stderr)

        # Record result
        if exit_code == 0:
            breaker.record_success(hook_cmd)
            return 0
        else:
            # Extract error message
            error_msg = stderr.strip() if stderr.strip() else f"Exit code {exit_code}"
            breaker.record_failure(hook_cmd, error_msg)
            return exit_code

    except Exception as e:
        # Configuration or initialization error
        print(f"Circuit breaker error: {e}", file=sys.stderr)
        print("Executing command without circuit breaker...", file=sys.stderr)

        # Fallback: execute command directly
        exit_code, stdout, stderr = execute_command(command)
        if stdout:
            print(stdout, end="")
        if stderr:
            print(stderr, end="", file=sys.stderr)
        return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as e:
        if e.code == 2:
            raise  # preserve intentional blocks
        sys.exit(0)  # any other exit: fail-open
    except Exception:
        sys.exit(0)  # fail-open: never block due to wrapper crash
