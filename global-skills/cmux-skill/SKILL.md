---
name: cmux-skill
description: "cmux terminal multiplexer automation. Splits panes, sends text, focuses surfaces, lists workspaces/windows, and controls the embedded browser — all via the Unix socket API."
always-loaded: true
triggers:
  - "split pane"
  - "new pane"
  - "open pane"
  - "send to pane"
  - "send text to"
  - "focus pane"
  - "focus surface"
  - "list panes"
  - "list surfaces"
  - "list workspaces"
  - "cmux"
  - "terminal pane"
  - "open browser"
  - "browser pane"
user-invocable: true
---

# /cmux-skill — cmux Automation

Use `lib/cmux_client.py` (already in this repo) or raw socket JSON calls whenever you need to control cmux surfaces, panes, workspaces, windows, or the embedded browser.

## Availability Check

Always check before doing cmux work:

```python
import sys; sys.path.insert(0, 'lib')
import cmux_client as cmux

if not cmux.is_available():
    print("Not running inside cmux — skip or fall back")
    sys.exit(0)
```

`is_available()` returns `True` only when `CMUX_SURFACE_ID` is set AND the socket responds to `system.capabilities`.

## Environment Variables

| Variable | Meaning |
|---|---|
| `CMUX_SURFACE_ID` | Current surface (terminal pane) ID |
| `CMUX_WORKSPACE_ID` | Current workspace (tab) ID |
| `CMUX_TAB_ID` | Alias for workspace ID |
| `CMUX_SOCKET_PATH` | Socket path (default: `~/Library/Application Support/cmux/cmux.sock`) |

## Raw Socket Protocol

All calls are newline-terminated JSON over a Unix socket:

```python
import json, socket, os
from pathlib import Path

def call(method, params=None):
    msg = json.dumps({"method": method, "params": params or {}}) + "\n"
    sock = Path(os.environ.get("CMUX_SOCKET_PATH",
                "~/Library/Application Support/cmux/cmux.sock")).expanduser()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(str(sock))
        s.sendall(msg.encode())
        data = b""
        while True:
            chunk = s.recv(4096)
            if not chunk or b"\n" in data:
                data += chunk; break
            data += chunk
    return json.loads(data.split(b"\n")[0])
```

Response shape: `{"ok": true, "id": null, "result": {...}}` — always read from `result`, never `data`.

---

## Surface (Terminal Pane) Operations

### Split a pane

```python
# Split right from current pane
new_sid = cmux.new_split("right")           # "left" | "right" | "up" | "down"

# Split a SPECIFIC pane (not the current one)
new_sid = cmux.new_split("right", from_surface="<target-surface-id>")
```

**CRITICAL**: `from_surface` must be explicit. Using `CMUX_SURFACE_ID` always splits *your* pane.

### Balanced 4-way equal split

```python
# All four panes end up equal width
ag1 = os.environ["CMUX_SURFACE_ID"]
ag2 = cmux.new_split("right", from_surface=ag1)   # ag1=464, ag2=464
ag3 = cmux.new_split("right", from_surface=ag2)   # ag2=232, ag3=232
ag4 = cmux.new_split("right", from_surface=ag1)   # ag1=232, ag4=232
```

### Send text / commands

```python
cmux.send_surface(surface_id, "ls -la\n")         # \n required to execute
cmux.send_surface(surface_id, "claude\n")
# Multiline: send full text + "\n" for Enter
```

### Focus a surface

```python
cmux.focus_surface(surface_id)
```

### List surfaces in current workspace

```python
surfaces = cmux.list_surfaces()
# → [{"id": "...", "title": "...", ...}, ...]
```

### Read surface text

```python
result = call("surface.read_text", {
    "surface_id": sid,
    "workspace_id": os.environ["CMUX_WORKSPACE_ID"],
})
text = result["result"]["text"]
```

### Close a surface

```python
call("surface.close", {
    "surface_id": sid,
    "workspace_id": os.environ["CMUX_WORKSPACE_ID"],
})
```

### Other surface methods

```python
call("surface.create",  {"workspace_id": wid})
call("surface.move",    {"surface_id": sid, "workspace_id": wid, "direction": "right"})
call("surface.reorder", {"surface_id": sid, "workspace_id": wid, "index": 0})
call("surface.trigger_flash", {"surface_id": sid, "workspace_id": wid})
call("surface.health",  {"surface_id": sid, "workspace_id": wid})
call("surface.send_key", {"surface_id": sid, "workspace_id": wid, "key": "ctrl+c"})
```

---

## Pane Operations

A *pane* is a layout container; a *surface* is the terminal inside a pane.

