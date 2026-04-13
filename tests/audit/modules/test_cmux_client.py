"""
CAF Audit — cmux Client Tests
==============================
Tests the cmux Unix socket client: is_available(), _socket_path(), _call(),
new_split(), send_surface(), focus_surface(), list_surfaces(), list_workspaces(),
and capabilities().

Uses monkeypatching on _call() for most tests. One test spins up a real
Unix domain socket server in a thread to exercise the actual socket code path.

Run standalone:
  uv run pytest tests/audit/modules/test_cmux_client.py -v
"""
from __future__ import annotations

import json
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "lib"))

TIMINGS: list[dict] = []


# ── dynamic import (skip entire module if not importable) ────────────────────

try:
    import cmux_client  # type: ignore
    _CMUX_AVAILABLE = True
except ImportError as e:
    _CMUX_AVAILABLE = False
    _CMUX_IMPORT_ERROR = str(e)


def record_timing(test_name: str, elapsed_ms: float) -> None:
    TIMINGS.append({"test": test_name, "ms": elapsed_ms})


# ── skip guard ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def require_cmux_client():
    if not _CMUX_AVAILABLE:
        pytest.skip(f"cmux_client not importable: {_CMUX_IMPORT_ERROR}")


# ── TestIsAvailable ──────────────────────────────────────────────────────────

class TestIsAvailable:
    @pytest.mark.timeout(5)
    def test_returns_false_when_no_env_var(self, monkeypatch):
        t0 = time.perf_counter()
        monkeypatch.delenv("CMUX_SURFACE_ID", raising=False)

        calls = []

        def mock_call(method, params=None):
            calls.append(method)
            return {"ok": True}

        monkeypatch.setattr(cmux_client, "_call", mock_call)
        result = cmux_client.is_available()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_returns_false_when_no_env_var", elapsed_ms)

        assert result is False
        # No socket attempt when env var missing
        assert calls == [], f"Expected no _call when CMUX_SURFACE_ID unset, got: {calls}"

    @pytest.mark.timeout(5)
    def test_returns_false_when_socket_unreachable(self, monkeypatch):
        t0 = time.perf_counter()
        monkeypatch.setenv("CMUX_SURFACE_ID", "test-surface-123")

        def mock_call(method, params=None):
            raise ConnectionRefusedError("No cmux process running")

        monkeypatch.setattr(cmux_client, "_call", mock_call)
        result = cmux_client.is_available()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_returns_false_when_socket_unreachable", elapsed_ms)

        assert result is False

    @pytest.mark.timeout(5)
    def test_returns_true_when_capabilities_ok(self, monkeypatch):
        t0 = time.perf_counter()
        calls = []

        def mock_call(method, params=None):
            calls.append(method)
            return {"ok": True}

        monkeypatch.setattr(cmux_client, "_call", mock_call)
        monkeypatch.setenv("CMUX_SURFACE_ID", "test-surface-123")
        result = cmux_client.is_available()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_returns_true_when_capabilities_ok", elapsed_ms)

        assert result is True
        assert "system.capabilities" in calls

    @pytest.mark.timeout(5)
    def test_returns_false_when_capabilities_not_ok(self, monkeypatch):
        t0 = time.perf_counter()

        def mock_call(method, params=None):
            return {"ok": False}

        monkeypatch.setattr(cmux_client, "_call", mock_call)
        monkeypatch.setenv("CMUX_SURFACE_ID", "test-surface-123")
        result = cmux_client.is_available()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_returns_false_when_capabilities_not_ok", elapsed_ms)

        assert result is False


# ── TestSocketPath ───────────────────────────────────────────────────────────

class TestSocketPath:
    @pytest.mark.timeout(5)
    def test_default_socket_path(self, monkeypatch):
        t0 = time.perf_counter()
        monkeypatch.delenv("CMUX_SOCKET_PATH", raising=False)
        path = cmux_client._socket_path()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_default_socket_path", elapsed_ms)

        assert "cmux.sock" in str(path), f"Default path should contain cmux.sock, got: {path}"

    @pytest.mark.timeout(5)
    def test_custom_socket_path_from_env(self, monkeypatch):
        t0 = time.perf_counter()
        monkeypatch.setenv("CMUX_SOCKET_PATH", "/tmp/test.sock")
        path = cmux_client._socket_path()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_custom_socket_path_from_env", elapsed_ms)

        assert str(path) == "/tmp/test.sock", f"Expected /tmp/test.sock, got: {path}"

    @pytest.mark.timeout(5)
    def test_socket_path_expands_tilde(self, monkeypatch):
        t0 = time.perf_counter()
        monkeypatch.setenv("CMUX_SOCKET_PATH", "~/my-cmux.sock")
        path = cmux_client._socket_path()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_socket_path_expands_tilde", elapsed_ms)

        assert "~" not in str(path), f"Tilde should be expanded, got: {path}"
        assert str(path).endswith("my-cmux.sock"), f"Filename preserved after tilde expand, got: {path}"


