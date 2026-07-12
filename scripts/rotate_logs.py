#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Cap the append-only sinks so evidence stays findable instead of infinite.

Every CAF log is append-only with no rotation. Left alone they reach hundreds of
MB, at which point nothing reads them and the "detailed log system" is decorative.
This trims each sink to its most recent N lines (the tail is what a postmortem
ever wants) and prunes session transcripts older than N days.

    uv run scripts/rotate_logs.py            # report only, changes nothing
    uv run scripts/rotate_logs.py --apply    # actually trim
    uv run scripts/rotate_logs.py --apply --keep-days 14

Safe by design: report-only unless --apply, and it never touches a file it did
not expect to find.
"""
from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

HOME = Path.home()

# sink -> max lines to retain
SINKS: dict[Path, int] = {
    HOME / ".claude" / "data" / "logs" / "config_audit.jsonl": 5_000,
    HOME / ".claude" / "data" / "agent_tracking.jsonl": 10_000,
    HOME / ".claude" / "data" / "subagent_alerts.jsonl": 5_000,
    HOME / ".claude" / "data" / "task_completions.jsonl": 5_000,
    HOME / ".claude" / "data" / "activity_log.jsonl": 5_000,
    HOME / ".claude" / "data" / "stop_failures.jsonl": 5_000,
    HOME / ".claude" / "logs" / "cost_tracking.jsonl": 20_000,   # feeds /costs
    HOME / ".claude" / "logs" / "caddy" / "analyses.jsonl": 5_000,
    HOME / ".claude" / "logs" / "caddy" / "delegations.jsonl": 5_000,
    HOME / ".caf" / "logs" / "incidents.jsonl": 20_000,          # feeds postmortem
}

# Sinks whose producer was retired — nothing writes or reads these any more.
DEAD: list[Path] = [
    HOME / ".claude" / "data" / "auto_skills_log.jsonl",   # auto_skill_generator, retired
    HOME / ".claude" / "data" / "facts_log.jsonl",         # FACTS.md layer, retired
]

SESSIONS = HOME / ".caf" / "sessions"


def human(n: int) -> str:
    for unit in ("B", "K", "M", "G"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.0f}T"


def trim(path: Path, keep: int, apply: bool) -> tuple[int, int]:
    """Return (bytes_before, bytes_after)."""
    if not path.is_file():
        return 0, 0
    before = path.stat().st_size
    with path.open(errors="ignore") as f:
        lines = f.readlines()
    if len(lines) <= keep:
        return before, before
    if not apply:
        # Estimate the post-trim size without writing.
        return before, sum(len(x.encode()) for x in lines[-keep:])
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(lines[-keep:]))
    os.replace(tmp, path)
    return before, path.stat().st_size


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually write (default: report only)")
    ap.add_argument("--keep-days", type=int, default=30, help="session transcript retention")
    a = ap.parse_args()

    mode = "APPLY" if a.apply else "DRY RUN (nothing written — pass --apply)"
    print(f"rotate_logs — {mode}\n")

    total_before = total_after = 0
    for path, keep in SINKS.items():
        b, aft = trim(path, keep, a.apply)
        if not b:
            continue
        total_before += b
        total_after += aft
        flag = "" if b == aft else f"  -> {human(aft)}"
        print(f"  {human(b):>6}  {path.name:<24} keep={keep:<6}{flag}")

    for path in DEAD:
        if path.is_file():
            sz = path.stat().st_size
            total_before += sz
            print(f"  {human(sz):>6}  {path.name:<24} {'DEAD (producer retired)'}")
            if a.apply:
                path.unlink()

    # Session transcripts: prune by age, not count.
    if SESSIONS.is_dir():
        cutoff = time.time() - a.keep_days * 86400
        olds = [p for p in SESSIONS.glob("*.jsonl") if p.stat().st_mtime < cutoff]
        alls = list(SESSIONS.glob("*.jsonl"))
        sz = sum(p.stat().st_size for p in olds)
        print(f"\n  sessions: {len(alls)} files, {len(olds)} older than {a.keep_days}d ({human(sz)})")
        if a.apply:
            for p in olds:
                p.unlink()
            print(f"  pruned {len(olds)} session transcripts")

    saved = total_before - total_after
    print(f"\n  total {human(total_before)} -> {human(total_after)}"
          f"   ({'freed' if a.apply else 'would free'} {human(max(saved, 0))})")
    if not a.apply:
        print("\n  re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
