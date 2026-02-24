#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
validate_facts.py - Stop Hook (Layer 2: Episodic Memory Maintenance)
=====================================================================

Validates and prunes FACTS.md at session end.

Responsibilities:
  1. Remove STALE entries older than 90 days (hard prune)
  2. Log fact count stats to ~/.claude/data/facts_log.jsonl for monitoring
  3. If FACTS.md grew > 200 entries, warn (context budget risk)

Does NOT mark facts as stale automatically — that requires human judgment
or a more complex fact-checking step. Contradiction detection is left for
future enhancement (would require reading files and running commands).

Exit: always 0 (never blocks)
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fact_manager import facts_path, prune_stale, count_facts, read

LOG_PATH = Path.home() / ".claude" / "data" / "facts_log.jsonl"
WARN_THRESHOLD = 50  # Warn if total facts > this (context budget concern)


def log_stats(cwd: str, counts: dict, pruned: int):
    """Append session stats to facts_log.jsonl."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "project": Path(cwd).resolve().name,
            "counts": counts,
            "pruned_stale": pruned,
        }
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def main():
    try:
        data = json.loads(sys.stdin.read())
        cwd = data.get("cwd", os.getcwd())
        path = facts_path(cwd)

        if not path.exists():
            print(json.dumps({}))
            sys.exit(0)

        # 1. Prune old stale entries
        pruned = prune_stale(path)

        # 2. Count facts
        counts = count_facts(path)
        total = sum(counts.values())

        # 3. Log
        log_stats(cwd, counts, pruned)

        # 4. Warn if getting large
        if total > WARN_THRESHOLD:
            print(
                f"validate_facts: FACTS.md has {total} facts (>{WARN_THRESHOLD}). "
                "Consider reviewing and pruning to keep context injection efficient.",
                file=sys.stderr,
            )

    except Exception as e:
        print(f"validate_facts error: {e}", file=sys.stderr)

    print(json.dumps({}))
    sys.exit(0)


if __name__ == "__main__":
    main()
