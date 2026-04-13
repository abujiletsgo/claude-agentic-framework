"""
CAF Audit — Lead Memory Writer Tests
======================================
Tests the SubagentStop hook that detects lead/PO agents and writes
domain-scoped memory files to .claude/lead-memories/.

Run standalone:
  uv run pytest tests/audit/modules/test_lead_memory.py -v
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent
SCRIPT = REPO_ROOT / "global-hooks/framework/memory/lead_memory_writer.py"

TIMINGS: list[dict] = []


def make_event(
    hook_event: str = "SubagentStop",
    agent_name: str = "backend-lead",
    subagent_type: str = "backend-lead",
    cwd: str | None = None,
) -> dict:
    """Build a minimal SubagentStop event payload."""
    payload: dict = {
        "hook_event_name": hook_event,
        "agent_name": agent_name,
        "subagent_type": subagent_type,
    }
    if cwd is not None:
        payload["cwd"] = cwd
    return payload


def run_script(event_payload: dict) -> subprocess.CompletedProcess:
    """Invoke lead_memory_writer.py via subprocess, passing event as stdin JSON."""
    return subprocess.run(
        ["python3", str(SCRIPT)],
        input=json.dumps(event_payload),
        capture_output=True,
        text=True,
    )


def record_timing(test_name: str, elapsed_ms: float) -> None:
    TIMINGS.append({"test": test_name, "ms": elapsed_ms})


# ── skip guard ─────────────────────────────────────────────────────────────────

pytestmark = pytest.mark.skipif(
    not SCRIPT.exists(),
    reason="lead_memory_writer.py not found",
)


# ── TestLeadDetection ─────────────────────────────────────────────────────────


class TestLeadDetection:
    @pytest.mark.timeout(5)
    def test_po_detected_by_subagent_type(self, tmp_path):
        t0 = time.perf_counter()
        (tmp_path / ".claude").mkdir()
        event = make_event(
            agent_name="some-agent",
            subagent_type="po",
            cwd=str(tmp_path),
        )
        result = run_script(event)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_po_detected_by_subagent_type", elapsed_ms)

        assert result.returncode == 0
        po_file = tmp_path / ".claude" / "lead-memories" / "PO.md"
        assert po_file.exists(), "PO.md should be created when subagent_type='po'"

    @pytest.mark.timeout(5)
    def test_po_detected_by_agent_name(self, tmp_path):
        t0 = time.perf_counter()
        (tmp_path / ".claude").mkdir()
        event = make_event(
            agent_name="my-po",
            subagent_type="orchestrator",
            cwd=str(tmp_path),
        )
        result = run_script(event)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_po_detected_by_agent_name", elapsed_ms)

        assert result.returncode == 0
        po_file = tmp_path / ".claude" / "lead-memories" / "PO.md"
        assert po_file.exists(), "PO.md should be created when 'po' appears in agent_name"

    @pytest.mark.timeout(5)
    def test_backend_lead_detected(self, tmp_path):
        t0 = time.perf_counter()
        (tmp_path / ".claude").mkdir()
        event = make_event(
            agent_name="backend-lead",
            subagent_type="backend-lead",
            cwd=str(tmp_path),
        )
        result = run_script(event)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_backend_lead_detected", elapsed_ms)

        assert result.returncode == 0
        mem_file = tmp_path / ".claude" / "lead-memories" / "backend-lead.md"
        assert mem_file.exists(), "backend-lead.md should be created for backend-lead agent"

    @pytest.mark.timeout(5)
    def test_frontend_lead_detected(self, tmp_path):
        t0 = time.perf_counter()
        (tmp_path / ".claude").mkdir()
        event = make_event(
            agent_name="frontend-lead",
            subagent_type="frontend-lead",
            cwd=str(tmp_path),
        )
        result = run_script(event)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_frontend_lead_detected", elapsed_ms)

        assert result.returncode == 0
        mem_file = tmp_path / ".claude" / "lead-memories" / "frontend-lead.md"
        assert mem_file.exists(), "frontend-lead.md should be created for frontend-lead agent"

    @pytest.mark.timeout(5)
    def test_non_lead_agent_skipped(self, tmp_path):
        t0 = time.perf_counter()
        (tmp_path / ".claude").mkdir()
        event = make_event(
            agent_name="builder",
            subagent_type="builder",
            cwd=str(tmp_path),
        )
        result = run_script(event)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_non_lead_agent_skipped", elapsed_ms)

        assert result.returncode == 0
        lead_memories_dir = tmp_path / ".claude" / "lead-memories"
        assert not lead_memories_dir.exists(), (
            "lead-memories dir should NOT be created for a non-lead agent"
        )

    @pytest.mark.timeout(5)
    def test_wrong_hook_event_skipped(self, tmp_path):
        t0 = time.perf_counter()
        (tmp_path / ".claude").mkdir()
        event = make_event(
            hook_event="PostToolUse",
            agent_name="backend-lead",
            subagent_type="backend-lead",
            cwd=str(tmp_path),
        )
        result = run_script(event)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_wrong_hook_event_skipped", elapsed_ms)

        assert result.returncode == 0
        lead_memories_dir = tmp_path / ".claude" / "lead-memories"
        assert not lead_memories_dir.exists(), (
            "lead-memories dir should NOT be created for non-SubagentStop events"
        )

    @pytest.mark.timeout(5)
    def test_empty_event_is_safe(self, tmp_path):
        t0 = time.perf_counter()
        result = subprocess.run(
            ["python3", str(SCRIPT)],
            input=json.dumps({}),
            capture_output=True,
            text=True,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_empty_event_is_safe", elapsed_ms)

        assert result.returncode == 0, (
            f"Empty JSON event should exit 0 (fail-open). Got returncode={result.returncode}"
        )


# ── TestMemoryFileCreation ────────────────────────────────────────────────────


class TestMemoryFileCreation:
    @pytest.mark.timeout(5)
    def test_creates_lead_memories_dir(self, tmp_path):
        t0 = time.perf_counter()
        (tmp_path / ".claude").mkdir()
        event = make_event(
            agent_name="backend-lead",
            subagent_type="backend-lead",
            cwd=str(tmp_path),
        )
        run_script(event)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_creates_lead_memories_dir", elapsed_ms)

        lead_memories_dir = tmp_path / ".claude" / "lead-memories"
        assert lead_memories_dir.is_dir(), (
            "lead-memories directory should be created under .claude/"
        )

    @pytest.mark.timeout(5)
    def test_po_creates_po_md(self, tmp_path):
        t0 = time.perf_counter()
        (tmp_path / ".claude").mkdir()
        event = make_event(
            agent_name="po",
            subagent_type="po",
            cwd=str(tmp_path),
        )
        run_script(event)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_po_creates_po_md", elapsed_ms)

        po_file = tmp_path / ".claude" / "lead-memories" / "PO.md"
        assert po_file.exists(), "PO.md should be created for PO agent"

    @pytest.mark.timeout(5)
    def test_backend_lead_creates_correct_file(self, tmp_path):
        t0 = time.perf_counter()
        (tmp_path / ".claude").mkdir()
        event = make_event(
            agent_name="backend-lead",
            subagent_type="backend-lead",
            cwd=str(tmp_path),
        )
        run_script(event)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_backend_lead_creates_correct_file", elapsed_ms)

        mem_file = tmp_path / ".claude" / "lead-memories" / "backend-lead.md"
        assert mem_file.exists(), "backend-lead.md should be created for backend-lead agent"
        # Ensure no other unexpected lead files were created
        lead_memories_dir = tmp_path / ".claude" / "lead-memories"
        files = list(lead_memories_dir.iterdir())
        assert len(files) == 1, f"Only one file should be created, got: {files}"

    @pytest.mark.timeout(5)
    def test_file_creation_idempotent(self, tmp_path):
        t0 = time.perf_counter()
        (tmp_path / ".claude").mkdir()
        event = make_event(
            agent_name="backend-lead",
            subagent_type="backend-lead",
            cwd=str(tmp_path),
        )
        # Run twice
        result1 = run_script(event)
        result2 = run_script(event)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_file_creation_idempotent", elapsed_ms)

        assert result1.returncode == 0, f"First run failed: {result1.stderr}"
        assert result2.returncode == 0, f"Second run failed: {result2.stderr}"
        mem_file = tmp_path / ".claude" / "lead-memories" / "backend-lead.md"
        assert mem_file.exists(), "Memory file should still exist after two runs"

    @pytest.mark.timeout(5)
    def test_cwd_based_project_root_discovery(self, tmp_path):
        t0 = time.perf_counter()
        # .claude/ is at tmp_path (project root), cwd is a subdir
        (tmp_path / ".claude").mkdir()
        subdir = tmp_path / "src" / "services"
        subdir.mkdir(parents=True)
        event = make_event(
            agent_name="backend-lead",
            subagent_type="backend-lead",
            cwd=str(subdir),
        )
        run_script(event)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_cwd_based_project_root_discovery", elapsed_ms)

        # Should discover project root as tmp_path by walking up from subdir
        mem_file = tmp_path / ".claude" / "lead-memories" / "backend-lead.md"
        assert mem_file.exists(), (
            "Script should walk up from cwd to find .claude/ and write memory there"
        )


# ── TestMemoryFileContent ─────────────────────────────────────────────────────


class TestMemoryFileContent:
    @pytest.mark.timeout(5)
    def test_lead_file_has_frontmatter(self, tmp_path):
        t0 = time.perf_counter()
        (tmp_path / ".claude").mkdir()
        event = make_event(
            agent_name="backend-lead",
            subagent_type="backend-lead",
            cwd=str(tmp_path),
        )
        run_script(event)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_lead_file_has_frontmatter", elapsed_ms)

        mem_file = tmp_path / ".claude" / "lead-memories" / "backend-lead.md"
        content = mem_file.read_text()
        assert content.startswith("#"), (
            "Lead memory file should start with a markdown heading (# ...)"
        )

    @pytest.mark.timeout(5)
    def test_lead_file_has_agent_name(self, tmp_path):
        t0 = time.perf_counter()
        (tmp_path / ".claude").mkdir()
        event = make_event(
            agent_name="backend-lead",
            subagent_type="backend-lead",
            cwd=str(tmp_path),
        )
        run_script(event)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_lead_file_has_agent_name", elapsed_ms)

        mem_file = tmp_path / ".claude" / "lead-memories" / "backend-lead.md"
        content = mem_file.read_text()
        assert "backend-lead" in content, (
            "Lead memory file should mention the agent name 'backend-lead'"
        )

    @pytest.mark.timeout(5)
    def test_po_file_differs_from_lead_file(self, tmp_path):
        t0 = time.perf_counter()
        (tmp_path / ".claude").mkdir()
        # Create PO memory file
        po_event = make_event(
            agent_name="po",
            subagent_type="po",
            cwd=str(tmp_path),
        )
        run_script(po_event)
        # Create lead memory file
        lead_event = make_event(
            agent_name="backend-lead",
            subagent_type="backend-lead",
            cwd=str(tmp_path),
        )
        run_script(lead_event)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_po_file_differs_from_lead_file", elapsed_ms)

        po_file = tmp_path / ".claude" / "lead-memories" / "PO.md"
        lead_file = tmp_path / ".claude" / "lead-memories" / "backend-lead.md"
        po_content = po_file.read_text()
        lead_content = lead_file.read_text()

        assert po_content != lead_content, "PO.md should have different content than a lead memory file"
        assert "PO" in po_content, "PO.md should contain PO-specific content"


# ── TestEdgeCases ─────────────────────────────────────────────────────────────


class TestEdgeCases:
    @pytest.mark.timeout(5)
    def test_invalid_json_stdin_exits_zero(self, tmp_path):
        t0 = time.perf_counter()
        result = subprocess.run(
            ["python3", str(SCRIPT)],
            input="this is not valid json {{{",
            capture_output=True,
            text=True,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_invalid_json_stdin_exits_zero", elapsed_ms)

        assert result.returncode == 0, (
            f"Malformed JSON input should exit 0 (fail-open). Got returncode={result.returncode}, "
            f"stderr={result.stderr!r}"
        )

    @pytest.mark.timeout(5)
    def test_missing_cwd_uses_current_dir(self, tmp_path):
        t0 = time.perf_counter()
        # Event has no "cwd" key — script should fall back to os.getcwd()
        # We can't control os.getcwd() for the subprocess, but we verify it doesn't crash
        event = {
            "hook_event_name": "SubagentStop",
            "agent_name": "backend-lead",
            "subagent_type": "backend-lead",
            # No "cwd" key
        }
        result = subprocess.run(
            ["python3", str(SCRIPT)],
            input=json.dumps(event),
            capture_output=True,
            text=True,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_missing_cwd_uses_current_dir", elapsed_ms)

        assert result.returncode == 0, (
            f"Missing cwd in event should not crash. Got returncode={result.returncode}, "
            f"stderr={result.stderr!r}"
        )

    @pytest.mark.timeout(5)
    def test_architecture_lead_detected(self, tmp_path):
        t0 = time.perf_counter()
        (tmp_path / ".claude").mkdir()
        event = make_event(
            agent_name="architecture-lead",
            subagent_type="architecture-lead",
            cwd=str(tmp_path),
        )
        result = run_script(event)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        record_timing("test_architecture_lead_detected", elapsed_ms)

        assert result.returncode == 0
        mem_file = tmp_path / ".claude" / "lead-memories" / "architecture-lead.md"
        assert mem_file.exists(), (
            "architecture-lead.md should be created for architecture-lead agent"
        )
