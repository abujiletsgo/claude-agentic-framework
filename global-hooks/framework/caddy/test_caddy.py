#!/usr/bin/env python3
"""
End-to-end test for Caddy hooks.

Tests analyze_request.py and auto_delegate.py with various prompt types
to verify correct classification, strategy selection, and skill matching.
"""

import json
import subprocess
import sys
from pathlib import Path

HOOK_DIR = Path(__file__).parent


def run_hook(hook_name, prompt, session_id="e2e-test"):
    """Run a hook with the given prompt and return parsed output."""
    hook_path = HOOK_DIR / hook_name
    inp = json.dumps({"prompt": prompt, "session_id": session_id})
    result = subprocess.run(
        [sys.executable, str(hook_path)],
        input=inp,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return None, result.returncode
    if not result.stdout.strip():
        return {}, 0
    try:
        return json.loads(result.stdout), 0
    except json.JSONDecodeError:
        return None, -1


def test_analyze_request():
    """Test analyze_request.py classifications."""
    test_cases = [
        {
            "prompt": "Fix typo in README",
            "expect": {
                "complexity": "simple",
                "task_type": "fix",
                "quality_need": "standard",
                "strategy": "direct",
            },
        },
        {
            "prompt": "Add authentication to the API with OAuth2",
            "expect": {
                "complexity": "complex",
                "task_type": "implement",
                "quality_need": "critical",
                "strategy": "fusion",
            },
        },
        {
            "prompt": "How does the payment processing work?",
            "expect": {
                "task_type": "research",
                "strategy": "research",
            },
        },
        {
            "prompt": "Find and fix all N+1 queries across entire codebase",
            "expect": {
                "complexity": "massive",
                "strategy": "rlm",
            },
        },
        {
            "prompt": "Plan the architecture for a new microservices system",
            "expect": {
                "task_type": "plan",
                "strategy": "brainstorm",
            },
        },
        {
            "prompt": "Refactor the utils module for better separation",
            "expect": {
                "task_type": "refactor",
            },
        },
        {
            "prompt": "Add comprehensive unit tests for the auth module",
            "expect": {
                "task_type": "test",
            },
        },
        {
            "prompt": "Build a REST API with rate limiting and tests",
            "expect": {
                "complexity": "complex",
                "task_type": "implement",
            },
        },
    ]

    passed = 0
    failed = 0
    print("=" * 90)
    print("ANALYZE REQUEST TESTS")
    print("=" * 90)

    for tc in test_cases:
        out, code = run_hook("analyze_request.py", tc["prompt"])
        if out is None:
            print(f"  FAIL  {tc['prompt'][:60]:<62} (hook error, exit={code})")
            failed += 1
            continue

        caddy = out.get("caddy", {})
        classification = caddy.get("classification", {})
        strategy = caddy.get("recommended_strategy", "")

        ok = True
        failures = []
        for key, expected in tc["expect"].items():
            if key == "strategy":
                actual = strategy
            else:
                actual = classification.get(key, "")
            if actual != expected:
                ok = False
                failures.append(f"{key}: expected={expected} got={actual}")

        if ok:
            conf = caddy.get("confidence", 0)
            skills = [s["name"] for s in caddy.get("relevant_skills", [])][:2]
            print(
                f"  PASS  {tc['prompt'][:60]:<62} "
                f"[{classification.get('complexity','?')}/{classification.get('task_type','?')}"
                f"/{classification.get('quality_need','?')}] "
                f"-> {strategy} ({conf:.0%}) skills={skills}"
            )
            passed += 1
        else:
            print(f"  FAIL  {tc['prompt'][:60]:<62} {'; '.join(failures)}")
            failed += 1

    return passed, failed


def test_auto_delegate():
    """Test auto_delegate.py execution plans."""
    test_cases = [
        {
            "prompt": "Build a REST API with authentication",
            "expect_strategy": "fusion",
        },
        {
            "prompt": "How does the auth system work?",
            "expect_strategy": "research",
        },
        {
            "prompt": "Fix typo in config file",
            "expect_strategy": None,  # direct - no delegation message
        },
    ]

    passed = 0
    failed = 0
    print()
    print("=" * 90)
    print("AUTO DELEGATE TESTS")
    print("=" * 90)

    for tc in test_cases:
        out, code = run_hook("auto_delegate.py", tc["prompt"])
        if out is None and code != 0:
            print(f"  FAIL  {tc['prompt'][:60]:<62} (hook error, exit={code})")
            failed += 1
            continue

        delegation = (out or {}).get("caddy_delegation", {})
        strategy = delegation.get("strategy", "")

        if tc["expect_strategy"] is None:
            # Expect no delegation (direct = no output)
            if not delegation or strategy == "direct":
                print(f"  PASS  {tc['prompt'][:60]:<62} -> direct (no delegation)")
                passed += 1
            else:
                print(f"  FAIL  {tc['prompt'][:60]:<62} expected direct, got {strategy}")
                failed += 1
        else:
            if strategy == tc["expect_strategy"]:
                skills = delegation.get("skills_to_invoke", [])[:3]
                est = delegation.get("estimated_time", "?")
                print(
                    f"  PASS  {tc['prompt'][:60]:<62} "
                    f"-> {strategy} (est: {est}, skills: {skills})"
                )
                passed += 1
            else:
                print(
                    f"  FAIL  {tc['prompt'][:60]:<62} "
                    f"expected={tc['expect_strategy']} got={strategy}"
                )
                failed += 1

    return passed, failed


def test_monitor_progress():
    """Test monitor_progress.py tracking."""
    print()
    print("=" * 90)
    print("MONITOR PROGRESS TESTS")
    print("=" * 90)

    passed = 0
    failed = 0

    # Test Task tool tracking
    inp = json.dumps({
        "session_id": "monitor-test",
        "tool_name": "Task",
        "tool_input": {
            "subagent_type": "general-purpose",
            "description": "Research something",
        },
        "tool_output": "Done.",
    })
    result = subprocess.run(
        [sys.executable, str(HOOK_DIR / "monitor_progress.py")],
        input=inp, capture_output=True, text=True, timeout=10,
    )
    if result.returncode == 0:
        print(f"  PASS  Task tool tracking                                     -> exit 0 (non-blocking)")
        passed += 1
    else:
        print(f"  FAIL  Task tool tracking                                     -> exit {result.returncode}")
        failed += 1

    # Test Edit tool tracking
    inp = json.dumps({
        "session_id": "monitor-test",
        "tool_name": "Edit",
        "tool_input": {"file_path": "/tmp/test.py", "old_string": "a", "new_string": "b"},
        "tool_output": "Edited.",
    })
    result = subprocess.run(
        [sys.executable, str(HOOK_DIR / "monitor_progress.py")],
        input=inp, capture_output=True, text=True, timeout=10,
    )
    if result.returncode == 0:
        print(f"  PASS  Edit tool tracking                                     -> exit 0 (non-blocking)")
        passed += 1
    else:
        print(f"  FAIL  Edit tool tracking                                     -> exit {result.returncode}")
        failed += 1

    # Test error detection
    inp = json.dumps({
        "session_id": "monitor-test",
        "tool_name": "Bash",
        "tool_input": {"command": "npm test"},
        "tool_output": "Error: test failed with 3 failures",
    })
    result = subprocess.run(
        [sys.executable, str(HOOK_DIR / "monitor_progress.py")],
        input=inp, capture_output=True, text=True, timeout=10,
    )
    if result.returncode == 0:
        print(f"  PASS  Error detection in Bash output                         -> exit 0 (non-blocking)")
        passed += 1
    else:
        print(f"  FAIL  Error detection in Bash output                         -> exit {result.returncode}")
        failed += 1

    # Verify state file has data
    progress_file = Path.home() / ".claude" / "logs" / "caddy" / "progress.json"
    if progress_file.exists():
        with open(progress_file) as f:
            state = json.load(f)
        session = state.get("sessions", {}).get("monitor-test", {})
        subagents = session.get("subagents", {})
        if subagents.get("spawned", 0) >= 1:
            print(f"  PASS  Progress file has correct sub-agent count              -> spawned={subagents['spawned']}")
            passed += 1
        else:
            print(f"  FAIL  Progress file sub-agent count                          -> spawned={subagents.get('spawned', 0)}")
            failed += 1

        errors = session.get("errors", [])
        if len(errors) >= 1:
            print(f"  PASS  Error tracking recorded                                -> errors={len(errors)}")
            passed += 1
        else:
            print(f"  FAIL  Error tracking not recorded                            -> errors={len(errors)}")
            failed += 1
    else:
        print(f"  FAIL  Progress file not found at {progress_file}")
        failed += 2

    return passed, failed


def test_slash_commands_skip():
    """Test that slash commands are skipped by hooks."""
    print()
    print("=" * 90)
    print("SLASH COMMAND SKIP TESTS")
    print("=" * 90)

    passed = 0
    failed = 0

    for cmd in ["/orchestrate something", "/rlm target", "/prime"]:
        out, code = run_hook("analyze_request.py", cmd)
        if code == 0 and (out is None or out == {}):
            print(f"  PASS  '{cmd}'  -> correctly skipped (no output)")
            passed += 1
        elif code == 0 and not out:
            print(f"  PASS  '{cmd}'  -> correctly skipped")
            passed += 1
        else:
            print(f"  FAIL  '{cmd}'  -> should have been skipped, got output")
            failed += 1

    return passed, failed


if __name__ == "__main__":
    total_passed = 0
    total_failed = 0

    p, f = test_analyze_request()
    total_passed += p
    total_failed += f

    p, f = test_auto_delegate()
    total_passed += p
    total_failed += f

    p, f = test_monitor_progress()
    total_passed += p
    total_failed += f

    p, f = test_slash_commands_skip()
    total_passed += p
    total_failed += f

    print()
    print("=" * 90)
    total = total_passed + total_failed
    print(f"TOTAL: {total_passed}/{total} passed, {total_failed} failed")
    print("=" * 90)

    sys.exit(0 if total_failed == 0 else 1)
