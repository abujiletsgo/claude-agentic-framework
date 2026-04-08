#!/usr/bin/env python3
"""
palace_init.py — Shared utility for project-local mempalace operations.

All mempalace data lives in CWD/.mempalace/ (project-local, never global).
Provides fail-open helpers: if mempalace is not installed, returns None gracefully.

Usage:
    from palace_init import ensure_palace, get_project_kg, get_project_stack, get_palace_path
"""

import glob
import json
import os
import subprocess
import sys
from pathlib import Path


def _find_mempalace_site_packages() -> str | None:
    """Find mempalace venv site-packages regardless of Python version."""
    base = os.path.expanduser("~/Documents/mempalace/.venv/lib")
    matches = glob.glob(os.path.join(base, "python3.*/site-packages"))
    return matches[0] if matches else None


def _get_mempalace_python() -> str | None:
    """Get the mempalace venv's own Python (handles version mismatch with system Python)."""
    venv_python = os.path.expanduser("~/Documents/mempalace/.venv/bin/python")
    if os.path.exists(venv_python):
        return venv_python
    return None


def _ensure_mempalace_importable() -> bool:
    """Add mempalace to sys.path if available. Returns True if importable."""
    venv_site = _find_mempalace_site_packages()
    if not venv_site:
        return False
    if venv_site not in sys.path:
        sys.path.insert(0, venv_site)
    return True


def get_palace_path(cwd: str | None = None) -> Path:
    """Return the project-local palace path: CWD/.mempalace/palace/"""
    cwd = cwd or os.getcwd()
    return Path(cwd).resolve() / ".mempalace" / "palace"


def get_kg_path(cwd: str | None = None) -> Path:
    """Return the project-local KG database path."""
    cwd = cwd or os.getcwd()
    return Path(cwd).resolve() / ".mempalace" / "knowledge_graph.sqlite3"


def ensure_palace(cwd: str | None = None) -> Path | None:
    """
    Ensure .mempalace/ directory exists in project root.
    Creates palace/ and returns the palace path, or None if mempalace unavailable.
    """
    if not _ensure_mempalace_importable():
        return None
    palace_path = get_palace_path(cwd)
    palace_path.mkdir(parents=True, exist_ok=True)
    return palace_path


def get_project_kg(cwd: str | None = None):
    """
    Return a KnowledgeGraph instance using project-local SQLite.
    Returns None if mempalace is unavailable.
    """
    if not _ensure_mempalace_importable():
        return None
    try:
        from mempalace.knowledge_graph import KnowledgeGraph
        kg_path = get_kg_path(cwd)
        kg_path.parent.mkdir(parents=True, exist_ok=True)
        return KnowledgeGraph(db_path=str(kg_path))
    except Exception:
        return None


def get_project_stack(cwd: str | None = None):
    """
    Return a MemoryStack instance using project-local palace.
    Returns None if mempalace is unavailable.
    """
    if not _ensure_mempalace_importable():
        return None
    try:
        from mempalace.layers import MemoryStack
        palace_path = ensure_palace(cwd)
        if not palace_path:
            return None
        return MemoryStack(palace_path=str(palace_path))
    except Exception:
        return None


def search_project_memories(query: str, cwd: str | None = None,
                            wing: str | None = None, room: str | None = None,
                            n_results: int = 5) -> list[dict]:
    """
    Search project-local mempalace for relevant memories.
    Uses subprocess with mempalace venv Python (ChromaDB needs matching numpy).
    Returns list of {text, similarity, room} dicts, or empty list on failure.
    """
    venv_python = _get_mempalace_python()
    if not venv_python:
        return []
    palace_path = get_palace_path(cwd)
    if not palace_path.exists():
        return []
    try:
        # Build kwargs dynamically to avoid passing None
        kwargs_parts = [
            f"    query={json.dumps(query)}",
            f"    palace_path={json.dumps(str(palace_path))}",
            f"    n_results={n_results}",
        ]
        if wing:
            kwargs_parts.append(f"    wing={json.dumps(wing)}")
        if room:
            kwargs_parts.append(f"    room={json.dumps(room)}")
        kwargs_str = ",\n".join(kwargs_parts)
        script = f"""
import json, sys
from mempalace.searcher import search_memories
results = search_memories(
{kwargs_str},
)
items = results.get("results", []) if isinstance(results, dict) else []
print(json.dumps(items))
"""
        result = subprocess.run(
            [venv_python, "-c", script],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except Exception:
        pass
    return []


def store_drawer(content: str, cwd: str | None = None,
                 wing: str | None = None, room: str = "general",
                 source_file: str = "") -> bool:
    """
    Store content in a project-local mempalace drawer.
    Uses subprocess with mempalace venv Python (ChromaDB needs matching numpy).
    Returns True on success, False on failure. Fail-open.
    """
    venv_python = _get_mempalace_python()
    if not venv_python:
        return False
    cwd = cwd or os.getcwd()
    palace_path = get_palace_path(cwd)
    palace_path.mkdir(parents=True, exist_ok=True)
    if not wing:
        wing = Path(cwd).resolve().name
    try:
        script = f"""
import sys
from mempalace.miner import get_collection, add_drawer
palace_path = {json.dumps(str(palace_path))}
collection = get_collection(palace_path)
add_drawer(
    collection=collection,
    wing={json.dumps(wing)},
    room={json.dumps(room)},
    content={json.dumps(content)},
    source_file={json.dumps(source_file)},
    chunk_index=0,
    agent="caf-hook",
)
print("OK")
"""
        result = subprocess.run(
            [venv_python, "-c", script],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0 and "OK" in result.stdout
    except Exception:
        return False


def has_mempalace() -> bool:
    """Check if mempalace is available without side effects."""
    return _find_mempalace_site_packages() is not None
