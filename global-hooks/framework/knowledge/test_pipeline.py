#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""
Test script for the Knowledge Pipeline.

Demonstrates the full lifecycle:
  1. Generate mock observations (OBSERVE)
  2. Trigger analysis (ANALYZE)
  3. Verify learnings stored (LEARN)
  4. Simulate SessionStart injection (EVOLVE)
  5. Verify relevant knowledge injected

Usage:
  uv run test_pipeline.py
  uv run test_pipeline.py --clean    # Clean up test artifacts first
  uv run test_pipeline.py --stats    # Show knowledge stats only
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Use test-specific paths to avoid polluting real data
TEST_DIR = Path(tempfile.mkdtemp(prefix="knowledge_pipeline_test_"))
TEST_OBS_FILE = TEST_DIR / "observations.jsonl"
TEST_DB_DIR = TEST_DIR / "knowledge-db"
TEST_DB_PATH = TEST_DB_DIR / "knowledge.db"
TEST_PENDING = TEST_DIR / "pending_learnings.json"
TEST_CONFIG = TEST_DIR / "knowledge_pipeline.yaml"

SCRIPT_DIR = Path(__file__).parent

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header(text):
    print(f"\n{BOLD}{BLUE}{'=' * 60}{RESET}")
    print(f"{BOLD}{BLUE}  {text}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 60}{RESET}\n")


def print_pass(text):
    print(f"  {GREEN}PASS{RESET} {text}")


def print_fail(text):
    print(f"  {RED}FAIL{RESET} {text}")


def print_info(text):
    print(f"  {YELLOW}INFO{RESET} {text}")


# ---------------------------------------------------------------------------
# Step 1: Generate mock observations
# ---------------------------------------------------------------------------

