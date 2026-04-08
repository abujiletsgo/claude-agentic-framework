#!/usr/bin/env python3
"""Tests for context-bundle-logger.py"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

HOOKS_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(HOOKS_ROOT))

import importlib.util
spec = importlib.util.spec_from_file_location(
    "context_bundle_logger",
    HOOKS_ROOT / "context-bundle-logger.py"
)
cbl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cbl)


# ── extract_file_path ────────────────────────────────────────────────

def test_extract_file_path_primary_key():
    assert cbl.extract_file_path({"file_path": "/src/foo.py"}) == "/src/foo.py"

def test_extract_file_path_notebook_key():
    assert cbl.extract_file_path({"notebook_path": "/src/nb.ipynb"}) == "/src/nb.ipynb"

def test_extract_file_path_fallback_path_key():
    assert cbl.extract_file_path({"path": "/src/bar.py"}) == "/src/bar.py"

def test_extract_file_path_returns_none_when_missing():
    assert cbl.extract_file_path({"command": "ls"}) is None

def test_extract_file_path_prefers_file_path():
    result = cbl.extract_file_path({"file_path": "/a.py", "path": "/b.py"})
    assert result == "/a.py"


# ── load_bundle / save_bundle ────────────────────────────────────────

def test_load_bundle_fresh():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "bundle.json"
        bundle = cbl.load_bundle(p)
        assert "operations" in bundle
        assert "files_read" in bundle
        assert "files_modified" in bundle
        assert bundle["summary"]["total_operations"] == 0

def test_load_bundle_existing():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "bundle.json"
        data = {
            "session_id": "abc",
            "created_at": "2026-02-17",
            "last_updated": "2026-02-17",
            "operations": [{"tool": "Read"}],
            "files_read": ["/foo.py"],
            "files_modified": [],
            "summary": {"read_count": 1, "edit_count": 0, "write_count": 0, "total_operations": 1},
        }
        p.write_text(json.dumps(data))
        bundle = cbl.load_bundle(p)
        assert bundle["session_id"] == "abc"
        assert len(bundle["operations"]) == 1

def test_load_bundle_handles_corrupt_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "bundle.json"
        p.write_text("not valid json {{")
        bundle = cbl.load_bundle(p)
        assert bundle["summary"]["total_operations"] == 0


# ── log_operation ────────────────────────────────────────────────────

def make_fresh_bundle():
    return {
        "session_id": "test",
        "created_at": "2026-02-17",
        "last_updated": "2026-02-17",
        "operations": [],
        "files_read": [],
        "files_modified": [],
        "summary": {"read_count": 0, "edit_count": 0, "write_count": 0, "total_operations": 0},
    }

def test_log_read_adds_to_files_read():
    bundle = make_fresh_bundle()
    cbl.log_operation(bundle, "Read", {"file_path": "/src/foo.py"}, "2026-02-17")
    assert "/src/foo.py" in bundle["files_read"]
    assert bundle["summary"]["read_count"] == 1
    assert bundle["summary"]["total_operations"] == 1

def test_log_write_adds_to_files_modified():
    bundle = make_fresh_bundle()
    cbl.log_operation(bundle, "Write", {"file_path": "/src/foo.py", "content": "x"}, "2026-02-17")
    assert "/src/foo.py" in bundle["files_modified"]
    assert bundle["summary"]["write_count"] == 1

def test_log_edit_increments_edit_count():
    bundle = make_fresh_bundle()
    cbl.log_operation(bundle, "Edit", {
        "file_path": "/src/foo.py",
        "old_string": "x" * 200,
        "new_string": "y" * 200,
    }, "2026-02-17")
    assert bundle["summary"]["edit_count"] == 1
    # Verify truncation at 100 chars
    op = bundle["operations"][-1]
    assert len(op.get("old_string", "")) <= 100
    assert len(op.get("new_string", "")) <= 100

def test_log_notebook_edit_increments_edit_count():
    bundle = make_fresh_bundle()
    cbl.log_operation(bundle, "NotebookEdit", {
        "notebook_path": "/src/nb.ipynb", "cell_id": "cell1"
    }, "2026-02-17")
    assert bundle["summary"]["edit_count"] == 1

def test_log_deduplicates_files_read():
    bundle = make_fresh_bundle()
    cbl.log_operation(bundle, "Read", {"file_path": "/src/foo.py"}, "t1")
    cbl.log_operation(bundle, "Read", {"file_path": "/src/foo.py"}, "t2")
    assert bundle["files_read"].count("/src/foo.py") == 1
    assert bundle["summary"]["read_count"] == 2  # operations incremented twice

def test_log_no_file_path_returns_early():
    bundle = make_fresh_bundle()
    cbl.log_operation(bundle, "Read", {"command": "ls"}, "t1")
    assert len(bundle["operations"]) == 0

def test_log_unknown_tool_returns_early():
    bundle = make_fresh_bundle()
    cbl.log_operation(bundle, "Bash", {"command": "ls"}, "t1")
    assert len(bundle["operations"]) == 0


# ── subprocess integration ───────────────────────────────────────────

import subprocess

HOOK = str(HOOKS_ROOT / "context-bundle-logger.py")

def test_hook_exits_0_for_read():
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle_dir = Path(tmpdir)
        with patch.object(cbl, "get_bundle_path", return_value=bundle_dir / "test.json"):
            payload = {
                "session_id": "test-sess",
                "tool_name": "Read",
                "tool_input": {"file_path": "/tmp/test.txt"},
                "timestamp": "2026-02-17T00:00:00",
            }
            r = subprocess.run(["python3", HOOK], input=json.dumps(payload),
                               capture_output=True, text=True)
            assert r.returncode == 0

def test_hook_exits_0_for_unknown_tool():
    payload = {
        "session_id": "test-sess",
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
    }
    r = subprocess.run(["python3", HOOK], input=json.dumps(payload),
                       capture_output=True, text=True)
    assert r.returncode == 0
