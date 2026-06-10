"""
test_cmux_integration.py — Tests for cmux_client and agent_display modules.
Runs without cmux installed or running (tests fallback/offline behavior).
"""
import io
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

pytestmark = pytest.mark.skip(reason="cmux system removed; file flagged for deletion")


# ---------------------------------------------------------------------------
# cmux_client tests
# ---------------------------------------------------------------------------

class TestCmuxClientOffline(unittest.TestCase):
    """Tests that run without a live cmux socket."""

    def test_import(self):
        import lib.cmux_client as m
        self.assertTrue(callable(m.is_available))
        self.assertTrue(callable(m.new_split))
        self.assertTrue(callable(m.send_surface))
        self.assertTrue(callable(m.set_status))
        self.assertTrue(callable(m.set_progress))
        self.assertTrue(callable(m.list_surfaces))

    def test_is_available_false_without_env(self):
        """is_available() must return False when CMUX_SURFACE_ID is not set."""
        import lib.cmux_client as m
        env = {k: v for k, v in os.environ.items() if k != "CMUX_SURFACE_ID"}
        with patch.dict(os.environ, env, clear=True):
            self.assertFalse(m.is_available())

    def test_is_available_false_when_socket_missing(self):
        """is_available() returns False when env var is set but socket doesn't exist."""
        import lib.cmux_client as m
        with patch.dict(os.environ, {"CMUX_SURFACE_ID": "test-surface-123",
                                      "CMUX_SOCKET_PATH": "/tmp/nonexistent_cmux.sock"}):
            self.assertFalse(m.is_available())

    def test_socket_path_respects_env_var(self):
        """_socket_path() uses CMUX_SOCKET_PATH if set."""
        import lib.cmux_client as m
        with patch.dict(os.environ, {"CMUX_SOCKET_PATH": "/custom/path/cmux.sock"}):
            result = m._socket_path()
            self.assertEqual(str(result), "/custom/path/cmux.sock")

    def test_socket_path_default(self):
        """_socket_path() defaults to ~/.cache/cmux/cmux.sock."""
        import lib.cmux_client as m
        env = {k: v for k, v in os.environ.items() if k != "CMUX_SOCKET_PATH"}
        with patch.dict(os.environ, env, clear=True):
            result = m._socket_path()
            self.assertEqual(result, Path.home() / ".cache" / "cmux" / "cmux.sock")

    def test_set_progress_clamps(self):
        """set_progress clamps values to 0-100."""
        import lib.cmux_client as m
        calls = []
        def fake_call(method, params=None):
            calls.append((method, params))
            return {}
        with patch.object(m, "_call", side_effect=fake_call):
            with patch.dict(os.environ, {"CMUX_SURFACE_ID": "sid-123"}):
                m.set_progress(150)
                m.set_progress(-10)
                m.set_progress(50)
        self.assertEqual(calls[0][1]["progress"], 100)
        self.assertEqual(calls[1][1]["progress"], 0)
        self.assertEqual(calls[2][1]["progress"], 50)

    def test_call_sends_correct_method(self):
        """_call() sends the right JSON method over the socket."""
        import lib.cmux_client as m
        import socket as _socket
        import json

        sent_data = []

        class FakeSocket:
            def __init__(self, *a, **kw): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def connect(self, path): pass
            def sendall(self, data): sent_data.append(data)
            def recv(self, n): return b'{"surface_id":"abc"}\n'

        with patch("socket.socket", return_value=FakeSocket()):
            result = m._call("new-split", {"direction": "right"})

        self.assertEqual(len(sent_data), 1)
        payload = json.loads(sent_data[0].decode().strip())
        self.assertEqual(payload["method"], "new-split")
        self.assertEqual(payload["params"]["direction"], "right")
        self.assertEqual(result["surface_id"], "abc")


# ---------------------------------------------------------------------------
# agent_display tests
# ---------------------------------------------------------------------------