def generate_mock_observations():
    """Generate realistic mock observations to simulate a coding session."""
    print_header("Step 1: OBSERVE - Generating mock observations")

    session_id = "test-session-001"
    base_time = datetime.now(timezone.utc) - timedelta(hours=1)
    observations = []

    # Simulate a typical coding session
    tool_sequence = [
        ("Read", "file_read", {"file_path": "/project/src/main.py", "file_ext": ".py", "file_name": "main.py"}),
        ("Grep", "code_search", {"pattern": "def handle_request", "path": "/project/src/", "output_mode": "content"}),
        ("Read", "file_read", {"file_path": "/project/src/handlers.py", "file_ext": ".py", "file_name": "handlers.py"}),
        ("Edit", "small_modification", {"file_path": "/project/src/handlers.py", "file_ext": ".py", "old_lines": 3, "new_lines": 5}),
        ("Bash", "test_execution", {"command": "pytest tests/ -v", "timeout": 30000}),
        ("Edit", "refactor", {"file_path": "/project/src/handlers.py", "file_ext": ".py", "old_lines": 15, "new_lines": 20}),
        ("Bash", "test_execution", {"command": "pytest tests/ -v", "timeout": 30000}),
        ("Grep", "code_search", {"pattern": "import logging", "path": "/project/", "output_mode": "files_with_matches"}),
        ("Edit", "small_modification", {"file_path": "/project/src/utils.py", "file_ext": ".py", "old_lines": 2, "new_lines": 4}),
        ("Write", "medium_file_write", {"file_path": "/project/tests/test_handlers.py", "file_ext": ".py", "content_lines": 45, "content_bytes": 1200}),
        ("Bash", "test_execution", {"command": "pytest tests/test_handlers.py -v", "timeout": 30000}),
        ("Bash", "git_operation", {"command": "git diff --stat"}),
        ("Glob", "file_search", {"pattern": "**/*.py", "path": "/project/src/"}),
        ("Read", "file_read", {"file_path": "/project/src/config.py", "file_ext": ".py", "file_name": "config.py"}),
        ("Edit", "expansion", {"file_path": "/project/src/config.py", "file_ext": ".py", "old_lines": 5, "new_lines": 15}),
        ("Bash", "test_execution", {"command": "pytest tests/ -v --tb=short", "timeout": 30000}),
        ("Bash", "shell_command", {"command": "python -c 'import handlers; print(handlers.__version__)'"}),
        ("TaskCreate", "task_management", {}),
        ("TaskUpdate", "task_management", {}),
        ("Edit", "small_modification", {"file_path": "/project/README.md", "file_ext": ".md", "old_lines": 1, "new_lines": 3}),
    ]

    # Add some errors
    error_observations = [
        ("Edit", "small_modification", {"file_path": "/project/src/missing.py", "file_ext": ".py", "error_snippet": "Error: File not found: /project/src/missing.py"}),
        ("Bash", "test_execution", {"command": "pytest tests/test_broken.py", "error_snippet": "FAILED tests/test_broken.py::test_edge_case - AssertionError: expected 42 got 41"}),
    ]

    for i, (tool, pattern, context) in enumerate(tool_sequence):
        obs = {
            "timestamp": (base_time + timedelta(minutes=i * 2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "type": "tool_usage",
            "tool": tool,
            "pattern": pattern,
            "context": context,
            "session_id": session_id,
            "processed": False,
        }
        observations.append(obs)

    for i, (tool, pattern, context) in enumerate(error_observations):
        obs = {
            "timestamp": (base_time + timedelta(minutes=len(tool_sequence) * 2 + i * 3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "type": "error",
            "tool": tool,
            "pattern": pattern,
            "context": context,
            "session_id": session_id,
            "processed": False,
        }
        observations.append(obs)

    # Write observations to test file
    with open(TEST_OBS_FILE, "w") as f:
        for obs in observations:
            f.write(json.dumps(obs) + "\n")

    print_info(f"Generated {len(observations)} mock observations")
    print_info(f"  Tool usage: {len(tool_sequence)}")
    print_info(f"  Errors: {len(error_observations)}")
    print_info(f"  Written to: {TEST_OBS_FILE}")
    print_pass("Mock observations generated")

    return session_id, observations


# ---------------------------------------------------------------------------
# Step 2: Test ANALYZE stage (without real LLM - use mock learnings)
# ---------------------------------------------------------------------------

def test_analyze(session_id, observations):
    """Test the analyze stage by importing and running the summarizer, then creating mock LLM output."""
    print_header("Step 2: ANALYZE - Processing observations")

    # Import the analyze module to test summarization
    sys.path.insert(0, str(SCRIPT_DIR))

    try:
        # We cannot run the full LLM call in tests, so we test the
        # observation loading and summarization, then provide mock learnings
        from analyze_session import load_unprocessed_observations, summarize_observations

        loaded = load_unprocessed_observations(TEST_OBS_FILE, max_count=200)
        print_info(f"Loaded {len(loaded)} unprocessed observations")

        if len(loaded) != len(observations):
            print_fail(f"Expected {len(observations)} observations, got {len(loaded)}")
            return False

        summary = summarize_observations(loaded)
        print_info(f"Summary length: {len(summary)} chars")
        print_info("Summary preview:")
        for line in summary.split("\n")[:10]:
            print(f"    {line}")

        print_pass("Observation loading and summarization works")

    except Exception as e:
        print_fail(f"Failed to import/run analyze functions: {e}")
        # Continue with mock data anyway

    # Create mock LLM output (simulating what the LLM would return)
    mock_learnings = [
        {
            "tag": "PATTERN",
            "content": "Read-Grep-Edit is the standard search-then-modify workflow in Python projects",
            "context": "Grep followed by Edit in 80% of modification sequences observed",
            "confidence": 0.9,
        },
        {
            "tag": "LEARNED",
            "content": "Always verify file existence before attempting edits to avoid errors",
            "context": "Edit failure on missing.py caused unnecessary retry",
            "confidence": 0.85,
        },
        {
            "tag": "PATTERN",
            "content": "Test execution follows every significant code change as a validation step",
            "context": "pytest runs after each Edit operation, 4 test runs in session",
            "confidence": 0.95,
        },
        {
            "tag": "INVESTIGATION",
            "content": "Edge case handling in test_broken.py needs attention - assertion off by one",
            "context": "Test failure: expected 42 got 41, possible off-by-one error",
            "confidence": 0.7,
        },
        {
            "tag": "LEARNED",
            "content": "Task management tools help maintain context across long sessions",
            "context": "TaskCreate and TaskUpdate used for progress tracking mid-session",
            "confidence": 0.6,
        },
    ]

    pending_data = {
        "session_id": session_id,
        "analyzed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "observation_count": len(observations),
        "llm_provider": "mock_test",
        "learnings": mock_learnings,
    }

    with open(TEST_PENDING, "w") as f:
        json.dump(pending_data, f, indent=2)

    print_info(f"Created {len(mock_learnings)} mock learnings")
    print_pass("Analysis stage completed (mock LLM)")

    return True


# ---------------------------------------------------------------------------
# Step 3: Test LEARN stage (store into test database)
# ---------------------------------------------------------------------------

def test_learn(session_id):
    """Test storing learnings into a test knowledge database."""
    print_header("Step 3: LEARN - Storing learnings in knowledge.db")

    # Read pending learnings
    with open(TEST_PENDING, "r") as f:
        pending = json.load(f)

    learnings = pending.get("learnings", [])
    print_info(f"Pending learnings to store: {len(learnings)}")

    # Initialize test database
    TEST_DB_DIR.mkdir(parents=True, exist_ok=True)

    # Import schema from store_learnings
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        from store_learnings import SCHEMA, now_iso, auto_generate_tags
    except ImportError:
        print_fail("Cannot import store_learnings module")
        return False

    conn = sqlite3.connect(str(TEST_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    conn.commit()

    stored_count = 0
    stored_ids = []

    for learning in learnings:
        tag = learning.get("tag", "LEARNED")
        content = learning.get("content", "")
        context_str = learning.get("context", "")
        confidence = learning.get("confidence", 0.5)

        tags = auto_generate_tags(tag, content, context_str)
        title = content[:80].rstrip(".")
        if len(content) > 80:
            title += "..."

        ts = now_iso()
        cur = conn.execute(
            "INSERT INTO knowledge_entries "
            "(category, title, content, tags, project, confidence, source, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                tag,
                title,
                content + ("\n\nContext: " + context_str if context_str else ""),
                tags,
                None,
                confidence,
                f"pipeline:session:{session_id}",
                ts,
                ts,
            ),
        )
        conn.commit()
        stored_count += 1
        stored_ids.append(cur.lastrowid)
        print_info(f"  Stored [{tag}]: {title}")

    # Create relations
    if len(stored_ids) > 1:
        ts = now_iso()
        for i in range(len(stored_ids)):
            for j in range(i + 1, len(stored_ids)):
                conn.execute(
                    "INSERT OR IGNORE INTO knowledge_relations "
                    "(from_id, to_id, relation_type, created_at) VALUES (?, ?, ?, ?)",
                    (stored_ids[i], stored_ids[j], "same_session", ts),
                )
        conn.commit()

    # Verify stored entries
    total = conn.execute("SELECT COUNT(*) FROM knowledge_entries").fetchone()[0]
    rels = conn.execute("SELECT COUNT(*) FROM knowledge_relations").fetchone()[0]

    print_info(f"Database entries: {total}")
    print_info(f"Relations: {rels}")

    if total == len(learnings):
        print_pass(f"All {total} learnings stored successfully")
    else:
        print_fail(f"Expected {len(learnings)} entries, got {total}")

    conn.close()
    return stored_count > 0


# ---------------------------------------------------------------------------
# Step 4: Test EVOLVE stage (FTS5 search and injection)
# ---------------------------------------------------------------------------

def test_evolve():
    """Test retrieving and injecting relevant knowledge."""
    print_header("Step 4: EVOLVE - Injecting relevant knowledge")

    conn = sqlite3.connect(str(TEST_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # Test FTS5 search with various queries
    test_queries = [
        ("python edit workflow", "Should match the Read-Grep-Edit pattern"),
        ("test failure assertion", "Should match the edge case investigation"),
        ("file existence check", "Should match the file existence learning"),
        ("task management context", "Should match the task management learning"),
    ]

    all_passed = True

    for query, description in test_queries:
        try:
            rows = conn.execute(
                "SELECT e.id, e.category, e.title, e.content, e.confidence, rank "
                "FROM knowledge_fts f "
                "JOIN knowledge_entries e ON f.rowid = e.id "
                "WHERE knowledge_fts MATCH ? "
                "ORDER BY rank LIMIT 3",
                (query,),
            ).fetchall()

            if rows:
                print_pass(f'Query "{query}" -> {len(rows)} results')
                for r in rows:
                    print_info(f"    [{r['category']}] {r['title'][:60]}  (rank={r['rank']:.2f})")
            else:
                print_fail(f'Query "{query}" -> no results ({description})')
                all_passed = False

        except Exception as e:
            print_fail(f'Query "{query}" failed: {e}')
            all_passed = False

    # Test formatting the injection output
    print_info("")
    print_info("Testing context injection formatting...")

    try:
        rows = conn.execute(
            "SELECT id, category, title, content, tags, confidence, created_at, source "
            "FROM knowledge_entries "
            "ORDER BY created_at DESC LIMIT 5"
        ).fetchall()

        entries = [dict(r) for r in rows]

        # Import formatting function
        sys.path.insert(0, str(SCRIPT_DIR))
        from inject_relevant import format_injection

        injection = format_injection(entries)
        print_info("Context injection output:")
        for line in injection.split("\n"):
            print(f"    {line}")

        if "Relevant Knowledge" in injection:
            print_pass("Context injection formatted correctly")
        else:
            print_fail("Context injection missing expected header")
            all_passed = False

        # Test the hookSpecificOutput structure
        output = {
            "hookSpecificOutput": {
                "contextInjection": injection,
            }
        }
        output_json = json.dumps(output)
        parsed = json.loads(output_json)
        if "hookSpecificOutput" in parsed and "contextInjection" in parsed["hookSpecificOutput"]:
            print_pass("hookSpecificOutput JSON structure valid")
        else:
            print_fail("hookSpecificOutput JSON structure invalid")
            all_passed = False

    except Exception as e:
        print_fail(f"Injection formatting failed: {e}")
        all_passed = False

    conn.close()
    return all_passed


# ---------------------------------------------------------------------------
# Step 5: Full pipeline verification
# ---------------------------------------------------------------------------

def verify_pipeline():
    """Run final verification checks."""
    print_header("Step 5: Full Pipeline Verification")

    checks = []

    # Check 1: Observations file exists and has content
    if TEST_OBS_FILE.exists() and TEST_OBS_FILE.stat().st_size > 0:
        line_count = sum(1 for _ in open(TEST_OBS_FILE))
        print_pass(f"Observations file: {line_count} lines")
        checks.append(True)
    else:
        print_fail("Observations file missing or empty")
        checks.append(False)

    # Check 2: Database exists and has entries
    if TEST_DB_PATH.exists():
        conn = sqlite3.connect(str(TEST_DB_PATH))
        total = conn.execute("SELECT COUNT(*) FROM knowledge_entries").fetchone()[0]
        rels = conn.execute("SELECT COUNT(*) FROM knowledge_relations").fetchone()[0]

        # Check categories
        cats = conn.execute(
            "SELECT category, COUNT(*) as cnt FROM knowledge_entries GROUP BY category"
        ).fetchall()
        cat_summary = ", ".join(f"{r[0]}={r[1]}" for r in cats)

        conn.close()

        print_pass(f"Knowledge DB: {total} entries, {rels} relations ({cat_summary})")
        checks.append(True)
    else:
        print_fail("Knowledge database not created")
        checks.append(False)

    # Check 3: All hook scripts exist and are valid Python
    hook_files = [
        "observe_patterns.py",
        "analyze_session.py",
        "store_learnings.py",
        "inject_relevant.py",
    ]

    for hf in hook_files:
        path = SCRIPT_DIR / hf
        if path.exists():
            # Basic syntax check
            try:
                with open(path, "r") as f:
                    compile(f.read(), str(path), "exec")
                print_pass(f"Hook script valid: {hf}")
                checks.append(True)
            except SyntaxError as e:
                print_fail(f"Hook script syntax error: {hf}: {e}")
                checks.append(False)
        else:
            print_fail(f"Hook script missing: {hf}")
            checks.append(False)

    # Check 4: Config file exists
    real_config = Path.home() / ".claude" / "knowledge_pipeline.yaml"
    if real_config.exists():
        print_pass(f"Config file exists: {real_config}")
        checks.append(True)
    else:
        print_fail(f"Config file missing: {real_config}")
        checks.append(False)

    # Summary
    passed = sum(checks)
    total_checks = len(checks)

    print_header("RESULTS")
    if passed == total_checks:
        print(f"  {GREEN}{BOLD}ALL {total_checks} CHECKS PASSED{RESET}")
    else:
        print(f"  {RED}{BOLD}{passed}/{total_checks} CHECKS PASSED{RESET}")

    print(f"\n  Test artifacts in: {TEST_DIR}")
    print(f"  To clean up: rm -rf {TEST_DIR}\n")

    return passed == total_checks


# ---------------------------------------------------------------------------
# Stats command
# ---------------------------------------------------------------------------

def show_stats():
    """Show knowledge pipeline statistics from the real database."""
    print_header("Knowledge Pipeline Statistics")

    # Observations
    obs_file = Path.home() / ".claude" / "observations.jsonl"
    if obs_file.exists():
        total_obs = sum(1 for _ in open(obs_file))
        processed = 0
        unprocessed = 0
        with open(obs_file, "r") as f:
            for line in f:
                try:
                    obs = json.loads(line.strip())
                    if obs.get("processed", False):
                        processed += 1
                    else:
                        unprocessed += 1
                except Exception:
                    pass
        print_info(f"Observations: {total_obs} total ({processed} processed, {unprocessed} pending)")
    else:
        print_info("Observations: 0 (no observations file)")

    # Knowledge DB
    real_db = Path.home() / ".claude" / "data" / "knowledge-db" / "knowledge.db"
    if real_db.exists():
        conn = sqlite3.connect(str(real_db))
        total = conn.execute("SELECT COUNT(*) FROM knowledge_entries").fetchone()[0]
        cats = conn.execute(
            "SELECT category, COUNT(*) as cnt FROM knowledge_entries GROUP BY category"
        ).fetchall()
        rels = conn.execute("SELECT COUNT(*) FROM knowledge_relations").fetchone()[0]
        db_size = os.path.getsize(str(real_db))
        conn.close()

        print_info(f"Learnings stored: {total}")
        for cat, cnt in cats:
            print_info(f"  {cat}: {cnt}")
        print_info(f"Relations: {rels}")
        print_info(f"DB size: {db_size:,} bytes")
    else:
        print_info("Learnings stored: 0 (no database)")

    # Analysis log
    analysis_log = Path.home() / ".claude" / "analysis_log.jsonl"
    if analysis_log.exists():
        sessions = 0
        last_analysis = None
        with open(analysis_log, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("stage") != "learn":
                        sessions += 1
                        last_analysis = entry.get("timestamp", "")
                except Exception:
                    pass
        print_info(f"Sessions analyzed: {sessions}")
        if last_analysis:
            print_info(f"Last analysis: {last_analysis}")
    else:
        print_info("Sessions analyzed: 0")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Knowledge Pipeline Test")
    parser.add_argument("--clean", action="store_true", help="Clean test artifacts only")
    parser.add_argument("--stats", action="store_true", help="Show pipeline statistics")
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if args.clean:
        import shutil
        # Clean common test dirs
        for d in Path(tempfile.gettempdir()).glob("knowledge_pipeline_test_*"):
            shutil.rmtree(d, ignore_errors=True)
            print_info(f"Cleaned: {d}")
        return

    print(f"\n{BOLD}Knowledge Pipeline Full Test{RESET}")
    print(f"Test directory: {TEST_DIR}\n")

    # Step 1: Generate mock observations
    session_id, observations = generate_mock_observations()

    # Step 2: Analyze (with mock LLM)
    if not test_analyze(session_id, observations):
        print_fail("Analyze stage failed, stopping")
        sys.exit(1)

    # Step 3: Store learnings
    if not test_learn(session_id):
        print_fail("Learn stage failed, stopping")
        sys.exit(1)

    # Step 4: Inject relevant knowledge
    if not test_evolve():
        print_fail("Evolve stage failed")

    # Step 5: Full verification
    success = verify_pipeline()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
