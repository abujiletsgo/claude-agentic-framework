#!/usr/bin/env python3
"""
Voice Done - Stop Hook

Announces when Claude finishes a response.
Uses macOS 'say' command (built-in, no dependencies).
Falls back silently on non-macOS.

Exit codes:
  0: Always (non-blocking)
"""

import json
import sys
import os
import subprocess
import platform

VOICE_ENABLED = os.environ.get("VOICE_NOTIFICATIONS", "true").lower() == "true"

DONE_MESSAGES = [
    "Done.",
    "Finished.",
    "Ready.",
    "Complete.",
]


def speak(message: str):
    if not VOICE_ENABLED:
        return
    if platform.system() != "Darwin":
        return
    try:
        subprocess.Popen(
            ["say", message],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass


def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    # Only speak on non-error stop (stop_hook_active means normal completion)
    stop_reason = hook_input.get("stop_reason", "")
    if stop_reason in ("error", "cancelled"):
        sys.exit(0)

    import random
    speak(random.choice(DONE_MESSAGES))
    sys.exit(0)


if __name__ == "__main__":
    main()