class TestLeadDisplayAnsi(unittest.TestCase):
    """Tests for LeadDisplay in ANSI fallback mode (no rich, no cmux)."""

    def _make_display(self, role="test-lead", mission="Do the thing"):
        """Create a LeadDisplay with rich and cmux patched out."""
        import lib.agent_display as m
        with patch.object(m, "_RICH", False), \
             patch.object(m, "_CMUX", False), \
             patch.dict(os.environ, {"CAF_SPRINT_ID": "sprint-test"}):
            d = m.LeadDisplay(role, mission)
        return d, m

    def test_import_and_instantiate(self):
        import lib.agent_display as m
        with patch.object(m, "_RICH", False), patch.object(m, "_CMUX", False):
            with patch.dict(os.environ, {"CAF_SPRINT_ID": "x"}):
                d = m.LeadDisplay("engineering-lead", "Build the thing")
        self.assertIsNotNone(d)

    def test_task_done_outputs_checkmark(self):
        import lib.agent_display as m
        with patch.object(m, "_RICH", False), patch.object(m, "_CMUX", False):
            with patch.dict(os.environ, {"CAF_SPRINT_ID": "x"}):
                captured = io.StringIO()
                with patch("sys.stdout", captured):
                    d = m.LeadDisplay("eng", "mission")
                    d.task("write file", "done")
                output = captured.getvalue()
        self.assertIn("✓", output)
        self.assertIn("write file", output)

    def test_task_running_outputs_arrow(self):
        import lib.agent_display as m
        with patch.object(m, "_RICH", False), patch.object(m, "_CMUX", False):
            with patch.dict(os.environ, {"CAF_SPRINT_ID": "x"}):
                captured = io.StringIO()
                with patch("sys.stdout", captured):
                    d = m.LeadDisplay("eng", "mission")
                    d.task("running task", "running")
                output = captured.getvalue()
        self.assertIn("►", output)

    def test_task_failed_outputs_x(self):
        import lib.agent_display as m
        with patch.object(m, "_RICH", False), patch.object(m, "_CMUX", False):
            with patch.dict(os.environ, {"CAF_SPRINT_ID": "x"}):
                captured = io.StringIO()
                with patch("sys.stdout", captured):
                    d = m.LeadDisplay("eng", "mission")
                    d.task("failed task", "failed")
                output = captured.getvalue()
        self.assertIn("✗", output)

    def test_progress_bar_renders(self):
        import lib.agent_display as m
        with patch.object(m, "_RICH", False), patch.object(m, "_CMUX", False):
            with patch.dict(os.environ, {"CAF_SPRINT_ID": "x"}):
                captured = io.StringIO()
                with patch("sys.stdout", captured):
                    d = m.LeadDisplay("eng", "mission")
                    d.progress(60, "building...")
                output = captured.getvalue()
        self.assertIn("60%", output)
        self.assertIn("building...", output)
        self.assertIn("█", output)

    def test_done_outputs_done_label(self):
        import lib.agent_display as m
        with patch.object(m, "_RICH", False), patch.object(m, "_CMUX", False):
            with patch.dict(os.environ, {"CAF_SPRINT_ID": "x"}):
                captured = io.StringIO()
                with patch("sys.stdout", captured):
                    d = m.LeadDisplay("eng", "mission")
                    d.done("All tasks complete.")
                output = captured.getvalue()
        self.assertIn("DONE", output)
        self.assertIn("All tasks complete.", output)

    def test_fail_outputs_failed_label(self):
        import lib.agent_display as m
        with patch.object(m, "_RICH", False), patch.object(m, "_CMUX", False):
            with patch.dict(os.environ, {"CAF_SPRINT_ID": "x"}):
                captured = io.StringIO()
                with patch("sys.stdout", captured):
                    d = m.LeadDisplay("eng", "mission")
                    d.fail("Something went wrong.")
                output = captured.getvalue()
        self.assertIn("FAILED", output)
        self.assertIn("Something went wrong.", output)

    def test_cmux_status_called_on_task_running(self):
        """When CMUX is available, task() calls set_status."""
        import lib.agent_display as m
        status_calls = []
        with patch.object(m, "_RICH", False), \
             patch.object(m, "_CMUX", True), \
             patch.object(m, "set_status", side_effect=lambda t: status_calls.append(t)), \
             patch.object(m, "set_progress", MagicMock()), \
             patch.dict(os.environ, {"CAF_SPRINT_ID": "x", "CMUX_SURFACE_ID": "s1"}):
            d = m.LeadDisplay("eng", "mission")
            d.task("doing work", "running")
        self.assertTrue(any("doing work" in c for c in status_calls))

    def test_cmux_progress_called_on_done(self):
        """When CMUX is available, done() calls set_progress(100)."""
        import lib.agent_display as m
        progress_calls = []
        with patch.object(m, "_RICH", False), \
             patch.object(m, "_CMUX", True), \
             patch.object(m, "set_status", MagicMock()), \
             patch.object(m, "set_progress", side_effect=lambda p: progress_calls.append(p)), \
             patch.dict(os.environ, {"CAF_SPRINT_ID": "x", "CMUX_SURFACE_ID": "s1"}):
            d = m.LeadDisplay("eng", "mission")
            d.done("finished")
        self.assertIn(100, progress_calls)


# ---------------------------------------------------------------------------
# bin/cmux-sprint script tests
# ---------------------------------------------------------------------------

class TestCmuxSprintScript(unittest.TestCase):

    SCRIPT = REPO_ROOT / "bin" / "cmux-sprint"

    def test_script_exists(self):
        self.assertTrue(self.SCRIPT.exists(), "bin/cmux-sprint not found")

    def test_script_is_executable(self):
        self.assertTrue(os.access(self.SCRIPT, os.X_OK), "bin/cmux-sprint not executable")

    def test_bash_syntax(self):
        import subprocess
        result = subprocess.run(["bash", "-n", str(self.SCRIPT)], capture_output=True)
        self.assertEqual(result.returncode, 0, f"bash -n failed: {result.stderr.decode()}")

    def test_usage_exits_nonzero(self):
        import subprocess
        result = subprocess.run([str(self.SCRIPT)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"Usage", result.stderr)

    def test_all_commands_present(self):
        content = self.SCRIPT.read_text()
        for cmd in ("create", "launch-lead", "poll-wave", "gate", "teardown", "status", "list"):
            self.assertIn(cmd, content, f"command '{cmd}' missing from script")

    def test_surfaces_json_logic_present(self):
        content = self.SCRIPT.read_text()
        self.assertIn("surfaces.json", content)
        self.assertIn("_save_surface", content)
        self.assertIn("_get_surface", content)

    def test_cmux_env_detection_present(self):
        content = self.SCRIPT.read_text()
        self.assertIn("CMUX_SURFACE_ID", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
