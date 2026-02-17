#!/usr/bin/env python3
"""
PreCompact Preservation Hook

Fires before any compaction (auto or manual). Reads the transcript to extract
key context that must survive compaction, then injects it as preservation
instructions so the compaction summary doesn't lose critical state.

Preserves:
  - Active/in-progress tasks (from TaskCreate/TaskUpdate calls)
  - Files modified this session (from Edit/Write tool calls)
  - Test commands that were run (from Bash tool calls)
  - Key decisions and validations

Exit: Always 0 (non-blocking)
"""

import json
import sys
from pathlib import Path
from collections import defaultdict


def parse_transcript(transcript_path: str) -> list[dict]:
    """Read and parse JSONL transcript file."""
    messages = []
    try:
        path = Path(transcript_path)
        if not path.exists():
            return []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return messages


def extract_tool_calls(messages: list[dict]) -> list[dict]:
    """Extract all tool calls from transcript messages."""
    calls = []
    for msg in messages:
        content = msg.get("message", {}).get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    calls.append(block)
    return calls


def extract_key_context(messages: list[dict]) -> dict:
    """Extract key context items from the transcript."""
    tool_calls = extract_tool_calls(messages)

    # Track tasks: look for TaskCreate/TaskUpdate tool calls
    active_tasks = []
    completed_tasks = []
    modified_files = []
    test_commands = []
    key_decisions = []

    seen_files = set()

    for call in tool_calls:
        name = call.get("name", "")
        inp = call.get("input", {})

        # Task tracking
        if name == "TaskCreate":
            subject = inp.get("subject", "")
            if subject:
                active_tasks.append(subject)

        elif name == "TaskUpdate":
            status = inp.get("status", "")
            task_id = inp.get("taskId", "")
            if status == "completed" and task_id:
                completed_tasks.append(task_id)
            elif status == "in_progress":
                pass  # Already in active_tasks from TaskCreate

        # File modifications
        elif name in ("Edit", "Write"):
            fp = inp.get("file_path", "")
            if fp and fp not in seen_files:
                seen_files.add(fp)
                modified_files.append(fp)

        # Test / build commands
        elif name == "Bash":
            cmd = inp.get("command", "")
            if cmd and any(kw in cmd for kw in [
                "pytest", "npm test", "npm run test", "bun test",
                "uv run pytest", "python -m pytest", "jest",
                "cargo test", "go test", "make test", "vitest"
            ]):
                test_commands.append(cmd[:80])

    # Remove completed tasks from active list
    active_tasks = [t for t in active_tasks if t not in completed_tasks]

    return {
        "active_tasks": active_tasks[-10:],       # Last 10 active tasks
        "modified_files": modified_files[-20:],   # Last 20 modified files
        "test_commands": list(dict.fromkeys(test_commands))[-5:],  # Last 5 unique test commands
    }


def build_preservation_instructions(context: dict, trigger: str) -> str:
    """Build compaction preservation instructions."""
    lines = [
        "═══ COMPACTION PRESERVATION INSTRUCTIONS ═══",
        "The following context MUST be preserved verbatim in the compaction summary:",
        "",
    ]

    if context["active_tasks"]:
        lines.append("📋 ACTIVE TASKS (preserve as-is):")
        for task in context["active_tasks"]:
            lines.append(f"  • {task}")
        lines.append("")

    if context["modified_files"]:
        lines.append("📝 MODIFIED FILES THIS SESSION:")
        for fp in context["modified_files"]:
            lines.append(f"  • {fp}")
        lines.append("")

    if context["test_commands"]:
        lines.append("🧪 TEST COMMANDS RUN:")
        for cmd in context["test_commands"]:
            lines.append(f"  • {cmd}")
        lines.append("")

    lines += [
        "COMPACTION RULES:",
        "  1. Include all active tasks with their current status",
        "  2. Include the complete modified files list",
        "  3. Preserve any in-progress work state and next steps",
        "  4. Keep key technical decisions and validation results",
        "  5. Do NOT discard any pending/in-progress task context",
        "═══════════════════════════════════════════",
    ]

    return "\n".join(lines)


def main():
    try:
        input_data = json.load(sys.stdin)
        transcript_path = input_data.get("transcript_path", "")
        trigger = input_data.get("trigger", "auto")

        if not transcript_path:
            sys.exit(0)

        # Parse transcript and extract key context
        messages = parse_transcript(transcript_path)
        if not messages:
            sys.exit(0)

        context = extract_key_context(messages)

        # Only inject if there's something worth preserving
        has_content = any([
            context["active_tasks"],
            context["modified_files"],
            context["test_commands"],
        ])

        if not has_content:
            sys.exit(0)

        instructions = build_preservation_instructions(context, trigger)

        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreCompact",
                "additionalContext": instructions,
            }
        }
        print(json.dumps(output))

    except Exception as e:
        print(f"pre_compact_preserve error (non-blocking): {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