# ── TestNewSplit ─────────────────────────────────────────────────────────────

class TestNewSplit:
    @pytest.mark.timeout(5)
    def test_new_split_default_direction(self, monkeypatch):
        t0 = time.perf_counter()
        captured = {}

        def mock_call(method, params=None):
            captured["method"] = method
            captured["params"] = params or {}
            return {"result": {"surface_id": "new-surface-abc"}}

        monkeypatch.setattr(cmux_client, "_call", mock_call)
        monkeypatch.setenv("CMUX_SURFACE_ID", "current-surface")
        monkeypatch.setenv("CMUX_WORKSPACE_ID", "ws-1")
        cmux_client.new_split()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_new_split_default_direction", elapsed_ms)

        assert captured["method"] == "surface.split", f"Expected surface.split, got: {captured['method']}"
        assert captured["params"]["direction"] == "right", (
            f"Default direction should be right, got: {captured['params'].get('direction')}"
        )

    @pytest.mark.timeout(5)
    def test_new_split_left_direction(self, monkeypatch):
        t0 = time.perf_counter()
        captured = {}

        def mock_call(method, params=None):
            captured["params"] = params or {}
            return {"result": {"surface_id": "new-surface-left"}}

        monkeypatch.setattr(cmux_client, "_call", mock_call)
        monkeypatch.setenv("CMUX_SURFACE_ID", "current-surface")
        monkeypatch.setenv("CMUX_WORKSPACE_ID", "ws-1")
        cmux_client.new_split(direction="left")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_new_split_left_direction", elapsed_ms)

        assert captured["params"]["direction"] == "left", (
            f"Expected direction=left, got: {captured['params'].get('direction')}"
        )

    @pytest.mark.timeout(5)
    def test_new_split_returns_surface_id(self, monkeypatch):
        t0 = time.perf_counter()

        def mock_call(method, params=None):
            return {"result": {"surface_id": "abc123"}}

        monkeypatch.setattr(cmux_client, "_call", mock_call)
        monkeypatch.setenv("CMUX_SURFACE_ID", "current-surface")
        monkeypatch.setenv("CMUX_WORKSPACE_ID", "ws-1")
        result = cmux_client.new_split()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_new_split_returns_surface_id", elapsed_ms)

        assert result == "abc123", f"Expected abc123, got: {result}"

    @pytest.mark.timeout(5)
    def test_new_split_with_from_surface(self, monkeypatch):
        t0 = time.perf_counter()
        captured = {}

        def mock_call(method, params=None):
            captured["params"] = params or {}
            return {"result": {"surface_id": "new-from-xyz"}}

        monkeypatch.setattr(cmux_client, "_call", mock_call)
        monkeypatch.setenv("CMUX_SURFACE_ID", "current-surface")
        monkeypatch.setenv("CMUX_WORKSPACE_ID", "ws-1")
        cmux_client.new_split(from_surface="xyz")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_new_split_with_from_surface", elapsed_ms)

        assert captured["params"]["surface_id"] == "xyz", (
            f"from_surface=xyz should be passed as surface_id, got: {captured['params'].get('surface_id')}"
        )


# ── TestSendSurface ──────────────────────────────────────────────────────────

class TestSendSurface:
    @pytest.mark.timeout(5)
    def test_send_surface_calls_correct_method(self, monkeypatch):
        t0 = time.perf_counter()
        captured = {}

        def mock_call(method, params=None):
            captured["method"] = method
            captured["params"] = params or {}
            return {"ok": True}

        monkeypatch.setattr(cmux_client, "_call", mock_call)
        monkeypatch.setenv("CMUX_WORKSPACE_ID", "ws-1")
        cmux_client.send_surface("surf-42", "hello world\n")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_send_surface_calls_correct_method", elapsed_ms)

        assert captured["method"] == "surface.send_text", (
            f"Expected surface.send_text, got: {captured['method']}"
        )
        assert captured["params"]["surface_id"] == "surf-42", (
            f"Expected surface_id=surf-42, got: {captured['params'].get('surface_id')}"
        )
        assert captured["params"]["text"] == "hello world\n", (
            f"Expected text='hello world\\n', got: {captured['params'].get('text')}"
        )

    @pytest.mark.timeout(5)
    def test_send_surface_returns_none(self, monkeypatch):
        """send_surface() returns None (calls _call but discards return value)."""
        t0 = time.perf_counter()

        def mock_call(method, params=None):
            return {"ok": True}

        monkeypatch.setattr(cmux_client, "_call", mock_call)
        monkeypatch.setenv("CMUX_WORKSPACE_ID", "ws-1")
        result = cmux_client.send_surface("surf-99", "test")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_send_surface_returns_none", elapsed_ms)

        assert result is None, f"send_surface() should return None, got: {result}"


