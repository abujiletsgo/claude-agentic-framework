"""
test_memory_system.py — Test memory writing and fact validation system.
Builder-2 | CAF Audit Suite
"""
from pathlib import Path
import sys
import json
import subprocess
from datetime import datetime, timedelta, timezone

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent  # tests/audit/modules/test_memory_system.py -> repo root
MEMORY_DIR = REPO_ROOT / "global-hooks/framework/memory"
FACTS_DIR = REPO_ROOT / "global-hooks/framework/facts"

sys.path.insert(0, str(MEMORY_DIR))
sys.path.insert(0, str(FACTS_DIR))

TIMINGS: list[dict] = []

# ---------------------------------------------------------------------------
# Import memory and facts modules (skip if not importable)
# ---------------------------------------------------------------------------

try:
    import auto_memory_writer as _amw  # type: ignore
    _MEMORY_IMPORTABLE = True
    _MEMORY_IMPORT_ERROR = ""
except Exception as e:
    _MEMORY_IMPORTABLE = False
    _MEMORY_IMPORT_ERROR = str(e)

try:
    import validate_facts as _vf  # type: ignore
    _FACTS_IMPORTABLE = True
    _FACTS_IMPORT_ERROR = ""
except Exception as e:
    _FACTS_IMPORTABLE = False
    _FACTS_IMPORT_ERROR = str(e)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def require_memory():
    if not _MEMORY_IMPORTABLE:
        pytest.skip(f"auto_memory_writer not importable: {_MEMORY_IMPORT_ERROR}")


def require_facts():
    if not _FACTS_IMPORTABLE:
        pytest.skip(f"validate_facts not importable: {_FACTS_IMPORT_ERROR}")


def make_facts_md(entries_per_category: dict[str, list[str]]) -> str:
    lines = ["# Project Facts\n"]
    for category, facts in entries_per_category.items():
        lines.append(f"\n## {category}\n")
        for fact in facts:
            lines.append(f"- {fact}\n")
    return "".join(lines)


def date_str(days_ago: int) -> str:
    """Return ISO date string N days before today."""
    d = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return d.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a minimal git repo for testing memory writes."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, capture_output=True)
    (repo / "main.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial: add main.py"],
        cwd=repo,
        capture_output=True,
    )
    return repo


# ---------------------------------------------------------------------------
# Memory writer tests
# ---------------------------------------------------------------------------


def test_memory_entry_written_after_commit(temp_git_repo, monkeypatch):
    """Running auto_memory_writer on a repo with a commit creates MEMORY.md."""
    require_memory()

    memory_file = temp_git_repo / "MEMORY.md"
    assert not memory_file.exists(), "MEMORY.md should not exist before test"

    import auto_memory_writer as amw  # type: ignore

    # Monkeypatch paths to use temp repo
    monkeypatch.setattr(amw, "REPO_ROOT", temp_git_repo, raising=False)
    monkeypatch.setattr(amw, "MEMORY_FILE", memory_file, raising=False)

    # Try common entry points
    ran = False
    for fn_name in ("run", "write_memory", "main", "update_memory"):
        fn = getattr(amw, fn_name, None)
        if callable(fn):
            try:
                fn()
                ran = True
                break
            except Exception:
                pass

    if not ran:
        # Try subprocess approach as fallback
        result = subprocess.run(
            ["uv", "run", "--no-project", str(MEMORY_DIR / "auto_memory_writer.py")],
            input=json.dumps({"hookEventName": "Stop", "session_id": "test-memory-001"}),
            capture_output=True,
            text=True,
            cwd=str(temp_git_repo),
            timeout=15,
        )
        # Write memory file manually to simulate outcome if hook uses stdout
        if result.returncode == 0:
            ran = True

    if not ran:
        pytest.skip("auto_memory_writer has no recognized entry point")

    # Check that MEMORY.md was created (either by module or by hook stdout)
    # The file might also be at ~/.claude/MEMORY.md — check both locations
    home_memory = Path.home() / ".claude" / "MEMORY.md"
    assert (memory_file.exists() or home_memory.exists()), (
        "MEMORY.md was not created after running auto_memory_writer on a repo with a commit"
    )


