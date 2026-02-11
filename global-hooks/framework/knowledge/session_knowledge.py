#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Session Knowledge - Shared utilities for the knowledge pipeline.

Provides backward-compatible load_recent() and get_db() functions,
plus shared constants used by all pipeline stages.
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_DIR = Path.home() / ".claude" / "data" / "knowledge-db"
DB_PATH = DB_DIR / "knowledge.db"
CONFIG_PATH = Path.home() / ".claude" / "knowledge_pipeline.yaml"
OBSERVATIONS_FILE = Path.home() / ".claude" / "observations.jsonl"
ANALYSIS_LOG = Path.home() / ".claude" / "analysis_log.jsonl"
PENDING_LEARNINGS = Path.home() / ".claude" / "pending_learnings.json"


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_db():
    """Get a read-only connection to the knowledge database."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def load_recent(project=None, limit=5):
    """Load recent knowledge entries, optionally filtered by project."""
    conn = get_db()
    if not conn:
        return []
    try:
        q = (
            "SELECT id, category, title, content, tags "
            "FROM knowledge_entries "
            "WHERE (expires_at IS NULL OR expires_at > ?)"
        )
        p = [now_iso()]
        if project:
            q += " AND (project = ? OR project IS NULL)"
            p.append(project)
        q += " ORDER BY updated_at DESC LIMIT ?"
        p.append(limit)
        return [dict(r) for r in conn.execute(q, p).fetchall()]
    finally:
        conn.close()
