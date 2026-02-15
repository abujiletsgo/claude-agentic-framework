#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = ["pyttsx3"]
# ///
"""
Auto Voice Notifications - PostToolUse Hook

Speaks notifications for:
- Task completions
- Errors/attention needed
- Agent team updates

Uses pyttsx3 for offline TTS (free).

Exit codes:
  0: Always (non-blocking)
"""

import json
import sys
import os
import subprocess
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────────

# Enable/disable voice notifications
VOICE_ENABLED = os.environ.get("VOICE_NOTIFICATIONS", "true").lower() == "true"

# TTS engine path
TTS_SCRIPT = Path(__file__).parent / "pyttsx3_tts.py"

# ─── Notification Messages ───────────────────────────────────────────

TASK_COMPLETED_MESSAGES = [
    "Task complete!",
    "Done!",
    "Finished!",
    "All set!",
    "Task finished!"
]

ERROR_MESSAGES = [
    "Attention needed!",
    "Error detected!",
    "Check the output!",
    "Something needs your attention!"
]

TEAM_UPDATE_MESSAGES = [
    "Team update!",
    "Agent finished!",
    "Worker done!"
]

# ─── Detection Logic ─────────────────────────────────────────────────

def detect_task_completion(hook_input):
    """Detect if a task was marked as completed."""
    # Flat snake_case keys per Claude Code docs
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Check if TaskUpdate with status=completed
    if tool_name == "TaskUpdate":
        status = tool_input.get("status", "")
        if status == "completed":
            subject = tool_input.get("subject", "Task")
            return True, subject

    return False, None

def detect_error_or_attention(hook_input):
    """Detect if there's an error or attention needed."""
    tool_name = hook_input.get("tool_name", "")
    tool_response = str(hook_input.get("tool_response", ""))

    # Check for error indicators in tool response
    error_indicators = [
        "error",
        "failed",
        "exception",
        "attention needed",
        "critical"
    ]

    output_lower = tool_response.lower()

    for indicator in error_indicators:
        if indicator in output_lower:
            return True, indicator

    return False, None

def detect_team_update(hook_input):
    """Detect team member completion."""
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name == "SendMessage":
        msg_type = tool_input.get("type", "")

        if msg_type in ["message", "broadcast"]:
            content = tool_input.get("content", "")
            if "completed" in content.lower() or "done" in content.lower():
                return True

    return False

# ─── TTS Playback ────────────────────────────────────────────────────

def speak(message):
    """Speak a message using pyttsx3 TTS."""
    if not VOICE_ENABLED:
        return

    if not TTS_SCRIPT.exists():
        print(f"[Voice] TTS script not found: {TTS_SCRIPT}", file=sys.stderr)
        return

    try:
        # Run TTS script in background (non-blocking)
        subprocess.Popen(
            ["uv", "run", str(TTS_SCRIPT), message],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    except Exception as e:
        print(f"[Voice] TTS error: {e}", file=sys.stderr)

# ─── Main Hook Logic ─────────────────────────────────────────────────

def main():
    try:
        # Read hook input
        hook_input = json.load(sys.stdin)

        # Check for task completion
        is_completed, subject = detect_task_completion(hook_input)
        if is_completed:
            import random
            message = random.choice(TASK_COMPLETED_MESSAGES)
            if subject and len(subject) < 30:
                message = f"{subject} complete!"
            speak(message)
            print(f"🔊 [Voice] {message}", file=sys.stderr)

        # Check for errors/attention
        has_error, error_type = detect_error_or_attention(hook_input)
        if has_error:
            import random
            message = random.choice(ERROR_MESSAGES)
            speak(message)
            print(f"🔊 [Voice] {message}", file=sys.stderr)

        # Check for team updates
        if detect_team_update(hook_input):
            import random
            message = random.choice(TEAM_UPDATE_MESSAGES)
            speak(message)
            print(f"🔊 [Voice] {message}", file=sys.stderr)

    except Exception as e:
        # Non-blocking: don't fail on TTS errors
        print(f"[Voice] Hook error (non-blocking): {e}", file=sys.stderr)

    # Always exit 0 (non-blocking)
    sys.exit(0)

if __name__ == "__main__":
    main()