# ── TestListFunctions ────────────────────────────────────────────────────────

class TestListFunctions:
    @pytest.mark.timeout(5)
    def test_list_surfaces_calls_surface_list(self, monkeypatch):
        t0 = time.perf_counter()
        captured = {}

        def mock_call(method, params=None):
            captured["method"] = method
            return {"result": {"surfaces": [{"id": "s1"}, {"id": "s2"}]}}

        monkeypatch.setattr(cmux_client, "_call", mock_call)
        monkeypatch.setenv("CMUX_WORKSPACE_ID", "ws-1")
        result = cmux_client.list_surfaces()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_list_surfaces_calls_surface_list", elapsed_ms)

        assert captured["method"] == "surface.list", (
            f"Expected surface.list, got: {captured['method']}"
        )
        assert result == [{"id": "s1"}, {"id": "s2"}], f"Unexpected surfaces: {result}"

    @pytest.mark.timeout(5)
    def test_list_workspaces_calls_workspace_list(self, monkeypatch):
        t0 = time.perf_counter()
        captured = {}

        def mock_call(method, params=None):
            captured["method"] = method
            return {"result": {"workspaces": [{"id": "w1"}]}}

        monkeypatch.setattr(cmux_client, "_call", mock_call)
        result = cmux_client.list_workspaces()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_list_workspaces_calls_workspace_list", elapsed_ms)

        assert captured["method"] == "workspace.list", (
            f"Expected workspace.list, got: {captured['method']}"
        )
        assert result == [{"id": "w1"}], f"Unexpected workspaces: {result}"

    @pytest.mark.timeout(5)
    def test_list_surfaces_returns_empty_on_missing_key(self, monkeypatch):
        """If response has no 'surfaces' key, returns empty list."""
        t0 = time.perf_counter()

        def mock_call(method, params=None):
            return {"result": {}}

        monkeypatch.setattr(cmux_client, "_call", mock_call)
        monkeypatch.setenv("CMUX_WORKSPACE_ID", "ws-1")
        result = cmux_client.list_surfaces()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_list_surfaces_returns_empty_on_missing_key", elapsed_ms)

        assert result == [], f"Expected [], got: {result}"

    @pytest.mark.timeout(5)
    def test_list_workspaces_returns_empty_on_missing_key(self, monkeypatch):
        """If response has no 'workspaces' key, returns empty list."""
        t0 = time.perf_counter()

        def mock_call(method, params=None):
            return {"result": {}}

        monkeypatch.setattr(cmux_client, "_call", mock_call)
        result = cmux_client.list_workspaces()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_list_workspaces_returns_empty_on_missing_key", elapsed_ms)

        assert result == [], f"Expected [], got: {result}"


# ── TestFocusSurface ─────────────────────────────────────────────────────────

class TestFocusSurface:
    @pytest.mark.timeout(5)
    def test_focus_surface_calls_correct_method(self, monkeypatch):
        t0 = time.perf_counter()
        captured = {}

        def mock_call(method, params=None):
            captured["method"] = method
            captured["params"] = params or {}
            return {"ok": True}

        monkeypatch.setattr(cmux_client, "_call", mock_call)
        monkeypatch.setenv("CMUX_WORKSPACE_ID", "ws-1")
        cmux_client.focus_surface("surf-focus-01")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_focus_surface_calls_correct_method", elapsed_ms)

        assert captured["method"] == "surface.focus", (
            f"Expected surface.focus, got: {captured['method']}"
        )
        assert captured["params"]["surface_id"] == "surf-focus-01", (
            f"Expected surface_id=surf-focus-01, got: {captured['params'].get('surface_id')}"
        )

    @pytest.mark.timeout(5)
    def test_focus_surface_returns_none(self, monkeypatch):
        """focus_surface() returns None (calls _call but discards return value)."""
        t0 = time.perf_counter()

        def mock_call(method, params=None):
            return {"ok": True}

        monkeypatch.setattr(cmux_client, "_call", mock_call)
        monkeypatch.setenv("CMUX_WORKSPACE_ID", "ws-1")
        result = cmux_client.focus_surface("surf-focus-02")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_focus_surface_returns_none", elapsed_ms)

        assert result is None, f"focus_surface() should return None, got: {result}"


