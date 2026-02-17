#!/usr/bin/env python3
"""
Consolidated SessionStart Hook

Runs all session startup tasks in sequence:
1. Session lock management
2. Skills integrity verification
3. Documentation validation
4. Auto-prime cache loading
"""
import json
import sys
import os
from pathlib import Path

# Add framework to path
framework_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(framework_dir))


def emit(obj):
    """Output JSON to stdout"""
    sys.stdout.write(json.dumps(obj) + "\n")


_LOG = Path("/tmp/claude_startup_debug.log")


def log(msg):
    try:
        with open(_LOG, "a") as f:
            import datetime
            f.write(f"{datetime.datetime.now().isoformat()} [startup] {msg}\n")
    except Exception:
        pass


def main():
    """Run all startup hooks in sequence."""
    log("main() started")
    # Read hook input once (sub-hooks use hook_event_name from JSON)
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}
    except Exception:
        hook_input = {}
    hook_input_str = json.dumps(hook_input)

    hooks = [
        "session/session_lock_manager.py",
        "security/verify_skills.py",
        "security/validate_docs.py",
        "automation/auto_prime.py"
    ]

    messages = []

    for hook_path in hooks:
        full_path = framework_dir / hook_path
        if not full_path.exists():
            continue

        try:
            import subprocess
            result = subprocess.run(
                ["uv", "run", str(full_path)],
                input=hook_input_str,
                capture_output=True,
                text=True,
                timeout=10
            )

            # Capture stderr warnings (like doc validation)
            if result.stderr:
                # Only show non-empty stderr
                stderr_clean = result.stderr.strip()
                if stderr_clean and not stderr_clean.startswith("Resolved"):
                    sys.stderr.write(stderr_clean + "\n")

            # Parse result
            if result.stdout.strip():
                try:
                    hook_result = json.loads(result.stdout.strip())
                    # Collect any messages
                    if "message" in hook_result:
                        messages.append(hook_result["message"])
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            # Non-blocking - log but continue
            sys.stderr.write(f"Startup hook {hook_path} error: {e}\n")

    # Build final result using correct SessionStart format
    if messages:
        emit({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "\n".join(messages)
            }
        })
    else:
        emit({})


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Last-resort guard: always exit 0 with valid JSON
        try:
            sys.stdout.write("{}\n")
        except Exception:
            pass
        sys.exit(0)
