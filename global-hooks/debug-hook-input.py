#!/usr/bin/env python3
"""Debug hook to see what stdin contains."""
import sys

# Read everything from stdin
stdin_content = sys.stdin.read()

# Write to a debug file
with open("/tmp/hook-debug.txt", "a") as f:
    f.write("=" * 50 + "\n")
    f.write(f"STDIN length: {len(stdin_content)}\n")
    f.write(f"STDIN content: {repr(stdin_content)}\n")
    f.write("=" * 50 + "\n")

# Always exit success
sys.exit(0)
