#!/usr/bin/env python3
"""SubagentStop hook: sprint lead result storage — mempalace removed, stub only."""
import json
import sys

def main():
    try:
        json.load(sys.stdin)
    except Exception:
        pass
    print(json.dumps({}))

if __name__ == "__main__":
    main()
