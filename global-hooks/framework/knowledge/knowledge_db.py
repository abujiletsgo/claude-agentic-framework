#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Knowledge Database - Persistent Memory with FTS5
=================================================

SQLite FTS5-backed knowledge store for cross-session learning.
Provides BM25-ranked full-text search, tag filtering, and JSONL
append-only logging for durability.

Database: ~/.claude/knowledge.db
Log:      ~/.claude/knowledge.jsonl

Tags: LEARNED, DECISION, FACT, PATTERN, INVESTIGATION
"""

import json
import sqlite3
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DB_DIR = Path.home() / ".claude"
DB_PATH = DB_DIR / "knowledge.db"
JSONL_PATH = DB_DIR / "knowledge.jsonl"

VALID_TAGS = {"LEARNED", "DECISION", "FACT", "PATTERN", "INVESTIGATION"}

# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------


def _secure_file(path: Path):
    """Set file permissions to 600 (owner read/write only)."""
    if path.exists():
        os.chmod(str(path), 0o600)


def validate_import_path(file_path: str) -> Path:
    """Validate import file path is safe.

    Restricts imports to:
    - ~/.claude/data/
    - ~/.claude/
    - Current working directory

    Blocks path traversal (..) and symlinks escaping allowed directories.
    """
    # Block path traversal in the raw input
    if ".." in str(file_path):
        raise ValueError("Path traversal (..) not allowed in import paths")

    path = Path(file_path).resolve()

    # Must be in allowed directories
    allowed_dirs = [
        Path.home() / ".claude" / "data",
        Path.home() / ".claude",
        Path.cwd(),
    ]

    is_allowed = False
    for allowed_dir in allowed_dirs:
        try:
            path.relative_to(allowed_dir.resolve())
            is_allowed = True
            break
        except ValueError:
            continue

    if not is_allowed:
        raise ValueError(
            f"Import path must be under one of: {', '.join(str(d) for d in allowed_dirs)}"
        )

    # Must exist and be a regular file
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Not a regular file: {file_path}")

    return path


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------


def _ensure_db_dir():
    """Create database directory if it does not exist."""
    DB_DIR.mkdir(parents=True, exist_ok=True)


def get_db() -> sqlite3.Connection:
    """Open (and optionally create) the knowledge database."""
    _ensure_db_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _init_schema(conn)
    _secure_file(DB_PATH)
    return conn


def _init_schema(conn: sqlite3.Connection):
    """Create tables if they do not exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            content   TEXT    NOT NULL,
            tag       TEXT    NOT NULL,
            context   TEXT,
            session_id TEXT,
            timestamp TEXT    NOT NULL,
            metadata  TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_knowledge_tag
            ON knowledge(tag);
        CREATE INDEX IF NOT EXISTS idx_knowledge_context
            ON knowledge(context);
        CREATE INDEX IF NOT EXISTS idx_knowledge_timestamp
            ON knowledge(timestamp DESC);
    """)

    # FTS5 virtual table (content-sync with knowledge table)
    # We use a content= external-content table so FTS stays in sync.
    try:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                content,
                tag,
                context,
                session_id,
                timestamp,
                content='knowledge',
                content_rowid='id',
                tokenize='porter unicode61'
            );
        """)
    except sqlite3.OperationalError:
        # FTS5 table already exists
        pass

    # Triggers to keep FTS in sync with main table
    conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
            INSERT INTO knowledge_fts(rowid, content, tag, context, session_id, timestamp)
            VALUES (new.id, new.content, new.tag, new.context, new.session_id, new.timestamp);
        END;

        CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, content, tag, context, session_id, timestamp)
            VALUES ('delete', old.id, old.content, old.tag, old.context, old.session_id, old.timestamp);
        END;

        CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, content, tag, context, session_id, timestamp)
            VALUES ('delete', old.id, old.content, old.tag, old.context, old.session_id, old.timestamp);
            INSERT INTO knowledge_fts(rowid, content, tag, context, session_id, timestamp)
            VALUES (new.id, new.content, new.tag, new.context, new.session_id, new.timestamp);
        END;
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# JSONL append-only log
# ---------------------------------------------------------------------------


