#!/usr/bin/env python3
"""Tests for session_lock_manager.py"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

SESSION_DIR = Path(__file__).parent.parent / "session"
sys.path.insert(0, str(SESSION_DIR))

import session_lock_manager as slm


# ── clean_stale_locks ────────────────────────────────────────────────

def test_clean_stale_locks_removes_old_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_dir = Path(tmpdir)
        old_lock = lock_dir / "old-session.json"
        old_lock.write_text(json.dumps({"session_id": "old"}))
        # Make it appear old by modifying mtime
        old_time = time.time() - (3 * 3600)  # 3 hours ago
        os.utime(old_lock, (old_time, old_time))

        with patch.object(slm, "get_session_dir", return_value=lock_dir):
            with patch.object(slm, "get_file_locks_dir", return_value=lock_dir):
                slm.clean_stale_locks(max_age_hours=2)

        assert not old_lock.exists(), "Stale lock should be removed"

def test_clean_stale_locks_preserves_recent_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_dir = Path(tmpdir)
        recent_lock = lock_dir / "recent-session.json"
        recent_lock.write_text(json.dumps({"session_id": "recent"}))
        # File is fresh (just created), don't modify mtime

        with patch.object(slm, "get_session_dir", return_value=lock_dir):
            with patch.object(slm, "get_file_locks_dir", return_value=lock_dir):
                slm.clean_stale_locks(max_age_hours=2)

        assert recent_lock.exists(), "Recent lock should be preserved"


# ── register_session / get_active_sessions ───────────────────────────

def test_register_session_creates_lock_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_dir = Path(tmpdir)
        with patch.object(slm, "get_session_dir", return_value=lock_dir):
            with patch.object(slm, "get_current_session_id", return_value="test-session-123"):
                slm.register_session()
                lock_file = lock_dir / "test-session-123.json"
                assert lock_file.exists()
                data = json.loads(lock_file.read_text())
                assert data["session_id"] == "test-session-123"

def test_get_active_sessions_excludes_current():
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_dir = Path(tmpdir)
        # Create another session's lock
        (lock_dir / "other-session.json").write_text(
            json.dumps({"session_id": "other-session", "cwd": "/tmp", "files": []})
        )
        # Create current session's lock
        (lock_dir / "current-session.json").write_text(
            json.dumps({"session_id": "current-session", "cwd": "/tmp", "files": []})
        )
        with patch.object(slm, "get_session_dir", return_value=lock_dir):
            with patch.object(slm, "get_current_session_id", return_value="current-session"):
                sessions = slm.get_active_sessions()
                ids = [s["session_id"] for s in sessions]
                assert "other-session" in ids
                assert "current-session" not in ids


# ── lock_file / unlock_file / check_file_conflict ────────────────────

def test_lock_and_unlock_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_dir = Path(tmpdir)
        with patch.object(slm, "get_file_locks_dir", return_value=lock_dir):
            with patch.object(slm, "get_current_session_id", return_value="sess-A"):
                slm.lock_file("/src/foo.py", "edit")
                # Verify lock exists
                import hashlib
                h = hashlib.md5(str(Path("/src/foo.py").resolve()).encode()).hexdigest()
                lock_path = lock_dir / f"{h}.lock"
                assert lock_path.exists()

                slm.unlock_file("/src/foo.py")
                assert not lock_path.exists()

def test_unlock_does_not_remove_other_sessions_lock():
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_dir = Path(tmpdir)
        import hashlib
        h = hashlib.md5(str(Path("/src/foo.py").resolve()).encode()).hexdigest()
        lock_path = lock_dir / f"{h}.lock"
        # Write a lock owned by another session
        lock_path.write_text(json.dumps({
            "session_id": "other-session",
            "file_path": "/src/foo.py",
            "operation": "edit",
        }))
        with patch.object(slm, "get_file_locks_dir", return_value=lock_dir):
            with patch.object(slm, "get_current_session_id", return_value="my-session"):
                slm.unlock_file("/src/foo.py")
                # Lock should still exist (owned by other session)
                assert lock_path.exists()

def test_check_file_conflict_detects_other_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_dir = Path(tmpdir)
        import hashlib
        h = hashlib.md5(str(Path("/src/foo.py").resolve()).encode()).hexdigest()
        lock_path = lock_dir / f"{h}.lock"
        lock_path.write_text(json.dumps({
            "session_id": "other-session",
            "file_path": "/src/foo.py",
            "operation": "edit",
            "locked_at": "2026-02-17T10:00:00",
        }))
        with patch.object(slm, "get_file_locks_dir", return_value=lock_dir):
            with patch.object(slm, "get_current_session_id", return_value="my-session"):
                conflict = slm.check_file_conflict("/src/foo.py", "edit")
                assert conflict is not None
                # check_file_conflict returns {"file": ..., "locked_by": ..., ...}
                assert conflict["locked_by"] == "other-session"

def test_check_file_conflict_no_conflict_own_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_dir = Path(tmpdir)
        import hashlib
        h = hashlib.md5(str(Path("/src/foo.py").resolve()).encode()).hexdigest()
        lock_path = lock_dir / f"{h}.lock"
        lock_path.write_text(json.dumps({
            "session_id": "my-session",
            "file_path": "/src/foo.py",
            "operation": "edit",
        }))
        with patch.object(slm, "get_file_locks_dir", return_value=lock_dir):
            with patch.object(slm, "get_current_session_id", return_value="my-session"):
                conflict = slm.check_file_conflict("/src/foo.py", "edit")
                assert conflict is None


# ── cleanup_session ───────────────────────────────────────────────────

def test_cleanup_session_removes_own_locks():
    with tempfile.TemporaryDirectory() as tmpdir:
        sess_dir = Path(tmpdir) / "sessions"
        file_dir = Path(tmpdir) / "files"
        sess_dir.mkdir()
        file_dir.mkdir()

        import hashlib
        h = hashlib.md5(str(Path("/src/foo.py").resolve()).encode()).hexdigest()
        file_lock = file_dir / f"{h}.lock"
        file_lock.write_text(json.dumps({"session_id": "my-session"}))
        sess_lock = sess_dir / "my-session.json"
        sess_lock.write_text(json.dumps({"session_id": "my-session"}))

        with patch.object(slm, "get_session_dir", return_value=sess_dir):
            with patch.object(slm, "get_file_locks_dir", return_value=file_dir):
                with patch.object(slm, "get_current_session_id", return_value="my-session"):
                    slm.cleanup_session()

        assert not sess_lock.exists()
        assert not file_lock.exists()
