"""
cmux Unix socket client.
Socket: os.environ.get('CMUX_SOCKET_PATH', '~/Library/Application Support/cmux/cmux.sock')
Protocol: newline-terminated JSON, method names use namespace.verb format (e.g. surface.split).
"""
import json
import os
import socket
from pathlib import Path


def _socket_path() -> Path:
    return Path(os.environ.get("CMUX_SOCKET_PATH", "~/Library/Application Support/cmux/cmux.sock")).expanduser()


def _workspace_id() -> str:
    return os.environ.get("CMUX_WORKSPACE_ID", "")


def _surface_id() -> str:
    return os.environ.get("CMUX_SURFACE_ID", "")


def _call(method: str, params: dict | None = None) -> dict:
    """Send one JSON command, return parsed response. Raises on socket error."""
    msg = json.dumps({"method": method, "params": params or {}}) + "\n"
    sock_path = _socket_path()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(str(sock_path))
        s.sendall(msg.encode())
        data = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break
    return json.loads(data.split(b"\n")[0])


def is_available() -> bool:
    """True if running inside cmux AND socket is reachable."""
    if "CMUX_SURFACE_ID" not in os.environ:
        return False
    try:
        resp = _call("system.capabilities")
        return resp.get("ok", False)
    except Exception:
        return False


def capabilities() -> dict:
    """Return cmux capabilities dict."""
    return _call("system.capabilities")


def new_split(direction: str = "right", from_surface: str | None = None) -> str:
    """Split a surface. Returns new surface_id. Defaults to splitting current surface."""
    resp = _call("surface.split", {
        "surface_id": from_surface or _surface_id(),
        "workspace_id": _workspace_id(),
        "direction": direction,
    })
    result = resp.get("result") or {}
    return result.get("surface_id") or result.get("id", "")


def send_surface(surface_id: str, text: str) -> None:
    """Send text to a specific surface (as keyboard input)."""
    _call("surface.send_text", {
        "surface_id": surface_id,
        "workspace_id": _workspace_id(),
        "text": text,
    })


def focus_surface(surface_id: str) -> None:
    """Focus a surface."""
    _call("surface.focus", {
        "surface_id": surface_id,
        "workspace_id": _workspace_id(),
    })


def list_surfaces() -> list[dict]:
    """Return list of surface dicts."""
    resp = _call("surface.list", {"workspace_id": _workspace_id()})
    result = resp.get("result") or {}
    return result.get("surfaces", [])


def list_workspaces() -> list[dict]:
    """Return list of workspace dicts."""
    resp = _call("workspace.list", {})
    result = resp.get("result") or {}
    return result.get("workspaces", [])


def set_status(text: str, surface_id: str | None = None) -> None:
    """No-op: cmux socket API has no set-status method. Placeholder for future."""
    pass


def set_progress(pct: int, surface_id: str | None = None) -> None:
    """No-op: cmux socket API has no set-progress method. Placeholder for future."""
    pass


def log(message: str, surface_id: str | None = None) -> None:
    """No-op: cmux socket API has no log method. Placeholder for future."""
    pass
