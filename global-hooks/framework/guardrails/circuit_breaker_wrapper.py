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
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from circuit_breaker import CircuitBreaker, CircuitBreakerDecision
from hook_state_manager import HookStateManager
from config_loader import load_config


def parse_args() -> Optional[list[str]]:
    """
    Parse command line arguments.

    Expected format: circuit_breaker_wrapper.py -- <command> [args...]

    Returns:
        Command to execute as list of strings, or None if invalid
    """
    args = sys.argv[1:]

    if not args:
        print("Error: No command provided", file=sys.stderr)
        print_usage()
        return None

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

    return command_args


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
    command = parse_args()
    if command is None:
        return 2

    # Build full command string for state tracking
    hook_cmd = " ".join(command)

    try:
        # Load configuration
        config = load_config()

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
    sys.exit(main())
