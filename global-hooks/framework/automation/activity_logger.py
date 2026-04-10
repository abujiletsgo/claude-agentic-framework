#!/usr/bin/env python3
"""
Activity Logger — Stop hook.

Writes a compact session summary to ~/.claude/data/activity_log.jsonl.
Captures sessions even without git commits (orchestrations, conversations).
Feeds dashboard/activity_report.py.

Input: Claude Code Stop event JSON on stdin
Output: empty JSON {} (never blocks)
"""
import json
import os
import subprocess
import sys
from datetime import datetime, UTC
from pathlib import Path

LOG_PATH = Path.home() / ".claude" / "data" / "activity_log.jsonl"
SUMMARY_DIR = Path.home() / ".claude" / "data" / "compressed_context"
MAX_ENTRIES = 200


def git(args: list, cwd: str) -> str:
    try:
        r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def get_compressed_tasks(session_id: str) -> list[str]:
    if not SUMMARY_DIR.exists():
        return []
    prefix = session_id[:8] if session_id and len(session_id) >= 8 else session_id
    tasks = []
    for f in sorted(SUMMARY_DIR.glob(f"{prefix}*.json")):
        try:
            data = json.loads(f.read_text())
            subj = data.get("subject", "")
            outcome = data.get("outcome", "")
            if subj:
                tasks.append(f"{subj} → {outcome}" if outcome else subj)
        except Exception:
            pass
        if len(tasks) >= 5:
            break
    return tasks


def build_entry(cwd: str, session_id: str) -> dict | None:
    entry: dict = {
        "ts": datetime.now(UTC).isoformat(),
        "session_id": session_id,
        "cwd": cwd,
        "commit": "",
        "changed": [],
        "tasks": [],
    }

    # Git info
    entry["commit"] = git(["log", "-1", "--format=%s (%h) by %an"], cwd)
    stat = git(["diff", "--stat", "HEAD~1", "HEAD", "--"], cwd)
    if not stat:
        stat = git(["diff", "--stat"], cwd)
    if stat:
        entry["changed"] = [
            l.strip() for l in stat.splitlines()
            if l.strip() and ("|" in l or "changed" in l)
        ][:10]

    # Compressed context task summaries
    entry["tasks"] = get_compressed_tasks(session_id)

    # Skip if truly nothing happened
    if not entry["commit"] and not entry["changed"] and not entry["tasks"]:
        return None

    return entry


def append_entry(entry: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Read existing, prune to MAX_ENTRIES - 1
    lines = []
    if LOG_PATH.exists():
        lines = [l for l in LOG_PATH.read_text().splitlines() if l.strip()]
    lines = lines[-(MAX_ENTRIES - 1):]
    lines.append(json.dumps(entry, ensure_ascii=False))
    LOG_PATH.write_text("\n".join(lines) + "\n")


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    cwd = data.get("cwd") or os.getcwd()
    session_id = data.get("session_id", "unknown")

    entry = build_entry(cwd, session_id)
    if entry:
        try:
            append_entry(entry)
        except Exception:
            pass

    print(json.dumps({}))


if __name__ == "__main__":
    main()
