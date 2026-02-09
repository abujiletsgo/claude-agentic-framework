#!/usr/bin/env python3
"""
Stop Hook: Test Suite Runner (Quality Gate)

Runs the project's test suite when the agent tries to stop.
- PASS (exit 0): Agent allowed to finish
- FAIL (exit 2): Agent blocked, error fed back for correction

Detection order:
1. Check for package.json → npm test
2. Check for pytest.ini / pyproject.toml / setup.cfg → pytest
3. Check for Makefile with test target → make test
4. Check for go.mod → go test ./...
5. No test runner found → pass silently (don't block)

Environment variable overrides:
  RALPH_TEST_CMD="custom test command"   → Use this instead of auto-detect
  RALPH_SKIP_TESTS=1                     → Skip test validation entirely
  RALPH_TEST_TIMEOUT=120                 → Test timeout in seconds (default: 120)
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def find_test_runner():
    """Auto-detect the project's test runner."""

    # Allow explicit override
    custom_cmd = os.environ.get("RALPH_TEST_CMD")
    if custom_cmd:
        return custom_cmd

    cwd = Path.cwd()

    # Node.js: package.json with test script
    pkg_json = cwd / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            scripts = pkg.get("scripts", {})
            if "test" in scripts:
                # Skip if test script is just the default placeholder
                test_script = scripts["test"]
                if "no test specified" not in test_script:
                    return "npm test"
        except (json.JSONDecodeError, KeyError):
            pass

    # Python: pytest
    for marker in ["pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini"]:
        if (cwd / marker).exists():
            return "python -m pytest -v --tb=short -q"

    # Python: check for tests/ directory
    if (cwd / "tests").is_dir() or (cwd / "test").is_dir():
        return "python -m pytest -v --tb=short -q"

    # Go
    if (cwd / "go.mod").exists():
        return "go test ./..."

    # Rust
    if (cwd / "Cargo.toml").exists():
        return "cargo test"

    # Makefile with test target
    makefile = cwd / "Makefile"
    if makefile.exists():
        content = makefile.read_text()
        if "test:" in content:
            return "make test"

    # No test runner found
    return None


def run_tests(cmd):
    """Execute the test command and capture results."""
    timeout = int(os.environ.get("RALPH_TEST_TIMEOUT", "120"))

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(Path.cwd()),
        )
        return {
            "passed": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:] if result.stdout else "",  # Last 2000 chars
            "stderr": result.stderr[-1000:] if result.stderr else "",  # Last 1000 chars
            "command": cmd,
        }
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Test suite timed out after {timeout}s",
            "command": cmd,
        }
    except Exception as e:
        return {
            "passed": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "command": cmd,
        }


def main():
    # Skip if explicitly disabled
    if os.environ.get("RALPH_SKIP_TESTS") == "1":
        print(json.dumps({"decision": "approve", "reason": "Tests skipped (RALPH_SKIP_TESTS=1)"}))
        sys.exit(0)

    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        hook_input = {}

    # Only run on Stop events (not SubagentStop unless configured)
    event_type = hook_input.get("event", "")
    if event_type == "SubagentStop":
        # Don't block sub-agents by default
        if os.environ.get("RALPH_TEST_SUBAGENTS") != "1":
            sys.exit(0)

    # Find test runner
    test_cmd = find_test_runner()

    if not test_cmd:
        # No test runner found — don't block the agent
        sys.exit(0)

    # Run tests
    result = run_tests(test_cmd)

    if result["passed"]:
        # Tests passed — allow agent to stop
        sys.exit(0)
    else:
        # Tests failed — block agent, feed error back
        error_output = result["stderr"] or result["stdout"]
        feedback = f"""Tests FAILED. You must fix the failing tests before stopping.

Command: {result['command']}
Exit code: {result['returncode']}

Output:
{error_output}

Fix the test failures, then try again."""

        print(feedback)
        sys.exit(2)  # Exit 2 = block agent from stopping


if __name__ == "__main__":
    main()
