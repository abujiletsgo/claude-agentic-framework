#!/usr/bin/env python3
"""
PreCompact Preservation Hook

Fires before any compaction (auto or manual). Reads the transcript to extract
key context that must survive compaction, then injects it as preservation
instructions so the compaction summary doesn't lose critical state.

Preserves:
  - Active/in-progress tasks (with proper ID→subject correlation)
  - Files modified this session (from Edit/Write tool calls)
  - Test commands that were run (from Bash tool calls)
  - Key decisions extracted from assistant text messages
  - Recent errors from Bash outputs
  - Git diff summary (what's actually changed on disk)

Exit: Always 0 (non-blocking)
"""

import json
import os
import subprocess
import sys
from pathlib import Path

SUMMARY_DIR = Path.home() / ".claude" / "data" / "compressed_context"


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


def get_block_text(content) -> str:
    """Extract text string from a content block (str or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(parts)
    return ""


def build_task_registry(messages: list[dict]) -> dict[str, str]:
    """
    Build a mapping of task_id -> subject by correlating:
      - TaskCreate tool_use blocks (have: tool_use id + subject in input)
      - tool_result blocks (have: tool_use_id + JSON with taskId)

    This fixes the original bug where active_tasks held subject strings
    while completed_tasks held ID strings — they never matched.
    """
    pending = {}  # tool_use_id -> subject (awaiting result)
    registry = {}  # task_id -> subject (confirmed)

    for msg in messages:
        content = msg.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict):
                continue

            btype = block.get("type", "")

            # Capture TaskCreate calls: remember tool_use_id -> subject
            if btype == "tool_use" and block.get("name") == "TaskCreate":
                tool_use_id = block.get("id", "")
                subject = block.get("input", {}).get("subject", "")
                if tool_use_id and subject:
                    pending[tool_use_id] = subject

            # Match tool results back to pending TaskCreate calls
            elif btype == "tool_result":
                tool_use_id = block.get("tool_use_id", "")
                if tool_use_id in pending:
                    text = get_block_text(block.get("content", ""))
                    try:
                        data = json.loads(text)
                        task_id = str(data.get("taskId") or data.get("id") or "")
                        if task_id:
                            registry[task_id] = pending[tool_use_id]
                    except (json.JSONDecodeError, AttributeError):
                        # Fallback: use tool_use_id as key if we can't parse
                        registry[tool_use_id] = pending[tool_use_id]
                    del pending[tool_use_id]

    return registry


def extract_tool_calls(messages: list[dict]) -> list[dict]:
    """Extract all tool_use blocks from transcript messages."""
    calls = []
    for msg in messages:
        content = msg.get("message", {}).get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    calls.append(block)
    return calls


def extract_tool_results(messages: list[dict]) -> list[dict]:
    """Extract all tool_result blocks keyed by tool_use_id."""
    results = {}
    for msg in messages:
        content = msg.get("message", {}).get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    tid = block.get("tool_use_id", "")
                    if tid:
                        results[tid] = block
    return results


# Keywords that signal a decision or key insight in assistant text
_DECISION_SIGNALS = [
    "decided", "chose", "choice:", "approach:", "strategy:",
    "going with", "will use", "using x because", "instead of",
    "key insight", "important:", "note:", "caveat:", "warning:",
    "root cause", "fix is", "the issue is", "because", "tradeoff",
    "recommendation", "prefer", "avoid", "do not", "never",
]


def extract_key_decisions(messages: list[dict]) -> list[str]:
    """
    Extract key decisions from assistant text messages.

    Heuristics:
    - Assistant role messages with text blocks
    - Contains at least one decision-signal keyword
    - Short enough to be a summary (< 400 chars) — long walls of text are not decisions
    - Bullet points from assistant responses (lines starting with - or •)
    """
    decisions = []
    seen = set()

    for msg in messages:
        role = msg.get("message", {}).get("role", "")
        if role != "assistant":
            continue

        content = msg.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict) or block.get("type") != "text":
                continue

            text = block.get("text", "").strip()
            if not text:
                continue

            text_lower = text.lower()

            # Extract bullet points that contain decision signals
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                # Must look like a bullet point
                if not (line.startswith("- ") or line.startswith("• ") or
                        line.startswith("* ") or line.startswith("→ ")):
                    continue
                # Must contain a decision signal
                line_lower = line.lower()
                if not any(sig in line_lower for sig in _DECISION_SIGNALS):
                    continue
                # Must be reasonably concise
                if len(line) > 300:
                    continue
                clean = line.lstrip("-•*→ ").strip()
                if clean and clean not in seen:
                    seen.add(clean)
                    decisions.append(clean)

            # Also capture short focused assistant messages that ARE a decision
            if len(text) < 400 and any(sig in text_lower for sig in _DECISION_SIGNALS):
                # Only single-paragraph messages (no double newlines = not a list/explanation)
                if "\n\n" not in text:
                    # Normalize: strip leading bullet chars before deduplicating
                    clean = text.lstrip("-•*→ ").strip()
                    if clean and clean not in seen:
                        seen.add(clean)
                        decisions.append(clean)

    return decisions[-15:]  # Keep last 15 decisions


# Error patterns in bash output
_ERROR_SIGNALS = [
    "error:", "traceback", "exception:", "failed:", "failure:",
    "fatal:", "critical:", "cannot", "no such file", "permission denied",
    "syntaxerror", "nameerror", "typeerror", "valueerror", "importerror",
    "modulenotfounderror", "attributeerror", "exit code", "returned non-zero",
    "command not found", "killed", "oom", "segfault",
]


def extract_recent_errors(
    messages: list[dict], tool_results: dict[str, dict]
) -> list[str]:
    """
    Extract recent errors from Bash tool results.

    Looks for tool_results where the output contains error signals.
    Captures the command and a short snippet of the error.
    """
    errors = []
    tool_calls = extract_tool_calls(messages)

    for call in tool_calls:
        if call.get("name") != "Bash":
            continue
        tool_use_id = call.get("id", "")
        result = tool_results.get(tool_use_id)
        if not result:
            continue

        output = get_block_text(result.get("content", ""))
        if not output:
            continue

        output_lower = output.lower()
        if not any(sig in output_lower for sig in _ERROR_SIGNALS):
            continue

        cmd = call.get("input", {}).get("command", "")[:80]
        # Grab the first error-containing line
        error_line = ""
        for line in output.splitlines():
            if any(sig in line.lower() for sig in _ERROR_SIGNALS):
                error_line = line.strip()[:150]
                break

        if error_line:
            entry = f"`{cmd}` → {error_line}"
            if entry not in errors:
                errors.append(entry)

    return errors[-8:]  # Keep last 8 errors


def load_precomputed_summaries(session_id: str) -> list[dict]:
    """
    Load structured summaries written by auto_context_manager.py.
    These are pre-computed for cold completed tasks and should be
    injected verbatim into the compaction prompt.
    """
    if not session_id or not SUMMARY_DIR.exists():
        return []
    summaries = []
    for p in SUMMARY_DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text())
            if data.get("session_id") == session_id:
                summaries.append(data)
        except Exception:
            pass
    return sorted(summaries, key=lambda x: x.get("end_turn") or 0)


def get_git_diff_stat() -> str:
    """Run git diff --stat to capture what's actually changed on disk."""
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        stat = result.stdout.strip()
        if stat:
            return stat
        # If HEAD diff is empty, try staged
        result2 = subprocess.run(
            ["git", "diff", "--stat", "--cached"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result2.stdout.strip()
    except Exception:
        return ""


def extract_key_context(messages: list[dict], session_id: str = "") -> dict:
    """Extract key context items from the transcript."""
    tool_calls = extract_tool_calls(messages)
    tool_results = extract_tool_results(messages)
    task_registry = build_task_registry(messages)  # task_id -> subject

    # Task tracking with proper ID correlation
    active_task_ids = []    # IDs of tasks that were created
    completed_task_ids = set()  # IDs of tasks marked completed
    in_progress_task_ids = set()

    modified_files = []
    test_commands = []
    seen_files = set()

    for call in tool_calls:
        name = call.get("name", "")
        inp = call.get("input", {})

        if name == "TaskCreate":
            # We'll resolve subject via task_registry; store tool_use_id for now
            # The registry handles the correlation
            pass

        elif name == "TaskUpdate":
            task_id = str(inp.get("taskId", ""))
            status = inp.get("status", "")
            if status == "completed" and task_id:
                completed_task_ids.add(task_id)
            elif status == "in_progress" and task_id:
                in_progress_task_ids.add(task_id)

        elif name in ("Edit", "Write"):
            fp = inp.get("file_path", "")
            if fp and fp not in seen_files:
                seen_files.add(fp)
                modified_files.append(fp)

        elif name == "Bash":
            cmd = inp.get("command", "")
            if cmd and any(kw in cmd for kw in [
                "pytest", "npm test", "npm run test", "bun test",
                "uv run pytest", "python -m pytest", "jest",
                "cargo test", "go test", "make test", "vitest",
            ]):
                test_commands.append(cmd[:80])

    # Build active tasks list: all tasks in registry that aren't completed
    active_tasks = []
    in_progress_tasks = []
    for task_id, subject in task_registry.items():
        if task_id in completed_task_ids:
            continue
        if task_id in in_progress_task_ids:
            in_progress_tasks.append(subject)
        else:
            active_tasks.append(subject)

    # In-progress tasks take priority in the list
    ordered_tasks = in_progress_tasks + active_tasks

    key_decisions = extract_key_decisions(messages)
    recent_errors = extract_recent_errors(messages, tool_results)
    git_stat = get_git_diff_stat()
    precomputed = load_precomputed_summaries(session_id)

    return {
        "active_tasks": ordered_tasks[-10:],
        "modified_files": modified_files[-20:],
        "test_commands": list(dict.fromkeys(test_commands))[-5:],
        "key_decisions": key_decisions,
        "recent_errors": recent_errors,
        "git_diff_stat": git_stat,
        "precomputed_summaries": precomputed,
    }


def build_preservation_instructions(context: dict, trigger: str) -> str:
    """Build compaction preservation instructions."""
    lines = [
        "═══ COMPACTION PRESERVATION INSTRUCTIONS ═══",
        f"Trigger: {trigger}",
        "The following context MUST be preserved verbatim in the compaction summary:",
        "",
    ]

    if context["active_tasks"]:
        lines.append("📋 ACTIVE / IN-PROGRESS TASKS (preserve as-is):")
        for task in context["active_tasks"]:
            lines.append(f"  • {task}")
        lines.append("")

    if context["modified_files"]:
        lines.append("📝 FILES MODIFIED THIS SESSION:")
        for fp in context["modified_files"]:
            lines.append(f"  • {fp}")
        lines.append("")

    if context["test_commands"]:
        lines.append("🧪 TEST COMMANDS RUN:")
        for cmd in context["test_commands"]:
            lines.append(f"  • {cmd}")
        lines.append("")

    if context["key_decisions"]:
        lines.append("🧠 KEY DECISIONS MADE:")
        for decision in context["key_decisions"]:
            lines.append(f"  • {decision}")
        lines.append("")

    if context["recent_errors"]:
        lines.append("⚠️  RECENT ERRORS (may still be relevant):")
        for err in context["recent_errors"]:
            lines.append(f"  • {err}")
        lines.append("")

    if context["git_diff_stat"]:
        lines.append("📦 GIT DIFF STAT (actual changes on disk):")
        for line in context["git_diff_stat"].splitlines():
            lines.append(f"  {line}")
        lines.append("")

    if context.get("precomputed_summaries"):
        lines.append("📁 PRE-COMPUTED TASK SUMMARIES (use these verbatim — already compressed):")
        for s in context["precomputed_summaries"]:
            lines.append(f"  ▸ Task: {s.get('subject', '?')}")
            if s.get("files_modified"):
                lines.append(f"    Files: {', '.join(s['files_modified'][:5])}")
            if s.get("key_outcomes"):
                for outcome in s["key_outcomes"][:3]:
                    lines.append(f"    → {outcome}")
            if s.get("errors_resolved"):
                for err in s["errors_resolved"][:2]:
                    lines.append(f"    ⚠ {err}")
        lines.append("")

    lines += [
        "COMPACTION RULES:",
        "  1. Include ALL active/in-progress tasks with their current status",
        "  2. Include the complete modified files list",
        "  3. Preserve all key decisions — these explain WHY things were done",
        "  4. Note any unresolved errors so work can resume correctly",
        "  5. Keep the git diff summary so the state of changes is clear",
        "  6. For PRE-COMPUTED SUMMARIES: use them verbatim, do not re-summarize",
        "  7. Preserve next steps and in-progress work state",
        "  8. Do NOT discard any pending/in-progress task context",
        "═══════════════════════════════════════════",
    ]

    return "\n".join(lines)


def main():
    try:
        input_data = json.load(sys.stdin)
        transcript_path = input_data.get("transcript_path", "")
        trigger = input_data.get("trigger", "auto")
        session_id = input_data.get("session_id") or os.environ.get("CLAUDE_SESSION_ID", "")

        if not transcript_path:
            sys.exit(0)

        messages = parse_transcript(transcript_path)
        if not messages:
            sys.exit(0)

        context = extract_key_context(messages, session_id)

        has_content = any([
            context["active_tasks"],
            context["modified_files"],
            context["test_commands"],
            context["key_decisions"],
            context["recent_errors"],
            context["git_diff_stat"],
            context["precomputed_summaries"],
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
