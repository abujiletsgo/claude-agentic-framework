# /// script
# requires-python = ">=3.8"
# dependencies = ["pyyaml"]
# ///
"""
Unified Damage Control - Single hook for Bash, Edit, and Write tools.
Merges bash-tool, edit-tool, and write-tool damage control into one process.

Exit codes:
  0 = Allow (or JSON with permissionDecision)
  2 = Block (stderr fed back to Claude)
"""

import json
import sys
import re
import os
import fnmatch
from pathlib import Path

import yaml

# -- Config loading (shared across all tools) --

def get_config_path():
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        p = Path(project_dir) / ".claude" / "hooks" / "damage-control" / "patterns.yaml"
        if p.exists():
            return p
    script_dir = Path(__file__).parent
    local = script_dir / "patterns.yaml"
    if local.exists():
        return local
    skill_root = script_dir.parent.parent / "patterns.yaml"
    if skill_root.exists():
        return skill_root
    return local

def load_config():
    config_path = get_config_path()
    if not config_path.exists():
        return {"bashToolPatterns": [], "zeroAccessPaths": [], "readOnlyPaths": [], "noDeletePaths": []}
    with open(config_path, "r") as f:
        return yaml.safe_load(f) or {}

# -- Path matching (used by Edit/Write and Bash path checks) --

def is_glob_pattern(pattern):
    return '*' in pattern or '?' in pattern or '[' in pattern

def match_path(file_path, pattern):
    expanded_pattern = os.path.realpath(os.path.expanduser(pattern))
    normalized = os.path.normpath(file_path)
    expanded_normalized = os.path.realpath(os.path.expanduser(normalized))

    if is_glob_pattern(pattern):
        basename = os.path.basename(expanded_normalized).lower()
        pattern_lower = pattern.lower()
        expanded_lower = expanded_pattern.lower()
        if fnmatch.fnmatch(basename, expanded_lower):
            return True
        if fnmatch.fnmatch(basename, pattern_lower):
            return True
        if fnmatch.fnmatch(expanded_normalized.lower(), expanded_lower):
            return True
        return False
    else:
        if expanded_normalized.startswith(expanded_pattern) or expanded_normalized == expanded_pattern.rstrip('/'):
            return True
        return False

# -- Edit/Write check --

def check_file_path(file_path, config):
    for zero_path in config.get("zeroAccessPaths", []):
        if match_path(file_path, zero_path):
            return True, f"zero-access path {zero_path} (no operations allowed)"
    for readonly in config.get("readOnlyPaths", []):
        if match_path(file_path, readonly):
            return True, f"read-only path {readonly}"
    return False, ""

# -- Bash command check --

def glob_to_regex(glob_pattern):
    result = ""
    for char in glob_pattern:
        if char == '*':
            result += r'[^\s/]*'
        elif char == '?':
            result += r'[^\s/]'
        elif char in r'\.^$+{}[]|()':
            result += '\\' + char
        else:
            result += char
    return result

# Operation patterns for bash commands
WRITE_PATTERNS = [
    (r'>\s*{path}', "write"),
    (r'\btee\s+(?!.*-a).*{path}', "write"),
]
APPEND_PATTERNS = [
    (r'>>\s*{path}', "append"),
    (r'\btee\s+-a\s+.*{path}', "append"),
    (r'\btee\s+.*-a.*{path}', "append"),
]
EDIT_PATTERNS = [
    (r'\bsed\s+-i.*{path}', "edit"),
    (r'\bperl\s+-[^\s]*i.*{path}', "edit"),
    (r'\bawk\s+-i\s+inplace.*{path}', "edit"),
]
MOVE_COPY_PATTERNS = [
    (r'\bmv\s+.*\s+{path}', "move"),
    (r'\bcp\s+.*\s+{path}', "copy"),
]
DELETE_PATTERNS = [
    (r'\brm\s+.*{path}', "delete"),
    (r'\bunlink\s+.*{path}', "delete"),
    (r'\brmdir\s+.*{path}', "delete"),
    (r'\bshred\s+.*{path}', "delete"),
]
PERMISSION_PATTERNS = [
    (r'\bchmod\s+.*{path}', "chmod"),
    (r'\bchown\s+.*{path}', "chown"),
    (r'\bchgrp\s+.*{path}', "chgrp"),
]
TRUNCATE_PATTERNS = [
    (r'\btruncate\s+.*{path}', "truncate"),
    (r':\s*>\s*{path}', "truncate"),
]

