#!/usr/bin/env python3
"""
Test runner for claude-agentic-framework.

Wraps eval_framework.py with CLI flags for CI integration.

Usage:
    python3 scripts/run_tests.py              # Run all tests
    python3 scripts/run_tests.py --fast       # Skip slow tests (knowledge pipeline, hook functional tests)
    python3 scripts/run_tests.py --verbose    # Show all output including passes
    python3 scripts/run_tests.py --fast -v    # Combined

Exit codes:
    0  All tests passed
    1  One or more tests failed
"""

import argparse
import sys
import os
from pathlib import Path

# Ensure the scripts directory is importable
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))


def main():
    parser = argparse.ArgumentParser(
        description="Run claude-agentic-framework evaluation tests"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip slow tests (knowledge pipeline, hook functional tests)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show verbose output including all pass messages",
    )
    args = parser.parse_args()

    # Import the eval module
    import eval_framework as ev

    if not args.verbose:
        # In non-verbose mode, suppress individual PASS messages
        original_pass = ev.PASS
        def quiet_pass(desc):
            ev._results.append(("PASS", ev._section, desc))
        ev.PASS = quiet_pass

    # Determine which test suites to run
    test_suites = [
        ("Install Validation", ev.test_install_validation, False),
        ("Knowledge Pipeline", ev.test_knowledge_pipeline, True),  # slow
        ("Hook Scripts", ev.test_hook_scripts, True),              # slow
        ("Damage Control Patterns", ev.test_damage_control, False),
        ("Agent Definitions", ev.test_agent_definitions, False),
        ("Settings Template", ev.test_settings_template, False),
        ("Skills", ev.test_skills, False),
        ("Memory Layer Guide", ev.test_memory_layer_guide, False),
    ]

    print("=" * 60)
    print("  Claude Agentic Framework - Test Runner")
    print(f"  Repo: {ev.REPO_DIR}")
    print(f"  Mode: {'fast' if args.fast else 'full'}")
    print("=" * 60)

    skipped_suites = []
    for name, test_fn, is_slow in test_suites:
        if args.fast and is_slow:
            skipped_suites.append(name)
            ev.section(name)
            ev.SKIP(f"Skipped in --fast mode", "slow test")
            continue
        test_fn()

    # Summary
    print("\n" + "=" * 60)
    print("  FINAL RESULTS")
    print("=" * 60)

    pass_count = sum(1 for s, _, _ in ev._results if s == "PASS")
    fail_count = sum(1 for s, _, _ in ev._results if s == "FAIL")
    skip_count = sum(1 for s, _, _ in ev._results if s == "SKIP")
    total = len(ev._results)

    if fail_count > 0:
        print("\n  FAILURES:")
        for status, sec, msg in ev._results:
            if status == "FAIL":
                print(f"    FAIL  [{sec}] {msg}")

    if skip_count > 0:
        print(f"\n  SKIPPED: {skip_count} test(s)")
        if args.verbose:
            for status, sec, msg in ev._results:
                if status == "SKIP":
                    print(f"    SKIP  [{sec}] {msg}")

    if skipped_suites:
        print(f"  Skipped suites (--fast): {', '.join(skipped_suites)}")

    print(f"\n  Score: {pass_count}/{total} tests passed")
    if skip_count:
        print(f"  ({skip_count} skipped)")
    if fail_count == 0:
        print("  ALL TESTS PASSED")
    else:
        print(f"  {fail_count} FAILURE(S)")

    print()
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
