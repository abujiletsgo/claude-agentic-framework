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
import time
from pathlib import Path

# Add framework to path
framework_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(framework_dir))


def _cleanup_stale_orch_state():
    """Remove stale orchestration guard state older than 24h."""
    orch_state_dir = Path.home() / '.caf' / 'orch_state'
    depth_file = orch_state_dir / 'depth'
    marker_file = orch_state_dir / 'guard.marker'

    if not depth_file.exists():
        return

    try:
        data = json.loads(depth_file.read_text())
        ts_str = data.get('ts', '')
        # Parse RFC3339 or unix timestamp
        if ts_str:
            from datetime import datetime, timezone
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            age_seconds = (datetime.now(timezone.utc) - ts).total_seconds()
            if age_seconds > 86400:
                depth_file.unlink(missing_ok=True)
                marker_file.unlink(missing_ok=True)
                age_h = int(age_seconds / 3600)
                print(f"[CAF] Cleaned stale orch state (age: {age_h}h)", file=sys.stderr)
    except Exception:
        pass  # Never block session startup


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
    _cleanup_stale_orch_state()
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
        "automation/auto_prime.py",
        "automation/inject_always_loaded_skills.py",
        "session/spawn_hud.py",
    ]

    messages = []

    for hook_path in hooks:
        full_path = framework_dir / hook_path
        if not full_path.exists():
            continue

        try:
            import subprocess
            result = subprocess.run(
                ["uv", "run", "--no-project", str(full_path)],
                input=hook_input_str,
                capture_output=True,
                text=True,
                timeout=15
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
        log("main() completed OK")
    except Exception as _e:
        log(f"main() raised: {type(_e).__name__}: {_e}")
        # Last-resort guard: always exit 0 with valid JSON
        try:
            sys.stdout.write("{}\n")
        except Exception:
            pass
        sys.exit(0)
