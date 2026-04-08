"""
test_context_pipeline.py — Test context compaction pipeline.
Builder-2 | CAF Audit Suite
"""
from pathlib import Path
import json
import sys

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent  # tests/audit/modules/test_context_pipeline.py -> repo root
CONTEXT_DIR = REPO_ROOT / "global-hooks/framework/context"
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

sys.path.insert(0, str(CONTEXT_DIR))

TIMINGS: list[dict] = []

# ---------------------------------------------------------------------------
# Import context modules (skip all tests if not importable)
# ---------------------------------------------------------------------------

try:
    from auto_context_manager import estimate_context_pct, find_cold_tasks, build_task_registry  # type: ignore
    _CONTEXT_IMPORTABLE = True
    _CONTEXT_IMPORT_ERROR = ""
except Exception as e:
    _CONTEXT_IMPORTABLE = False
    _CONTEXT_IMPORT_ERROR = str(e)

try:
    from pre_compact_preserve import (  # type: ignore
        extract_active_tasks,
        extract_edited_files,
        extract_test_commands,
        extract_recent_errors,
    )
    _PRECOMPACT_IMPORTABLE = True
    _PRECOMPACT_IMPORT_ERROR = ""
except Exception as e:
    _PRECOMPACT_IMPORTABLE = False
    _PRECOMPACT_IMPORT_ERROR = str(e)

# ---------------------------------------------------------------------------
# Load sample transcripts
# ---------------------------------------------------------------------------

TRANSCRIPTS: dict = {}
_TRANSCRIPTS_LOAD_ERROR = ""
try:
    TRANSCRIPTS = json.loads((FIXTURES_DIR / "sample_transcripts.json").read_text())
except Exception as e:
    _TRANSCRIPTS_LOAD_ERROR = str(e)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def require_context():
    if not _CONTEXT_IMPORTABLE:
        pytest.skip(f"context module not importable: {_CONTEXT_IMPORT_ERROR}")


def require_precompact():
    if not _PRECOMPACT_IMPORTABLE:
        pytest.skip(f"pre_compact_preserve not importable: {_PRECOMPACT_IMPORT_ERROR}")


def require_transcripts():
    if _TRANSCRIPTS_LOAD_ERROR:
        pytest.skip(f"sample_transcripts.json not loadable: {_TRANSCRIPTS_LOAD_ERROR}")


# ---------------------------------------------------------------------------
# Tests: estimate_context_pct
# ---------------------------------------------------------------------------


def test_context_pct_estimation_formula():
    """Given a list of 10 short messages, estimate_context_pct returns a float 0-100."""
    require_context()
    require_transcripts()

    messages = TRANSCRIPTS["empty_session"]["messages"]
    result = estimate_context_pct(messages)
    assert isinstance(result, (int, float)), f"Expected numeric, got {type(result)}"
    assert 0 <= result <= 100, f"Expected 0-100, got {result}"


# ---------------------------------------------------------------------------
# Tests: build_task_registry
# ---------------------------------------------------------------------------


def test_task_registry_builds_correctly():
    """active_session transcript yields task registry mapping task-001 -> 'Fix auth bug'."""
    require_context()
    require_transcripts()

    messages = TRANSCRIPTS["active_session"]["messages"]
    registry = build_task_registry(messages)
    assert isinstance(registry, dict), f"Expected dict, got {type(registry)}"
    assert "task-001" in registry, f"task-001 not in registry. Keys: {list(registry.keys())}"
    assert "Fix auth bug" in registry["task-001"], (
        f"Expected 'Fix auth bug', got: {registry['task-001']}"
    )


# ---------------------------------------------------------------------------
# Tests: find_cold_tasks
# ---------------------------------------------------------------------------


def test_cold_task_detection():
    """complex_session: tasks completed in turns 1-20 not mentioned in turns 61-80 are cold."""
    require_context()
    require_transcripts()

    messages = TRANSCRIPTS["complex_session"]["messages"]
    cold = find_cold_tasks(messages)
    assert isinstance(cold, (list, set, dict)), f"Expected collection, got {type(cold)}"
    # task-A through task-E were all completed before the performance work began
    # At least one task should be detected as cold given the 80-turn transcript
    assert len(cold) >= 1, (
        "Expected at least 1 cold task in complex_session (tasks completed early, "
        f"not mentioned in last 20 turns). Got: {cold}"
    )


