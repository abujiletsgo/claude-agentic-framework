#!/usr/bin/env python3
"""
Auto Error Analyzer - PostToolUse Hook

Detects failed test commands and spawns error-analyzer skill to analyze
the failure. Only triggers for Bash tool with test commands (pytest, npm test,
go test, cargo test, jest).

Usage:
    Called automatically after each Bash tool use by Claude Code.
    Detects test command patterns and exit code != 0.
    Spawns error-analyzer skill with captured stderr.

Test command patterns:
    - pytest, py.test
    - npm test, npm run test, yarn test
    - go test
    - cargo test
    - jest
    - make test

Exit codes:
    0: Always (never block workflow)
"""

import json
import re
import subprocess
import sys
from pathlib import Path


# Test command patterns to detect
TEST_PATTERNS = [
    r'\bpytest\b',
    r'\bpy\.test\b',
    r'\bnpm\s+test\b',
    r'\bnpm\s+run\s+test\b',
    r'\byarn\s+test\b',
    r'\bgo\s+test\b',
    r'\bcargo\s+test\b',
    r'\bjest\b',
    r'\bmake\s+test\b',
    r'\buv\s+run\s+pytest\b',
]


def is_test_command(command):
    """Check if command matches test command patterns."""
    if not command:
        return False

    command_lower = command.lower()
    for pattern in TEST_PATTERNS:
        if re.search(pattern, command_lower):
            return True
    return False


def extract_error_context(stderr, stdout, exit_code):
    """Extract relevant error context from command output."""
    # Combine stderr and stdout for analysis
    output = ""
    if stderr:
        output += f"=== STDERR ===\n{stderr}\n\n"
    if stdout:
        output += f"=== STDOUT ===\n{stdout}\n\n"

    output += f"Exit Code: {exit_code}\n"

    # Limit output size (max 5000 chars to avoid overwhelming the skill)
    if len(output) > 5000:
        # Try to find stack trace or error section
        lines = output.split("\n")
        error_lines = []

        # Look for common error indicators
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in [
                "error", "exception", "traceback", "failed",
                "assert", "expected", "got", "stack trace"
            ]):
                # Include context around error (5 lines before and after)
                start = max(0, i - 5)
                end = min(len(lines), i + 6)
                error_lines.extend(lines[start:end])

        if error_lines:
            output = "\n".join(error_lines[:200])  # Limit to 200 lines
        else:
            output = output[:5000]  # Fallback to truncation

    return output


def spawn_error_analyzer(error_context, command):
    """Spawn error-analyzer skill with captured error.

    This would normally integrate with Claude Code's skill system.
    For now, we output the analysis request to stderr.
    """
    # In a full implementation, this would use Claude Code's Skill tool
    # to spawn the error-analyzer skill with the error context

    # For now, output a structured error analysis request
    print("\n" + "="*60, file=sys.stderr)
    print("🔍 AUTO ERROR ANALYSIS", file=sys.stderr)
    print("="*60, file=sys.stderr)
    print(f"Command: {command}", file=sys.stderr)
    print(f"\nError context ({len(error_context)} chars):", file=sys.stderr)
    print("-"*60, file=sys.stderr)
    print(error_context, file=sys.stderr)
    print("-"*60, file=sys.stderr)
    print("\nℹ️  Run /error-analyzer for detailed analysis", file=sys.stderr)
    print("="*60 + "\n", file=sys.stderr)


def main():
    """Main entry point for auto error analyzer hook."""
    try:
        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        # Only process Bash tool
        tool_name = hook_input.get("toolName", "")
        if tool_name != "Bash":
            sys.exit(0)

        # Get command and execution details
        tool_input = hook_input.get("toolInput", {})
        if isinstance(tool_input, str):
            tool_input = json.loads(tool_input)

        command = tool_input.get("command", "")

        # Check if this is a test command
        if not is_test_command(command):
            sys.exit(0)

        # Get execution results
        tool_output = hook_input.get("toolOutput", {})
        if isinstance(tool_output, str):
            try:
                tool_output = json.loads(tool_output)
            except json.JSONDecodeError:
                # Output might be plain text
                tool_output = {"stdout": tool_output}

        # Check exit code
        exit_code = tool_output.get("exit_code")
        if exit_code is None:
            # Try to extract from output
            stdout = tool_output.get("stdout", "")
            stderr = tool_output.get("stderr", "")
            # Assume failure if stderr contains error keywords
            if stderr and any(kw in stderr.lower() for kw in ["error", "failed", "exception"]):
                exit_code = 1
            else:
                sys.exit(0)

        # Only analyze failures
        if exit_code == 0:
            sys.exit(0)

        # Extract error context
        stderr = tool_output.get("stderr", "")
        stdout = tool_output.get("stdout", "")
        error_context = extract_error_context(stderr, stdout, exit_code)

        # Spawn error analyzer
        spawn_error_analyzer(error_context, command)

    except Exception as e:
        # Fail silently - error analysis should never block operations
        print(f"Auto error analyzer error (non-blocking): {e}", file=sys.stderr)

    # Always exit 0 (never block workflow)
    sys.exit(0)


if __name__ == "__main__":
    main()
