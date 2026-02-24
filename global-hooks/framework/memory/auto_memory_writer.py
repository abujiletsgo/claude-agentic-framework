#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
auto_memory_writer.py - Stop Hook (Layer 2: Project Mid-Term Memory Write)
===========================================================================

At session end, appends a compact summary to .claude/MEMORY.md.

Captures what actually happened in the session using ground-truth signals:
  - git diff --stat (files changed — most reliable signal)
  - git log -1 (last commit message if one was made)
  - Task summaries from auto_context_manager compressed context

Format: one dated entry per session, ~5-15 lines.
Only writes if something actually changed (git diff non-empty).

Exit: always 0 (never blocks)
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

COMPRESSED_DIR = Path.home() / ".claude" / "data" / "compressed_context"
MAX_MEMORY_ENTRIES = 30     # Prune oldest entries if file grows beyond this
MAX_ENTRY_LINES = 20        # Cap per-session entry to keep file lean


def memory_path(cwd: str) -> Path:
    return Path(cwd).resolve() / ".claude" / "MEMORY.md"


def run(cmd: list, cwd: str, timeout: int = 5) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def get_git_changes(cwd: str) -> list[str]:
    """Get changed files from git diff. Returns list of 'N files changed' lines."""
    stat = run(["git", "diff", "--stat", "HEAD~1", "HEAD", "--"], cwd)
    if not stat:
        # No commit yet — try staged/unstaged changes
        stat = run(["git", "diff", "--stat"], cwd)
    if not stat:
        stat = run(["git", "diff", "--stat", "--cached"], cwd)
    if not stat:
        return []
    return [line for line in stat.splitlines() if line.strip()]


def get_last_commit(cwd: str) -> str:
    return run(["git", "log", "-1", "--format=%s (%h)"], cwd)


def get_compressed_summaries(session_id: str) -> list[str]:
    """Read any compressed task summaries from auto_context_manager for this session."""
    summaries = []
    if not COMPRESSED_DIR.exists():
        return summaries
    try:
        for f in sorted(COMPRESSED_DIR.glob(f"{session_id[:8]}*.json")):
            data = json.loads(f.read_text())
            subj = data.get("subject", "")
            outcome = data.get("outcome", "")
            if subj:
                line = f"- Task: {subj}"
                if outcome:
                    line += f" → {outcome}"
                summaries.append(line)
    except Exception:
        pass
    return summaries[:5]  # Cap at 5 task summaries


def build_entry(cwd: str, session_id: str) -> str | None:
    """Build a session memory entry. Returns None if nothing to record."""
    lines = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    time_str = datetime.now(timezone.utc).strftime("%H:%M UTC")
    project = Path(cwd).resolve().name

    # Ground truth: what files actually changed
    git_changes = get_git_changes(cwd)
    last_commit = get_last_commit(cwd)
    task_summaries = get_compressed_summaries(session_id)

    # Only write if something happened
    if not git_changes and not task_summaries:
        return None

    lines.append(f"## {today} ({time_str})")

    if last_commit:
        lines.append(f"**Commit:** {last_commit}")

    if git_changes:
        lines.append("**Changed:**")
        # Show file list, cap at 10
        for line in git_changes[:10]:
            if "|" in line or "changed" in line:
                lines.append(f"  {line.strip()}")
        if len(git_changes) > 10:
            lines.append(f"  ... and {len(git_changes) - 10} more files")

    if task_summaries:
        lines.append("**Tasks completed:**")
        lines.extend(task_summaries)

    lines.append("")  # trailing newline
    return "\n".join(lines)


def prune_old_entries(content: str, max_entries: int) -> str:
    """Keep only the most recent max_entries session blocks."""
    parts = re.split(r"(## \d{4}-\d{2}-\d{2})", content)
    if len(parts) <= 1:
        return content

    file_header = parts[0]
    sessions = []
    i = 1
    while i < len(parts):
        header = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        sessions.append(header + body)
        i += 2

    if len(sessions) <= max_entries:
        return content

    # Keep most recent
    return file_header + "".join(sessions[-max_entries:])


def ensure_memory_file(path: Path, project: str) -> str:
    """Create MEMORY.md if it doesn't exist."""
    if path.exists():
        return path.read_text()

    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# Project Memory — {project}\n"
        "<!-- Mid-term project memory: one entry per session. Auto-maintained. -->\n"
        "<!-- Layer 2 (episodic): what changed, was fixed, was decided across sessions. -->\n\n"
    )
    path.write_text(header)
    return header


def main():
    try:
        data = json.loads(sys.stdin.read())
        cwd = data.get("cwd", os.getcwd())
        session_id = data.get("session_id", "unknown")
        project = Path(cwd).resolve().name
        path = memory_path(cwd)

        entry = build_entry(cwd, session_id)
        if not entry:
            print(json.dumps({}))
            sys.exit(0)

        content = ensure_memory_file(path, project)
        content = content.rstrip() + "\n\n" + entry
        content = prune_old_entries(content, MAX_MEMORY_ENTRIES)
        path.write_text(content)

    except Exception as e:
        print(f"auto_memory_writer error: {e}", file=sys.stderr)

    print(json.dumps({}))
    sys.exit(0)


if __name__ == "__main__":
    main()