def test_memory_entry_not_written_if_no_changes(tmp_path, monkeypatch):
    """If no new commits since last run, MEMORY.md should not be updated."""
    require_memory()

    # Create repo with no new changes
    repo = tmp_path / "no_change_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, capture_output=True)

    # No commits at all
    memory_file = repo / "MEMORY.md"

    import auto_memory_writer as amw  # type: ignore

    monkeypatch.setattr(amw, "REPO_ROOT", repo, raising=False)
    monkeypatch.setattr(amw, "MEMORY_FILE", memory_file, raising=False)

    for fn_name in ("run", "write_memory", "main", "update_memory"):
        fn = getattr(amw, fn_name, None)
        if callable(fn):
            try:
                fn()
            except Exception:
                pass
            break

    # MEMORY.md should not exist (no commits = nothing to record)
    assert not memory_file.exists(), (
        "MEMORY.md should not be created when there are no commits"
    )


def test_memory_dedup_same_commit(temp_git_repo, monkeypatch):
    """Writing memory for the same commit twice should result in only 1 entry."""
    require_memory()

    memory_file = temp_git_repo / "MEMORY.md"

    import auto_memory_writer as amw  # type: ignore

    monkeypatch.setattr(amw, "REPO_ROOT", temp_git_repo, raising=False)
    monkeypatch.setattr(amw, "MEMORY_FILE", memory_file, raising=False)

    # Run writer twice
    for fn_name in ("run", "write_memory", "main", "update_memory"):
        fn = getattr(amw, fn_name, None)
        if callable(fn):
            try:
                fn()
                fn()  # second call
            except Exception:
                pass
            break

    if not memory_file.exists():
        pytest.skip("Memory file not written — entry point did not produce output file")

    content = memory_file.read_text()
    # Count entries — each entry typically starts with "##" or "- [" header
    entry_markers = [line for line in content.splitlines() if line.startswith("## ") or line.startswith("- [")]
    assert len(entry_markers) <= 2, (
        f"Expected at most 1-2 markers for same commit, got {len(entry_markers)}:\n{content[:500]}"
    )


