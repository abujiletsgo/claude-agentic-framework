"""
CAF Audit — orch-shared IPC Script Tests
=========================================
Tests the bin/orch-shared Bash IPC hub for multi-agent orchestration.
Covers init, domain registry, working memory, broadcast, events, and merge-results.

Run standalone:
  uv run pytest tests/audit/modules/test_orchestration.py -v
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent
ORCH_SCRIPT = REPO_ROOT / "bin" / "orch-shared"

# Use a test-specific ORCH_BASE, injected via CAF_ORCH_DIR env var
ORCH_BASE = Path("/tmp/caf_orch_test")

TIMINGS: list[dict] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_orch_id() -> str:
    """Return a unique orch_id safe for use in /tmp/caf_orch/."""
    return "test_" + uuid.uuid4().hex[:8]


def run_orch(*args: str, orch_id: str) -> subprocess.CompletedProcess:
    """Invoke bin/orch-shared with the given subcommand args."""
    return subprocess.run(
        ["python3", str(ORCH_SCRIPT), *args],
        capture_output=True,
        text=True,
        env={**os.environ, "CAF_ORCH_DIR": str(ORCH_BASE)},
    )


def cleanup_orch(orch_id: str) -> None:
    """Remove the orch job dir from /tmp/caf_orch/."""
    job_dir = ORCH_BASE / orch_id
    if job_dir.exists():
        shutil.rmtree(str(job_dir))


def record_timing(test_name: str, elapsed_ms: float) -> None:
    TIMINGS.append({"test": test_name, "ms": round(elapsed_ms, 2)})


# ---------------------------------------------------------------------------
# Skip guard
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    not ORCH_SCRIPT.exists(),
    reason="bin/orch-shared not found",
)


# ---------------------------------------------------------------------------
# TestOrchInit
# ---------------------------------------------------------------------------

class TestOrchInit:
    """Tests for the init subcommand."""

    @pytest.mark.timeout(10)
    def test_init_creates_directory_structure(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            result = run_orch("init", orch_id, orch_id=orch_id)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_init_creates_directory_structure", elapsed_ms)

            assert result.returncode == 0, f"init failed: {result.stderr}"
            job_dir = ORCH_BASE / orch_id
            assert job_dir.exists(), f"job dir not created: {job_dir}"
        finally:
            cleanup_orch(orch_id)

    @pytest.mark.timeout(10)
    def test_init_creates_shared_subdir(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            result = run_orch("init", orch_id, orch_id=orch_id)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_init_creates_shared_subdir", elapsed_ms)

            assert result.returncode == 0, f"init failed: {result.stderr}"
            shared = ORCH_BASE / orch_id / "shared"
            assert shared.exists(), f"shared/ dir not created: {shared}"
            assert (shared / "domains.json").exists(), "domains.json not seeded"
            assert (shared / "working_memory.jsonl").exists(), "working_memory.jsonl not seeded"
            assert (shared / "discoveries.jsonl").exists(), "discoveries.jsonl not seeded"
        finally:
            cleanup_orch(orch_id)

    @pytest.mark.timeout(10)
    def test_init_writes_meta_json(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            result = run_orch("init", orch_id, orch_id=orch_id)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_init_writes_meta_json", elapsed_ms)

            assert result.returncode == 0, f"init failed: {result.stderr}"
            meta_path = ORCH_BASE / orch_id / "meta.json"
            assert meta_path.exists(), f"meta.json not created: {meta_path}"
            meta = json.loads(meta_path.read_text())
            assert meta.get("orch_id") == orch_id, (
                f"meta.json orch_id mismatch: {meta}"
            )
            assert "cwd" in meta, f"meta.json missing 'cwd': {meta}"
        finally:
            cleanup_orch(orch_id)

    @pytest.mark.timeout(10)
    def test_init_idempotent(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            # First init
            r1 = run_orch("init", orch_id, orch_id=orch_id)
            assert r1.returncode == 0, f"first init failed: {r1.stderr}"

            # Write a sentinel into working_memory.jsonl to confirm it is not wiped
            mem_file = ORCH_BASE / orch_id / "shared" / "working_memory.jsonl"
            mem_file.write_text('{"lead":"sentinel","summary":"preserved"}\n')

            # Second init — must not overwrite existing files
            r2 = run_orch("init", orch_id, orch_id=orch_id)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_init_idempotent", elapsed_ms)

            assert r2.returncode == 0, f"second init failed: {r2.stderr}"
            contents = mem_file.read_text()
            assert "sentinel" in contents, (
                "Second init wiped working_memory.jsonl — must be idempotent"
            )
        finally:
            cleanup_orch(orch_id)


# ---------------------------------------------------------------------------
# TestDomainRegistry
# ---------------------------------------------------------------------------

class TestDomainRegistry:
    """Tests for register-domain and check-domain subcommands."""

    @pytest.mark.timeout(10)
    def test_register_domain_creates_domains_json(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            result = run_orch(
                "register-domain", orch_id, "frontend-lead", "src/components/**",
                orch_id=orch_id,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_register_domain_creates_domains_json", elapsed_ms)

            assert result.returncode == 0, f"register-domain failed: {result.stderr}"
            domains_path = ORCH_BASE / orch_id / "shared" / "domains.json"
            assert domains_path.exists(), "domains.json not created after register-domain"
        finally:
            cleanup_orch(orch_id)

    @pytest.mark.timeout(10)
    def test_register_domain_records_owner(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            run_orch(
                "register-domain", orch_id, "backend-lead", "src/api/**",
                orch_id=orch_id,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_register_domain_records_owner", elapsed_ms)

            domains_path = ORCH_BASE / orch_id / "shared" / "domains.json"
            domains = json.loads(domains_path.read_text())
            assert "src/api/**" in domains, f"glob not in domains: {domains}"
            assert domains["src/api/**"] == "backend-lead", (
                f"owner mismatch: expected 'backend-lead', got {domains['src/api/**']!r}"
            )
        finally:
            cleanup_orch(orch_id)

    @pytest.mark.timeout(10)
    def test_check_domain_available_before_register(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            result = run_orch(
                "check-domain", orch_id, "src/unclaimed/file.py",
                orch_id=orch_id,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_check_domain_available_before_register", elapsed_ms)

            assert result.returncode == 0, f"check-domain failed: {result.stderr}"
            assert "unclaimed" in result.stdout, (
                f"Expected 'unclaimed' output, got: {result.stdout!r}"
            )
        finally:
            cleanup_orch(orch_id)

    @pytest.mark.timeout(10)
    def test_check_domain_taken_after_register(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            run_orch(
                "register-domain", orch_id, "db-lead", "src/db/*",
                orch_id=orch_id,
            )
            result = run_orch(
                "check-domain", orch_id, "src/db/models.py",
                orch_id=orch_id,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_check_domain_taken_after_register", elapsed_ms)

            assert result.returncode == 0, f"check-domain failed: {result.stderr}"
            assert "db-lead" in result.stdout, (
                f"Expected 'db-lead' in output, got: {result.stdout!r}"
            )
        finally:
            cleanup_orch(orch_id)

    @pytest.mark.timeout(10)
    def test_register_multiple_domains(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            run_orch(
                "register-domain", orch_id, "frontend-lead",
                "src/components/**", "src/styles/**",
                orch_id=orch_id,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_register_multiple_domains", elapsed_ms)

            domains_path = ORCH_BASE / orch_id / "shared" / "domains.json"
            domains = json.loads(domains_path.read_text())
            assert "src/components/**" in domains, f"first glob missing: {domains}"
            assert "src/styles/**" in domains, f"second glob missing: {domains}"
            assert domains["src/components/**"] == "frontend-lead"
            assert domains["src/styles/**"] == "frontend-lead"
        finally:
            cleanup_orch(orch_id)


# ---------------------------------------------------------------------------
# TestWorkingMemory
# ---------------------------------------------------------------------------

class TestWorkingMemory:
    """Tests for append-memory and read-memory subcommands."""

    @pytest.mark.timeout(10)
    def test_append_memory_creates_file(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            result = run_orch(
                "append-memory", orch_id,
                '{"lead":"test-lead","summary":"initial finding"}',
                orch_id=orch_id,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_append_memory_creates_file", elapsed_ms)

            assert result.returncode == 0, f"append-memory failed: {result.stderr}"
            mem_file = ORCH_BASE / orch_id / "shared" / "working_memory.jsonl"
            assert mem_file.exists(), "working_memory.jsonl not created"
            assert mem_file.stat().st_size > 0, "working_memory.jsonl is empty"
        finally:
            cleanup_orch(orch_id)

    @pytest.mark.timeout(10)
    def test_append_memory_valid_jsonl(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            run_orch(
                "append-memory", orch_id,
                '{"lead":"test-lead","summary":"valid json test"}',
                orch_id=orch_id,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_append_memory_valid_jsonl", elapsed_ms)

            mem_file = ORCH_BASE / orch_id / "shared" / "working_memory.jsonl"
            lines = [l for l in mem_file.read_text().splitlines() if l.strip()]
            assert len(lines) >= 1, "No lines in working_memory.jsonl after append"
            for line in lines:
                parsed = json.loads(line)  # raises if invalid JSON
                assert isinstance(parsed, dict), f"Line is not a JSON object: {line}"
        finally:
            cleanup_orch(orch_id)

    @pytest.mark.timeout(10)
    def test_read_memory_returns_array(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            run_orch(
                "append-memory", orch_id,
                '{"lead":"test-lead","summary":"read test entry"}',
                orch_id=orch_id,
            )
            result = run_orch("read-memory", orch_id, orch_id=orch_id)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_read_memory_returns_array", elapsed_ms)

            assert result.returncode == 0, f"read-memory failed: {result.stderr}"
            assert result.stdout.strip(), "read-memory produced no output"
            # read-memory prints formatted lines — confirm our summary appears
            assert "read test entry" in result.stdout, (
                f"Expected summary in read-memory output, got: {result.stdout!r}"
            )
        finally:
            cleanup_orch(orch_id)

    @pytest.mark.timeout(10)
    def test_append_multiple_entries_preserved(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            for i in range(3):
                run_orch(
                    "append-memory", orch_id,
                    json.dumps({"lead": "test-lead", "summary": f"entry {i}"}),
                    orch_id=orch_id,
                )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_append_multiple_entries_preserved", elapsed_ms)

            mem_file = ORCH_BASE / orch_id / "shared" / "working_memory.jsonl"
            lines = [l for l in mem_file.read_text().splitlines() if l.strip()]
            assert len(lines) == 3, (
                f"Expected 3 entries in working_memory.jsonl, got {len(lines)}"
            )
            summaries = [json.loads(l)["summary"] for l in lines]
            assert summaries == ["entry 0", "entry 1", "entry 2"], (
                f"Unexpected entries: {summaries}"
            )
        finally:
            cleanup_orch(orch_id)

    @pytest.mark.timeout(10)
    def test_memory_entry_has_timestamp(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            run_orch(
                "append-memory", orch_id,
                '{"lead":"ts-lead","summary":"timestamp check"}',
                orch_id=orch_id,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_memory_entry_has_timestamp", elapsed_ms)

            mem_file = ORCH_BASE / orch_id / "shared" / "working_memory.jsonl"
            lines = [l for l in mem_file.read_text().splitlines() if l.strip()]
            assert lines, "No lines written to working_memory.jsonl"
            entry = json.loads(lines[-1])
            assert "ts" in entry, f"Entry missing 'ts' field: {entry}"
            assert entry["ts"], f"'ts' field is empty: {entry}"
        finally:
            cleanup_orch(orch_id)


# ---------------------------------------------------------------------------
# TestBroadcast
# ---------------------------------------------------------------------------

class TestBroadcast:
    """Tests for the broadcast subcommand."""

    @pytest.mark.timeout(10)
    def test_broadcast_creates_discoveries_file(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            result = run_orch(
                "broadcast", orch_id,
                "backend-lead", "security", "Found SQL injection in query builder",
                orch_id=orch_id,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_broadcast_creates_discoveries_file", elapsed_ms)

            assert result.returncode == 0, f"broadcast failed: {result.stderr}"
            disc_file = ORCH_BASE / orch_id / "shared" / "discoveries.jsonl"
            assert disc_file.exists(), "discoveries.jsonl not created after broadcast"
            assert disc_file.stat().st_size > 0, "discoveries.jsonl is empty"
        finally:
            cleanup_orch(orch_id)

    @pytest.mark.timeout(10)
    def test_broadcast_is_valid_jsonl(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            run_orch(
                "broadcast", orch_id,
                "frontend-lead", "perf", "Bundle size exceeded 500KB",
                orch_id=orch_id,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_broadcast_is_valid_jsonl", elapsed_ms)

            disc_file = ORCH_BASE / orch_id / "shared" / "discoveries.jsonl"
            lines = [l for l in disc_file.read_text().splitlines() if l.strip()]
            assert lines, "No lines in discoveries.jsonl after broadcast"
            for line in lines:
                parsed = json.loads(line)  # raises if invalid
                assert "from" in parsed, f"broadcast entry missing 'from': {parsed}"
                assert "topic" in parsed, f"broadcast entry missing 'topic': {parsed}"
                assert "message" in parsed, f"broadcast entry missing 'message': {parsed}"
                assert "ts" in parsed, f"broadcast entry missing 'ts': {parsed}"
        finally:
            cleanup_orch(orch_id)

    @pytest.mark.timeout(10)
    def test_multiple_broadcasts_accumulate(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            for i in range(3):
                run_orch(
                    "broadcast", orch_id,
                    "lead-a", "info", f"discovery {i}",
                    orch_id=orch_id,
                )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_multiple_broadcasts_accumulate", elapsed_ms)

            disc_file = ORCH_BASE / orch_id / "shared" / "discoveries.jsonl"
            lines = [l for l in disc_file.read_text().splitlines() if l.strip()]
            assert len(lines) == 3, (
                f"Expected 3 broadcast entries, got {len(lines)}"
            )
            messages = [json.loads(l)["message"] for l in lines]
            assert messages == ["discovery 0", "discovery 1", "discovery 2"], (
                f"Unexpected broadcast messages: {messages}"
            )
        finally:
            cleanup_orch(orch_id)


# ---------------------------------------------------------------------------
# TestReadEvents
# ---------------------------------------------------------------------------

class TestReadEvents:
    """Tests for the read-events subcommand."""

    @pytest.mark.timeout(10)
    def test_read_events_returns_empty_array_when_no_events(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            # Remove events.jsonl if init created one (init itself emits no events)
            events_file = ORCH_BASE / orch_id / "events.jsonl"
            if events_file.exists():
                events_file.unlink()

            result = run_orch("read-events", orch_id, orch_id=orch_id)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_read_events_returns_empty_array_when_no_events", elapsed_ms)

            assert result.returncode == 0, f"read-events failed: {result.stderr}"
            # When no events file exists, script prints "(no events)"
            assert result.stdout.strip(), "read-events produced no output"
            output = result.stdout.strip()
            assert "no events" in output or output == "", (
                f"Expected '(no events)' for empty state, got: {output!r}"
            )
        finally:
            cleanup_orch(orch_id)

    @pytest.mark.timeout(10)
    def test_read_events_valid_json_output(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            # Trigger an event by appending memory (append-memory calls _emit_event)
            run_orch(
                "append-memory", orch_id,
                '{"lead":"event-lead","summary":"triggers an event"}',
                orch_id=orch_id,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_read_events_valid_json_output", elapsed_ms)

            # Verify the events.jsonl file has valid JSONL entries
            events_file = ORCH_BASE / orch_id / "events.jsonl"
            assert events_file.exists(), "events.jsonl not created by append-memory"
            lines = [l for l in events_file.read_text().splitlines() if l.strip()]
            assert lines, "No events written to events.jsonl"
            for line in lines:
                entry = json.loads(line)  # raises if invalid
                assert "ts" in entry, f"event missing 'ts': {entry}"
                assert "agent" in entry, f"event missing 'agent': {entry}"
                assert "status" in entry, f"event missing 'status': {entry}"
        finally:
            cleanup_orch(orch_id)


# ---------------------------------------------------------------------------
# TestMergeResults
# ---------------------------------------------------------------------------

class TestMergeResults:
    """Tests for the merge-results subcommand."""

    @pytest.mark.timeout(10)
    def test_merge_results_creates_merged_file(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            results_dir = ORCH_BASE / orch_id / "results"
            results_dir.mkdir(parents=True, exist_ok=True)
            (results_dir / "frontend-lead.md").write_text("# Frontend\nDone.\n")

            result = run_orch("merge-results", orch_id, orch_id=orch_id)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_merge_results_creates_merged_file", elapsed_ms)

            assert result.returncode == 0, f"merge-results failed: {result.stderr}"
            merged = ORCH_BASE / orch_id / "shared" / "merged_results.md"
            assert merged.exists(), f"merged_results.md not created: {result.stdout}"
        finally:
            cleanup_orch(orch_id)

    @pytest.mark.timeout(10)
    def test_merge_results_includes_all_lead_outputs(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            results_dir = ORCH_BASE / orch_id / "results"
            results_dir.mkdir(parents=True, exist_ok=True)
            (results_dir / "frontend-lead.md").write_text("# Frontend\nFrontend content.\n")
            (results_dir / "backend-lead.md").write_text("# Backend\nBackend content.\n")
            (results_dir / "db-lead.md").write_text("# DB\nDB content.\n")

            result = run_orch("merge-results", orch_id, orch_id=orch_id)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_merge_results_includes_all_lead_outputs", elapsed_ms)

            assert result.returncode == 0, f"merge-results failed: {result.stderr}"
            merged = ORCH_BASE / orch_id / "shared" / "merged_results.md"
            content = merged.read_text()
            assert "Frontend content." in content, "frontend-lead output missing from merge"
            assert "Backend content." in content, "backend-lead output missing from merge"
            assert "DB content." in content, "db-lead output missing from merge"
        finally:
            cleanup_orch(orch_id)

    @pytest.mark.timeout(10)
    def test_merge_results_handles_empty_results_dir(self, tmp_path):
        orch_id = make_orch_id()
        t0 = time.perf_counter()
        try:
            run_orch("init", orch_id, orch_id=orch_id)
            # Do NOT create any result files — results dir either absent or empty

            result = run_orch("merge-results", orch_id, orch_id=orch_id)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            record_timing("test_merge_results_handles_empty_results_dir", elapsed_ms)

            # Script should exit 0 and print "(no results found)"
            assert result.returncode == 0, (
                f"merge-results should not fail on empty dir. stderr: {result.stderr}"
            )
            assert "no results" in result.stdout, (
                f"Expected '(no results found)' output, got: {result.stdout!r}"
            )
        finally:
            cleanup_orch(orch_id)
