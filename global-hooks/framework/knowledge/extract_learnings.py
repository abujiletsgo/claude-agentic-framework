#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Extract Learnings - PostToolUse Hook
=====================================

Monitors tool outputs for knowledge-worthy content and automatically
stores it in the knowledge database. Looks for patterns like:

- Error corrections (LEARNED)
- Architecture decisions (DECISION)
- Project facts discovered (FACT)
- Recurring patterns (PATTERN)
- Open questions (INVESTIGATION)

This hook reads from stdin (Claude hook protocol) and never blocks.
Exit: Always 0 (never blocks the tool pipeline)
"""

import json
import re
import sys
from pathlib import Path

# Import knowledge_db from same directory
sys.path.insert(0, str(Path(__file__).parent))


# Explicit markers in file content or command output
_EXPLICIT_MARKERS = {
    r"#\s*DECISION\s*:\s*(.+)": "DECISION",
    r"#\s*LEARNED\s*:\s*(.+)": "LEARNED",
    r"#\s*FACT\s*:\s*(.+)": "FACT",
    r"#\s*NOTE\s*:\s*(.+)": "FACT",
    r"#\s*PATTERN\s*:\s*(.+)": "PATTERN",
    r"#\s*INVESTIGATION\s*:\s*(.+)": "INVESTIGATION",
    r"#\s*TODO.*investigate\s*:\s*(.+)": "INVESTIGATION",
}

# Success signals in Bash output → LEARNED
_SUCCESS_SIGNALS = [
    r"(\d+) passed",
    r"all tests passed",
    r"build successful",
    r"successfully installed",
    r"successfully deployed",
    r"successfully migrated",
    r"done\. start a new",
    r"installed successfully",
]

# Key config/architecture file patterns → DECISION
_ARCH_FILES = (
    "architecture", "config", "schema", "migration",
    ".env", "dockerfile", "docker-compose", "makefile",
    "justfile", "pyproject.toml", "package.json", "install.sh",
    "settings.json", "requirements.txt", "cargo.toml",
)

# Key knowledge files worth reading for FACTs
_KNOWLEDGE_FILES = (
    "readme", "claude.md", "contributing", "architecture",
    "framework_reference", "quickstart", "admin",
)


def extract_from_tool_output(tool_name: str, tool_input: dict, tool_output: str, session_id: str) -> list[dict]:
    """
    Analyze tool output and extract knowledge entries.
    Returns a list of dicts with keys: content, tag, context
    """
    entries = []
    output = tool_output or ""
    output_lower = output.lower()
    tool_input = tool_input or {}

    # --- Bash ---
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        desc = tool_input.get("description", "")

        # Errors → INVESTIGATION
        if any(kw in output_lower for kw in ("error:", "failed", "traceback", "exception", "syntax error")):
            if len(output) < 2000:
                entries.append({
                    "content": f"Command produced error: `{command[:120]}`\nOutput: {output[:400]}",
                    "tag": "INVESTIGATION",
                    "context": _infer_context(command),
                })

        # Success signals → LEARNED
        for pattern in _SUCCESS_SIGNALS:
            m = re.search(pattern, output_lower)
            if m:
                label = desc or command[:80]
                entries.append({
                    "content": f"Successful outcome: {label}\nSignal: {m.group(0)}",
                    "tag": "LEARNED",
                    "context": _infer_context(command),
                })
                break  # one LEARNED per command

        # Git commits → DECISION (what was decided/committed)
        if "git commit" in command and output:
            m = re.search(r"\[[\w/]+ \w+\]\s+(.+)", output)
            if m:
                entries.append({
                    "content": f"Git commit: {m.group(1).strip()}",
                    "tag": "DECISION",
                    "context": _infer_context(command),
                })

        # Install/setup commands → FACT
        if any(kw in command for kw in ("install.sh", "npm install", "pip install", "uv sync", "brew install")):
            if "error" not in output_lower and len(output) < 1000:
                entries.append({
                    "content": f"Installed/set up: `{command[:120]}`",
                    "tag": "FACT",
                    "context": _infer_context(command),
                })

    # --- Write / Edit ---
    elif tool_name in ("Write", "Edit"):
        file_path = tool_input.get("file_path", "")
        content = tool_input.get("new_string", "") or tool_input.get("content", "")

        # Architecture/config files → DECISION
        if any(name in file_path.lower() for name in _ARCH_FILES):
            entries.append({
                "content": f"Modified architecture/config file: {file_path}",
                "tag": "DECISION",
                "context": _infer_context(file_path),
            })

        # New file creation → FACT (skip temp files and /tmp/)
        if tool_name == "Write" and file_path:
            fname = Path(file_path).name.lower()
            if (not file_path.startswith("/tmp/")
                    and not any(fname.endswith(ext) for ext in (".log", ".tmp", ".pyc", ".txt"))):
                entries.append({
                    "content": f"Created file: {file_path}",
                    "tag": "FACT",
                    "context": _infer_context(file_path),
                })

        # Explicit markers in written content
        entries.extend(_extract_markers(content, file_path))

    # --- Read (key knowledge files only) ---
    elif tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        fname = Path(file_path).name.lower()
        if any(kw in fname for kw in _KNOWLEDGE_FILES):
            # Extract first meaningful paragraph as a FACT
            lines = [l.strip() for l in output.splitlines() if l.strip() and not l.strip().startswith("#")]
            if lines:
                snippet = " ".join(lines[:3])[:200]
                entries.append({
                    "content": f"Key file `{Path(file_path).name}`: {snippet}",
                    "tag": "FACT",
                    "context": _infer_context(file_path),
                })

    # --- Explicit markers in any tool output ---
    entries.extend(_extract_markers(output, tool_input.get("file_path", "") or tool_input.get("command", "")))

    # Deduplicate by content
    seen = set()
    unique = []
    for e in entries:
        key = (e["tag"], e["content"][:100])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique


def _extract_markers(text: str, source: str) -> list[dict]:
    """Extract explicit DECISION/LEARNED/FACT markers from text."""
    entries = []
    for pattern, tag in _EXPLICIT_MARKERS.items():
        for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            content = m.group(1).strip()
            if len(content) > 10:
                entries.append({
                    "content": content,
                    "tag": tag,
                    "context": _infer_context(source),
                })
    return entries


def _infer_context(text: str) -> str:
    """Infer a context label from a file path or command."""
    text = text.lower()
    patterns = {
        "vaultmind": "vaultmind",
        "claude-agentic": "claude-agentic-framework",
        "obsidian": "obsidian",
        "knowledge": "knowledge-system",
        "hook": "hooks",
        "agent": "agents",
        "test": "testing",
        "docker": "infrastructure",
        "deploy": "deployment",
    }
    for keyword, ctx in patterns.items():
        if keyword in text:
            return ctx
    return "general"


def main():
    """Hook entry point - reads from stdin, never blocks."""
    try:
        input_data = json.load(sys.stdin)

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        tool_output = str(input_data.get("tool_output", ""))
        session_id = input_data.get("session_id", "unknown")

        entries = extract_from_tool_output(tool_name, tool_input, tool_output, session_id)

        if entries:
            try:
                from knowledge_db import add_knowledge
                for entry in entries:
                    add_knowledge(
                        content=entry["content"],
                        tag=entry["tag"],
                        context=entry.get("context"),
                        session_id=session_id,
                    )
            except Exception:
                # Never block on DB errors
                pass

    except Exception:
        # Never block the pipeline
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
