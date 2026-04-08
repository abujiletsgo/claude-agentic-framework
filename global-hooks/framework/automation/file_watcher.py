#!/usr/bin/env python3
"""FileChanged Hook — watches dependency files (package.json, pyproject.toml,
Cargo.toml, go.mod). Logs changes and injects advisory context. Exit: always 0."""
import json, sys
from datetime import datetime, timezone
from pathlib import Path

WATCHED = {"package.json", "pyproject.toml", "Cargo.toml", "go.mod"}
LOG_PATH = Path.home() / ".claude" / "data" / "file_changes.jsonl"


def main():
    try:
        data = json.load(sys.stdin)
        session_id = data.get("session_id", "unknown")
        file_path = data.get("file", {}).get("filePath", "") or data.get("filePath", "")
        filename = Path(file_path).name if file_path else ""
        if filename not in WATCHED:
            print(json.dumps({}))
            sys.exit(0)
        # Log to JSONL
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {"timestamp": datetime.now(timezone.utc).isoformat(),
                 "session_id": session_id, "file": file_path, "filename": filename}
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
        # Inject advisory context
        output = {"hookSpecificOutput": {
            "hookEventName": data.get("hook_event_name", "FileChanged"),
            "additionalContext": (
                f"Dependency file {filename} was modified externally. "
                "Consider running dependency audit or checking for breaking changes."
            ),
        }}
        print(json.dumps(output))
    except Exception as e:
        print(f"file_watcher error (non-blocking): {e}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
