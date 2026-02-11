#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""
LEARN stage of the Knowledge Pipeline.

Hook: SessionEnd (runs after analyze_session.py)
Reads pending_learnings.json produced by the ANALYZE stage,
stores each learning into the knowledge.db FTS5 database,
with deduplication, auto-tagging, and session linking.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude" / "knowledge_pipeline.yaml"
PENDING_LEARNINGS = Path.home() / ".claude" / "pending_learnings.json"
DB_DIR = Path.home() / ".claude" / "data" / "knowledge-db"
DB_PATH = DB_DIR / "knowledge.db"

# ---------------------------------------------------------------------------
# Schema (matches knowledge_cli.py exactly)
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT DEFAULT '',
    project TEXT DEFAULT NULL,
    confidence REAL DEFAULT 0.5,
    source TEXT DEFAULT 'user',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    expires_at TEXT DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_cat ON knowledge_entries(category);
CREATE INDEX IF NOT EXISTS idx_proj ON knowledge_entries(project);
CREATE INDEX IF NOT EXISTS idx_created ON knowledge_entries(created_at);
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    title, content, tags,
    content=knowledge_entries, content_rowid=id,
    tokenize='porter unicode61'
);
CREATE TRIGGER IF NOT EXISTS kn_ai AFTER INSERT ON knowledge_entries BEGIN
    INSERT INTO knowledge_fts(rowid, title, content, tags) VALUES (new.id, new.title, new.content, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS kn_ad AFTER DELETE ON knowledge_entries BEGIN
    INSERT INTO knowledge_fts(knowledge_fts, rowid, title, content, tags) VALUES ('delete', old.id, old.title, old.content, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS kn_au AFTER UPDATE ON knowledge_entries BEGIN
    INSERT INTO knowledge_fts(knowledge_fts, rowid, title, content, tags) VALUES ('delete', old.id, old.title, old.content, old.tags);
    INSERT INTO knowledge_fts(rowid, title, content, tags) VALUES (new.id, new.title, new.content, new.tags);
END;
CREATE TABLE IF NOT EXISTS knowledge_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id INTEGER NOT NULL REFERENCES knowledge_entries(id) ON DELETE CASCADE,
    to_id INTEGER NOT NULL REFERENCES knowledge_entries(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(from_id, to_id, relation_type)
);
CREATE INDEX IF NOT EXISTS idx_rel_from ON knowledge_relations(from_id);
CREATE INDEX IF NOT EXISTS idx_rel_to ON knowledge_relations(to_id);
"""


def load_config():
    """Load pipeline config with safe defaults."""
    defaults = {
        "learn": {
            "enabled": True,
            "auto_tag": True,
            "deduplicate": True,
            "min_confidence": 0.3,
            "source": "pipeline",
        }
    }
    if CONFIG_PATH.exists():
        try:
            import yaml
            with open(CONFIG_PATH, "r") as f:
                cfg = yaml.safe_load(f) or {}
            learn = cfg.get("learn", {})
            for k, v in learn.items():
                defaults["learn"][k] = v
        except Exception:
            pass
    return defaults["learn"]


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_db():
    """Get database connection, initializing schema if needed."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def is_duplicate(conn, content, threshold=0.7):
    """Check if a similar learning already exists using FTS5 search.

    Uses BM25 ranking: if the top match has a very good score and
    the content is very similar, treat it as a duplicate.
    """
    # Extract key words for FTS search (first 100 chars, remove special chars)
    search_terms = content[:100].replace('"', "").replace("'", "")
    # Build a simple search query from content words
    words = [w for w in search_terms.split() if len(w) > 3]
    if not words:
        return False

    # Use OR query with top words
    query = " OR ".join(words[:8])

    try:
        rows = conn.execute(
            "SELECT e.content, rank FROM knowledge_fts f "
            "JOIN knowledge_entries e ON f.rowid = e.id "
            "WHERE knowledge_fts MATCH ? "
            "ORDER BY rank LIMIT 3",
            (query,),
        ).fetchall()

        for row in rows:
            existing = row["content"].lower().strip()
            new = content.lower().strip()
            # Simple similarity check: if the contents share > 70% of words
            existing_words = set(existing.split())
            new_words = set(new.split())
            if not new_words:
                continue
            overlap = len(existing_words & new_words) / len(new_words)
            if overlap > threshold:
                return True
    except Exception:
        # FTS table might not have data yet
        pass

    return False


def auto_generate_tags(tag, content, context_str):
    """Generate tags from the learning tag, content, and context."""
    tags = [tag.lower()]

    # Extract tool names mentioned
    tools = ["Edit", "Write", "Read", "Bash", "Grep", "Glob", "Task"]
    for tool in tools:
        if tool.lower() in content.lower() or tool.lower() in context_str.lower():
            tags.append(f"tool:{tool.lower()}")

    # Extract common concepts
    concepts = {
        "error": "error-handling",
        "test": "testing",
        "performance": "performance",
        "security": "security",
        "workflow": "workflow",
        "git": "git",
        "search": "search",
        "file": "file-operations",
        "debug": "debugging",
        "refactor": "refactoring",
    }
    combined = (content + " " + context_str).lower()
    for keyword, concept_tag in concepts.items():
        if keyword in combined:
            tags.append(concept_tag)

    return ",".join(sorted(set(tags)))


def store_learning(conn, learning, session_id, config):
    """Store a single learning entry into the database."""
    tag = learning.get("tag", "LEARNED")
    content = learning.get("content", "")
    context_str = learning.get("context", "")
    confidence = learning.get("confidence", 0.5)

    if not content:
        return None

    # Check minimum confidence
    min_conf = config.get("min_confidence", 0.3)
    if confidence < min_conf:
        return None

    # Deduplication check
    if config.get("deduplicate", True):
        if is_duplicate(conn, content):
            return None

    # Generate tags
    if config.get("auto_tag", True):
        tags = auto_generate_tags(tag, content, context_str)
    else:
        tags = tag.lower()

    # Build title from content (first 80 chars)
    title = content[:80].rstrip(".")
    if len(content) > 80:
        title += "..."

    # Store in database
    source = config.get("source", "pipeline")
    ts = now_iso()

    cur = conn.execute(
        "INSERT INTO knowledge_entries "
        "(category, title, content, tags, project, confidence, source, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            tag,           # category = LEARNED / PATTERN / INVESTIGATION
            title,
            content + ("\n\nContext: " + context_str if context_str else ""),
            tags,
            None,          # project = global (not project-specific)
            confidence,
            f"{source}:session:{session_id}",
            ts,
            ts,
        ),
    )
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    config = load_config()

    if not config.get("enabled", True):
        sys.exit(0)

    session_id = input_data.get("session_id", "unknown")

    # Load pending learnings from ANALYZE stage
    if not PENDING_LEARNINGS.exists():
        sys.exit(0)

    try:
        with open(PENDING_LEARNINGS, "r") as f:
            pending = json.load(f)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    learnings = pending.get("learnings", [])
    if not learnings:
        sys.exit(0)

    # Open database
    try:
        conn = get_db()
    except Exception:
        sys.exit(0)

    stored_count = 0
    stored_ids = []
    try:
        for learning in learnings:
            entry_id = store_learning(conn, learning, session_id, config)
            if entry_id is not None:
                stored_count += 1
                stored_ids.append(entry_id)

        # Create relations between learnings from same session
        if len(stored_ids) > 1:
            ts = now_iso()
            for i in range(len(stored_ids)):
                for j in range(i + 1, len(stored_ids)):
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO knowledge_relations "
                            "(from_id, to_id, relation_type, created_at) "
                            "VALUES (?, ?, ?, ?)",
                            (stored_ids[i], stored_ids[j], "same_session", ts),
                        )
                    except Exception:
                        pass
            conn.commit()

    finally:
        conn.close()

    # Clean up pending file after successful storage
    try:
        # Rename to processed instead of deleting (for auditing)
        processed_path = PENDING_LEARNINGS.with_suffix(".processed.json")
        PENDING_LEARNINGS.rename(processed_path)
    except Exception:
        try:
            PENDING_LEARNINGS.unlink()
        except Exception:
            pass

    # Log storage result to analysis log
    try:
        log_entry = {
            "timestamp": now_iso(),
            "stage": "learn",
            "session_id": session_id,
            "learnings_received": len(learnings),
            "learnings_stored": stored_count,
            "entry_ids": stored_ids,
        }
        log_file = Path.home() / ".claude" / "analysis_log.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