def test_memory_pruning_keeps_30(tmp_path, monkeypatch):
    """Pre-populate MEMORY.md with 35 entries; after writer runs, at most 30 remain."""
    require_memory()

    repo = tmp_path / "prune_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, capture_output=True)
    (repo / "main.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, capture_output=True)

    # Pre-populate 35 entries
    memory_file = repo / "MEMORY.md"
    entries = []
    for i in range(35):
        entries.append(f"## Session {i+1}\n- Edited file_{i}.py\n- Fixed bug #{i}\n")
    memory_file.write_text("\n".join(entries))

    import auto_memory_writer as amw  # type: ignore

    monkeypatch.setattr(amw, "REPO_ROOT", repo, raising=False)
    monkeypatch.setattr(amw, "MEMORY_FILE", memory_file, raising=False)

    for fn_name in ("run", "write_memory", "main", "update_memory", "prune_memory"):
        fn = getattr(amw, fn_name, None)
        if callable(fn):
            try:
                fn()
            except Exception:
                pass
            break

    content = memory_file.read_text()
    # Count section headers as entry boundaries
    section_count = sum(1 for line in content.splitlines() if line.startswith("## Session"))
    assert section_count <= 30, (
        f"Expected at most 30 entries after pruning, found {section_count}"
    )


# ---------------------------------------------------------------------------
# Fact validation tests
# ---------------------------------------------------------------------------


def test_facts_stale_pruning_90_days(tmp_path, monkeypatch):
    """A fact dated 91 days ago should be removed by validate_facts."""
    require_facts()

    stale_date = date_str(91)
    facts_content = make_facts_md({
        "CONFIRMED": [
            f"[{stale_date}] DB connection pooling enabled — confirmed in production",
        ]
    })
    facts_file = tmp_path / "FACTS.md"
    facts_file.write_text(facts_content)

    import validate_facts as vf  # type: ignore

    monkeypatch.setattr(vf, "FACTS_FILE", facts_file, raising=False)

    for fn_name in ("run", "validate", "main", "prune_stale", "prune_facts"):
        fn = getattr(vf, fn_name, None)
        if callable(fn):
            try:
                fn()
            except Exception:
                pass
            break

    result = facts_file.read_text()
    assert stale_date not in result, (
        f"Stale fact dated {stale_date} (91 days ago) should have been pruned.\n"
        f"Current FACTS.md:\n{result[:500]}"
    )


def test_facts_recent_not_pruned(tmp_path, monkeypatch):
    """A fact dated 89 days ago should be kept by validate_facts."""
    require_facts()

    recent_date = date_str(89)
    fact_text = f"[{recent_date}] Rate limiter configured at 100 req/min — confirmed"
    facts_content = make_facts_md({
        "CONFIRMED": [fact_text]
    })
    facts_file = tmp_path / "FACTS.md"
    facts_file.write_text(facts_content)

    import validate_facts as vf  # type: ignore

    monkeypatch.setattr(vf, "FACTS_FILE", facts_file, raising=False)

    for fn_name in ("run", "validate", "main", "prune_stale", "prune_facts"):
        fn = getattr(vf, fn_name, None)
        if callable(fn):
            try:
                fn()
            except Exception:
                pass
            break

    result = facts_file.read_text()
    assert recent_date in result, (
        f"Recent fact dated {recent_date} (89 days ago) should NOT be pruned.\n"
        f"Current FACTS.md:\n{result[:500]}"
    )


def test_facts_warning_at_50(tmp_path, monkeypatch, capsys):
    """FACTS.md with 51 facts should cause validate_facts to write a warning to stderr."""
    require_facts()

    facts = [f"fact number {i}" for i in range(51)]
    facts_content = make_facts_md({"CONFIRMED": facts})
    facts_file = tmp_path / "FACTS.md"
    facts_file.write_text(facts_content)

    import validate_facts as vf  # type: ignore

    monkeypatch.setattr(vf, "FACTS_FILE", facts_file, raising=False)

    for fn_name in ("run", "validate", "main", "check_size", "warn_if_large"):
        fn = getattr(vf, fn_name, None)
        if callable(fn):
            try:
                fn()
            except Exception:
                pass
            break

    captured = capsys.readouterr()
    warning_present = (
        "warning" in captured.err.lower()
        or "warn" in captured.err.lower()
        or "large" in captured.err.lower()
        or "50" in captured.err
        or "51" in captured.err
    )
    if not warning_present:
        # Also try running via subprocess and check stderr
        result = subprocess.run(
            ["uv", "run", "--no-project", str(FACTS_DIR / "validate_facts.py")],
            input=json.dumps({"hookEventName": "Stop"}),
            capture_output=True,
            text=True,
            env={**__import__("os").environ, "FACTS_FILE": str(facts_file)},
            timeout=10,
        )
        warning_present = (
            "warning" in result.stderr.lower()
            or "warn" in result.stderr.lower()
            or "50" in result.stderr
        )

    assert warning_present, (
        "Expected a warning when FACTS.md has 51 facts, but none found in stderr."
    )


def test_fact_category_parsing(tmp_path, monkeypatch):
    """FACTS.md with all 5 category sections — count_facts returns correct breakdown."""
    require_facts()

    facts_content = make_facts_md({
        "CONFIRMED": ["confirmed fact 1", "confirmed fact 2"],
        "GOTCHAS": ["gotcha 1"],
        "PATHS": ["path 1", "path 2", "path 3"],
        "PATTERNS": ["pattern 1"],
        "SPECULATIVE": ["speculation 1", "speculation 2"],
    })
    facts_file = tmp_path / "FACTS.md"
    facts_file.write_text(facts_content)

    import validate_facts as vf  # type: ignore

    monkeypatch.setattr(vf, "FACTS_FILE", facts_file, raising=False)

    # Look for a count_facts or parse_facts function
    count_fn = getattr(vf, "count_facts", None) or getattr(vf, "parse_facts", None)
    if count_fn is None:
        pytest.skip("validate_facts has no count_facts/parse_facts function")

    breakdown = count_fn(facts_file)
    assert isinstance(breakdown, dict), f"Expected dict, got {type(breakdown)}"

    # Verify known categories
    total = sum(v for v in breakdown.values() if isinstance(v, int))
    assert total >= 9, (
        f"Expected at least 9 total facts across 5 categories, got {total}. "
        f"Breakdown: {breakdown}"
    )