# ── TestCapabilities ─────────────────────────────────────────────────────────

class TestCapabilities:
    @pytest.mark.timeout(5)
    def test_capabilities_calls_system_capabilities(self, monkeypatch):
        t0 = time.perf_counter()
        captured = {}

        def mock_call(method, params=None):
            captured["method"] = method
            return {"ok": True, "version": "1.0"}

        monkeypatch.setattr(cmux_client, "_call", mock_call)
        result = cmux_client.capabilities()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_capabilities_calls_system_capabilities", elapsed_ms)

        assert captured["method"] == "system.capabilities", (
            f"Expected system.capabilities, got: {captured['method']}"
        )
        assert result == {"ok": True, "version": "1.0"}, f"Unexpected result: {result}"


# ── TestMockSocketServer ─────────────────────────────────────────────────────

class TestMockSocketServer:
    @pytest.mark.timeout(5)
    def test_call_with_real_unix_socket(self, tmp_path, monkeypatch):
        """Spin up a real Unix socket server, verify _call() sends/receives correctly."""
        t0 = time.perf_counter()
        import uuid as _uuid
        sock_path = Path(f"/tmp/caf_test_{_uuid.uuid4().hex[:8]}.sock")

        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_sock.bind(str(sock_path))
        server_sock.listen(1)

        def server():
            conn, _ = server_sock.accept()
            data = b""
            while b"\n" not in data:
                chunk = conn.recv(1024)
                if not chunk:
                    break
                data += chunk
            req = json.loads(data.split(b"\n")[0])
            resp = json.dumps({
                "ok": True,
                "surface_id": "test-123",
                "echo_method": req["method"],
            }) + "\n"
            conn.sendall(resp.encode())
            conn.close()
            server_sock.close()

        t = threading.Thread(target=server, daemon=True)
        t.start()

        monkeypatch.setenv("CMUX_SOCKET_PATH", str(sock_path))
        result = cmux_client._call("surface.split", {"direction": "right"})
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_call_with_real_unix_socket", elapsed_ms)

        assert result["ok"] is True, f"Expected ok=True, got: {result}"
        assert result["surface_id"] == "test-123", f"Expected surface_id=test-123, got: {result}"
        assert result["echo_method"] == "surface.split", (
            f"Expected echo_method=surface.split, got: {result.get('echo_method')}"
        )
        t.join(timeout=2)

    @pytest.mark.timeout(5)
    def test_call_sends_correct_json_structure(self, tmp_path, monkeypatch):
        """Verify the JSON payload sent by _call() has method and params keys."""
        t0 = time.perf_counter()
        import uuid as _uuid2
        sock_path = Path(f"/tmp/caf_test2_{_uuid2.uuid4().hex[:8]}.sock")
        received_payloads: list[dict] = []

        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_sock.bind(str(sock_path))
        server_sock.listen(1)

        def server():
            conn, _ = server_sock.accept()
            data = b""
            while b"\n" not in data:
                chunk = conn.recv(1024)
                if not chunk:
                    break
                data += chunk
            req = json.loads(data.split(b"\n")[0])
            received_payloads.append(req)
            resp = json.dumps({"ok": True}) + "\n"
            conn.sendall(resp.encode())
            conn.close()
            server_sock.close()

        t = threading.Thread(target=server, daemon=True)
        t.start()

        monkeypatch.setenv("CMUX_SOCKET_PATH", str(sock_path))
        cmux_client._call("workspace.list", {"extra": "param"})
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_call_sends_correct_json_structure", elapsed_ms)

        t.join(timeout=2)
        assert len(received_payloads) == 1, f"Expected 1 payload, got: {len(received_payloads)}"
        payload = received_payloads[0]
        assert "method" in payload, f"Payload missing 'method' key: {payload}"
        assert "params" in payload, f"Payload missing 'params' key: {payload}"
        assert payload["method"] == "workspace.list", (
            f"Expected method=workspace.list, got: {payload['method']}"
        )
        assert payload["params"] == {"extra": "param"}, (
            f"Unexpected params: {payload['params']}"
        )