def _append_jsonl(entry: dict):
    """Append a single JSON line to the durability log."""
    _ensure_db_dir()
    with open(JSONL_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    _secure_file(JSONL_PATH)


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------


def add_knowledge(
    content: str,
    tag: str,
    context: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> int:
    """
    Add a knowledge entry to both SQLite and JSONL log.

    Returns the row id of the inserted entry.
    """
    tag = tag.upper()
    if tag not in VALID_TAGS:
        raise ValueError(f"Invalid tag '{tag}'. Must be one of: {', '.join(sorted(VALID_TAGS))}")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

    conn = get_db()
    try:
        cursor = conn.execute(
            """
            INSERT INTO knowledge (content, tag, context, session_id, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (content, tag, context, session_id, now, metadata_json),
        )
        conn.commit()
        row_id = cursor.lastrowid

        # Append to JSONL log
        _append_jsonl({
            "id": row_id,
            "timestamp": now,
            "tag": tag,
            "content": content,
            "context": context,
            "session_id": session_id,
            "metadata": metadata,
        })

        return row_id
    finally:
        conn.close()


def search_knowledge(
    query: str,
    tags: Optional[list[str]] = None,
    context: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """
    Full-text search with BM25 ranking.

    Args:
        query:   Search terms (FTS5 query syntax supported)
        tags:    Optional list of tags to filter by
        context: Optional context string to filter by
        limit:   Maximum number of results (default 10)

    Returns list of dicts with id, content, tag, context, session_id,
    timestamp, metadata, and bm25_score (lower is better match).
    """
    conn = get_db()
    try:
        # Build the FTS5 match query
        # We search the content column primarily
        where_clauses = ["knowledge_fts MATCH ?"]
        params: list = [query]

        if tags:
            tags_upper = [t.upper() for t in tags]
            placeholders = ",".join("?" * len(tags_upper))
            where_clauses.append(f"k.tag IN ({placeholders})")
            params.extend(tags_upper)

        if context:
            where_clauses.append("k.context = ?")
            params.append(context)

        params.append(limit)

        where_str = " AND ".join(where_clauses)

        rows = conn.execute(
            f"""
            SELECT k.id, k.content, k.tag, k.context, k.session_id,
                   k.timestamp, k.metadata,
                   bm25(knowledge_fts) AS bm25_score
            FROM knowledge_fts
            JOIN knowledge k ON k.id = knowledge_fts.rowid
            WHERE {where_str}
            ORDER BY bm25(knowledge_fts)
            LIMIT ?
            """,
            params,
        ).fetchall()

        results = []
        for row in rows:
            entry = dict(row)
            if entry.get("metadata"):
                try:
                    entry["metadata"] = json.loads(entry["metadata"])
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append(entry)
        return results
    except sqlite3.OperationalError as e:
        # Handle case where FTS query syntax is invalid
        if "fts5" in str(e).lower():
            # Retry with quoted query (treat as literal phrase)
            return search_knowledge(f'"{query}"', tags=tags, context=context, limit=limit)
        raise
    finally:
        conn.close()


def get_recent(
    limit: int = 10,
    tags: Optional[list[str]] = None,
    context: Optional[str] = None,
) -> list[dict]:
    """
    Get most recent knowledge entries.

    Args:
        limit:   Maximum number of results
        tags:    Optional list of tags to filter by
        context: Optional context string to filter by
    """
    conn = get_db()
    try:
        where_clauses = []
        params: list = []

        if tags:
            tags_upper = [t.upper() for t in tags]
            placeholders = ",".join("?" * len(tags_upper))
            where_clauses.append(f"tag IN ({placeholders})")
            params.extend(tags_upper)

        if context:
            where_clauses.append("context = ?")
            params.append(context)

        where_str = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        params.append(limit)

        rows = conn.execute(
            f"""
            SELECT id, content, tag, context, session_id, timestamp, metadata
            FROM knowledge
            {where_str}
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

        results = []
        for row in rows:
            entry = dict(row)
            if entry.get("metadata"):
                try:
                    entry["metadata"] = json.loads(entry["metadata"])
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append(entry)
        return results
    finally:
        conn.close()


def get_by_id(entry_id: int) -> Optional[dict]:
    """Get a single knowledge entry by ID."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, content, tag, context, session_id, timestamp, metadata FROM knowledge WHERE id = ?",
            (entry_id,),
        ).fetchone()
        if row:
            entry = dict(row)
            if entry.get("metadata"):
                try:
                    entry["metadata"] = json.loads(entry["metadata"])
                except (json.JSONDecodeError, TypeError):
                    pass
            return entry
        return None
    finally:
        conn.close()


def delete_knowledge(entry_id: int) -> bool:
    """Delete a knowledge entry by ID."""
    conn = get_db()
    try:
        cursor = conn.execute("DELETE FROM knowledge WHERE id = ?", (entry_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def count_entries(tags: Optional[list[str]] = None) -> dict:
    """Get count of entries, optionally filtered by tags."""
    conn = get_db()
    try:
        if tags:
            tags_upper = [t.upper() for t in tags]
            placeholders = ",".join("?" * len(tags_upper))
            row = conn.execute(
                f"SELECT COUNT(*) as total FROM knowledge WHERE tag IN ({placeholders})",
                tags_upper,
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) as total FROM knowledge").fetchone()

        total = row["total"] if row else 0

        # Also get per-tag counts
        tag_counts = {}
        for tag_row in conn.execute(
            "SELECT tag, COUNT(*) as cnt FROM knowledge GROUP BY tag ORDER BY cnt DESC"
        ).fetchall():
            tag_counts[tag_row["tag"]] = tag_row["cnt"]

        return {"total": total, "by_tag": tag_counts}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Import / Export
# ---------------------------------------------------------------------------


def export_to_jsonl(output_path: Optional[str] = None, limit: int = 10000) -> str:
    """
    Export knowledge entries to a JSONL file.

    Args:
        output_path: Path to write to (defaults to ~/.claude/knowledge.jsonl)
        limit:       Maximum number of entries to export (default 10,000)

    Returns the path written to.
    """
    out = Path(output_path) if output_path else JSONL_PATH
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, content, tag, context, session_id, timestamp, metadata FROM knowledge ORDER BY id LIMIT ?",
            (limit,),
        ).fetchall()

        if len(rows) >= limit:
            print(
                f"WARNING: Export limited to {limit} entries. Pass a higher limit to export more.",
                file=sys.stderr,
            )

        with open(out, "w", encoding="utf-8") as f:
            for row in rows:
                entry = dict(row)
                if entry.get("metadata"):
                    try:
                        entry["metadata"] = json.loads(entry["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        _secure_file(out)
        return str(out)
    finally:
        conn.close()


def import_from_jsonl(input_path: Optional[str] = None) -> int:
    """
    Import knowledge entries from a JSONL file.
    Skips entries whose id already exists in the database.

    Args:
        input_path: Path to read from (defaults to ~/.claude/knowledge.jsonl)

    Returns count of newly imported entries.

    Raises:
        ValueError: If the import path is outside allowed directories.
        FileNotFoundError: If the import file does not exist.
    """
    if input_path:
        src = validate_import_path(input_path)
    else:
        src = JSONL_PATH
    if not src.exists():
        return 0

    conn = get_db()
    imported = 0
    try:
        with open(src, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                content = entry.get("content", "")
                tag = entry.get("tag", "FACT").upper()
                context = entry.get("context")
                session_id = entry.get("session_id")
                timestamp = entry.get("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
                metadata = entry.get("metadata")
                metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

                if tag not in VALID_TAGS:
                    tag = "FACT"

                # Skip if this exact content+tag+timestamp already exists
                existing = conn.execute(
                    "SELECT id FROM knowledge WHERE content = ? AND tag = ? AND timestamp = ?",
                    (content, tag, timestamp),
                ).fetchone()

                if existing:
                    continue

                conn.execute(
                    """
                    INSERT INTO knowledge (content, tag, context, session_id, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (content, tag, context, session_id, timestamp, metadata_json),
                )
                imported += 1

        conn.commit()
        return imported
    finally:
        conn.close()


def rebuild_fts():
    """Rebuild the FTS5 index from the knowledge table."""
    conn = get_db()
    try:
        conn.execute("INSERT INTO knowledge_fts(knowledge_fts) VALUES('rebuild')")
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI interface
# ---------------------------------------------------------------------------


def _format_entry(entry: dict, verbose: bool = False) -> str:
    """Format a knowledge entry for display."""
    tag = entry.get("tag", "?")
    content = entry.get("content", "")
    context = entry.get("context", "")
    ts = entry.get("timestamp", "")
    entry_id = entry.get("id", "?")
    score = entry.get("bm25_score")

    # Tag colors using ANSI
    tag_colors = {
        "LEARNED": "\033[32m",       # green
        "DECISION": "\033[34m",      # blue
        "FACT": "\033[33m",          # yellow
        "PATTERN": "\033[35m",       # magenta
        "INVESTIGATION": "\033[36m", # cyan
    }
    reset = "\033[0m"
    color = tag_colors.get(tag, "")

    header = f"  [{color}{tag}{reset}] #{entry_id}"
    if context:
        header += f"  ({context})"
    if score is not None:
        header += f"  score={score:.2f}"

    lines = [header]

    # Wrap content at ~76 chars for readability
    words = content.split()
    line = "    "
    for word in words:
        if len(line) + len(word) + 1 > 78:
            lines.append(line)
            line = "    " + word
        else:
            line += (" " if line.strip() else "") + word
    if line.strip():
        lines.append(line)

    if verbose:
        lines.append(f"    ts: {ts}")
        session = entry.get("session_id", "")
        if session:
            lines.append(f"    session: {session}")
        meta = entry.get("metadata")
        if meta:
            lines.append(f"    metadata: {json.dumps(meta)}")

    return "\n".join(lines)


def cli_main():
    """CLI entry point for claude-knowledge."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="claude-knowledge",
        description="Persistent knowledge database with FTS5 full-text search",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # --- search ---
    p_search = sub.add_parser("search", help="Full-text search with BM25 ranking")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--tag", action="append", help="Filter by tag (repeatable)")
    p_search.add_argument("--context", help="Filter by context")
    p_search.add_argument("--limit", type=int, default=10, help="Max results (default 10)")
    p_search.add_argument("-v", "--verbose", action="store_true", help="Show metadata")
    p_search.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")

    # --- add ---
    p_add = sub.add_parser("add", help="Add a knowledge entry")
    p_add.add_argument("content", help="Knowledge content")
    p_add.add_argument("--tag", required=True, help="Tag: LEARNED, DECISION, FACT, PATTERN, INVESTIGATION")
    p_add.add_argument("--context", help="Context label (e.g. 'vaultmind-architecture')")
    p_add.add_argument("--session-id", help="Session ID")
    p_add.add_argument("--metadata", help="JSON metadata string")

    # --- recent ---
    p_recent = sub.add_parser("recent", help="Show recent entries")
    p_recent.add_argument("--tag", action="append", help="Filter by tag (repeatable)")
    p_recent.add_argument("--context", help="Filter by context")
    p_recent.add_argument("--limit", type=int, default=10, help="Max results (default 10)")
    p_recent.add_argument("-v", "--verbose", action="store_true", help="Show metadata")
    p_recent.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")

    # --- export ---
    p_export = sub.add_parser("export", help="Export all entries to JSONL")
    p_export.add_argument("--output", help="Output file path (default: ~/.claude/knowledge.jsonl)")

    # --- import ---
    p_import = sub.add_parser("import", help="Import entries from JSONL")
    p_import.add_argument("--input", dest="input_path", help="Input file path (default: ~/.claude/knowledge.jsonl)")

    # --- stats ---
    sub.add_parser("stats", help="Show database statistics")

    # --- delete ---
    p_delete = sub.add_parser("delete", help="Delete an entry by ID")
    p_delete.add_argument("entry_id", type=int, help="Entry ID to delete")

    # --- rebuild ---
    sub.add_parser("rebuild", help="Rebuild FTS5 index")

    # --- init ---
    sub.add_parser("init", help="Initialize database (creates if not exists)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # ---- dispatch ----

    if args.command == "init":
        get_db().close()
        print(f"Database initialized at {DB_PATH}")
        return

    if args.command == "add":
        metadata = None
        if args.metadata:
            try:
                metadata = json.loads(args.metadata)
            except json.JSONDecodeError:
                print("Error: --metadata must be valid JSON", file=sys.stderr)
                sys.exit(1)
        row_id = add_knowledge(
            content=args.content,
            tag=args.tag,
            context=args.context,
            session_id=args.session_id,
            metadata=metadata,
        )
        print(f"Added entry #{row_id} [{args.tag.upper()}]")
        return

    if args.command == "search":
        results = search_knowledge(
            query=args.query,
            tags=args.tag,
            context=args.context,
            limit=args.limit,
        )
        if args.as_json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        elif not results:
            print("No results found.")
        else:
            print(f"\n  Found {len(results)} result(s):\n")
            for entry in results:
                print(_format_entry(entry, verbose=args.verbose))
                print()
        return

    if args.command == "recent":
        results = get_recent(
            limit=args.limit,
            tags=args.tag,
            context=args.context,
        )
        if args.as_json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        elif not results:
            print("No entries found.")
        else:
            print(f"\n  Recent {len(results)} entry(ies):\n")
            for entry in results:
                print(_format_entry(entry, verbose=args.verbose))
                print()
        return

    if args.command == "export":
        path = export_to_jsonl(args.output)
        count = count_entries()
        print(f"Exported {count['total']} entries to {path}")
        return

    if args.command == "import":
        count = import_from_jsonl(args.input_path)
        print(f"Imported {count} new entries")
        return

    if args.command == "stats":
        stats = count_entries()
        print(f"\n  Knowledge Database Statistics")
        print(f"  {'=' * 35}")
        print(f"  Database: {DB_PATH}")
        print(f"  Total entries: {stats['total']}")
        if stats["by_tag"]:
            print(f"\n  By tag:")
            for tag, cnt in stats["by_tag"].items():
                print(f"    {tag:15s} {cnt:5d}")
        print()
        return

    if args.command == "delete":
        if delete_knowledge(args.entry_id):
            print(f"Deleted entry #{args.entry_id}")
        else:
            print(f"Entry #{args.entry_id} not found", file=sys.stderr)
            sys.exit(1)
        return

    if args.command == "rebuild":
        rebuild_fts()
        print("FTS5 index rebuilt successfully")
        return


if __name__ == "__main__":
    cli_main()
