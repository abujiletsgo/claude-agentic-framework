#!/usr/bin/env python3
"""
auto_voice_notifications.py — TTS only when user input is required.
Fires ONLY on AskUserQuestion tool calls.
"""
import json
import sys
import subprocess


def speak(text: str) -> None:
    try:
        subprocess.Popen(["say", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")

    if tool_name == "AskUserQuestion":
        speak("Input required")

    sys.exit(0)


if __name__ == "__main__":
    main()
