#!/usr/bin/env python3
"""
spawn_hud.py — Session startup hook that auto-launches caf-hud when inside a cmux surface.

Only fires if CMUX_SURFACE_ID is set (i.e., the user is inside a cmux workspace).
Finds the most recently active orch job under /tmp/caf_orch/ and launches
`bin/cmux-sprint launch-hud <orch_id>` as a background process.

Non-blocking: uses Popen so Claude's session start is not delayed.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    # Only act when inside a cmux surface
    cmux_sid = os.environ.get("CMUX_SURFACE_ID", "")
    if not cmux_sid:
        sys.stdout.write("{}\n")
        return

    orch_base = Path("/tmp/caf_orch")
    if not orch_base.exists():
        sys.stdout.write("{}\n")
        return

    # Find most-recently-modified orch dir that has acceptance_criteria.md
    dirs = []
    try:
        for entry in orch_base.iterdir():
            if entry.is_dir() and (entry / "acceptance_criteria.md").exists():
                dirs.append(entry)
    except Exception:
        sys.stdout.write("{}\n")
        return

    if not dirs:
        sys.stdout.write("{}\n")
        return

    dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    orch_id = dirs[0].name

    # Resolve caf-team repo root from this file's location
    # Path: global-hooks/framework/session/spawn_hud.py → repo root is 4 parents up
    caf_dir = Path(__file__).resolve().parent.parent.parent.parent

    try:
        subprocess.Popen(
            [str(caf_dir / "bin" / "cmux-sprint"), "launch-hud", orch_id],
            env={**os.environ},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass  # Non-blocking: never fail session startup

    sys.stdout.write("{}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.stdout.write("{}\n")
        sys.exit(0)
