#!/usr/bin/env python3
"""SessionStart hook: check gstack health (non-blocking, fail-open)."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

CACHE_FILE = Path("/tmp/caf_gstack_status.json")
CACHE_TTL = 60  # seconds
BRIDGE_CMD = "bin/gstack-bridge"

def main():
    # Read stdin (hook input)
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        hook_input = {}

    try:
        # Check cache
        if CACHE_FILE.exists():
            age = time.time() - CACHE_FILE.stat().st_mtime
            if age < CACHE_TTL:
                print(json.dumps({}))
                return

        # Find gstack-bridge relative to this script or in PATH
        script_dir = Path(__file__).resolve().parent.parent.parent
        bridge = script_dir / BRIDGE_CMD
        if not bridge.exists():
            # Try common locations
            for candidate in [Path.home() / "Documents/claude-agentic-framework" / BRIDGE_CMD]:
                if candidate.exists():
                    bridge = candidate
                    break

        if bridge.exists():
            result = subprocess.run(
                [str(bridge), "status"],
                capture_output=True, text=True, timeout=2
            )
            if result.stdout.strip():
                try:
                    status = json.loads(result.stdout)
                    # Write cache
                    CACHE_FILE.write_text(result.stdout)
                    if not status.get("installed"):
                        print(json.dumps({}), end="", file=sys.stderr)
                    if status.get("update_needed"):
                        print("gstack update available — run: bin/gstack-bridge update", file=sys.stderr)
                except json.JSONDecodeError:
                    pass
    except subprocess.TimeoutExpired:
        print("gstack-bridge timed out (2s)", file=sys.stderr)
    except Exception as e:
        print(f"check_gstack: {e}", file=sys.stderr)

    # Always output empty JSON — never block session
    print(json.dumps({}))

if __name__ == "__main__":
    main()
