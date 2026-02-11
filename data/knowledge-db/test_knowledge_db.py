#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Test suite for the Knowledge Database with FTS5.

Tests:
1. Database initialization and schema creation
2. Adding 10 sample knowledge entries
3. Full-text search with BM25 ranking
4. Tag filtering
5. Context filtering
6. Recent entries retrieval
7. JSONL export/import sync
8. Delete functionality
9. Statistics
10. FTS5 rebuild
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add the knowledge module to path
KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "global-hooks" / "framework" / "knowledge"
sys.path.insert(0, str(KNOWLEDGE_DIR))

import knowledge_db as kdb

# Use a temporary database for testing
TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="knowledge_test_"))
TEST_DB_PATH = TEST_DB_DIR / "knowledge_test.db"
TEST_JSONL_PATH = TEST_DB_DIR / "knowledge_test.jsonl"

# Monkey-patch paths for testing
_orig_db_path = kdb.DB_PATH
_orig_jsonl_path = kdb.JSONL_PATH
_orig_db_dir = kdb.DB_DIR


def setup():
    """Redirect database to temp directory."""
    kdb.DB_PATH = TEST_DB_PATH
    kdb.JSONL_PATH = TEST_JSONL_PATH
    kdb.DB_DIR = TEST_DB_DIR


def teardown():
    """Restore original paths and clean up."""
    kdb.DB_PATH = _orig_db_path
    kdb.JSONL_PATH = _orig_jsonl_path
    kdb.DB_DIR = _orig_db_dir
    # Clean up temp files
    for f in TEST_DB_DIR.glob("*"):
        f.unlink()
    TEST_DB_DIR.rmdir()


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_ENTRIES = [
    {
        "content": "Always use Vault.process() for atomic file writes in Obsidian plugins to prevent data corruption",
        "tag": "LEARNED",
        "context": "vaultmind-architecture",
        "session_id": "session-001",
        "metadata": {"source": "debugging", "severity": "high"},
    },
    {
        "content": "Store API keys in window.localStorage, never in data.json which syncs to Google Drive",
        "tag": "DECISION",
        "context": "vaultmind-security",
        "session_id": "session-001",
        "metadata": {"rationale": "security-audit"},
    },
    {
        "content": "Plugin source is at /Users/tomkwon/Library/CloudStorage/GoogleDrive/My Drive/Obsidian/.obsidian/plugins/vaultmind/src/",
        "tag": "FACT",
        "context": "vaultmind-architecture",
        "session_id": "session-002",
    },
    {
        "content": "FTS5 with porter stemmer and unicode61 tokenizer provides the best balance of accuracy and performance for mixed English/Korean content",
        "tag": "LEARNED",
        "context": "knowledge-system",
        "session_id": "session-003",
    },
    {
        "content": "Use dual-provider LLM architecture: Anthropic SDK for Claude + OpenAI-compatible HTTP for Ollama/LM Studio",
        "tag": "DECISION",
        "context": "vaultmind-architecture",
        "session_id": "session-002",
        "metadata": {"components": ["LLMService", "GeminiService"]},
    },
    {
        "content": "Hierarchical tags with / separator, English only, full paths required in Obsidian frontmatter",
        "tag": "FACT",
        "context": "vaultmind-architecture",
        "session_id": "session-002",
    },
    {
        "content": "Hook scripts should always exit 0 to never block the pipeline, handle all errors gracefully",
        "tag": "PATTERN",
        "context": "claude-agentic-framework",
        "session_id": "session-003",
    },
    {
        "content": "SQLite WAL mode significantly improves concurrent read performance for knowledge queries",
        "tag": "LEARNED",
        "context": "knowledge-system",
        "session_id": "session-003",
        "metadata": {"benchmark": "3x faster reads"},
    },
    {
        "content": "Should we add vector embeddings alongside FTS5 for semantic search? Current BM25 may miss conceptual matches",
        "tag": "INVESTIGATION",
        "context": "knowledge-system",
        "session_id": "session-003",
    },
    {
        "content": "Agent subprocesses that exceed context window should use Ralph Loops (stateless resampling) for iterative refinement",
        "tag": "PATTERN",
        "context": "claude-agentic-framework",
        "session_id": "session-004",
        "metadata": {"related": "rlm-root agent"},
    },
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

passed = 0
failed = 0
total = 0


def test(name: str):
    """Decorator for test functions."""
    def decorator(func):
        def wrapper():
            global passed, failed, total
            total += 1
            try:
                func()
                passed += 1
                print(f"  \033[32mPASS\033[0m  {name}")
            except Exception as e:
                failed += 1
                print(f"  \033[31mFAIL\033[0m  {name}: {e}")
        return wrapper
    return decorator


@test("Database initialization and schema creation")
def test_init():
    conn = kdb.get_db()
    # Check tables exist
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = [t["name"] for t in tables]
    assert "knowledge" in table_names, f"knowledge table missing. Tables: {table_names}"
    # FTS5 tables show up differently
    vtables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'knowledge_fts%'"
    ).fetchall()
    assert len(vtables) > 0, "knowledge_fts virtual table missing"
    conn.close()


