#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Config Change Auditor - ConfigChange Hook

Security auditing hook that logs all configuration changes to
~/.claude/data/logs/config_audit.jsonl. Prints a warning to stderr
if hooks or permissions sections were modified (potential privilege
escalation vector).

Hook event: ConfigChange
Exit codes:
  0 = Always (never blocks, audit-only)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


SENSITIVE_KEYS = {"hooks", "permissions", "allow", "deny"}


def get_audit_log_path():
    """Return path to config audit JSONL file, creating dirs if needed."""
    audit_path = Path.home() / ".claude" / "data" / "logs" / "config_audit.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    return audit_path


def check_sensitive_fields(change_data):
    """Check if the config change touches hooks or permissions."""
    warnings = []

    # Check top-level keys in the change payload
    changed_keys = set()
    if isinstance(change_data, dict):
        changed_keys = set(change_data.keys())

        # Also check nested structures
        for key, value in change_data.items():
            if isinstance(value, dict):
                changed_keys.update(value.keys())

    sensitive_hit = changed_keys & SENSITIVE_KEYS
    if sensitive_hit:
        warnings.append(
            f"[SECURITY AUDIT] Config change modifies sensitive sections: {', '.join(sorted(sensitive_hit))}"
        )

    return warnings


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)

        hook_input = json.loads(raw)

        # Extract change details from hook payload
        change_data = hook_input if isinstance(hook_input, dict) else {}
        tool_input = change_data.get("tool_input", change_data)

        # Build audit record
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "config_change",
            "change_keys": list(change_data.keys()) if isinstance(change_data, dict) else [],
            "details": change_data,
        }

        # Write audit log
        audit_path = get_audit_log_path()
        with open(audit_path, "a") as f:
            f.write(json.dumps(record) + "\n")

        # Check for sensitive field modifications and warn
        warnings = check_sensitive_fields(change_data)
        if isinstance(tool_input, dict):
            warnings.extend(check_sensitive_fields(tool_input))

        for warning in warnings:
            print(warning, file=sys.stderr)

    except Exception:
        # Never fail, never block
        pass

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
