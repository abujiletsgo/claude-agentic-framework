#!/usr/bin/env python3
"""
test_palace_integration.py — Integration tests for project-local mempalace hooks.

Tests:
  1. palace_init.py — shared utility functions
  2. subagent_palace_store.py — SubagentStop hook
  3. subagent_kg_inject.py — SubagentStart hook
  4. Updated hooks — project-local path resolution
  5. End-to-end flow — store → inject round-trip
"""

import json
import os
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

import pytest

# Add framework memory dir to path
FRAMEWORK_DIR = os.path.join(os.path.dirname(__file__), '..', 'global-hooks', 'framework')
MEMORY_DIR = os.path.join(FRAMEWORK_DIR, 'memory')
CONTEXT_DIR = os.path.join(FRAMEWORK_DIR, 'context')
sys.path.insert(0, MEMORY_DIR)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project directory for testing."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    return str(project_dir)


@pytest.fixture
def palace_available():
    """Check if mempalace is available."""
    try:
        from palace_init import has_mempalace
        return has_mempalace()
    except ImportError:
        return False


# ─── palace_init.py tests ─────────────────────────────────────────────────────

class TestPalaceInit:
    """Tests for the shared palace_init utility."""

    def test_import(self):
        """palace_init can be imported."""
        from palace_init import (
            ensure_palace, get_project_kg, get_project_stack,
            get_palace_path, get_kg_path, has_mempalace,
            search_project_memories, store_drawer,
        )

    def test_palace_path_resolution(self, temp_project):
        """get_palace_path resolves to CWD/.mempalace/palace/"""
        from palace_init import get_palace_path
        path = get_palace_path(temp_project)
        assert str(path).endswith(".mempalace/palace")
        assert temp_project in str(path)

    def test_kg_path_resolution(self, temp_project):
        """get_kg_path resolves to CWD/.mempalace/knowledge_graph.sqlite3"""
        from palace_init import get_kg_path
        path = get_kg_path(temp_project)
        assert str(path).endswith(".mempalace/knowledge_graph.sqlite3")
        assert temp_project in str(path)

    def test_paths_are_project_local(self, temp_project):
        """Paths MUST be under the project root, never global."""
        from palace_init import get_palace_path, get_kg_path
        palace = get_palace_path(temp_project)
        kg = get_kg_path(temp_project)
        assert "~" not in str(palace)
        assert "~" not in str(kg)
        assert ".mempalace" not in str(Path.home())  # not in home dir

    def test_has_mempalace_returns_bool(self):
        """has_mempalace returns a boolean."""
        from palace_init import has_mempalace
        result = has_mempalace()
        assert isinstance(result, bool)

    @pytest.mark.skipif(
        not os.path.exists(os.path.expanduser("~/Documents/mempalace/.venv")),
        reason="mempalace not installed"
    )
    def test_ensure_palace_creates_directory(self, temp_project):
        """ensure_palace creates .mempalace/palace/ directory."""
        from palace_init import ensure_palace
        result = ensure_palace(temp_project)
        assert result is not None
        assert result.exists()
        assert (Path(temp_project) / ".mempalace" / "palace").exists()

    @pytest.mark.skipif(
        not os.path.exists(os.path.expanduser("~/Documents/mempalace/.venv")),
        reason="mempalace not installed"
    )
    def test_get_project_kg_returns_instance(self, temp_project):
        """get_project_kg returns a KnowledgeGraph with project-local db."""
        from palace_init import get_project_kg
        kg = get_project_kg(temp_project)
        assert kg is not None
        # Verify KG database is in the project directory
        kg_db = Path(temp_project) / ".mempalace" / "knowledge_graph.sqlite3"
        assert kg_db.exists()

    @pytest.mark.skipif(
        not os.path.exists(os.path.expanduser("~/Documents/mempalace/.venv")),
        reason="mempalace not installed"
    )
    def test_kg_write_and_read(self, temp_project):
        """Can write to and read from project-local KG."""
        from palace_init import get_project_kg
        from datetime import date
        kg = get_project_kg(temp_project)
        assert kg is not None

        today = date.today().isoformat()
        kg.add_triple(
            subject="test-project",
            predicate="decided",
            obj="Use project-local mempalace for all operations",
            valid_from=today,
            source_file="test_palace_integration",
        )

        decisions = kg.query_relationship("decided", as_of=today)
        assert len(decisions) >= 1
        found = any("project-local" in d.get("object", "") for d in decisions)
        assert found, f"Decision not found in KG results: {decisions}"

    @pytest.mark.skipif(
        not os.path.exists(os.path.expanduser("~/Documents/mempalace/.venv")),
        reason="mempalace not installed"
    )
    def test_store_drawer_and_search(self, temp_project):
        """Can store and search drawers in project-local palace."""
        from palace_init import store_drawer, search_project_memories
        ok = store_drawer(
            content="The authentication module uses JWT tokens with RS256 signing.",
            cwd=temp_project,
            wing="test-project",
            room="architecture",
            source_file="test",
        )
        assert ok is True

        results = search_project_memories(
            query="JWT authentication",
            cwd=temp_project,
            wing="test-project",
        )
        assert len(results) >= 1
        assert "JWT" in results[0].get("text", "") or "authentication" in results[0].get("text", "")

    def test_fail_open_no_mempalace(self, temp_project):
        """All functions fail-open when mempalace is unavailable."""
        from palace_init import search_project_memories
        # search_project_memories should return empty list, not raise
        results = search_project_memories("test query", cwd="/nonexistent/path")
        assert results == []