@test("Add 10 sample knowledge entries")
def test_add_entries():
    ids = []
    for entry in SAMPLE_ENTRIES:
        row_id = kdb.add_knowledge(**entry)
        assert row_id is not None, "add_knowledge returned None"
        assert isinstance(row_id, int), f"Expected int id, got {type(row_id)}"
        ids.append(row_id)
    assert len(ids) == 10, f"Expected 10 entries, got {len(ids)}"
    assert len(set(ids)) == 10, "IDs are not unique"


@test("Full-text search with BM25 ranking")
def test_fts_search():
    results = kdb.search_knowledge("atomic file writes Obsidian")
    assert len(results) > 0, "No results for 'atomic file writes Obsidian'"
    # The most relevant result should mention Vault.process()
    top = results[0]
    assert "atomic" in top["content"].lower() or "vault" in top["content"].lower(), \
        f"Top result not relevant: {top['content'][:80]}"
    # Check BM25 score is present
    assert "bm25_score" in top, "BM25 score missing from results"


@test("Search with tag filtering")
def test_tag_filter():
    results = kdb.search_knowledge("architecture", tags=["DECISION"])
    for r in results:
        assert r["tag"] == "DECISION", f"Expected DECISION tag, got {r['tag']}"

    results_learned = kdb.search_knowledge("performance", tags=["LEARNED"])
    for r in results_learned:
        assert r["tag"] == "LEARNED", f"Expected LEARNED tag, got {r['tag']}"


@test("Search with context filtering")
def test_context_filter():
    results = kdb.search_knowledge("plugin", context="vaultmind-architecture")
    for r in results:
        assert r["context"] == "vaultmind-architecture", \
            f"Expected vaultmind-architecture context, got {r['context']}"


@test("Get recent entries")
def test_recent():
    recent = kdb.get_recent(limit=5)
    assert len(recent) == 5, f"Expected 5 recent entries, got {len(recent)}"
    # Should be ordered by timestamp descending
    timestamps = [r["timestamp"] for r in recent]
    assert timestamps == sorted(timestamps, reverse=True), "Recent entries not sorted by timestamp desc"


@test("Get recent with tag filter")
def test_recent_tag_filter():
    recent = kdb.get_recent(limit=10, tags=["PATTERN"])
    assert len(recent) == 2, f"Expected 2 PATTERN entries, got {len(recent)}"
    for r in recent:
        assert r["tag"] == "PATTERN", f"Expected PATTERN tag, got {r['tag']}"


@test("JSONL log sync - entries written during add")
def test_jsonl_sync():
    assert TEST_JSONL_PATH.exists(), "JSONL file was not created"
    lines = TEST_JSONL_PATH.read_text().strip().split("\n")
    assert len(lines) == 10, f"Expected 10 JSONL lines, got {len(lines)}"
    # Verify each line is valid JSON
    for i, line in enumerate(lines):
        entry = json.loads(line)
        assert "content" in entry, f"Line {i} missing 'content' key"
        assert "tag" in entry, f"Line {i} missing 'tag' key"
        assert "timestamp" in entry, f"Line {i} missing 'timestamp' key"


