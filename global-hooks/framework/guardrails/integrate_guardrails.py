#!/usr/bin/env python3
"""
Integrate circuit breaker wrapper into Claude Code hooks settings.

This script wraps all hook commands with the circuit breaker wrapper to
provide anti-loop protection.
"""

import json
import shutil
from pathlib import Path

# Paths
SETTINGS_FILE = Path.home() / ".claude" / "settings.json"
BACKUP_FILE = Path.home() / ".claude" / "settings.json.backup-before-guardrails"
WRAPPER_PATH = "/Users/tomkwon/Documents/claude-agentic-framework/global-hooks/framework/guardrails/circuit_breaker_wrapper.py"

def wrap_command(command: str) -> str:
    """Wrap a command with the circuit breaker wrapper if not already wrapped."""
    if "circuit_breaker_wrapper.py" in command:
        return command  # Already wrapped

    return f"uv run {WRAPPER_PATH} -- {command}"

def process_hooks(hooks_config: dict) -> dict:
    """Process all hooks in the configuration."""
    modified = False

    for event_type, event_hooks in hooks_config.items():
        if not isinstance(event_hooks, list):
            continue

        for hook_group in event_hooks:
            if "hooks" not in hook_group:
                continue

            for hook in hook_group["hooks"]:
                if hook.get("type") == "command":
                    original_cmd = hook["command"]
                    wrapped_cmd = wrap_command(original_cmd)

                    if wrapped_cmd != original_cmd:
                        print(f"  Wrapping: {original_cmd[:80]}...")
                        hook["command"] = wrapped_cmd
                        modified = True

    return hooks_config, modified

def main():
    """Main integration logic."""
    print("Guardrails Integration")
    print("=" * 60)
    print()

    # Check if settings file exists
    if not SETTINGS_FILE.exists():
        print(f"Error: Settings file not found at {SETTINGS_FILE}")
        return 1

    # Create backup
    print(f"Creating backup: {BACKUP_FILE}")
    shutil.copy2(SETTINGS_FILE, BACKUP_FILE)
    print("✓ Backup created")
    print()

    # Load settings
    print("Loading settings...")
    with open(SETTINGS_FILE) as f:
        settings = json.load(f)

    if "hooks" not in settings:
        print("No hooks found in settings.json")
        return 0

    print("✓ Settings loaded")
    print()

    # Process hooks
    print("Wrapping hooks with circuit breaker...")
    settings["hooks"], modified = process_hooks(settings["hooks"])

    if not modified:
        print("✓ No hooks needed wrapping (already protected)")
        return 0

    print()
    print("✓ All hooks wrapped")
    print()

    # Write updated settings
    print("Writing updated settings...")
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

    print("✓ Settings updated")
    print()

    print("=" * 60)
    print("Integration Complete!")
    print()
    print("Guardrails System Status:")
    print("  ✓ Circuit breaker wrapper: Active")
    print("  ✓ All hooks protected: Yes")
    print("  ✓ Failure threshold: 3 consecutive failures")
    print("  ✓ Cooldown period: 5 minutes")
    print()
    print("Commands:")
    print("  claude-hooks health    # Monitor hook health")
    print("  claude-hooks list      # List all tracked hooks")
    print("  claude-hooks --help    # Show all commands")
    print()
    print(f"Backup saved at: {BACKUP_FILE}")
    print("To revert: cp ~/.claude/settings.json.backup-before-guardrails ~/.claude/settings.json")

    return 0

if __name__ == "__main__":
    exit(main())