READ_ONLY_BLOCKED = (
    WRITE_PATTERNS + APPEND_PATTERNS + EDIT_PATTERNS +
    MOVE_COPY_PATTERNS + DELETE_PATTERNS + PERMISSION_PATTERNS + TRUNCATE_PATTERNS
)
NO_DELETE_BLOCKED = DELETE_PATTERNS

def check_path_patterns(command, path, patterns, path_type):
    if is_glob_pattern(path):
        glob_regex = glob_to_regex(path)
        for pattern_template, operation in patterns:
            try:
                cmd_prefix = pattern_template.replace("{path}", "")
                if cmd_prefix and re.search(cmd_prefix + glob_regex, command, re.IGNORECASE):
                    return True, f"Blocked: {operation} operation on {path_type} {path}"
            except re.error:
                continue
    else:
        expanded = os.path.expanduser(path)
        escaped_expanded = re.escape(expanded)
        escaped_original = re.escape(path)
        for pattern_template, operation in patterns:
            pattern_expanded = pattern_template.replace("{path}", escaped_expanded)
            pattern_original = pattern_template.replace("{path}", escaped_original)
            try:
                if re.search(pattern_expanded, command) or re.search(pattern_original, command):
                    return True, f"Blocked: {operation} operation on {path_type} {path}"
            except re.error:
                continue
    return False, ""

def check_bash_command(command, config):
    patterns = config.get("bashToolPatterns", [])
    zero_access_paths = config.get("zeroAccessPaths", [])
    read_only_paths = config.get("readOnlyPaths", [])
    no_delete_paths = config.get("noDeletePaths", [])

    for item in patterns:
        pattern = item.get("pattern", "")
        reason = item.get("reason", "Blocked by pattern")
        should_ask = item.get("ask", False)
        try:
            if re.search(pattern, command, re.IGNORECASE):
                if should_ask:
                    return False, True, reason
                else:
                    return True, False, f"Blocked: {reason}"
        except re.error:
            continue

    for zero_path in zero_access_paths:
        if is_glob_pattern(zero_path):
            try:
                if re.search(glob_to_regex(zero_path), command, re.IGNORECASE):
                    return True, False, f"Blocked: zero-access pattern {zero_path} (no operations allowed)"
            except re.error:
                continue
        else:
            expanded = os.path.expanduser(zero_path)
            if re.search(re.escape(expanded), command) or re.search(re.escape(zero_path), command):
                return True, False, f"Blocked: zero-access path {zero_path} (no operations allowed)"

    for readonly in read_only_paths:
        blocked, reason = check_path_patterns(command, readonly, READ_ONLY_BLOCKED, "read-only path")
        if blocked:
            return True, False, reason

    for no_delete in no_delete_paths:
        blocked, reason = check_path_patterns(command, no_delete, NO_DELETE_BLOCKED, "no-delete path")
        if blocked:
            return True, False, reason

    return False, False, ""

# -- Main --

def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    config = load_config()

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if not command:
            sys.exit(0)
        is_blocked, should_ask, reason = check_bash_command(command, config)
        if is_blocked:
            print(f"SECURITY: {reason}", file=sys.stderr)
            print(f"Command: {command[:100]}{'...' if len(command) > 100 else ''}", file=sys.stderr)
            sys.exit(2)
        elif should_ask:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": reason
                }
            }
            print(json.dumps(output))
            sys.exit(0)

    elif tool_name in ("Edit", "Write"):
        file_path = tool_input.get("file_path", "")
        if not file_path:
            sys.exit(0)
        blocked, reason = check_file_path(file_path, config)
        if blocked:
            print(f"SECURITY: Blocked {tool_name.lower()} to {reason}: {file_path}", file=sys.stderr)
            sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
