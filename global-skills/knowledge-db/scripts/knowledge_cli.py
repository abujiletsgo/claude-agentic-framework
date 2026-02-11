# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Knowledge Database CLI - SQLite FTS5 persistent memory for Claude Code."""

import argparse
import json
import sqlite3
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

DB_DIR = Path.home() / ".claude" / "data" / "knowledge-db"
DB_PATH = DB_DIR / "knowledge.db"


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


def get_db():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _secure_file(DB_PATH)
    return conn


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


def init_db(conn):
    conn.executescript(SCHEMA)
    conn.commit()


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def row_to_dict(row):
    return dict(row)


def cmd_store(args, conn):
    cur = conn.execute(
        "INSERT INTO knowledge_entries (category, title, content, tags, project, confidence, source, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (args.category, args.title, args.content, args.tags or "", args.project, args.confidence, args.source, now_iso(), now_iso()))
    conn.commit()
    print(json.dumps({"status": "stored", "id": cur.lastrowid}, indent=2))


def cmd_search(args, conn):
    sql = "SELECT e.*, rank FROM knowledge_fts f JOIN knowledge_entries e ON f.rowid = e.id WHERE knowledge_fts MATCH ?"
    params = [args.query]
    if args.category:
        sql += " AND e.category = ?"
        params.append(args.category)
    if args.project:
        sql += " AND e.project = ?"
        params.append(args.project)
    if args.tags:
        for tag in args.tags.split(","):
            sql += " AND e.tags LIKE ?"
            params.append(f"%{tag.strip()}%")
    sql += " AND (e.expires_at IS NULL OR e.expires_at > ?)"
    params.append(now_iso())
    sql += " ORDER BY rank LIMIT ?"
    params.append(args.limit or 10)
    rows = conn.execute(sql, params).fetchall()
    print(json.dumps({"count": len(rows), "results": [row_to_dict(r) for r in rows]}, indent=2))


def cmd_recent(args, conn):
    sql = "SELECT * FROM knowledge_entries WHERE 1=1"
    params = []
    if args.category:
        sql += " AND category = ?"
        params.append(args.category)
    if args.project:
        sql += " AND project = ?"
        params.append(args.project)
    sql += " AND (expires_at IS NULL OR expires_at > ?)"
    params.append(now_iso())
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(args.limit or 10)
    rows = conn.execute(sql, params).fetchall()
    print(json.dumps({"count": len(rows), "results": [row_to_dict(r) for r in rows]}, indent=2))


def cmd_get(args, conn):
    row = conn.execute("SELECT * FROM knowledge_entries WHERE id = ?", (args.id,)).fetchone()
    if row:
        print(json.dumps(row_to_dict(row), indent=2))
    else:
        print(json.dumps({"error": f"Entry {args.id} not found"}), file=sys.stderr)
        sys.exit(1)


def cmd_update(args, conn):
    ups, params = [], []
    if args.content:
        ups.append("content = ?")
        params.append(args.content)
    if args.confidence is not None:
        ups.append("confidence = ?")
        params.append(args.confidence)
    if args.tags is not None:
        ups.append("tags = ?")
        params.append(args.tags)
    if args.title:
        ups.append("title = ?")
        params.append(args.title)
    if not ups:
        print(json.dumps({"error": "No fields"}), file=sys.stderr)
        sys.exit(1)
    ups.append("updated_at = ?")
    params.append(now_iso())
    params.append(args.id)
    conn.execute(f"UPDATE knowledge_entries SET {', '.join(ups)} WHERE id = ?", params)
    conn.commit()
    print(json.dumps({"status": "updated", "id": args.id}, indent=2))


def cmd_expire(args, conn):
    conn.execute("UPDATE knowledge_entries SET expires_at = ? WHERE id = ?", (now_iso(), args.id))
    conn.commit()
    print(json.dumps({"status": "expired", "id": args.id}, indent=2))


def cmd_purge(args, conn):
    cur = conn.execute("DELETE FROM knowledge_entries WHERE expires_at IS NOT NULL AND expires_at < ?", (now_iso(),))
    conn.commit()
    print(json.dumps({"status": "purged", "deleted_count": cur.rowcount}, indent=2))


def cmd_export(args, conn):
    limit = getattr(args, "limit", None) or 10000
    rows = conn.execute("SELECT * FROM knowledge_entries ORDER BY id LIMIT ?", (limit,)).fetchall()
    rels = conn.execute("SELECT * FROM knowledge_relations ORDER BY id").fetchall()
    if len(rows) >= limit:
        print(f"WARNING: Output limited to {limit} entries. Use --limit to increase.", file=sys.stderr)
    print(json.dumps({"version": 1, "exported_at": now_iso(), "entries": [row_to_dict(r) for r in rows], "relations": [row_to_dict(r) for r in rels]}, indent=2))


def cmd_import_json(args, conn):
    # Validate import path before opening
    try:
        safe_path = validate_import_path(args.file)
    except (ValueError, FileNotFoundError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

    with open(safe_path, "r") as f:
        data = json.load(f)
    count = 0
    for e in data.get("entries", []):
        try:
            conn.execute(
                "INSERT OR IGNORE INTO knowledge_entries (category,title,content,tags,project,confidence,source,created_at,updated_at,expires_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (e["category"], e["title"], e["content"], e.get("tags", ""), e.get("project"), e.get("confidence", 0.5), e.get("source", "import"), e.get("created_at", now_iso()), e.get("updated_at", now_iso()), e.get("expires_at")))
            count += 1
        except Exception as ex:
            print(f"Skip: {ex}", file=sys.stderr)
    conn.commit()
    print(json.dumps({"status": "imported", "count": count}, indent=2))


def cmd_stats(args, conn):
    total = conn.execute("SELECT COUNT(*) FROM knowledge_entries").fetchone()[0]
    by_cat = conn.execute("SELECT category, COUNT(*) as count FROM knowledge_entries GROUP BY category").fetchall()
    by_proj = conn.execute("SELECT COALESCE(project, '(global)') as project, COUNT(*) as count FROM knowledge_entries GROUP BY project").fetchall()
    expired = conn.execute("SELECT COUNT(*) FROM knowledge_entries WHERE expires_at IS NOT NULL AND expires_at < ?", (now_iso(),)).fetchone()[0]
    rels = conn.execute("SELECT COUNT(*) FROM knowledge_relations").fetchone()[0]
    print(json.dumps({"total": total, "expired": expired, "relations": rels,
        "by_category": {r["category"]: r["count"] for r in by_cat},
        "by_project": {r["project"]: r["count"] for r in by_proj},
        "db_size": os.path.getsize(str(DB_PATH)) if DB_PATH.exists() else 0}, indent=2))


def cmd_relate(args, conn):
    conn.execute("INSERT OR IGNORE INTO knowledge_relations (from_id, to_id, relation_type, created_at) VALUES (?,?,?,?)", (args.from_id, args.to_id, args.relation_type, now_iso()))
    conn.commit()
    print(json.dumps({"status": "related", "from": args.from_id, "to": args.to_id, "type": args.relation_type}, indent=2))


def cmd_related(args, conn):
    rows = conn.execute("SELECT e.*, r.relation_type, 'out' as dir FROM knowledge_relations r JOIN knowledge_entries e ON r.to_id = e.id WHERE r.from_id = ? UNION ALL SELECT e.*, r.relation_type, 'in' as dir FROM knowledge_relations r JOIN knowledge_entries e ON r.from_id = e.id WHERE r.to_id = ?", (args.id, args.id)).fetchall()
    print(json.dumps({"entry_id": args.id, "count": len(rows), "related": [row_to_dict(r) for r in rows]}, indent=2))


def cmd_init(args, conn):
    print(json.dumps({"status": "initialized", "db_path": str(DB_PATH)}, indent=2))


def main():
    p = argparse.ArgumentParser(description="Knowledge DB CLI")
    sp = p.add_subparsers(dest="command", required=True)

    s = sp.add_parser("store")
    s.add_argument("--category", required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--content", required=True)
    s.add_argument("--tags", default="")
    s.add_argument("--project", default=None)
    s.add_argument("--confidence", type=float, default=0.5)
    s.add_argument("--source", default="user")

    s = sp.add_parser("search")
    s.add_argument("query")
    s.add_argument("--category", default=None)
    s.add_argument("--project", default=None)
    s.add_argument("--tags", default=None)
    s.add_argument("--limit", type=int, default=10)

    s = sp.add_parser("recent")
    s.add_argument("--category", default=None)
    s.add_argument("--project", default=None)
    s.add_argument("--limit", type=int, default=10)

    s = sp.add_parser("get")
    s.add_argument("id", type=int)

    s = sp.add_parser("update")
    s.add_argument("id", type=int)
    s.add_argument("--content", default=None)
    s.add_argument("--confidence", type=float, default=None)
    s.add_argument("--tags", default=None)
    s.add_argument("--title", default=None)

    s = sp.add_parser("expire")
    s.add_argument("id", type=int)

    sp.add_parser("purge-expired")

    s = sp.add_parser("export")
    s.add_argument("--limit", type=int, default=10000, help="Max entries to export (default: 10000)")

    s = sp.add_parser("import-json")
    s.add_argument("file")

    sp.add_parser("stats")

    s = sp.add_parser("relate")
    s.add_argument("from_id", type=int)
    s.add_argument("to_id", type=int)
    s.add_argument("relation_type")

    s = sp.add_parser("related")
    s.add_argument("id", type=int)

    sp.add_parser("init")

    args = p.parse_args()
    conn = get_db()
    init_db(conn)
    cmds = {
        "store": cmd_store, "search": cmd_search, "recent": cmd_recent,
        "get": cmd_get, "update": cmd_update, "expire": cmd_expire,
        "purge-expired": cmd_purge, "export": cmd_export,
        "import-json": cmd_import_json, "stats": cmd_stats,
        "relate": cmd_relate, "related": cmd_related, "init": cmd_init,
    }
    try:
        cmds[args.command](args, conn)
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