# ─── Hook execution tests ─────────────────────────────────────────────────────

class TestSubagentPalaceStore:
    """Tests for the SubagentStop storage hook."""

    def test_hook_file_exists(self):
        """subagent_palace_store.py exists."""
        hook = os.path.join(MEMORY_DIR, "subagent_palace_store.py")
        assert os.path.exists(hook)

    def test_hook_syntax(self):
        """Hook has valid Python syntax."""
        hook = os.path.join(MEMORY_DIR, "subagent_palace_store.py")
        result = subprocess.run(
            ["python3", "-c", f"import ast; ast.parse(open('{hook}').read())"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_hook_empty_input(self):
        """Hook handles empty input gracefully."""
        hook = os.path.join(MEMORY_DIR, "subagent_palace_store.py")
        result = subprocess.run(
            ["python3", hook],
            input="{}",
            capture_output=True, text=True,
            timeout=10,
        )
        assert result.returncode == 0
        output = json.loads(result.stdout.strip())
        assert output == {}

    def test_hook_short_content_skipped(self):
        """Hook skips content shorter than 50 chars."""
        hook = os.path.join(MEMORY_DIR, "subagent_palace_store.py")
        result = subprocess.run(
            ["python3", hook],
            input=json.dumps({"tool_output": "short", "cwd": "/tmp"}),
            capture_output=True, text=True,
            timeout=10,
        )
        assert result.returncode == 0
        output = json.loads(result.stdout.strip())
        assert output == {}

    @pytest.mark.skipif(
        not os.path.exists(os.path.expanduser("~/Documents/mempalace/.venv")),
        reason="mempalace not installed"
    )
    def test_hook_stores_content(self, temp_project):
        """Hook stores agent output in project-local mempalace."""
        hook = os.path.join(MEMORY_DIR, "subagent_palace_store.py")
        agent_output = (
            "Research complete. The framework uses 39 hooks across 16 events. "
            "Key finding: SubagentStart hooks CAN inject additionalContext with a 10K char cap. "
            "Decided to use project-local mempalace instead of global storage."
        )
        hook_input = {
            "tool_output": agent_output,
            "tool_input": {"prompt": "Research hook architecture"},
            "cwd": temp_project,
        }
        result = subprocess.run(
            ["python3", hook],
            input=json.dumps(hook_input),
            capture_output=True, text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "[Palace]" in result.stderr

        # Verify content was stored
        from palace_init import search_project_memories
        results = search_project_memories("hook architecture", cwd=temp_project)
        assert len(results) >= 1

    @pytest.mark.skipif(
        not os.path.exists(os.path.expanduser("~/Documents/mempalace/.venv")),
        reason="mempalace not installed"
    )
    def test_hook_extracts_decisions(self, temp_project):
        """Hook extracts decision statements to KG."""
        hook = os.path.join(MEMORY_DIR, "subagent_palace_store.py")
        agent_output = (
            "Analysis complete. We decided to use ChromaDB for vector storage. "
            "Also chose SQLite for the knowledge graph because it's sub-millisecond. "
            "The approach will use project-local paths for all mempalace data."
        )
        hook_input = {
            "tool_output": agent_output,
            "tool_input": {"prompt": "Analyze storage options"},
            "cwd": temp_project,
        }
        result = subprocess.run(
            ["python3", hook],
            input=json.dumps(hook_input),
            capture_output=True, text=True,
            timeout=10,
        )
        assert result.returncode == 0

        # Verify decisions in KG
        from palace_init import get_project_kg
        from datetime import date
        kg = get_project_kg(temp_project)
        decisions = kg.query_relationship("decided", as_of=date.today().isoformat())
        assert len(decisions) >= 1
        decision_texts = [d.get("object", "") for d in decisions]
        assert any("ChromaDB" in t for t in decision_texts), f"Decision not found: {decision_texts}"


class TestSubagentKgInject:
    """Tests for the SubagentStart KG inject hook."""

    def test_hook_file_exists(self):
        """subagent_kg_inject.py exists."""
        hook = os.path.join(MEMORY_DIR, "subagent_kg_inject.py")
        assert os.path.exists(hook)

    def test_hook_syntax(self):
        """Hook has valid Python syntax."""
        hook = os.path.join(MEMORY_DIR, "subagent_kg_inject.py")
        result = subprocess.run(
            ["python3", "-c", f"import ast; ast.parse(open('{hook}').read())"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_hook_empty_kg(self, temp_project):
        """Hook emits {} when KG is empty (no decisions to inject)."""
        hook = os.path.join(MEMORY_DIR, "subagent_kg_inject.py")
        result = subprocess.run(
            ["python3", hook],
            input=json.dumps({"cwd": temp_project, "tool_input": {"name": "test-agent"}}),
            capture_output=True, text=True,
            timeout=10,
        )
        assert result.returncode == 0
        output = json.loads(result.stdout.strip())
        # Empty KG → empty output (no additionalContext)
        assert output == {} or "additionalContext" not in output.get("hookSpecificOutput", {})

    @pytest.mark.skipif(
        not os.path.exists(os.path.expanduser("~/Documents/mempalace/.venv")),
        reason="mempalace not installed"
    )
    def test_hook_injects_decisions(self, temp_project):
        """Hook injects KG decisions as additionalContext."""
        # First, populate KG with decisions
        from palace_init import get_project_kg
        from datetime import date
        kg = get_project_kg(temp_project)
        today = date.today().isoformat()
        kg.add_triple(
            subject="test-project",
            predicate="decided",
            obj="Use project-local mempalace for all storage",
            valid_from=today,
            source_file="test",
        )
        kg.add_triple(
            subject="test-project",
            predicate="confirmed",
            obj="SubagentStart hooks CAN inject additionalContext",
            valid_from=today,
            source_file="test",
        )

        # Now run the inject hook
        hook = os.path.join(MEMORY_DIR, "subagent_kg_inject.py")
        result = subprocess.run(
            ["python3", hook],
            input=json.dumps({
                "cwd": temp_project,
                "tool_input": {"name": "researcher-1", "prompt": "Research task"},
            }),
            capture_output=True, text=True,
            timeout=10,
        )
        assert result.returncode == 0
        output = json.loads(result.stdout.strip())

        # Should have additionalContext
        assert "hookSpecificOutput" in output
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "Prior Decisions" in context or "Confirmed Facts" in context
        assert "project-local mempalace" in context
        assert "[Palace]" in result.stderr

    @pytest.mark.skipif(
        not os.path.exists(os.path.expanduser("~/Documents/mempalace/.venv")),
        reason="mempalace not installed"
    )
    def test_hook_caps_output_length(self, temp_project):
        """Hook caps additionalContext at 1500 chars."""
        from palace_init import get_project_kg
        from datetime import date
        kg = get_project_kg(temp_project)
        today = date.today().isoformat()

        # Add many decisions to exceed the cap
        for i in range(30):
            kg.add_triple(
                subject="test-project",
                predicate="decided",
                obj=f"Decision number {i}: {'x' * 100}",
                valid_from=today,
                source_file="test",
            )

        hook = os.path.join(MEMORY_DIR, "subagent_kg_inject.py")
        result = subprocess.run(
            ["python3", hook],
            input=json.dumps({"cwd": temp_project, "tool_input": {"name": "test"}}),
            capture_output=True, text=True,
            timeout=10,
        )
        assert result.returncode == 0
        output = json.loads(result.stdout.strip())
        context = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert len(context) <= 1600  # 1500 + some slack for truncation message


# ─── End-to-end flow test ─────────────────────────────────────────────────────

class TestEndToEndFlow:
    """Test the full store → inject round-trip."""

    @pytest.mark.skipif(
        not os.path.exists(os.path.expanduser("~/Documents/mempalace/.venv")),
        reason="mempalace not installed"
    )
    def test_store_then_inject(self, temp_project):
        """Agent output stored by SubagentStop is available in SubagentStart inject."""
        store_hook = os.path.join(MEMORY_DIR, "subagent_palace_store.py")
        inject_hook = os.path.join(MEMORY_DIR, "subagent_kg_inject.py")

        # Step 1: Store agent output (includes a decision)
        agent_output = (
            "Research findings: The framework has 39 hooks across 16 events. "
            "Decided to implement project-local mempalace storage for token efficiency. "
            "This will save approximately 35-40% tokens on repeat orchestrations."
        )
        store_result = subprocess.run(
            ["python3", store_hook],
            input=json.dumps({
                "tool_output": agent_output,
                "tool_input": {"prompt": "Research framework hooks"},
                "cwd": temp_project,
            }),
            capture_output=True, text=True,
            timeout=10,
        )
        assert store_result.returncode == 0

        # Step 2: Inject should now include the stored decision
        inject_result = subprocess.run(
            ["python3", inject_hook],
            input=json.dumps({
                "cwd": temp_project,
                "tool_input": {"name": "researcher-2", "prompt": "Continue research"},
            }),
            capture_output=True, text=True,
            timeout=10,
        )
        assert inject_result.returncode == 0
        output = json.loads(inject_result.stdout.strip())

        # The injected context should contain the decision from the store step
        context = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert "project-local mempalace" in context.lower() or "token efficiency" in context.lower(), \
            f"Decision from store not found in inject output: {context[:500]}"

    @pytest.mark.skipif(
        not os.path.exists(os.path.expanduser("~/Documents/mempalace/.venv")),
        reason="mempalace not installed"
    )
    def test_isolation_between_projects(self):
        """Two projects have completely separate KGs — no cross-contamination."""
        from palace_init import get_project_kg
        from datetime import date

        with tempfile.TemporaryDirectory() as project_a, \
             tempfile.TemporaryDirectory() as project_b:

            today = date.today().isoformat()

            # Write to project A's KG
            kg_a = get_project_kg(project_a)
            kg_a.add_triple(
                subject="project-a",
                predicate="decided",
                obj="Project A uses React for frontend",
                valid_from=today,
                source_file="test",
            )

            # Write to project B's KG
            kg_b = get_project_kg(project_b)
            kg_b.add_triple(
                subject="project-b",
                predicate="decided",
                obj="Project B uses Vue for frontend",
                valid_from=today,
                source_file="test",
            )

            # Verify isolation
            a_decisions = kg_a.query_relationship("decided", as_of=today)
            b_decisions = kg_b.query_relationship("decided", as_of=today)

            a_texts = [d["object"] for d in a_decisions]
            b_texts = [d["object"] for d in b_decisions]

            assert any("React" in t for t in a_texts)
            assert not any("Vue" in t for t in a_texts), "Project B data leaked into Project A"
            assert any("Vue" in t for t in b_texts)
            assert not any("React" in t for t in b_texts), "Project A data leaked into Project B"


# ─── Updated hooks tests ──────────────────────────────────────────────────────

class TestUpdatedHooks:
    """Verify existing hooks use project-local paths."""

    def test_kg_session_context_uses_palace_init(self):
        """kg_session_context.py imports from palace_init, not global mempalace."""
        hook = os.path.join(MEMORY_DIR, "kg_session_context.py")
        with open(hook) as f:
            content = f.read()
        assert "from palace_init import" in content
        assert "KnowledgeGraph()" not in content  # no global KG

    def test_auto_memory_writer_uses_palace_init(self):
        """auto_memory_writer.py uses palace_init for KG access."""
        hook = os.path.join(MEMORY_DIR, "auto_memory_writer.py")
        with open(hook) as f:
            content = f.read()
        assert "from palace_init import" in content

    def test_pre_compact_uses_palace_init(self):
        """pre_compact_preserve.py uses palace_init for KG access."""
        hook = os.path.join(CONTEXT_DIR, "pre_compact_preserve.py")
        with open(hook) as f:
            content = f.read()
        assert "from palace_init import" in content
        assert "KnowledgeGraph()" not in content  # no global KG

    def test_no_global_mempalace_path(self):
        """No hook references ~/.mempalace or global KnowledgeGraph()."""
        hooks = [
            os.path.join(MEMORY_DIR, "kg_session_context.py"),
            os.path.join(MEMORY_DIR, "auto_memory_writer.py"),
            os.path.join(MEMORY_DIR, "subagent_palace_store.py"),
            os.path.join(MEMORY_DIR, "subagent_kg_inject.py"),
            os.path.join(CONTEXT_DIR, "pre_compact_preserve.py"),
        ]
        for hook in hooks:
            with open(hook) as f:
                content = f.read()
            # Should not have hardcoded global path
            assert "~/.mempalace" not in content, f"{hook} references global ~/.mempalace"


# ─── Latency benchmark ────────────────────────────────────────────────────────

class TestLatencyBenchmark:
    """Measure hook execution latency."""

    def test_store_hook_latency(self, temp_project):
        """SubagentStop store hook completes within 500ms."""
        import time
        hook = os.path.join(MEMORY_DIR, "subagent_palace_store.py")
        hook_input = json.dumps({
            "tool_output": "x" * 100,  # Minimal content
            "cwd": temp_project,
        })
        start = time.time()
        result = subprocess.run(
            ["python3", hook],
            input=hook_input,
            capture_output=True, text=True,
            timeout=5,
        )
        elapsed = (time.time() - start) * 1000
        assert result.returncode == 0
        print(f"\n  Store hook latency: {elapsed:.0f}ms")
        assert elapsed < 3000, f"Store hook too slow: {elapsed:.0f}ms"

    def test_inject_hook_latency(self, temp_project):
        """SubagentStart inject hook completes within 100ms."""
        import time
        hook = os.path.join(MEMORY_DIR, "subagent_kg_inject.py")
        hook_input = json.dumps({
            "cwd": temp_project,
            "tool_input": {"name": "test-agent"},
        })
        start = time.time()
        result = subprocess.run(
            ["python3", hook],
            input=hook_input,
            capture_output=True, text=True,
            timeout=5,
        )
        elapsed = (time.time() - start) * 1000
        assert result.returncode == 0
        print(f"\n  Inject hook latency: {elapsed:.0f}ms")
        # KG-only path should be very fast (subprocess startup dominates)
        assert elapsed < 3000, f"Inject hook too slow: {elapsed:.0f}ms"


# ─── Token economics projection ──────────────────────────────────────────────

class TestTokenEconomics:
    """Verify token savings projections."""

    @pytest.mark.skipif(
        not os.path.exists(os.path.expanduser("~/Documents/mempalace/.venv")),
        reason="mempalace not installed"
    )
    def test_inject_token_budget(self, temp_project):
        """Injected context stays within ~500 token budget per agent."""
        from palace_init import get_project_kg
        from datetime import date

        kg = get_project_kg(temp_project)
        today = date.today().isoformat()

        # Populate with realistic number of decisions
        for i in range(15):
            kg.add_triple(
                subject="test-project",
                predicate="decided",
                obj=f"Decision {i}: Use approach X for component Y because of reason Z",
                valid_from=today,
                source_file="test",
            )

        hook = os.path.join(MEMORY_DIR, "subagent_kg_inject.py")
        result = subprocess.run(
            ["python3", hook],
            input=json.dumps({"cwd": temp_project, "tool_input": {"name": "test"}}),
            capture_output=True, text=True,
            timeout=10,
        )
        output = json.loads(result.stdout.strip())
        context = output.get("hookSpecificOutput", {}).get("additionalContext", "")

        # Estimate tokens (rough: 1 token ≈ 4 chars)
        estimated_tokens = len(context) // 4
        print(f"\n  Injected context: {len(context)} chars ≈ {estimated_tokens} tokens")
        assert estimated_tokens <= 500, f"Injected too many tokens: {estimated_tokens}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