```python
panes = call("pane.list", {"workspace_id": wid})
# → {"panes": [...], "container_frame": {"width": N, "height": N}}

call("pane.resize", {
    "pane_id": pid,
    "workspace_id": wid,
    "direction": "right",   # left | right | up | down
    "amount": 100,          # pixels
})

call("pane.focus",   {"pane_id": pid, "workspace_id": wid})
call("pane.surfaces", {"pane_id": pid, "workspace_id": wid})
call("pane.break",   {"pane_id": pid, "workspace_id": wid})   # detach to own workspace
call("pane.swap",    {"pane_id": pid, "workspace_id": wid, "target_pane_id": other_pid})
call("pane.join",    {"source_pane_id": pid, "target_workspace_id": wid})
call("pane.create",  {"workspace_id": wid})
call("pane.last",    {"workspace_id": wid})  # focus last-used pane
```

**AVOID** `workspace.equalize_splits` — it equalizes ALL panes globally and breaks custom layouts.

---

## Workspace (Tab) Operations

```python
workspaces = cmux.list_workspaces()
# → [{"id": "...", "name": "...", ...}, ...]

call("workspace.create",  {"window_id": win_id, "name": "my-tab"})
call("workspace.rename",  {"workspace_id": wid, "name": "new-name"})
call("workspace.select",  {"workspace_id": wid})
call("workspace.close",   {"workspace_id": wid})
call("workspace.next",    {"workspace_id": wid})
call("workspace.previous", {"workspace_id": wid})
call("workspace.current", {})
call("workspace.last",    {})
call("workspace.reorder", {"workspace_id": wid, "index": 0})
call("workspace.move_to_window", {"workspace_id": wid, "window_id": win_id})
call("workspace.action",  {"workspace_id": wid, "action": "<action>"})
```

---

## Window Operations

```python
call("window.list",    {})
call("window.create",  {})
call("window.current", {})
call("window.focus",   {"window_id": win_id})
call("window.close",   {"window_id": win_id})
```

---

## Notification Operations

```python
call("notification.create", {
    "title": "Sprint done",
    "body": "All waves complete.",
})

call("notification.create_for_surface", {
    "surface_id": sid,
    "workspace_id": wid,
    "title": "Task finished",
    "body": "See results/",
})

call("notification.list",  {})
call("notification.clear", {"notification_id": nid})
```

---

## Browser Operations (cmux embedded browser)

cmux has a full Playwright-compatible browser API. Open a browser split from a surface:

```python
call("browser.open_split", {"surface_id": sid, "workspace_id": wid})
call("browser.navigate",   {"url": "https://example.com"})
call("browser.screenshot", {"path": "/tmp/screen.png"})
call("browser.snapshot",   {})   # accessibility tree
call("browser.get.text",   {"selector": "h1"})
call("browser.click",      {"selector": "button#submit"})
call("browser.fill",       {"selector": "input[name=q]", "value": "search term"})
call("browser.eval",       {"expression": "document.title"})
call("browser.tab.list",   {})
call("browser.tab.new",    {"url": "https://..."})
```

---

## System / Debug

```python
call("system.capabilities", {})   # full method list + version
call("system.identify",     {})   # app identity
call("system.ping",         {})   # heartbeat
call("system.tree",         {})   # full workspace/pane/surface tree
call("debug.terminals",     {})   # low-level terminal state
call("settings.open",       {})   # open cmux settings UI
call("feedback.open",       {})   # open feedback panel
```

---

## Common Patterns

### Launch a command in a new pane, return focus

```python
import os, time, sys
sys.path.insert(0, 'lib')
import cmux_client as cmux

if cmux.is_available():
    original = os.environ["CMUX_SURFACE_ID"]
    new_sid = cmux.new_split("right")
    cmux.send_surface(new_sid, f"cd {os.getcwd()}\n")
    cmux.send_surface(new_sid, "your-command\n")
    cmux.focus_surface(original)
```

### Launch claude in a new pane with a prompt

```python
new_sid = cmux.new_split("right")
cmux.send_surface(new_sid, f"cd {os.getcwd()}\n")
cmux.send_surface(new_sid, "claude\n")
time.sleep(1)   # let claude initialize
cmux.send_surface(new_sid, "Your prompt here\n")
```

### Read output from a surface

```python
text = call("surface.read_text", {
    "surface_id": new_sid,
    "workspace_id": os.environ["CMUX_WORKSPACE_ID"],
})["result"]["text"]
```

### Show a desktop notification when done

```python
call("notification.create", {"title": "Done", "body": "Task complete."})
```

---

## What Does NOT Exist

- `set_status()` — no such socket method; `lib/cmux_client.py` stubs it as no-op
- `set_progress()` — same; no-op stub
- `log()` — same; no-op stub
- `workspace.equalize_splits` — exists but AVOID (global, breaks custom layouts)

---

## Graceful Fallback

Always guard cmux calls so the script works outside cmux:

```python
if cmux.is_available():
    # cmux path
else:
    # fallback: print to stdout, use subprocess, etc.
```