@test("JSONL export/import roundtrip")
def test_export_import():
    export_path = TEST_DB_DIR / "export_test.jsonl"
    kdb.export_to_jsonl(str(export_path))
    assert export_path.exists(), "Export file not created"

    lines = export_path.read_text().strip().split("\n")
    assert len(lines) == 10, f"Expected 10 exported lines, got {len(lines)}"

    # Create a fresh database for import test
    import_db_path = TEST_DB_DIR / "import_test.db"
    orig_path = kdb.DB_PATH
    kdb.DB_PATH = import_db_path
    try:
        count = kdb.import_from_jsonl(str(export_path))
        assert count == 10, f"Expected 10 imported entries, got {count}"

        # Verify import contents
        stats = kdb.count_entries()
        assert stats["total"] == 10, f"Expected 10 total after import, got {stats['total']}"

        # Import again - should skip duplicates
        count2 = kdb.import_from_jsonl(str(export_path))
        assert count2 == 0, f"Expected 0 duplicates imported, got {count2}"
    finally:
        kdb.DB_PATH = orig_path
        if import_db_path.exists():
            import_db_path.unlink()
        # Clean up WAL/SHM files
        for suffix in ("-wal", "-shm"):
            p = Path(str(import_db_path) + suffix)
            if p.exists():
                p.unlink()


@test("Delete entry")
def test_delete():
    # Get the first entry
    recent = kdb.get_recent(limit=1, tags=["INVESTIGATION"])
    assert len(recent) == 1, "No INVESTIGATION entry to delete"
    entry_id = recent[0]["id"]

    result = kdb.delete_knowledge(entry_id)
    assert result is True, "Delete returned False"

    # Verify it is gone
    entry = kdb.get_by_id(entry_id)
    assert entry is None, "Entry still exists after delete"

    # Verify count decreased
    stats = kdb.count_entries()
    assert stats["total"] == 9, f"Expected 9 entries after delete, got {stats['total']}"


@test("Statistics")
def test_stats():
    stats = kdb.count_entries()
    assert stats["total"] == 9, f"Expected 9 total (after delete), got {stats['total']}"
    assert "by_tag" in stats, "Missing by_tag breakdown"
    assert stats["by_tag"].get("LEARNED", 0) == 3, \
        f"Expected 3 LEARNED, got {stats['by_tag'].get('LEARNED', 0)}"
    assert stats["by_tag"].get("DECISION", 0) == 2, \
        f"Expected 2 DECISION, got {stats['by_tag'].get('DECISION', 0)}"


@test("FTS5 rebuild")
def test_rebuild():
    kdb.rebuild_fts()
    # After rebuild, search should still work
    results = kdb.search_knowledge("SQLite WAL mode")
    assert len(results) > 0, "No results after FTS rebuild"


@test("Invalid tag rejection")
def test_invalid_tag():
    try:
        kdb.add_knowledge("test", tag="INVALID_TAG")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid tag" in str(e), f"Wrong error message: {e}"


@test("BM25 ranking quality - most relevant first")
def test_bm25_ranking():
    results = kdb.search_knowledge("API keys localStorage security")
    assert len(results) > 0, "No results for security query"
    # The entry about localStorage API keys should rank highly
    top_contents = [r["content"][:50] for r in results[:3]]
    found = any("localStorage" in c or "API key" in c for c in top_contents)
    assert found, f"Expected localStorage/API key entry in top 3. Got: {top_contents}"


@test("Search with porter stemming (writes -> write)")
def test_stemming():
    # Porter stemmer should match "writes" to "write"
    results = kdb.search_knowledge("writing files atomically")
    # Should find the Vault.process() entry because "writes" stems to "write"
    # and "files" matches "file"
    assert len(results) > 0, "Stemming did not match 'writing' to 'writes'"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main():
    print(f"\n  Knowledge Database Test Suite")
    print(f"  {'=' * 40}")
    print(f"  Test DB: {TEST_DB_PATH}")
    print(f"  Test JSONL: {TEST_JSONL_PATH}\n")

    setup()

    try:
        test_init()
        test_add_entries()
        test_fts_search()
        test_tag_filter()
        test_context_filter()
        test_recent()
        test_recent_tag_filter()
        test_jsonl_sync()
        test_export_import()
        test_delete()
        test_stats()
        test_rebuild()
        test_invalid_tag()
        test_bm25_ranking()
        test_stemming()

        print(f"\n  {'=' * 40}")
        print(f"  Results: {passed} passed, {failed} failed, {total} total")

        if failed > 0:
            print(f"  \033[31mSOME TESTS FAILED\033[0m\n")
            sys.exit(1)
        else:
            print(f"  \033[32mALL TESTS PASSED\033[0m\n")
            sys.exit(0)
    finally:
        teardown()


if __name__ == "__main__":
    main()