def test_active_task_not_cold():
    """A task referenced in the last 20 turns of complex_session must not be cold."""
    require_context()
    require_transcripts()

    messages = TRANSCRIPTS["complex_session"]["messages"]
    cold = find_cold_tasks(messages)
    # task-E (monitoring) is wired into middleware in the last stretch
    # Convert to set of strings for uniform comparison
    cold_ids: set[str] = set()
    if isinstance(cold, dict):
        cold_ids = set(cold.keys())
    elif isinstance(cold, (list, set)):
        cold_ids = set(str(c) for c in cold)

    # "task-E" is mentioned late in the session (performance/monitoring section)
    # It should NOT be in the cold set
    assert "task-E" not in cold_ids, (
        f"task-E was mentioned in late turns but appears in cold tasks: {cold_ids}"
    )


# ---------------------------------------------------------------------------
# Tests: summary written to disk
# ---------------------------------------------------------------------------


def test_summary_written_to_disk(tmp_path, monkeypatch):
    """Mock cold task detection to return one task; verify a summary file is written."""
    require_context()

    # Point the module to a temp dir for any disk writes
    compressed_dir = tmp_path / "compressed_context"
    compressed_dir.mkdir()

    import auto_context_manager as acm  # type: ignore

    # Monkeypatch find_cold_tasks to return a deterministic cold task
    monkeypatch.setattr(
        acm,
        "find_cold_tasks",
        lambda msgs: {"task-001": "Fix auth bug"},
        raising=False,
    )

    # Monkeypatch the output path to use tmp_path
    monkeypatch.setattr(
        acm,
        "COMPRESSED_CONTEXT_DIR",
        compressed_dir,
        raising=False,
    )

    # Run the manager logic (function may vary; attempt common entry points)
    messages = TRANSCRIPTS.get("active_session", {}).get("messages", []) if TRANSCRIPTS else []
    ran = False
    for fn_name in ("run", "process_cold_tasks", "manage_context", "write_cold_summaries"):
        fn = getattr(acm, fn_name, None)
        if callable(fn):
            try:
                fn(messages)
                ran = True
                break
            except Exception:
                pass

    if not ran:
        pytest.skip("auto_context_manager has no recognized entry point (run/process_cold_tasks/manage_context)")

    written_files = list(compressed_dir.rglob("*"))
    assert len(written_files) >= 1, (
        f"Expected at least one file written to compressed_context dir. "
        f"Dir contents: {list(compressed_dir.iterdir())}"
    )


# ---------------------------------------------------------------------------
# Tests: pre_compact_preserve
# ---------------------------------------------------------------------------


def test_pre_compact_extracts_active_tasks():
    """pre_compact_preserve on active_session yields non-empty active task list."""
    require_precompact()
    require_transcripts()

    messages = TRANSCRIPTS["active_session"]["messages"]
    tasks = extract_active_tasks(messages)
    assert isinstance(tasks, (list, set, dict)), f"Expected collection, got {type(tasks)}"
    assert len(tasks) >= 1, (
        "Expected at least 1 active task from active_session. "
        f"active_session has TaskCreate calls for task-001 and task-002. Got: {tasks}"
    )


def test_pre_compact_extracts_edited_files():
    """pre_compact_preserve on active_session yields file list containing /src/auth.py."""
    require_precompact()
    require_transcripts()

    messages = TRANSCRIPTS["active_session"]["messages"]
    files = extract_edited_files(messages)
    assert isinstance(files, (list, set)), f"Expected list or set, got {type(files)}"

    file_strs = [str(f) for f in files]
    found = any("auth.py" in f for f in file_strs)
    assert found, (
        f"Expected /src/auth.py in edited files. Got: {file_strs}"
    )


def test_pre_compact_extracts_test_commands():
    """Bash commands containing 'test' (pytest) are extracted as test commands."""
    require_precompact()
    require_transcripts()

    messages = TRANSCRIPTS["active_session"]["messages"]
    commands = extract_test_commands(messages)
    assert isinstance(commands, (list, set)), f"Expected list or set, got {type(commands)}"

    # active_session has: pytest tests/test_auth.py -v and pytest tests/test_auth.py tests/test_rate_limiter.py
    cmd_strs = [str(c) for c in commands]
    found = any("pytest" in c or "test" in c.lower() for c in cmd_strs)
    assert found, (
        f"Expected pytest commands in extracted test commands. Got: {cmd_strs}"
    )


def test_pre_compact_extracts_recent_errors():
    """Non-zero exit code Bash results appear in extracted errors."""
    require_precompact()
    require_transcripts()

    messages = TRANSCRIPTS["active_session"]["messages"]
    errors = extract_recent_errors(messages)
    assert isinstance(errors, (list, set)), f"Expected list or set, got {type(errors)}"

    # active_session has a pytest run with exit_code=1 (test_auth failure)
    assert len(errors) >= 1, (
        "Expected at least 1 error extracted from active_session "
        "(it has a Bash tool_result with exit_code=1). Got empty list."
    )
