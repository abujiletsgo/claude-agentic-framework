# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""
Comprehensive Hook Test Framework
==================================

Tests both command hooks (pattern-based) and validates prompt hook configurations.
Uses mock inputs from mock_inputs.json to verify security patterns.

Usage:
  # Run all tests
  uv run test_hooks.py

  # Run specific category
  uv run test_hooks.py --category bash_dangerous

  # Run specific test by ID
  uv run test_hooks.py --id bash_d01

  # Verbose output
  uv run test_hooks.py -v

  # Test only command hooks (skip prompt hook config validation)
  uv run test_hooks.py --command-only

  # List all test IDs
  uv run test_hooks.py --list

  # Run with JSON output for CI
  uv run test_hooks.py --json

Exit codes:
  0 = All tests passed
  1 = Some tests failed
  2 = Configuration error
"""

import json
import sys
import os
import subprocess
import argparse
import time
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
FRAMEWORK_DIR = SCRIPT_DIR.parent
HOOKS_DIR = FRAMEWORK_DIR.parent
REPO_DIR = HOOKS_DIR.parent
DAMAGE_CONTROL_DIR = HOOKS_DIR / "damage-control"
MOCK_INPUTS_FILE = SCRIPT_DIR / "mock_inputs.json"

# Also check ~/.claude/hooks/damage-control for installed hooks
HOME_HOOKS_DIR = Path.home() / ".claude" / "hooks" / "damage-control"

HOOK_SCRIPTS = {
    "Bash": "bash-tool-damage-control.py",
    "Edit": "edit-tool-damage-control.py",
    "Write": "write-tool-damage-control.py",
}


# ---------------------------------------------------------------------------
# Color output
# ---------------------------------------------------------------------------

class Colors:
    PASS = "\033[92m"
    FAIL = "\033[91m"
    WARN = "\033[93m"
    INFO = "\033[94m"
    DIM = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def color(text: str, c: str) -> str:
    return f"{c}{text}{Colors.RESET}"


# ---------------------------------------------------------------------------
# Hook script location
# ---------------------------------------------------------------------------

def find_hook_script(tool_name: str) -> Path | None:
    """Find the hook script for a given tool, checking multiple locations."""
    script_name = HOOK_SCRIPTS.get(tool_name)
    if not script_name:
        return None

    # Check repo location first
    repo_path = DAMAGE_CONTROL_DIR / script_name
    if repo_path.exists():
        return repo_path

    # Check home hooks location
    home_path = HOME_HOOKS_DIR / script_name
    if home_path.exists():
        return home_path

    return None


# ---------------------------------------------------------------------------
# Load mock inputs
# ---------------------------------------------------------------------------

def load_mock_inputs() -> dict[str, Any]:
    """Load mock inputs from JSON file."""
    if not MOCK_INPUTS_FILE.exists():
        print(f"Error: Mock inputs file not found: {MOCK_INPUTS_FILE}", file=sys.stderr)
        sys.exit(2)

    with open(MOCK_INPUTS_FILE) as f:
        return json.load(f)


def expand_home_in_value(value: Any) -> Any:
    """Recursively replace $HOME placeholder with actual home directory in test data."""
    home = str(Path.home())
    if isinstance(value, str):
        return value.replace("$HOME", home)
    elif isinstance(value, dict):
        return {k: expand_home_in_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [expand_home_in_value(item) for item in value]
    return value


def get_all_tests(data: dict) -> list[dict]:
    """Extract all test cases from mock inputs, expanding $HOME placeholders."""
    tests = []
    # Categories that contain PreToolUse test cases
    categories = [
        "bash_dangerous", "bash_safe", "bash_edge_cases", "bash_obfuscated",
        "edit_dangerous", "edit_safe",
        "write_dangerous", "write_safe",
    ]
    for cat in categories:
        for test in data.get(cat, []):
            test = expand_home_in_value(test)
            test["_category"] = cat
            tests.append(test)
    return tests


# ---------------------------------------------------------------------------
# Run command hook test
# ---------------------------------------------------------------------------

def run_command_hook_test(test: dict, common_fields: dict, verbose: bool = False) -> dict:
    """
    Run a command hook test by invoking the damage control script via subprocess.

    Returns dict with: id, description, expect, actual, passed, duration_ms, details
    """
    test_id = test["id"]
    tool_name = test["tool_name"]
    tool_input = test["tool_input"]
    expected = test["expect"]  # "block", "allow", or "ask"
    category = test.get("_category", "unknown")

    result = {
        "id": test_id,
        "description": test["description"],
        "category": category,
        "expect": expected,
        "actual": None,
        "passed": False,
        "duration_ms": 0,
        "details": "",
        "note": test.get("note", ""),
    }

    # Find hook script
    hook_script = find_hook_script(tool_name)
    if not hook_script:
        result["actual"] = "error"
        result["details"] = f"Hook script not found for {tool_name}"
        return result

    # Build input JSON
    input_data = {
        **common_fields,
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": tool_input,
    }
    input_json = json.dumps(input_data)

    # Execute hook
    start = time.monotonic()
    try:
        proc = subprocess.run(
            ["uv", "run", str(hook_script)],
            input=input_json,
            capture_output=True,
            text=True,
            timeout=15,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        result["duration_ms"] = duration_ms

        exit_code = proc.returncode
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        # Determine actual result from exit code
        if exit_code == 2:
            result["actual"] = "block"
        elif exit_code == 0:
            # Check for JSON output with ask decision
            if stdout:
                try:
                    output = json.loads(stdout)
                    hook_output = output.get("hookSpecificOutput", {})
                    decision = hook_output.get("permissionDecision", "")
                    if decision == "ask":
                        result["actual"] = "ask"
                    elif decision == "deny":
                        result["actual"] = "block"
                    elif decision == "allow":
                        result["actual"] = "allow"
                    else:
                        result["actual"] = "allow"
                except json.JSONDecodeError:
                    result["actual"] = "allow"
            else:
                result["actual"] = "allow"
        else:
            result["actual"] = "error"
            result["details"] = f"Unexpected exit code {exit_code}"

        if verbose:
            if stderr:
                result["details"] += f" stderr: {stderr[:200]}"
            if stdout:
                result["details"] += f" stdout: {stdout[:200]}"

    except subprocess.TimeoutExpired:
        duration_ms = int((time.monotonic() - start) * 1000)
        result["duration_ms"] = duration_ms
        result["actual"] = "error"
        result["details"] = "Hook timed out after 15s"
    except Exception as e:
        result["actual"] = "error"
        result["details"] = str(e)

    # Check pass/fail
    result["passed"] = result["actual"] == expected

    return result


# ---------------------------------------------------------------------------
# Validate prompt hook configuration
# ---------------------------------------------------------------------------

def validate_prompt_hooks(settings_path: Path | None = None) -> list[dict]:
    """
    Validate prompt hook configurations in settings.json.
    Checks that prompt hooks have correct format and required fields.
    """
    results = []

    if settings_path is None:
        settings_path = Path.home() / ".claude" / "settings.json"

    if not settings_path.exists():
        results.append({
            "id": "config_01",
            "description": "Settings file exists",
            "passed": False,
            "details": f"Not found: {settings_path}",
        })
        return results

    with open(settings_path) as f:
        settings = json.load(f)

    hooks = settings.get("hooks", {})
    pre_tool_use = hooks.get("PreToolUse", [])

    # Check that prompt hooks exist for Bash, Edit, Write
    prompt_hook_tools = set()
    command_hook_tools = set()

    for matcher_group in pre_tool_use:
        matcher = matcher_group.get("matcher", "*")
        for hook in matcher_group.get("hooks", []):
            hook_type = hook.get("type", "")
            if hook_type == "prompt":
                prompt_hook_tools.add(matcher)
            elif hook_type == "command":
                command_hook_tools.add(matcher)

    # Test: Bash prompt hook exists
    results.append({
        "id": "config_bash_prompt",
        "description": "Bash prompt hook configured",
        "passed": "Bash" in prompt_hook_tools,
        "details": "Bash prompt hook found" if "Bash" in prompt_hook_tools else "Missing Bash prompt hook",
    })

    # Test: Edit prompt hook exists
    results.append({
        "id": "config_edit_prompt",
        "description": "Edit prompt hook configured",
        "passed": "Edit" in prompt_hook_tools,
        "details": "Edit prompt hook found" if "Edit" in prompt_hook_tools else "Missing Edit prompt hook",
    })

    # Test: Write prompt hook exists
    results.append({
        "id": "config_write_prompt",
        "description": "Write prompt hook configured",
        "passed": "Write" in prompt_hook_tools,
        "details": "Write prompt hook found" if "Write" in prompt_hook_tools else "Missing Write prompt hook",
    })

    # Test: Hybrid approach -- command hooks still present
    results.append({
        "id": "config_bash_command",
        "description": "Bash command hook preserved (hybrid)",
        "passed": "Bash" in command_hook_tools,
        "details": "Bash command hook found" if "Bash" in command_hook_tools else "Missing Bash command hook -- hybrid approach broken",
    })
    results.append({
        "id": "config_edit_command",
        "description": "Edit command hook preserved (hybrid)",
        "passed": "Edit" in command_hook_tools,
        "details": "Edit command hook found" if "Edit" in command_hook_tools else "Missing Edit command hook -- hybrid approach broken",
    })
    results.append({
        "id": "config_write_command",
        "description": "Write command hook preserved (hybrid)",
        "passed": "Write" in command_hook_tools,
        "details": "Write command hook found" if "Write" in command_hook_tools else "Missing Write command hook -- hybrid approach broken",
    })

    # Validate prompt hook fields
    for matcher_group in pre_tool_use:
        matcher = matcher_group.get("matcher", "*")
        for hook in matcher_group.get("hooks", []):
            if hook.get("type") != "prompt":
                continue

            hook_id = f"config_{matcher.lower()}_prompt_fields"

            # Check required fields
            has_prompt = bool(hook.get("prompt"))
            has_arguments = "$ARGUMENTS" in hook.get("prompt", "")
            has_timeout = "timeout" in hook
            has_ok_format = '"ok"' in hook.get("prompt", "")

            issues = []
            if not has_prompt:
                issues.append("missing prompt field")
            if not has_arguments:
                issues.append("missing $ARGUMENTS placeholder")
            if not has_timeout:
                issues.append("missing timeout field")
            if not has_ok_format:
                issues.append("prompt does not mention ok/true/false response format")

            results.append({
                "id": hook_id,
                "description": f"{matcher} prompt hook has valid fields",
                "passed": len(issues) == 0,
                "details": "; ".join(issues) if issues else "All fields valid",
            })

    # Validate ordering: command hook should come before prompt hook
    for matcher_group in pre_tool_use:
        matcher = matcher_group.get("matcher", "*")
        hooks_list = matcher_group.get("hooks", [])
        types_in_order = [h.get("type") for h in hooks_list]

        if "command" in types_in_order and "prompt" in types_in_order:
            cmd_idx = types_in_order.index("command")
            prompt_idx = types_in_order.index("prompt")
            correct_order = cmd_idx < prompt_idx
            results.append({
                "id": f"config_{matcher.lower()}_order",
                "description": f"{matcher}: command hook runs before prompt hook",
                "passed": correct_order,
                "details": "Correct: fast pattern match first, then LLM" if correct_order else "Wrong order: prompt hook should come after command hook",
            })

    return results


# ---------------------------------------------------------------------------
# Validate template consistency
# ---------------------------------------------------------------------------

def validate_template_consistency() -> list[dict]:
    """Check that settings.json.template has the same prompt hooks as settings.json."""
    results = []

    template_path = REPO_DIR / "templates" / "settings.json.template"
    settings_path = Path.home() / ".claude" / "settings.json"

    if not template_path.exists():
        results.append({
            "id": "template_exists",
            "description": "Template file exists",
            "passed": False,
            "details": f"Not found: {template_path}",
        })
        return results

    with open(template_path) as f:
        template_content = f.read()

    # Check template has prompt hooks
    has_prompt_type = '"type": "prompt"' in template_content
    has_arguments = "$ARGUMENTS" in template_content
    # In JSON strings, "ok" appears as \"ok\" due to escaping
    has_ok_format = '\\"ok\\"' in template_content or '"ok"' in template_content

    results.append({
        "id": "template_has_prompt_hooks",
        "description": "Template has prompt-based hooks",
        "passed": has_prompt_type,
        "details": "Template contains prompt hooks" if has_prompt_type else "Template missing prompt hooks",
    })

    results.append({
        "id": "template_has_arguments",
        "description": "Template uses $ARGUMENTS placeholder",
        "passed": has_arguments,
        "details": "Template uses $ARGUMENTS" if has_arguments else "Template missing $ARGUMENTS",
    })

    results.append({
        "id": "template_correct_format",
        "description": "Template uses correct ok/true/false response format",
        "passed": has_ok_format,
        "details": "Template uses ok format" if has_ok_format else "Template uses old decision/approve/block format -- needs update",
    })

    # Check it does NOT use old deprecated format (check both raw and JSON-escaped)
    has_old_format = (
        '"decision": "approve"' in template_content
        or '"decision": "block"' in template_content
        or '\\"decision\\": \\"approve\\"' in template_content
        or '\\"decision\\": \\"block\\"' in template_content
    )
    results.append({
        "id": "template_no_deprecated",
        "description": "Template does not use deprecated decision format",
        "passed": not has_old_format,
        "details": "No deprecated format found" if not has_old_format else "Template still uses deprecated decision/approve/block format",
    })

    return results


# ---------------------------------------------------------------------------
# Print results
# ---------------------------------------------------------------------------

def print_result(r: dict, verbose: bool = False) -> None:
    """Print a single test result."""
    status = color("PASS", Colors.PASS) if r["passed"] else color("FAIL", Colors.FAIL)
    duration = f" ({r['duration_ms']}ms)" if "duration_ms" in r and r["duration_ms"] > 0 else ""

    print(f"  {status} [{r['id']}] {r['description']}{duration}")

    if not r["passed"] or verbose:
        if r.get("expect"):
            print(f"         Expected: {r['expect']}, Got: {r.get('actual', 'N/A')}")
        if r.get("details"):
            print(f"         {color(r['details'], Colors.DIM)}")
        if r.get("note"):
            print(f"         Note: {color(r['note'], Colors.WARN)}")


def print_summary(all_results: list[dict]) -> None:
    """Print test summary."""
    total = len(all_results)
    passed = sum(1 for r in all_results if r["passed"])
    failed = total - passed

    print()
    print("=" * 70)
    if failed == 0:
        print(color(f"  ALL {total} TESTS PASSED", Colors.PASS))
    else:
        print(color(f"  {failed}/{total} TESTS FAILED", Colors.FAIL))

    # Show timing stats for command hook tests
    timed = [r for r in all_results if r.get("duration_ms", 0) > 0]
    if timed:
        avg_ms = sum(r["duration_ms"] for r in timed) / len(timed)
        max_ms = max(r["duration_ms"] for r in timed)
        print(f"  Timing: avg={avg_ms:.0f}ms, max={max_ms}ms ({len(timed)} timed tests)")

    print("=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Hook Test Framework")
    parser.add_argument("--category", "-c", help="Run tests for specific category")
    parser.add_argument("--id", help="Run specific test by ID")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--command-only", action="store_true", help="Only test command hooks")
    parser.add_argument("--config-only", action="store_true", help="Only validate configuration")
    parser.add_argument("--list", action="store_true", help="List all test IDs")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--settings", help="Path to settings.json (default: ~/.claude/settings.json)")
    args = parser.parse_args()

    data = load_mock_inputs()
    common_fields = data.get("common_fields", {})
    all_tests = get_all_tests(data)

    # List mode
    if args.list:
        print(f"{'ID':<15} {'Category':<20} {'Expect':<8} Description")
        print("-" * 80)
        for t in all_tests:
            print(f"{t['id']:<15} {t.get('_category', ''):<20} {t['expect']:<8} {t['description']}")
        return 0

    all_results: list[dict] = []

    # -----------------------------------------------------------------------
    # Configuration validation
    # -----------------------------------------------------------------------
    if not args.command_only:
        print(color("\n--- Configuration Validation ---", Colors.BOLD))

        settings_path = Path(args.settings) if args.settings else None
        config_results = validate_prompt_hooks(settings_path)
        all_results.extend(config_results)
        for r in config_results:
            print_result(r, args.verbose)

        print(color("\n--- Template Consistency ---", Colors.BOLD))
        template_results = validate_template_consistency()
        all_results.extend(template_results)
        for r in template_results:
            print_result(r, args.verbose)

    if args.config_only:
        print_summary(all_results)
        if args.json:
            print(json.dumps(all_results, indent=2))
        return 0 if all(r["passed"] for r in all_results) else 1

    # -----------------------------------------------------------------------
    # Command hook tests
    # -----------------------------------------------------------------------
    # Filter tests
    if args.id:
        tests_to_run = [t for t in all_tests if t["id"] == args.id]
        if not tests_to_run:
            print(f"Error: Test ID '{args.id}' not found", file=sys.stderr)
            return 2
    elif args.category:
        tests_to_run = [t for t in all_tests if t.get("_category") == args.category]
        if not tests_to_run:
            print(f"Error: Category '{args.category}' not found", file=sys.stderr)
            return 2
    else:
        tests_to_run = all_tests

    # Group by category for display
    categories_seen: dict[str, list[dict]] = {}
    for t in tests_to_run:
        cat = t.get("_category", "unknown")
        categories_seen.setdefault(cat, []).append(t)

    for cat, tests in categories_seen.items():
        print(color(f"\n--- {cat} ({len(tests)} tests) ---", Colors.BOLD))

        for test in tests:
            result = run_command_hook_test(test, common_fields, args.verbose)
            all_results.append(result)
            print_result(result, args.verbose)

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print_summary(all_results)

    if args.json:
        print(json.dumps(all_results, indent=2))

    return 0 if all(r["passed"] for r in all_results) else 1


if __name__ == "__main__":
    sys.exit(main())
