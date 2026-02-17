#!/usr/bin/env python3
"""
Comprehensive tests for the Knowledge Pipeline.

Covers every failure point across all three stages:
  - inject_relevant.py (SessionStart)
  - extract_learnings.py (PostToolUse)
  - store_learnings.py (Stop)

Run: python3 test_knowledge_pipeline_full.py
"""

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Add the knowledge directory to the path so we can import the modules
# ---------------------------------------------------------------------------
KNOWLEDGE_DIR = Path(__file__).parent
sys.path.insert(0, str(KNOWLEDGE_DIR))


# ---------------------------------------------------------------------------
# Helper: create a minimal knowledge DB with FTS5
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
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    title, content, tags,
    content=knowledge_entries, content_rowid=id,
    tokenize='porter unicode61'
);
CREATE TRIGGER IF NOT EXISTS kn_ai AFTER INSERT ON knowledge_entries BEGIN
    INSERT INTO knowledge_fts(rowid, title, content, tags)
    VALUES (new.id, new.title, new.content, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS kn_ad AFTER DELETE ON knowledge_entries BEGIN
    INSERT INTO knowledge_fts(knowledge_fts, rowid, title, content, tags)
    VALUES ('delete', old.id, old.title, old.content, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS kn_au AFTER UPDATE ON knowledge_entries BEGIN
    INSERT INTO knowledge_fts(knowledge_fts, rowid, title, content, tags)
    VALUES ('delete', old.id, old.title, old.content, old.tags);
    INSERT INTO knowledge_fts(rowid, title, content, tags)
    VALUES (new.id, new.title, new.content, new.tags);
END;
CREATE TABLE IF NOT EXISTS knowledge_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id INTEGER NOT NULL REFERENCES knowledge_entries(id) ON DELETE CASCADE,
    to_id INTEGER NOT NULL REFERENCES knowledge_entries(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(from_id, to_id, relation_type)
);
"""


def make_db(path: Path) -> sqlite3.Connection:
    """Create a fresh knowledge DB at path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def insert_entry(conn, category, title, content, tags="", confidence=0.8,
                 created_at=None, expires_at=None):
    """Insert a single knowledge entry for testing."""
    if created_at is None:
        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT INTO knowledge_entries "
        "(category, title, content, tags, confidence, source, created_at, updated_at, expires_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (category, title, content, tags, confidence, "test", created_at, ts, expires_at),
    )
    conn.commit()


# ===========================================================================
# INJECT_RELEVANT.PY tests
# ===========================================================================

import inject_relevant as ir


class TestInjectCWDContext(unittest.TestCase):
    """Tests for get_cwd_context()."""

    def test_returns_list(self):
        terms = ir.get_cwd_context()
        self.assertIsInstance(terms, list)

    def test_limits_to_15_terms(self):
        terms = ir.get_cwd_context()
        self.assertLessEqual(len(terms), 15)

    def test_no_common_stopwords(self):
        terms = ir.get_cwd_context()
        stopwords = {"users", "home", "documents", "src", "lib"}
        for t in terms:
            self.assertNotIn(t, stopwords)

    def test_short_words_excluded(self):
        # All terms should be len > 2
        terms = ir.get_cwd_context()
        for t in terms:
            self.assertGreater(len(t), 2, f"Short word found: {t!r}")


class TestInjectSearchKnowledge(unittest.TestCase):
    """Tests for search_knowledge()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "knowledge.db"
        self.conn = make_db(self.db_path)
        self.config = {
            "include_categories": ["LEARNED", "PATTERN", "INVESTIGATION"],
            "max_injections": 5,
            "lookback_days": 30,
        }

    def tearDown(self):
        self.conn.close()

    def _search(self, terms):
        # Patch DB_PATH and use our conn
        with patch.object(ir, "DB_PATH", self.db_path):
            return ir.search_knowledge(self.conn, terms, self.config)

    def test_empty_terms_returns_empty(self):
        result = ir.search_knowledge(self.conn, [], self.config)
        self.assertEqual(result, [])

    def test_no_matching_entries_returns_empty(self):
        result = self._search(["xyznonexistentterm999"])
        self.assertEqual(result, [])

    def test_matching_entry_is_returned(self):
        insert_entry(self.conn, "LEARNED", "Test hook fix",
                     "Fixed the hook configuration to use uv run")
        result = self._search(["hook", "configuration"])
        self.assertGreater(len(result), 0)

    def test_category_filter_works(self):
        insert_entry(self.conn, "LEARNED", "A learned thing", "content about hooks")
        insert_entry(self.conn, "DECISION", "A decision", "content about hooks also")
        config = {**self.config, "include_categories": ["DECISION"]}
        result = ir.search_knowledge(self.conn, ["hooks"], config)
        for r in result:
            self.assertEqual(r["category"], "DECISION")

    def test_expired_entries_excluded(self):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        insert_entry(self.conn, "LEARNED", "Expired entry",
                     "this entry is expired hook content", expires_at=past)
        result = self._search(["expired", "hook"])
        # Should not include the expired entry
        for r in result:
            self.assertNotEqual(r["title"], "Expired entry")

    def test_old_entries_excluded_by_lookback(self):
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
        insert_entry(self.conn, "LEARNED", "Old entry",
                     "old hook pattern content", created_at=old_date)
        result = self._search(["hook", "pattern"])
        for r in result:
            self.assertNotEqual(r["title"], "Old entry")

    def test_max_results_respected(self):
        for i in range(10):
            insert_entry(self.conn, "LEARNED", f"Hook entry {i}",
                         f"hook configuration pattern {i}")
        config = {**self.config, "max_injections": 3}
        result = ir.search_knowledge(self.conn, ["hook", "configuration"], config)
        # Returns up to max_injections * 2 raw, rank_and_filter trims further
        self.assertLessEqual(len(result), 6)


class TestInjectRankAndFilter(unittest.TestCase):
    """Tests for rank_and_filter()."""

    def _make_entry(self, rank=-1.0, confidence=0.8, age_days=0):
        ts = (datetime.now(timezone.utc) - timedelta(days=age_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        return {"rank": rank, "confidence": confidence, "created_at": ts,
                "category": "LEARNED", "content": "x", "tags": ""}

    def test_empty_returns_empty(self):
        self.assertEqual(ir.rank_and_filter([], {"max_injections": 5, "recency_boost": 0.2}), [])

    def test_respects_max_injections(self):
        entries = [self._make_entry() for _ in range(10)]
        result = ir.rank_and_filter(entries, {"max_injections": 3, "recency_boost": 0.2})
        self.assertEqual(len(result), 3)

    def test_newer_entries_rank_higher(self):
        old = self._make_entry(rank=-1.0, age_days=29)
        new = self._make_entry(rank=-1.0, age_days=0)
        result = ir.rank_and_filter([old, new], {"max_injections": 2, "recency_boost": 0.5})
        # New entry should come first
        self.assertGreater(result[0]["_score"], result[1]["_score"])
        self.assertEqual(result[0]["created_at"], new["created_at"])

    def test_higher_confidence_adds_score(self):
        low_conf = self._make_entry(rank=-1.0, confidence=0.1)
        high_conf = self._make_entry(rank=-1.0, confidence=0.9)
        result = ir.rank_and_filter([low_conf, high_conf],
                                    {"max_injections": 2, "recency_boost": 0.0})
        self.assertGreater(result[0]["_score"], result[1]["_score"])
        self.assertEqual(result[0]["confidence"], 0.9)

    def test_bad_created_at_doesnt_crash(self):
        bad = {"rank": -1.0, "confidence": 0.5, "created_at": "NOT_A_DATE",
               "category": "LEARNED", "content": "x", "tags": ""}
        result = ir.rank_and_filter([bad], {"max_injections": 5, "recency_boost": 0.2})
        self.assertEqual(len(result), 1)


class TestInjectFormatInjection(unittest.TestCase):
    """Tests for format_injection()."""

    def _entry(self, category="LEARNED", content="Test content", confidence=0.8, tags=""):
        return {"category": category, "content": content,
                "confidence": confidence, "tags": tags}

    def test_empty_list_returns_empty_string(self):
        self.assertEqual(ir.format_injection([]), "")

    def test_output_contains_additionalcontext_header(self):
        text = ir.format_injection([self._entry()])
        self.assertIn("## Relevant Knowledge", text)

    def test_strips_context_suffix(self):
        entry = self._entry(content="Main content\n\nContext: some context here")
        text = ir.format_injection([entry])
        self.assertIn("Main content", text)
        self.assertNotIn("Context: some context here", text)

    def test_high_confidence_label(self):
        text = ir.format_injection([self._entry(confidence=0.9)])
        self.assertIn("high confidence", text)

    def test_medium_confidence_label(self):
        text = ir.format_injection([self._entry(confidence=0.5)])
        self.assertIn("medium confidence", text)

    def test_low_confidence_label(self):
        text = ir.format_injection([self._entry(confidence=0.2)])
        self.assertIn("low confidence", text)

    def test_tags_appear_when_present(self):
        text = ir.format_injection([self._entry(tags="hook,python")])
        self.assertIn("hook,python", text)

    def test_no_tags_skips_tag_line(self):
        text = ir.format_injection([self._entry(tags="")])
        self.assertNotIn("_Tags:", text)

    def test_count_in_footer(self):
        entries = [self._entry() for _ in range(3)]
        text = ir.format_injection(entries)
        self.assertIn("3 relevant entries found", text)


class TestInjectMainOutputFormat(unittest.TestCase):
    """Test the main() output JSON format (the critical bug we fixed)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "knowledge.db"
        self.conn = make_db(self.db_path)
        insert_entry(self.conn, "LEARNED", "Hook pattern", "hook configuration pattern")
        self.conn.close()

    def test_output_uses_additionalContext_not_contextInjection(self):
        """The critical field name bug: must be additionalContext, not contextInjection."""
        import io
        from unittest.mock import patch
        import inject_relevant as ir_mod

        stdin_data = json.dumps({"session_id": "test"})

        with patch.object(ir_mod, "DB_PATH", self.db_path), \
             patch.object(ir_mod, "get_cwd_context", return_value=["hook", "configuration"]), \
             patch.object(ir_mod, "get_recent_files_context", return_value=[]):

            conn = make_db(self.db_path)
            with patch.object(ir_mod, "get_db", return_value=conn):
                import io as _io
                captured = _io.StringIO()
                with patch("sys.stdin", _io.StringIO(stdin_data)), \
                     patch("sys.stdout", captured):
                    try:
                        ir_mod.main()
                    except SystemExit:
                        pass

        output = captured.getvalue().strip()
        if output:
            parsed = json.loads(output)
            # Must have hookSpecificOutput.additionalContext — not contextInjection
            self.assertIn("hookSpecificOutput", parsed)
            hook_out = parsed["hookSpecificOutput"]
            self.assertIn("additionalContext", hook_out,
                          "Must use 'additionalContext', not 'contextInjection'")
            self.assertNotIn("contextInjection", hook_out)

    def test_invalid_json_exits_cleanly(self):
        """Invalid stdin JSON should exit 0, never crash."""
        import io
        with patch("sys.stdin", io.StringIO("NOT JSON")):
            with self.assertRaises(SystemExit) as ctx:
                ir.main()
            self.assertEqual(ctx.exception.code, 0)

    def test_missing_db_exits_cleanly(self):
        """If DB doesn't exist, exit 0 silently."""
        import io
        with patch.object(ir, "DB_PATH", Path("/nonexistent/path/knowledge.db")), \
             patch("sys.stdin", io.StringIO(json.dumps({}))):
            with self.assertRaises(SystemExit) as ctx:
                ir.main()
            self.assertEqual(ctx.exception.code, 0)

    def test_disabled_config_exits_cleanly(self):
        """If evolve.enabled=False, exit 0."""
        import io
        with patch.object(ir, "load_config", return_value={"enabled": False}), \
             patch("sys.stdin", io.StringIO(json.dumps({}))):
            with self.assertRaises(SystemExit) as ctx:
                ir.main()
            self.assertEqual(ctx.exception.code, 0)


# ===========================================================================
# EXTRACT_LEARNINGS.PY tests
# ===========================================================================

import extract_learnings as el


class TestExtractFromToolOutput(unittest.TestCase):
    """Tests for extract_from_tool_output()."""

    def test_skip_read_tool(self):
        result = el.extract_from_tool_output("Read", {}, "some output", "sess")
        self.assertEqual(result, [])

    def test_skip_glob_tool(self):
        result = el.extract_from_tool_output("Glob", {}, "some output", "sess")
        self.assertEqual(result, [])

    def test_skip_websearch_tool(self):
        result = el.extract_from_tool_output("WebSearch", {}, "some output", "sess")
        self.assertEqual(result, [])

    def test_bash_error_creates_investigation(self):
        result = el.extract_from_tool_output(
            "Bash",
            {"command": "python test.py"},
            "Traceback (most recent call last):\n  File ...\nError: something failed",
            "sess"
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tag"], "INVESTIGATION")

    def test_bash_error_truncates_long_output(self):
        long_output = "Error: " + "x" * 3000
        result = el.extract_from_tool_output(
            "Bash", {"command": "cmd"}, long_output, "sess"
        )
        # Output > 2000 chars should be skipped
        self.assertEqual(result, [])

    def test_bash_error_truncates_long_command(self):
        long_cmd = "python " + "arg " * 50  # 200+ chars
        result = el.extract_from_tool_output(
            "Bash",
            {"command": long_cmd},
            "Error: failed",
            "sess"
        )
        if result:
            # Command should be truncated to 100 chars in content
            self.assertLessEqual(len(result[0]["content"].split("`")[1]), 100)

    def test_bash_no_error_creates_no_entry(self):
        result = el.extract_from_tool_output(
            "Bash",
            {"command": "ls -la"},
            "total 8\ndrwxr-xr-x 2 user group 4096 Jan 1 12:00 .",
            "sess"
        )
        self.assertEqual(result, [])

    def test_write_config_file_creates_decision(self):
        result = el.extract_from_tool_output(
            "Write",
            {"file_path": "/project/config/settings.yaml"},
            "",
            "sess"
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tag"], "DECISION")

    def test_write_architecture_file_creates_decision(self):
        result = el.extract_from_tool_output(
            "Write",
            {"file_path": "/project/architecture/overview.md"},
            "",
            "sess"
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tag"], "DECISION")

    def test_write_pyproject_creates_decision(self):
        result = el.extract_from_tool_output(
            "Write",
            {"file_path": "/project/pyproject.toml"},
            "",
            "sess"
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tag"], "DECISION")

    def test_edit_regular_file_creates_no_entry(self):
        result = el.extract_from_tool_output(
            "Edit",
            {"file_path": "/project/src/main.py"},
            "",
            "sess"
        )
        self.assertEqual(result, [])

    def test_write_dockerfile_creates_decision(self):
        result = el.extract_from_tool_output(
            "Write",
            {"file_path": "/project/Dockerfile"},
            "",
            "sess"
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tag"], "DECISION")

    def test_missing_tool_input_no_crash(self):
        result = el.extract_from_tool_output("Bash", None, "Error: crash", "sess")
        # Should not crash; tool_input=None means command="" which is still valid
        self.assertIsInstance(result, list)

    def test_failed_keyword_match(self):
        # "failed" in output should trigger INVESTIGATION
        result = el.extract_from_tool_output(
            "Bash",
            {"command": "pytest tests/"},
            "3 failed, 1 passed",
            "sess"
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tag"], "INVESTIGATION")

    def test_exception_keyword_match(self):
        result = el.extract_from_tool_output(
            "Bash",
            {"command": "python app.py"},
            "Exception: ValueError: bad value",
            "sess"
        )
        self.assertEqual(len(result), 1)

    def test_error_colon_keyword_match(self):
        result = el.extract_from_tool_output(
            "Bash",
            {"command": "make build"},
            "error: undefined reference to main",
            "sess"
        )
        self.assertEqual(len(result), 1)


class TestExtractContextInference(unittest.TestCase):
    """Tests for _infer_context()."""

    def test_vaultmind_context(self):
        self.assertEqual(el._infer_context("vaultmind/plugin"), "vaultmind")

    def test_hook_context(self):
        self.assertEqual(el._infer_context("global-hooks/framework"), "hooks")

    def test_agent_context(self):
        self.assertEqual(el._infer_context("global-agents/orchestrator"), "agents")

    def test_test_context(self):
        self.assertEqual(el._infer_context("test_something.py"), "testing")

    def test_docker_context(self):
        self.assertEqual(el._infer_context("Dockerfile"), "infrastructure")

    def test_deploy_context(self):
        self.assertEqual(el._infer_context("deploy.sh"), "deployment")

    def test_unknown_returns_general(self):
        self.assertEqual(el._infer_context("completely_unknown_thing"), "general")

    def test_claude_agentic_context(self):
        # "claude-agentic" pattern matches before "hook" (dict order), so returns "claude-agentic-framework"
        self.assertEqual(el._infer_context("claude-agentic-framework/hook"), "claude-agentic-framework")


class TestExtractMainHookBehavior(unittest.TestCase):
    """Tests for extract_learnings.main() — hook protocol behavior."""

    def _run_main(self, stdin_data: dict):
        """Run main() and capture exit code."""
        import io
        with patch("sys.stdin", io.StringIO(json.dumps(stdin_data))):
            with self.assertRaises(SystemExit) as ctx:
                el.main()
            return ctx.exception.code

    def test_always_exits_zero_on_valid_input(self):
        code = self._run_main({
            "tool_name": "Read",
            "tool_input": {},
            "tool_output": "some content",
            "session_id": "test"
        })
        self.assertEqual(code, 0)

    def test_always_exits_zero_on_invalid_json(self):
        import io
        with patch("sys.stdin", io.StringIO("INVALID JSON")):
            with self.assertRaises(SystemExit) as ctx:
                el.main()
            self.assertEqual(ctx.exception.code, 0)

    def test_exits_zero_even_when_db_fails(self):
        """DB import failure must not block the pipeline."""
        with patch.dict("sys.modules", {"knowledge_db": None}):
            code = self._run_main({
                "tool_name": "Bash",
                "tool_input": {"command": "pytest"},
                "tool_output": "Error: test failed",
                "session_id": "test"
            })
        self.assertEqual(code, 0)

    def test_exits_zero_on_missing_tool_name(self):
        code = self._run_main({"tool_input": {}, "tool_output": ""})
        self.assertEqual(code, 0)

    def test_exits_zero_on_empty_input(self):
        code = self._run_main({})
        self.assertEqual(code, 0)


# ===========================================================================
# STORE_LEARNINGS.PY tests
# ===========================================================================

import store_learnings as sl


class TestStoreAutoGenerateTags(unittest.TestCase):
    """Tests for auto_generate_tags()."""

    def test_tag_always_in_output(self):
        tags = sl.auto_generate_tags("LEARNED", "some content", "general")
        self.assertIn("learned", tags)

    def test_tool_mention_adds_tool_tag(self):
        tags = sl.auto_generate_tags("LEARNED", "Use Edit to fix files", "general")
        self.assertIn("tool:edit", tags)

    def test_error_keyword_adds_error_handling_tag(self):
        tags = sl.auto_generate_tags("LEARNED", "error in this code", "general")
        self.assertIn("error-handling", tags)

    def test_test_keyword_adds_testing_tag(self):
        tags = sl.auto_generate_tags("LEARNED", "test coverage improved", "general")
        self.assertIn("testing", tags)

    def test_git_keyword_adds_git_tag(self):
        tags = sl.auto_generate_tags("LEARNED", "git push failed", "general")
        self.assertIn("git", tags)

    def test_no_duplicate_tags(self):
        # "error" appears in both content and context
        tags_str = sl.auto_generate_tags("LEARNED", "error in code", "error context")
        tags = tags_str.split(",")
        self.assertEqual(len(tags), len(set(tags)))

    def test_tags_sorted(self):
        tags_str = sl.auto_generate_tags("INVESTIGATION", "error test workflow", "general")
        tags = tags_str.split(",")
        self.assertEqual(tags, sorted(tags))


class TestStoreIssDuplicate(unittest.TestCase):
    """Tests for is_duplicate()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "knowledge.db"
        self.conn = make_db(self.db_path)

    def tearDown(self):
        self.conn.close()

    def test_empty_db_not_duplicate(self):
        self.assertFalse(sl.is_duplicate(self.conn, "some new content here"))

    def test_exact_content_is_duplicate(self):
        content = "The hook configuration uses uv run for all scripts"
        insert_entry(self.conn, "LEARNED", "title", content)
        self.assertTrue(sl.is_duplicate(self.conn, content))

    def test_very_different_content_not_duplicate(self):
        insert_entry(self.conn, "LEARNED", "title", "The hook configuration uses uv run")
        self.assertFalse(sl.is_duplicate(self.conn, "Completely unrelated topic about databases"))

    def test_short_content_not_duplicate(self):
        """Content with no words >3 chars should never be considered duplicate."""
        self.assertFalse(sl.is_duplicate(self.conn, "ok"))

    def test_custom_threshold(self):
        content = "The hook configuration uses uv run for all scripts here today"
        insert_entry(self.conn, "LEARNED", "title", content)
        # With threshold=1.0 (100% overlap required), similar but not identical shouldn't match
        self.assertFalse(sl.is_duplicate(self.conn, content + " extra words", threshold=1.0))


class TestStoreStoreLearning(unittest.TestCase):
    """Tests for store_learning()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "knowledge.db"
        self.conn = make_db(self.db_path)
        self.config = {
            "auto_tag": True,
            "deduplicate": True,
            "min_confidence": 0.3,
            "source": "pipeline",
        }

    def tearDown(self):
        self.conn.close()

    def test_stores_basic_learning(self):
        entry_id = sl.store_learning(
            self.conn,
            {"tag": "LEARNED", "content": "Fixed the hook configuration", "confidence": 0.8},
            "test-session",
            self.config,
        )
        self.assertIsNotNone(entry_id)
        self.assertIsInstance(entry_id, int)

    def test_empty_content_returns_none(self):
        entry_id = sl.store_learning(
            self.conn,
            {"tag": "LEARNED", "content": "", "confidence": 0.8},
            "test-session",
            self.config,
        )
        self.assertIsNone(entry_id)

    def test_low_confidence_filtered(self):
        entry_id = sl.store_learning(
            self.conn,
            {"tag": "LEARNED", "content": "Some learning", "confidence": 0.1},
            "test-session",
            self.config,
        )
        # 0.1 < 0.3 min_confidence
        self.assertIsNone(entry_id)

    def test_confidence_at_threshold_stored(self):
        entry_id = sl.store_learning(
            self.conn,
            {"tag": "LEARNED", "content": "Some threshold learning", "confidence": 0.3},
            "test-session",
            self.config,
        )
        self.assertIsNotNone(entry_id)

    def test_title_truncated_at_80_chars(self):
        long_content = "x" * 200
        sl.store_learning(
            self.conn,
            {"tag": "LEARNED", "content": long_content, "confidence": 0.8},
            "test-session",
            self.config,
        )
        row = self.conn.execute("SELECT title FROM knowledge_entries ORDER BY id DESC LIMIT 1").fetchone()
        # Title = first 80 chars + "..."
        self.assertLessEqual(len(row["title"]), 83)  # 80 + "..."

    def test_context_appended_to_content(self):
        sl.store_learning(
            self.conn,
            {"tag": "LEARNED", "content": "Main content", "context": "my-project", "confidence": 0.8},
            "test-session",
            self.config,
        )
        row = self.conn.execute("SELECT content FROM knowledge_entries ORDER BY id DESC LIMIT 1").fetchone()
        self.assertIn("Context: my-project", row["content"])

    def test_no_context_no_context_suffix(self):
        sl.store_learning(
            self.conn,
            {"tag": "LEARNED", "content": "Main content only", "confidence": 0.8},
            "test-session",
            self.config,
        )
        row = self.conn.execute("SELECT content FROM knowledge_entries ORDER BY id DESC LIMIT 1").fetchone()
        self.assertNotIn("Context:", row["content"])

    def test_deduplication_prevents_reinsert(self):
        content = "The circuit breaker should track consecutive failures carefully"
        self.config["deduplicate"] = True
        sl.store_learning(
            self.conn,
            {"tag": "LEARNED", "content": content, "confidence": 0.8},
            "test-session",
            self.config,
        )
        # Try to insert the same content
        entry_id2 = sl.store_learning(
            self.conn,
            {"tag": "LEARNED", "content": content, "confidence": 0.8},
            "test-session",
            self.config,
        )
        self.assertIsNone(entry_id2)

    def test_deduplication_disabled_allows_reinsert(self):
        content = "The circuit breaker should track consecutive failures carefully"
        config = {**self.config, "deduplicate": False}
        id1 = sl.store_learning(
            self.conn,
            {"tag": "LEARNED", "content": content, "confidence": 0.8},
            "test-session",
            config,
        )
        id2 = sl.store_learning(
            self.conn,
            {"tag": "LEARNED", "content": content, "confidence": 0.8},
            "test-session",
            config,
        )
        self.assertIsNotNone(id1)
        self.assertIsNotNone(id2)
        self.assertNotEqual(id1, id2)

    def test_source_includes_session_id(self):
        sl.store_learning(
            self.conn,
            {"tag": "LEARNED", "content": "Some learning about hooks", "confidence": 0.8},
            "my-session-123",
            self.config,
        )
        row = self.conn.execute("SELECT source FROM knowledge_entries ORDER BY id DESC LIMIT 1").fetchone()
        self.assertIn("my-session-123", row["source"])


class TestStoreMainHookBehavior(unittest.TestCase):
    """Tests for store_learnings.main() — hook protocol behavior."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "knowledge.db"
        self.pending_path = Path(self.tmpdir) / "pending_learnings.json"

    def _run_main(self, stdin_data=None, pending=None):
        """Set up files and run main(), return exit code."""
        import io
        if stdin_data is None:
            stdin_data = {}
        if pending is not None:
            with open(self.pending_path, "w") as f:
                json.dump(pending, f)

        with patch.object(sl, "PENDING_LEARNINGS", self.pending_path), \
             patch.object(sl, "DB_PATH", self.db_path), \
             patch.object(sl, "DB_DIR", self.db_path.parent), \
             patch("sys.stdin", io.StringIO(json.dumps(stdin_data))):
            with self.assertRaises(SystemExit) as ctx:
                sl.main()
            return ctx.exception.code

    def test_missing_pending_file_exits_cleanly(self):
        # No pending_learnings.json created
        code = self._run_main()
        self.assertEqual(code, 0)

    def test_malformed_json_pending_exits_cleanly(self):
        self.pending_path.write_text("NOT JSON")
        with patch.object(sl, "PENDING_LEARNINGS", self.pending_path), \
             patch.object(sl, "DB_PATH", self.db_path), \
             patch.object(sl, "DB_DIR", self.db_path.parent), \
             patch("sys.stdin", __import__("io").StringIO(json.dumps({}))):
            with self.assertRaises(SystemExit) as ctx:
                sl.main()
            self.assertEqual(ctx.exception.code, 0)

    def test_empty_learnings_list_exits_cleanly(self):
        code = self._run_main(pending={"learnings": []})
        self.assertEqual(code, 0)

    def test_disabled_config_exits_cleanly(self):
        import io
        pending = {"learnings": [{"tag": "LEARNED", "content": "x", "confidence": 0.8}]}
        with open(self.pending_path, "w") as f:
            json.dump(pending, f)
        with patch.object(sl, "load_config", return_value={"enabled": False}), \
             patch.object(sl, "PENDING_LEARNINGS", self.pending_path), \
             patch("sys.stdin", io.StringIO(json.dumps({}))):
            with self.assertRaises(SystemExit) as ctx:
                sl.main()
            self.assertEqual(ctx.exception.code, 0)

    def test_valid_learning_stored_to_db(self):
        pending = {
            "learnings": [
                {"tag": "LEARNED", "content": "Hook configuration best practice found", "confidence": 0.9}
            ]
        }
        self._run_main(stdin_data={"session_id": "test-123"}, pending=pending)
        conn = make_db(self.db_path)
        rows = conn.execute("SELECT * FROM knowledge_entries").fetchall()
        conn.close()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["category"], "LEARNED")

    def test_pending_file_renamed_after_store(self):
        pending = {
            "learnings": [
                {"tag": "LEARNED", "content": "Something was stored successfully here", "confidence": 0.9}
            ]
        }
        self._run_main(stdin_data={"session_id": "test"}, pending=pending)
        # Original pending file should not exist
        self.assertFalse(self.pending_path.exists())
        # Processed file should exist
        processed = self.pending_path.with_suffix(".processed.json")
        self.assertTrue(processed.exists())

    def test_multiple_learnings_creates_relations(self):
        pending = {
            "learnings": [
                {"tag": "LEARNED", "content": "First learning about hooks and framework", "confidence": 0.9},
                {"tag": "PATTERN", "content": "Second learning about circuit breakers here", "confidence": 0.9},
            ]
        }
        self._run_main(stdin_data={"session_id": "test"}, pending=pending)
        conn = make_db(self.db_path)
        rels = conn.execute("SELECT * FROM knowledge_relations").fetchall()
        conn.close()
        self.assertEqual(len(rels), 1)  # 1 relation for 2 entries (n*(n-1)/2 = 1)
        self.assertEqual(rels[0]["relation_type"], "same_session")

    def test_invalid_json_stdin_exits_cleanly(self):
        import io
        with patch.object(sl, "PENDING_LEARNINGS", self.pending_path), \
             patch("sys.stdin", io.StringIO("INVALID")):
            with self.assertRaises(SystemExit) as ctx:
                sl.main()
            self.assertEqual(ctx.exception.code, 0)


# ===========================================================================
# Integration: Full Pipeline Round-Trip
# ===========================================================================

class TestPipelineRoundTrip(unittest.TestCase):
    """End-to-end test: store via store_learnings logic, retrieve via inject logic."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "knowledge.db"
        self.conn = make_db(self.db_path)

    def tearDown(self):
        self.conn.close()

    def test_store_then_retrieve(self):
        """Store a learning via store_learnings logic, then find it via inject_relevant."""
        config = {
            "auto_tag": True, "deduplicate": False,
            "min_confidence": 0.3, "source": "pipeline"
        }
        sl.store_learning(
            self.conn,
            {
                "tag": "LEARNED",
                "content": "Always use circuit breaker wrapper for automation hooks",
                "confidence": 0.9,
                "context": "hooks",
            },
            "session-abc",
            config,
        )

        inject_config = {
            "include_categories": ["LEARNED", "PATTERN", "INVESTIGATION"],
            "max_injections": 5,
            "lookback_days": 30,
            "recency_boost": 0.2,
        }

        with patch.object(ir, "DB_PATH", self.db_path):
            results = ir.search_knowledge(self.conn, ["circuit", "breaker", "hooks"], inject_config)

        self.assertGreater(len(results), 0)
        contents = [r["content"] for r in results]
        self.assertTrue(any("circuit breaker" in c.lower() for c in contents))

    def test_extract_then_inject(self):
        """Extract an entry from tool output, store it, then verify inject finds it."""
        entries = el.extract_from_tool_output(
            "Bash",
            {"command": "pytest tests/knowledge/"},
            "Error: 3 tests failed\nfailed assertions in test_knowledge",
            "session-xyz",
        )
        self.assertEqual(len(entries), 1)

        # Store the extracted entry
        config = {
            "auto_tag": True, "deduplicate": False,
            "min_confidence": 0.3, "source": "pipeline"
        }
        entry_id = sl.store_learning(
            self.conn,
            {
                "tag": entries[0]["tag"],
                "content": entries[0]["content"],
                "context": entries[0]["context"],
                "confidence": 0.6,
            },
            "session-xyz",
            config,
        )
        self.assertIsNotNone(entry_id)

        # Now inject should find it
        inject_config = {
            "include_categories": ["LEARNED", "PATTERN", "INVESTIGATION"],
            "max_injections": 5,
            "lookback_days": 30,
            "recency_boost": 0.2,
        }
        with patch.object(ir, "DB_PATH", self.db_path):
            results = ir.search_knowledge(self.conn, ["pytest", "knowledge", "failed"], inject_config)
        self.assertGreater(len(results), 0)


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Group tests by component
    groups = [
        ("inject_relevant.py — CWD Context", TestInjectCWDContext),
        ("inject_relevant.py — Search", TestInjectSearchKnowledge),
        ("inject_relevant.py — Rank & Filter", TestInjectRankAndFilter),
        ("inject_relevant.py — Format Injection", TestInjectFormatInjection),
        ("inject_relevant.py — Main Output Format", TestInjectMainOutputFormat),
        ("extract_learnings.py — Tool Output", TestExtractFromToolOutput),
        ("extract_learnings.py — Context Inference", TestExtractContextInference),
        ("extract_learnings.py — Hook Behavior", TestExtractMainHookBehavior),
        ("store_learnings.py — Auto Tag Generation", TestStoreAutoGenerateTags),
        ("store_learnings.py — Deduplication", TestStoreIssDuplicate),
        ("store_learnings.py — Store Entry", TestStoreStoreLearning),
        ("store_learnings.py — Hook Behavior", TestStoreMainHookBehavior),
        ("Integration — Round-Trip", TestPipelineRoundTrip),
    ]

    for group_name, test_class in groups:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
        print(f"\n--- {group_name} ({tests.countTestCases()} tests) ---")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    print(f"\n{'='*60}")
    print(f"TOTAL: {total} tests | PASSED: {total - failed} | FAILED: {failed}")
    sys.exit(0 if result.wasSuccessful() else 1)
