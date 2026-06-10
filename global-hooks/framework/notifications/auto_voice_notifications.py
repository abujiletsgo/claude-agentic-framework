#!/usr/bin/env python3
"""
auto_voice_notifications.py — TTS only when user input is required.
Fires ONLY on AskUserQuestion tool calls.

Picks the spoken phrase based on question content:
  - "please confirm"  → confirmation-style ask (yes/no, are you sure, proceed?)
  - "question"        → general question
  - "input required"  → fallback when content can't be inspected
"""
import json
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
    try:
        subprocess.run(
            ["/usr/bin/say", text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
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

    if hook_input.get("tool_name", "") != "AskUserQuestion":
        sys.exit(0)

    question_text = extract_question_text(hook_input.get("tool_input"))
    speak(classify(question_text))
    sys.exit(0)


if __name__ == "__main__":
    main()
