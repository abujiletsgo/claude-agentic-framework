# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""
Test Utilities for the Hook Testing Framework
==============================================

Shared helpers for generating mock hook inputs, LLM responses,
temporary directories, database fixtures, git repo fixtures,
and settings.json fixtures.

Usage:
    from test_utils import (
        make_hook_input,
        make_observation,
        make_learning,
        MockLLMResponse,
        TempDirFixture,
        DatabaseFixture,
        GitRepoFixture,
        SettingsFixture,
    )
"""

import json
import os
import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Mock hook input generators
# ---------------------------------------------------------------------------


def make_hook_input(
    hook_event_name: str = "PreToolUse",
    tool_name: str = "Bash",
    tool_input: Optional[dict] = None,
    session_id: str = "test-session-001",
    cwd: str = "/tmp/test-project",
    transcript_path: str = "/tmp/test-transcript.jsonl",
    permission_mode: str = "default",
    tool_output: str = "",
    **extra: Any,
) -> dict:
    """
    Generate a mock hook input dict matching Claude Code hook schema.

    Args:
        hook_event_name: One of PreToolUse, PostToolUse, SessionStart, SessionEnd, etc.
        tool_name: Tool being used (Bash, Edit, Write, Read, Grep, Glob, etc.)
        tool_input: Tool-specific input dict
        session_id: Session identifier
        cwd: Working directory
        transcript_path: Path to transcript JSONL
        permission_mode: Permission mode string
        tool_output: Output from tool (for PostToolUse)
        **extra: Additional fields to merge

    Returns:
        Complete hook input dict
    """
    result = {
        "hook_event_name": hook_event_name,
        "session_id": session_id,
        "cwd": cwd,
        "transcript_path": transcript_path,
        "permission_mode": permission_mode,
    }
    if tool_name:
        result["tool_name"] = tool_name
    if tool_input is not None:
        result["tool_input"] = tool_input
    else:
        result["tool_input"] = _default_tool_input(tool_name)
    if tool_output:
        result["tool_output"] = tool_output
    result.update(extra)
    return result


def _default_tool_input(tool_name: str) -> dict:
    """Generate reasonable default tool_input for a given tool."""
    defaults = {
        "Bash": {"command": "echo hello"},
        "Edit": {
            "file_path": "/tmp/test.py",
            "old_string": "old",
            "new_string": "new",
        },
        "Write": {
            "file_path": "/tmp/test.py",
            "content": "print('hello')\n",
        },
        "Read": {"file_path": "/tmp/test.py"},
        "Grep": {"pattern": "TODO", "path": "/tmp"},
        "Glob": {"pattern": "**/*.py", "path": "/tmp"},
        "TaskCreate": {"subject": "Test task", "description": "A test"},
        "TaskUpdate": {"taskId": "1", "status": "completed"},
        "TaskGet": {"taskId": "1"},
        "TaskList": {},
        "WebSearch": {"query": "test query"},
        "WebFetch": {"url": "https://example.com", "prompt": "summarize"},
    }
    return defaults.get(tool_name, {})


def make_pre_tool_use_input(
    tool_name: str = "Bash",
    tool_input: Optional[dict] = None,
    **kwargs: Any,
) -> dict:
    """Shortcut for PreToolUse hook inputs."""
    return make_hook_input(
        hook_event_name="PreToolUse",
        tool_name=tool_name,
        tool_input=tool_input,
        **kwargs,
    )


def make_post_tool_use_input(
    tool_name: str = "Bash",
    tool_input: Optional[dict] = None,
    tool_output: str = "command output",
    **kwargs: Any,
) -> dict:
    """Shortcut for PostToolUse hook inputs."""
    return make_hook_input(
        hook_event_name="PostToolUse",
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=tool_output,
        **kwargs,
    )


def make_session_start_input(**kwargs: Any) -> dict:
    """Shortcut for SessionStart hook inputs."""
    return make_hook_input(
        hook_event_name="SessionStart",
        tool_name="",
        tool_input=None,
        **kwargs,
    )


def make_session_end_input(**kwargs: Any) -> dict:
    """Shortcut for SessionEnd hook inputs."""
    return make_hook_input(
        hook_event_name="SessionEnd",
        tool_name="",
        tool_input=None,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Mock observation and learning generators
# ---------------------------------------------------------------------------


def make_observation(
    tool: str = "Bash",
    pattern: str = "shell_command",
    obs_type: str = "tool_usage",
    session_id: str = "test-session-001",
    context: Optional[dict] = None,
    processed: bool = False,
) -> dict:
    """Generate a mock observation dict (as written to observations.jsonl)."""
    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": obs_type,
        "tool": tool,
        "pattern": pattern,
        "context": context or {"command": "echo test"},
        "session_id": session_id,
        "processed": processed,
    }


def make_learning(
    tag: str = "LEARNED",
    content: str = "Always check file existence before editing",
    context: str = "Multiple edit failures observed",
    confidence: float = 0.8,
) -> dict:
    """Generate a mock learning dict (as produced by analyze stage)."""
    return {
        "tag": tag,
        "content": content,
        "context": context,
        "confidence": confidence,
    }


def make_pending_learnings(
    session_id: str = "test-session-001",
    learnings: Optional[list[dict]] = None,
    provider: str = "anthropic",
) -> dict:
    """Generate a mock pending_learnings.json structure."""
    if learnings is None:
        learnings = [
            make_learning("LEARNED", "Check file existence before editing"),
            make_learning("PATTERN", "Grep then Edit is common workflow"),
            make_learning("INVESTIGATION", "Error rate seems high in git ops"),
        ]
    return {
        "session_id": session_id,
        "analyzed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "observation_count": 50,
        "llm_provider": provider,
        "learnings": learnings,
    }


# ---------------------------------------------------------------------------
# Mock LLM responses
# ---------------------------------------------------------------------------


class MockLLMResponse:
    """Factory for generating mock LLM responses for different stages."""

    @staticmethod
    def analysis_response(learnings: Optional[list[dict]] = None) -> str:
        """Generate a valid JSON analysis response."""
        if learnings is None:
            learnings = [
                {
                    "tag": "LEARNED",
                    "content": "Always verify file paths before editing",
                    "context": "3 edit failures due to missing files",
                    "confidence": 0.85,
                },
                {
                    "tag": "PATTERN",
                    "content": "Grep-then-Edit is the standard modification workflow",
                    "context": "Grep followed by Edit in 80% of cases",
                    "confidence": 0.9,
                },
                {
                    "tag": "INVESTIGATION",
                    "content": "Git operations have higher failure rate than expected",
                    "context": "15% failure rate on git commands vs 5% for other tools",
                    "confidence": 0.6,
                },
            ]
        return json.dumps(learnings)

    @staticmethod
    def analysis_response_with_markdown() -> str:
        """Generate a response wrapped in markdown code fences."""
        learnings = [
            {
                "tag": "LEARNED",
                "content": "Test learning in markdown block",
                "context": "Testing markdown stripping",
                "confidence": 0.7,
            }
        ]
        return f"```json\n{json.dumps(learnings, indent=2)}\n```"

    @staticmethod
    def analysis_response_invalid() -> str:
        """Generate an invalid (non-JSON) response."""
        return "This is not valid JSON and should be handled gracefully."

    @staticmethod
    def analysis_response_empty_array() -> str:
        """Generate an empty array response."""
        return "[]"

    @staticmethod
    def analysis_response_missing_fields() -> str:
        """Generate response with some entries missing required fields."""
        return json.dumps([
            {"tag": "LEARNED", "content": "Valid entry", "confidence": 0.8},
            {"invalid_key": "Missing tag and content"},
            {"tag": "PATTERN"},  # Missing content
        ])


# ---------------------------------------------------------------------------
# Temporary directory fixture
# ---------------------------------------------------------------------------


class TempDirFixture:
    """
    Managed temporary directory for tests.

    Usage:
        with TempDirFixture() as tmp:
            path = tmp.path / "test.txt"
            path.write_text("hello")
    """

    def __init__(self, prefix: str = "hook_test_"):
        self.prefix = prefix
        self._dir: Optional[str] = None
        self.path: Optional[Path] = None

    def __enter__(self) -> "TempDirFixture":
        self._dir = tempfile.mkdtemp(prefix=self.prefix)
        self.path = Path(self._dir)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._dir and os.path.exists(self._dir):
            shutil.rmtree(self._dir)

    def write_json(self, name: str, data: Any) -> Path:
        """Write a JSON file into the temp directory."""
        p = self.path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            json.dump(data, f, indent=2)
        return p

    def write_text(self, name: str, content: str) -> Path:
        """Write a text file into the temp directory."""
        p = self.path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return p

    def write_jsonl(self, name: str, records: list[dict]) -> Path:
        """Write a JSONL file into the temp directory."""
        p = self.path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
        return p


# ---------------------------------------------------------------------------
# Database fixture
# ---------------------------------------------------------------------------


class DatabaseFixture:
    """
    Managed SQLite database fixture for knowledge DB tests.

    Creates a temporary database with the knowledge schema.
    """

    KNOWLEDGE_SCHEMA = """
        CREATE TABLE IF NOT EXISTS knowledge (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            content   TEXT    NOT NULL,
            tag       TEXT    NOT NULL,
            context   TEXT,
            session_id TEXT,
            timestamp TEXT    NOT NULL,
            metadata  TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_tag ON knowledge(tag);
        CREATE INDEX IF NOT EXISTS idx_knowledge_timestamp ON knowledge(timestamp DESC);
    """

    KNOWLEDGE_ENTRIES_SCHEMA = """
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
    """

    def __init__(self, schema: str = "knowledge"):
        """
        Args:
            schema: Which schema to use: 'knowledge' (knowledge_db.py) or
                    'knowledge_entries' (store_learnings.py)
        """
        self.schema_type = schema
        self._dir: Optional[str] = None
        self.db_path: Optional[Path] = None
        self.conn: Optional[sqlite3.Connection] = None

    def __enter__(self) -> "DatabaseFixture":
        self._dir = tempfile.mkdtemp(prefix="hook_test_db_")
        self.db_path = Path(self._dir) / "knowledge.db"
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        if self.schema_type == "knowledge_entries":
            self.conn.executescript(self.KNOWLEDGE_ENTRIES_SCHEMA)
        else:
            self.conn.executescript(self.KNOWLEDGE_SCHEMA)
        self.conn.commit()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
        if self._dir and os.path.exists(self._dir):
            shutil.rmtree(self._dir)

    def insert_knowledge(self, content: str, tag: str = "LEARNED",
                         context: str = "", session_id: str = "test",
                         metadata: Optional[dict] = None) -> int:
        """Insert a knowledge entry and return its row ID."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        meta_json = json.dumps(metadata) if metadata else None
        cur = self.conn.execute(
            "INSERT INTO knowledge (content, tag, context, session_id, timestamp, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (content, tag, context, session_id, ts, meta_json),
        )
        self.conn.commit()
        return cur.lastrowid

    def insert_knowledge_entry(self, category: str, title: str, content: str,
                               tags: str = "", confidence: float = 0.8,
                               source: str = "test") -> int:
        """Insert a knowledge_entries row and return its row ID."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cur = self.conn.execute(
            "INSERT INTO knowledge_entries "
            "(category, title, content, tags, confidence, source, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (category, title, content, tags, confidence, source, ts, ts),
        )
        self.conn.commit()
        return cur.lastrowid

    def count_rows(self, table: str = "knowledge") -> int:
        """Count rows in a table."""
        row = self.conn.execute(f"SELECT COUNT(*) as cnt FROM {table}").fetchone()
        return row["cnt"]


# ---------------------------------------------------------------------------
# Git repo fixture
# ---------------------------------------------------------------------------


class GitRepoFixture:
    """
    Creates a temporary git repository for testing hooks that depend on git.

    Usage:
        with GitRepoFixture() as repo:
            repo.write_file("hello.py", "print('hello')")
            repo.commit("Initial commit")
    """

    def __init__(self):
        self._dir: Optional[str] = None
        self.path: Optional[Path] = None

    def __enter__(self) -> "GitRepoFixture":
        self._dir = tempfile.mkdtemp(prefix="hook_test_repo_")
        self.path = Path(self._dir)
        os.system(f'cd "{self._dir}" && git init -q && git config user.email "test@test.com" && git config user.name "Test"')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._dir and os.path.exists(self._dir):
            shutil.rmtree(self._dir)

    def write_file(self, name: str, content: str) -> Path:
        """Write a file into the repo."""
        p = self.path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return p

    def add_and_commit(self, message: str = "test commit") -> str:
        """Stage all and commit. Returns the commit hash."""
        os.system(f'cd "{self._dir}" && git add -A && git commit -q -m "{message}"')
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self._dir,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def get_diff(self) -> str:
        """Get the current diff."""
        import subprocess
        result = subprocess.run(
            ["git", "diff"],
            cwd=self._dir,
            capture_output=True,
            text=True,
        )
        return result.stdout


# ---------------------------------------------------------------------------
# Settings.json fixture
# ---------------------------------------------------------------------------


class SettingsFixture:
    """
    Creates a temporary settings.json for testing configuration loading.
    """

    DEFAULT_SETTINGS = {
        "permissions": {
            "allow": ["*"],
            "deny": [
                "Bash(rm -rf /)",
                "Bash(sudo *)",
            ],
        },
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "uv run /tmp/bash-hook.py",
                        },
                        {
                            "type": "prompt",
                            "prompt": "Review this Bash command for safety. The tool input is: $ARGUMENTS\n\nRespond with JSON: {\"ok\": true} if safe, {\"ok\": false, \"message\": \"reason\"} if dangerous.",
                            "timeout": 30,
                        },
                    ],
                },
                {
                    "matcher": "Edit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "uv run /tmp/edit-hook.py",
                        },
                        {
                            "type": "prompt",
                            "prompt": "Review this Edit operation for safety. The tool input is: $ARGUMENTS\n\nRespond with JSON: {\"ok\": true} if safe, {\"ok\": false, \"message\": \"reason\"} if dangerous.",
                            "timeout": 30,
                        },
                    ],
                },
                {
                    "matcher": "Write",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "uv run /tmp/write-hook.py",
                        },
                        {
                            "type": "prompt",
                            "prompt": "Review this Write operation for safety. The tool input is: $ARGUMENTS\n\nRespond with JSON: {\"ok\": true} if safe, {\"ok\": false, \"message\": \"reason\"} if dangerous.",
                            "timeout": 30,
                        },
                    ],
                },
            ],
            "PostToolUse": [],
            "SessionStart": [],
            "SessionEnd": [],
        },
    }

    def __init__(self):
        self._dir: Optional[str] = None
        self.settings_path: Optional[Path] = None

    def __enter__(self) -> "SettingsFixture":
        self._dir = tempfile.mkdtemp(prefix="hook_test_settings_")
        self.settings_path = Path(self._dir) / "settings.json"
        with open(self.settings_path, "w") as f:
            json.dump(self.DEFAULT_SETTINGS, f, indent=2)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._dir and os.path.exists(self._dir):
            shutil.rmtree(self._dir)

    def update_settings(self, updates: dict) -> None:
        """Merge updates into the settings file."""
        with open(self.settings_path) as f:
            current = json.load(f)
        _deep_merge_in_place(current, updates)
        with open(self.settings_path, "w") as f:
            json.dump(current, f, indent=2)

    def get_settings(self) -> dict:
        """Read and return the current settings."""
        with open(self.settings_path) as f:
            return json.load(f)


def _deep_merge_in_place(base: dict, override: dict) -> None:
    """Recursively merge override into base in-place."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge_in_place(base[key], value)
        else:
            base[key] = value
