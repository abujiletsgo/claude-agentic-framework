#!/usr/bin/env python3
"""SessionStart hook: no-op. Live TUI is launched by cteam instead."""
import json
import sys

json.load(sys.stdin)
print(json.dumps({}))
