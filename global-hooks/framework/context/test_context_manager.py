#!/usr/bin/env python3
"""
Test suite for auto_context_manager.py and pre_compact_preserve.py

Tests the two-hook context compaction pipeline.
"""

import json
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add context dir to path
sys.path.insert(0, str(Path(__file__).parent))


# ─── Helper: build a fake JSONL transcript ───────────────────────────

def make_transcript(messages: list[dict], path: str):
    """Write a list of message dicts as JSONL."""
    with open(path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")


def wrap(role: str, content) -> dict:
    """Wrap a message in the Claude Code JSONL format."""
    if isinstance(content, str):
        content = [{"type": "text", "text": content}]
    return {"message": {"role": role, "content": content}}


def tool_use(tool_use_id: str, name: str, inp: dict) -> dict:
    return wrap("assistant", [{"type": "tool_use", "id": tool_use_id, "name": name, "input": inp}])


def tool_result(tool_use_id: str, text: str) -> dict:
    return wrap("user", [{"type": "tool_result", "tool_use_id": tool_use_id, "content": [{"type": "text", "text": text}]}])


# ─── Tests ───────────────────────────────────────────────────────────

def test_transcript_key_fix():
    """
    The critical regression test: count_assistant_turns must read the
    message wrapper correctly. The old code used msg.get("role") which
    always returned None — so the hook never fired.
    """
    from auto_context_manager import count_assistant_turns, parse_transcript

    msgs = [
        wrap("assistant", "hello"),
        wrap("user", "world"),
        wrap("assistant", "hi"),
        wrap("user", "ok"),
        wrap("assistant", "done"),
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for m in msgs:
            f.write(json.dumps(m) + "\n")
        tmppath = f.name

    try:
        loaded = parse_transcript(tmppath)
        turns = count_assistant_turns(loaded)
        assert turns == 3, f"Expected 3 assistant turns, got {turns} (key bug not fixed)"
        print("✅ test_transcript_key_fix passed")
    finally:
        os.unlink(tmppath)


def test_task_registry_correlation():
    """
    build_task_registry must correctly correlate TaskCreate tool_use_id
    with tool_result to get real task_id → subject mapping.
    """
    from auto_context_manager import build_task_registry, parse_transcript

    msgs = [
        tool_use("toolu_001", "TaskCreate", {"subject": "Implement OAuth2"}),
        tool_result("toolu_001", '{"taskId": "1", "subject": "Implement OAuth2"}'),
        tool_use("toolu_002", "TaskCreate", {"subject": "Fix auth middleware"}),
        tool_result("toolu_002", '{"taskId": "2"}'),
        tool_use("toolu_003", "TaskUpdate", {"taskId": "1", "status": "completed"}),
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for m in msgs:
            f.write(json.dumps(m) + "\n")
        tmppath = f.name

    try:
        loaded = parse_transcript(tmppath)
        registry = build_task_registry(loaded)

        assert "1" in registry, f"Task 1 missing from registry: {registry}"
        assert "2" in registry, f"Task 2 missing from registry: {registry}"
        assert registry["1"]["subject"] == "Implement OAuth2"
        assert registry["2"]["subject"] == "Fix auth middleware"
        assert registry["1"]["status"] == "completed"
        assert registry["2"]["status"] == "pending"

        print("✅ test_task_registry_correlation passed")
    finally:
        os.unlink(tmppath)


def test_cold_task_detection():
    """
    find_cold_tasks must return completed tasks not referenced in
    TURNS_UNTIL_COLD turns. Recent tasks and active tasks must be excluded.
    """
    from auto_context_manager import (
        build_task_registry, find_cold_tasks, parse_transcript
    )

    # Task 1: created at turn 1, completed at turn 5, 25 turns ago → cold
    # Task 2: created at turn 30, not completed yet → not cold
    msgs = [
        tool_use("toolu_001", "TaskCreate", {"subject": "Old OAuth2 task"}),
        tool_result("toolu_001", '{"taskId": "1"}'),
        *[wrap("assistant", f"working {i}") for i in range(3)],
        tool_use("toolu_002", "TaskUpdate", {"taskId": "1", "status": "completed"}),
        # 25 turns of unrelated work
        *[wrap("assistant", f"unrelated turn {i}") for i in range(25)],
        tool_use("toolu_003", "TaskCreate", {"subject": "Current active task"}),
        tool_result("toolu_003", '{"taskId": "2"}'),
        wrap("assistant", "working on active task"),
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for m in msgs:
            f.write(json.dumps(m) + "\n")
        tmppath = f.name

    try:
        from auto_context_manager import count_assistant_turns
        loaded = parse_transcript(tmppath)
        current_turn = count_assistant_turns(loaded)
        registry = build_task_registry(loaded)
        cold = find_cold_tasks(loaded, registry, current_turn)

        cold_subjects = [t["subject"] for t in cold]
        assert "Old OAuth2 task" in cold_subjects, \
            f"Completed old task should be cold: {cold_subjects}"
        assert "Current active task" not in cold_subjects, \
            f"Active task should not be cold: {cold_subjects}"

        print(f"✅ test_cold_task_detection passed ({len(cold)} cold tasks)")
    finally:
        os.unlink(tmppath)


def test_segment_content_extraction():
    """
    extract_segment_content must capture files modified, commands run,
    and key outcomes within a task's turn range.
    """
    from auto_context_manager import extract_segment_content, parse_transcript

    msgs = [
        wrap("assistant", "starting OAuth2 work"),
        tool_use("toolu_e1", "Edit", {"file_path": "/src/auth/oauth2.py", "old_string": "x", "new_string": "y"}),
        tool_use("toolu_b1", "Bash", {"command": "pytest tests/test_auth.py -v"}),
        wrap("assistant", "decided to use PKCE flow for public clients"),
        wrap("assistant", "fixed JWT validation issue"),
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for m in msgs:
            f.write(json.dumps(m) + "\n")
        tmppath = f.name

    try:
        loaded = parse_transcript(tmppath)
        content = extract_segment_content(loaded, start_turn=0, end_turn=10)

        assert "/src/auth/oauth2.py" in content["files_modified"], \
            f"Expected file in modified: {content['files_modified']}"
        assert any("pytest" in cmd for cmd in content["commands_run"]), \
            f"Expected pytest in commands: {content['commands_run']}"
        assert any("PKCE" in o for o in content["key_outcomes"]), \
            f"Expected PKCE decision in outcomes: {content['key_outcomes']}"

        print("✅ test_segment_content_extraction passed")
    finally:
        os.unlink(tmppath)


def test_summary_write_and_load():
    """
    write_summary must persist to disk and load_session_summaries
    must return it for the correct session_id only.
    """
    from auto_context_manager import write_summary, load_session_summaries, summary_exists, SUMMARY_DIR

    session_id = "test-session-xxxxxxxx"
    task = {
        "task_id": "99",
        "subject": "Test summary persistence",
        "start_turn": 1,
        "end_turn": 10,
        "status": "completed",
    }
    content = {
        "files_modified": ["/test/foo.py"],
        "commands_run": ["pytest tests/"],
        "key_outcomes": ["chose approach A over B"],
        "errors_resolved": [],
    }

    # Clean up any leftover test summary
    import hashlib
    safe_id = hashlib.md5(f"{session_id}:99".encode()).hexdigest()[:12]
    test_file = SUMMARY_DIR / f"{safe_id}.json"
    if test_file.exists():
        test_file.unlink()

    try:
        assert not summary_exists(session_id, "99")

        write_summary(session_id, task, content)
        assert summary_exists(session_id, "99"), "Summary should exist after write"

        summaries = load_session_summaries(session_id)
        assert len(summaries) >= 1, "Should load at least 1 summary"
        subjects = [s["subject"] for s in summaries]
        assert "Test summary persistence" in subjects, \
            f"Expected subject in summaries: {subjects}"

        # Different session_id should not see it
        other_summaries = load_session_summaries("other-session-yyyyyyy")
        other_subjects = [s["subject"] for s in other_summaries]
        assert "Test summary persistence" not in other_subjects, \
            "Other session should not see this summary"

        print("✅ test_summary_write_and_load passed")
    finally:
        if test_file.exists():
            test_file.unlink()


def test_pre_compact_injects_summaries():
    """
    pre_compact_preserve must load pre-computed summaries and include
    them in the preservation block output.
    """
    from pre_compact_preserve import extract_key_context, build_preservation_instructions
    from auto_context_manager import write_summary, SUMMARY_DIR
    import hashlib

    session_id = "test-precompact-zzzzz"
    task = {
        "task_id": "88",
        "subject": "OAuth2 login flow",
        "start_turn": 1,
        "end_turn": 8,
        "status": "completed",
    }
    content = {
        "files_modified": ["/src/auth.py"],
        "commands_run": [],
        "key_outcomes": ["used PKCE flow"],
        "errors_resolved": [],
    }

    safe_id = hashlib.md5(f"{session_id}:88".encode()).hexdigest()[:12]
    test_file = SUMMARY_DIR / f"{safe_id}.json"
    if test_file.exists():
        test_file.unlink()

    # Also need a minimal transcript
    msgs = [
        tool_use("toolu_x", "Edit", {"file_path": "/src/foo.py", "old_string": "a", "new_string": "b"}),
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for m in msgs:
            f.write(json.dumps(m) + "\n")
        tmppath = f.name

    try:
        write_summary(session_id, task, content)

        from pre_compact_preserve import parse_transcript as pcp_parse
        loaded = pcp_parse(tmppath)
        ctx = extract_key_context(loaded, session_id)

        assert len(ctx["precomputed_summaries"]) >= 1, \
            f"Expected pre-computed summaries, got {ctx['precomputed_summaries']}"

        block = build_preservation_instructions(ctx, "auto")
        assert "PRE-COMPUTED TASK SUMMARIES" in block, \
            "Preservation block should include pre-computed summaries section"
        assert "OAuth2 login flow" in block, \
            "Task subject should appear in preservation block"

        print("✅ test_pre_compact_injects_summaries passed")
    finally:
        os.unlink(tmppath)
        if test_file.exists():
            test_file.unlink()


def test_compression_helper():
    """Test compress_segments.py helper (unchanged)."""
    import compress_segments as cs

    with tempfile.TemporaryDirectory() as tmpdir:
        original_get_l2 = cs.get_l2_storage_dir
        temp_l2 = Path(tmpdir) / "l2_storage"
        temp_l2.mkdir()
        cs.get_l2_storage_dir = lambda: temp_l2

        try:
            storage_path = cs.save_compressed_segment(
                segment_id="test_seg_1",
                topic="Test OAuth2 implementation",
                compressed_content="Implemented OAuth2 with JWT tokens...",
                key_decisions=["Used JWT", "1-hour expiry"],
                key_files=["src/auth/oauth2.ts"],
                original_tokens=2400,
                compressed_tokens=350,
                metadata={"start_turn": 10, "end_turn": 30},
            )

            assert Path(storage_path).exists(), f"Storage file not created: {storage_path}"

            with open(storage_path) as f:
                data = json.load(f)

            assert data["segment_id"] == "test_seg_1"
            assert data["topic"] == "Test OAuth2 implementation"
            assert data["original_tokens"] == 2400
            assert data["compressed_tokens"] == 350
            assert data["compression_ratio"] == 6.9
            assert len(data["key_decisions"]) == 2
            assert len(data["key_files"]) == 1

            print("✅ test_compression_helper passed")
        finally:
            cs.get_l2_storage_dir = original_get_l2


# ─── Runner ──────────────────────────────────────────────────────────

def run_all_tests():
    print("\n🧪 Running Context Manager Tests...\n")
    tests = [
        test_transcript_key_fix,
        test_task_registry_correlation,
        test_cold_task_detection,
        test_segment_content_extraction,
        test_summary_write_and_load,
        test_pre_compact_injects_summaries,
        test_compression_helper,
    ]
    passed = failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {test.__name__} error: {e}")
            failed += 1
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
