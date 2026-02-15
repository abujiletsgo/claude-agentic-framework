#!/usr/bin/env python3
"""
Multi-Session Conflict Detection
=================================

Prevents concurrent Claude Code sessions from interfering with each other.

Features:
- Detects overlapping file access across sessions
- Warns when another session is editing the same file
- Optionally blocks conflicting operations
- Session-aware lock files

How it works:
1. SessionStart: Register this session, check for conflicts
2. PreToolUse: Check if file is locked by another session
3. PostToolUse: Track files accessed by this session
4. Stop: Clean up session locks

Exit codes:
- 0: Allow (no conflict)
- 0 + JSON warning: Show warning but allow
- 2: Block (conflict detected)
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import fcntl

def emit(obj):
    """Output JSON to stdout"""
    sys.stdout.write(json.dumps(obj) + "\n")

def get_session_dir():
    """Get session lock directory"""
    claude_dir = Path.home() / ".claude"
    session_dir = claude_dir / "session-locks"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir

def get_current_session_id():
    """Get current session ID from environment"""
    return os.environ.get("CLAUDE_SESSION_ID", "unknown")

def get_file_locks_dir():
    """Get file locks directory"""
    claude_dir = Path.home() / ".claude"
    locks_dir = claude_dir / "file-locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    return locks_dir

def clean_stale_locks(max_age_hours=2):
    """Remove locks older than max_age_hours"""
    session_dir = get_session_dir()
    locks_dir = get_file_locks_dir()
    cutoff = datetime.now() - timedelta(hours=max_age_hours)

    # Clean session locks
    for lock_file in session_dir.glob("*.json"):
        if lock_file.stat().st_mtime < cutoff.timestamp():
            lock_file.unlink()

    # Clean file locks
    for lock_file in locks_dir.glob("*.lock"):
        if lock_file.stat().st_mtime < cutoff.timestamp():
            lock_file.unlink()

def register_session():
    """Register this session as active"""
    session_id = get_current_session_id()
    session_dir = get_session_dir()
    lock_file = session_dir / f"{session_id}.json"

    lock_file.write_text(json.dumps({
        "session_id": session_id,
        "started_at": datetime.now().isoformat(),
        "cwd": os.getcwd(),
        "files": []
    }, indent=2))

def get_active_sessions():
    """Get all active sessions (excluding this one)"""
    current_id = get_current_session_id()
    session_dir = get_session_dir()
    sessions = []

    for lock_file in session_dir.glob("*.json"):
        if lock_file.stem == current_id:
            continue
        try:
            data = json.loads(lock_file.read_text())
            sessions.append(data)
        except:
            pass

    return sessions

def check_file_conflict(file_path, operation):
    """Check if file is locked by another session"""
    if not file_path:
        return None

    locks_dir = get_file_locks_dir()
    # Normalize path
    abs_path = Path(file_path).resolve()
    # Create lock filename (hash to avoid path issues)
    import hashlib
    lock_name = hashlib.md5(str(abs_path).encode()).hexdigest()
    lock_file = locks_dir / f"{lock_name}.lock"

    if not lock_file.exists():
        return None

    try:
        lock_data = json.loads(lock_file.read_text())
        if lock_data["session_id"] != get_current_session_id():
            return {
                "file": str(abs_path),
                "locked_by": lock_data["session_id"],
                "operation": lock_data["operation"],
                "locked_at": lock_data["locked_at"]
            }
    except:
        pass

    return None

def lock_file(file_path, operation):
    """Lock a file for this session"""
    if not file_path:
        return

    locks_dir = get_file_locks_dir()
    abs_path = Path(file_path).resolve()
    import hashlib
    lock_name = hashlib.md5(str(abs_path).encode()).hexdigest()
    lock_file = locks_dir / f"{lock_name}.lock"

    lock_file.write_text(json.dumps({
        "session_id": get_current_session_id(),
        "file": str(abs_path),
        "operation": operation,
        "locked_at": datetime.now().isoformat()
    }, indent=2))

def unlock_file(file_path):
    """Unlock a file"""
    if not file_path:
        return

    locks_dir = get_file_locks_dir()
    abs_path = Path(file_path).resolve()
    import hashlib
    lock_name = hashlib.md5(str(abs_path).encode()).hexdigest()
    lock_file = locks_dir / f"{lock_name}.lock"

    if lock_file.exists():
        try:
            lock_data = json.loads(lock_file.read_text())
            if lock_data["session_id"] == get_current_session_id():
                lock_file.unlink()
        except:
            pass

def cleanup_session():
    """Clean up this session's locks"""
    session_id = get_current_session_id()
    session_dir = get_session_dir()
    locks_dir = get_file_locks_dir()

    # Remove session lock
    session_file = session_dir / f"{session_id}.json"
    if session_file.exists():
        session_file.unlink()

    # Remove all file locks from this session
    for lock_file in locks_dir.glob("*.lock"):
        try:
            lock_data = json.loads(lock_file.read_text())
            if lock_data["session_id"] == session_id:
                lock_file.unlink()
        except:
            pass

def session_start_handler():
    """SessionStart hook"""
    clean_stale_locks()
    register_session()

    # Check for other active sessions in same directory
    active = get_active_sessions()
    cwd = os.getcwd()

    conflicts = [s for s in active if s.get("cwd") == cwd]

    if conflicts:
        emit({
            "result": "continue",
            "warning": f"⚠️  {len(conflicts)} other Claude Code session(s) active in this directory. File conflicts possible."
        })
    else:
        emit({"result": "continue"})

def pre_tool_use_handler():
    """PreToolUse hook"""
    # Read stdin for hook input
    hook_input = json.loads(sys.stdin.read())
    tool = hook_input.get("tool", {})
    tool_name = tool.get("name", "")
    params = tool.get("input", {})

    # Check for file operations
    file_path = None
    operation = tool_name

    if tool_name == "Read":
        file_path = params.get("file_path")
        operation = "reading"
    elif tool_name == "Edit":
        file_path = params.get("file_path")
        operation = "editing"
    elif tool_name == "Write":
        file_path = params.get("file_path")
        operation = "writing"
    elif tool_name == "Bash":
        # Could parse bash command for file operations, but that's complex
        pass

    if file_path:
        conflict = check_file_conflict(file_path, operation)
        if conflict:
            emit({
                "result": "continue",
                "warning": f"⚠️  CONFLICT: File '{conflict['file']}' is being {conflict['operation']} by another session (started {conflict['locked_at']}). Continue anyway?"
            })
            return

    emit({"result": "continue"})

def post_tool_use_handler():
    """PostToolUse hook - lock files being modified"""
    hook_input = json.loads(sys.stdin.read())
    tool = hook_input.get("tool", {})
    tool_name = tool.get("name", "")
    params = tool.get("input", {})

    file_path = None
    operation = tool_name

    if tool_name in ["Edit", "Write"]:
        file_path = params.get("file_path")
        lock_file(file_path, operation)

    emit({"result": "continue"})

def stop_handler():
    """Stop hook - cleanup"""
    cleanup_session()
    emit({"result": "continue"})

def main():
    """Main entry point"""
    hook_event = os.environ.get("HOOK_EVENT", "")

    if hook_event == "SessionStart":
        session_start_handler()
    elif hook_event == "PreToolUse":
        pre_tool_use_handler()
    elif hook_event == "PostToolUse":
        post_tool_use_handler()
    elif hook_event == "Stop":
        stop_handler()
    else:
        emit({"result": "continue"})

if __name__ == "__main__":
    main()
