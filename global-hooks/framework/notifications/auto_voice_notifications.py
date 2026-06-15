#!/usr/bin/env python3
"""
auto_voice_notifications.py — TTS when Claude needs the user.

Handles two hook events:
  - PreToolUse / AskUserQuestion : speaks a phrase based on the question content
  - Notification                 : speaks when Claude Code raises a notification
                                   (permission needed, or idle waiting for input)

The Notification event is the reliable one: AskUserQuestion is an interactive
tool that does NOT always pass through the PreToolUse gate, so registering on
Notification guarantees an audible alert whenever Claude is blocked on you.

Phrases:
  - "please confirm"   → confirmation-style ask (yes/no, are you sure, proceed?)
  - "question"         → general question
  - "permission needed"→ Notification asking to approve a tool
  - "input required"   → fallback when content can't be inspected

Voice: uses the macOS default system voice. To pin a specific voice, set the
CAF_TTS_VOICE env var (e.g. CAF_TTS_VOICE="Zoe (Premium)") — see
System Settings → Accessibility → Spoken Content → System Voice to install more.
"""
import json
import os
import re
import sys
import subprocess


CONFIRM_PATTERNS = re.compile(
    r"\b(confirm|are you sure|sure\?|proceed|continue|ok to|okay to|"
    r"shall i|should i|do you want|approve|approval|yes/no|y/n|"
    r"go ahead|safe to|delete|overwrite|force[- ]?push|reset|drop)\b",
    re.IGNORECASE,
)


def speak(text: str) -> None:
    cmd = ["/usr/bin/say"]
    voice = os.environ.get("CAF_TTS_VOICE", "").strip()
    if voice:
        cmd += ["-v", voice]
    cmd.append(text)
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def extract_question_text(tool_input) -> str:
    """Pull every bit of question text out of the AskUserQuestion tool_input."""
    if not isinstance(tool_input, dict):
        return ""
    parts = []
    # Common shapes: {"question": "..."} or {"questions": [{"question": "...", "header": "..."}]}
    if isinstance(tool_input.get("question"), str):
        parts.append(tool_input["question"])
    if isinstance(tool_input.get("header"), str):
        parts.append(tool_input["header"])
    questions = tool_input.get("questions")
    if isinstance(questions, list):
        for q in questions:
            if isinstance(q, dict):
                for key in ("question", "header"):
                    val = q.get(key)
                    if isinstance(val, str):
                        parts.append(val)
    return " ".join(parts)


def classify(question_text: str) -> str:
    if not question_text:
        return "input required"
    if CONFIRM_PATTERNS.search(question_text):
        return "please confirm"
    return "question"


def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")
    event = hook_input.get("hook_event_name", "")

    if tool_name == "AskUserQuestion":
        question_text = extract_question_text(hook_input.get("tool_input"))
        speak(classify(question_text))
    elif event == "Notification" or hook_input.get("message"):
        # Claude Code raised a notification — permission request or idle wait.
        message = str(hook_input.get("message", "") or "")
        if re.search(r"\b(permission|approve|allow|trust)\b", message, re.IGNORECASE):
            speak("permission needed")
        else:
            speak("input required")

    sys.exit(0)


if __name__ == "__main__":
    main()
