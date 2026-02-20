#!/usr/bin/env python3
"""
Korean Language Mode Hook - UserPromptSubmit

When korean_mode is enabled (~/.claude/korean_mode exists):
1. Detects Korean input
2. Translates to English via Haiku (token-efficient reasoning)
3. Injects English translation + Korean response instruction as additionalContext

Architecture:
  User (Korean) → Haiku translates → Main model reasons in English → Outputs Korean natively
  This avoids the main model burning tokens on translation; it just switches output language.
"""

import json
import os
import re
import sys
from pathlib import Path

KOREAN_RE = re.compile(r"[\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F\uA960-\uA97F\uD7B0-\uD7FF]")
FLAG_PATH = Path.home() / ".claude" / "korean_mode"


def has_korean(text: str) -> bool:
    return bool(KOREAN_RE.search(text))


def translate_to_english(text: str) -> str | None:
    """Translate Korean prompt to English using Haiku."""
    try:
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Translate the following Korean text to English. "
                        "Return ONLY the translation, no explanation:\n\n"
                        f"{text}"
                    ),
                }
            ],
        )
        return response.content[0].text.strip()
    except Exception:
        return None


def main():
    # Short-circuit if Korean mode is not enabled
    if not FLAG_PATH.exists():
        sys.exit(0)

    try:
        input_data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    prompt = input_data.get("prompt", "")
    if not prompt.strip():
        sys.exit(0)

    # Skip slash commands
    if prompt.strip().startswith("/"):
        sys.exit(0)

    context_lines = [
        "[한국어 모드 활성화 | Korean Mode Active]",
        "INSTRUCTION: Respond ENTIRELY in Korean (한국어). Every word of your response must be in Korean.",
        "INSTRUCTION: Use Korean for all explanations, code comments, variable names in prose, and summaries.",
    ]

    if has_korean(prompt):
        english = translate_to_english(prompt)
        if english:
            context_lines.append(
                f"\n[English translation of user's Korean prompt — use this for reasoning efficiency]:\n{english}"
            )
            context_lines.append(
                "Reason internally using the English translation above, but your output to the user MUST be in Korean."
            )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n".join(context_lines),
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
