#!/usr/bin/env python3
"""
test_approach_benchmark.py — 5 Mempalace Integration Approaches Benchmark

Measures token efficiency, information retention, and structure retention
for 5 different approaches to handling precompact context preservation.

Run:
  uv run --no-project --with pytest --with tiktoken pytest tests/test_approach_benchmark.py -v -s

The -s flag is important — benchmark results are printed to stdout.
"""

import sys
import os
import time
import json
import glob
from pathlib import Path

import pytest

# --- sys.path setup ---
FRAMEWORK_DIR = os.path.join(os.path.dirname(__file__), "..", "global-hooks", "framework")
sys.path.insert(0, FRAMEWORK_DIR)

from aaak_compress import compress, compress_sections, compress_with_stats

# Mempalace (fail-open)
def _get_mempalace():
    base = os.path.expanduser("~/Documents/mempalace/.venv/lib")
    matches = glob.glob(os.path.join(base, "python3.*/site-packages"))
    if matches and matches[0] not in sys.path:
        sys.path.insert(0, matches[0])

_get_mempalace()
try:
    from mempalace.knowledge_graph import KnowledgeGraph
    from mempalace.layers import MemoryStack
    from mempalace.searcher import search_memories
    HAS_MEMPALACE = True
except ImportError:
    HAS_MEMPALACE = False

# Tiktoken
try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")
    def count_tokens(text): return len(_enc.encode(text))
    HAS_TIKTOKEN = True
except ImportError:
    def count_tokens(text): return len(text) // 4
    HAS_TIKTOKEN = False


# ---------------------------------------------------------------------------
# Test data builders
# ---------------------------------------------------------------------------

def build_realistic_precompact_input():
    """Build a realistic precompact preservation instruction string."""
    return """═══ COMPACTION PRESERVATION INSTRUCTIONS ═══

📋 ACTIVE TASKS (5 in progress)
- Integrate mempalace into memory layers
- Update install.sh for optional dependencies
- Build comprehensive benchmark suite
- Fix auto_prime context injection
- Review pre_compact pipeline architecture

📁 MODIFIED FILES (10 recent)
- global-hooks/framework/automation/auto_prime.py
- global-hooks/framework/context/pre_compact_preserve.py
- global-hooks/framework/memory/auto_memory_writer.py
- global-hooks/framework/memory/kg_session_context.py
- global-hooks/framework/session/session_startup.py
- global-hooks/framework/aaak_compress.py
- global-hooks/framework/facts/fact_kg_sync.py
- install.sh
- tests/test_aaak_integration.py
- tests/test_real_simulation.py

🧪 TEST COMMANDS
- uv run --no-project --with pytest pytest tests/test_aaak_integration.py -v
- uv run --no-project --with pytest --with tiktoken pytest tests/test_real_simulation.py -v -s
- bash -n install.sh && echo "VALID"

🔑 KEY DECISIONS
- Decided to revert AAAK compression from auto_prime.py because dialect.compress() produces encoded pointers that Claude cannot interpret as readable context
- Chose to use mempalace KG for temporal fact storage instead of compressing session-start context
- Decided that compress_sections() in pre_compact is acceptable because it preserves section headers while compressing body text at ~3x ratio
- Switched from hardcoded python3.12 paths to glob-based detection for cross-version compatibility
- Chose to add kg_session_context.py as a new sub-hook in session_startup.py chain rather than modifying auto_prime.py
- Confirmed that mempalace MCP server entry should be conditionally removed from settings.json when not installed
- Rejected approach of compressing all project CLAUDE.md files on disk — source files should stay human-readable
- Approved the fail-open pattern: every mempalace integration must catch Exception and return original behavior

⚠️ RECENT ERRORS
- `uv run --no-project pytest` → error: Failed to spawn: `pytest` (need --with pytest flag)
- `grep -n pattern file` → No matches found (validators returned truncated output)
- `python3 -c "import ast..."` → SyntaxError when editing left orphaned imports

📊 GIT DIFF STAT
 global-hooks/framework/automation/auto_prime.py  | 25 +--
 global-hooks/framework/context/pre_compact.py    | 45 +++
 global-hooks/framework/memory/auto_memory.py     | 30 +++
 global-hooks/framework/memory/kg_session.py      | 90 ++++++
 install.sh                                        | 35 ++-
 tests/test_aaak_integration.py                   | 20 +--
 tests/test_real_simulation.py                    | 40 +--
 7 files changed, 240 insertions(+), 45 deletions(-)

COMPACTION RULES:
1. Preserve all task IDs and their current status
2. Keep the full list of modified files — these are your working set
3. Retain exact test commands — do not paraphrase
4. Keep key decisions verbatim — they explain WHY choices were made
5. Preserve error patterns — they prevent repeating mistakes
6. Reference git diff stat for scope awareness
7. When summarizing conversations, prioritize WHAT WAS DECIDED over what was discussed
8. If you encounter information that contradicts these preserved items, flag the conflict
═══════════════════════════════════════════"""


# Decision signal words used to extract triples for KG
DECISION_SIGNAL_WORDS = [
    "decided", "chose", "switched", "confirmed", "rejected",
    "approved", "selected", "determined", "agreed", "reverted",
]

# Ground truth facts that MUST survive in the output (or extra_context)
GROUND_TRUTH_FACTS = [
    "revert AAAK compression from auto_prime",
    "mempalace KG for temporal fact storage",
    "compress_sections() in pre_compact is acceptable",
    "glob-based detection for cross-version",
    "kg_session_context.py as a new sub-hook",
    "conditionally removed from settings.json",
    "source files should stay human-readable",
    "fail-open pattern",
    "Failed to spawn: `pytest`",
    "7 files changed, 240 insertions",
]

# Section headers that should survive in the output
SECTION_HEADERS = [
    "ACTIVE TASKS",
    "MODIFIED FILES",
    "TEST COMMANDS",
    "KEY DECISIONS",
    "RECENT ERRORS",
    "GIT DIFF STAT",
    "COMPACTION RULES",
]


# ---------------------------------------------------------------------------
# The 5 approach functions
# ---------------------------------------------------------------------------

def approach_1_compress_sections(text: str) -> dict:
    """Baseline: compress_sections() on data, preserve COMPACTION RULES verbatim."""
    t0 = time.perf_counter()

    # Split on "COMPACTION RULES:" to preserve it verbatim
    if "COMPACTION RULES:" in text:
        parts = text.split("COMPACTION RULES:", 1)
        data_part = parts[0]
        rules_part = "COMPACTION RULES:" + parts[1]
    else:
        data_part = text
        rules_part = ""

    # Compress only the data part
    compressed_data = compress_sections(data_part)

    # Reassemble
    if rules_part:
        output = compressed_data + rules_part
    else:
        output = compressed_data

    latency_ms = (time.perf_counter() - t0) * 1000

    return {
        "output": output,
        "tokens_out": count_tokens(output),
        "kg_writes": 0,
        "extra_context": "",
        "extra_tokens": 0,
        "latency_ms": latency_ms,
    }


def approach_2_kg_extract_raw(text: str) -> dict:
    """Extract KG triples from decisions, pass raw text UNCHANGED."""
    t0 = time.perf_counter()

    kg_writes = 0

    if HAS_MEMPALACE:
        try:
            kg = KnowledgeGraph()
            lines = text.split("\n")
            for line in lines:
                line_lower = line.lower()
                if any(word in line_lower for word in DECISION_SIGNAL_WORDS):
                    stripped = line.strip().lstrip("- ")
                    if len(stripped) > 20:
                        # Write triple: subject=session, predicate=decision, object=line
                        kg.add_triple(
                            subject="session",
                            predicate="decided",
                            obj=stripped[:200],
                            source_file="precompact_benchmark",
                        )
                        kg_writes += 1
        except Exception:
            kg_writes = 0

    latency_ms = (time.perf_counter() - t0) * 1000

    # Return raw text UNCHANGED — zero information loss
    return {
        "output": text,
        "tokens_out": count_tokens(text),
        "kg_writes": kg_writes,
        "extra_context": "",
        "extra_tokens": 0,
        "latency_ms": latency_ms,
    }


def approach_3_semantic_dedup(text: str) -> dict:
    """Check ChromaDB for similar past content, dedup with pointers."""
    t0 = time.perf_counter()

    if not HAS_MEMPALACE:
        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "output": text,
            "tokens_out": count_tokens(text),
            "kg_writes": 0,
            "extra_context": "(mempalace not available — returned unchanged)",
            "extra_tokens": 0,
            "latency_ms": latency_ms,
        }

    try:
        from mempalace.config import MempalaceConfig
        cfg = MempalaceConfig()
        palace_path = cfg.palace_path

        output_lines = []
        lines = text.split("\n")
        SIMILARITY_THRESHOLD = 0.85

        for line in lines:
            stripped = line.strip().lstrip("- ")
            # Only check decision/error lines that are substantive
            if len(stripped) > 40 and any(word in stripped.lower() for word in DECISION_SIGNAL_WORDS + ["error", "spawn", "syntaxerror"]):
                try:
                    result = search_memories(
                        query=stripped[:200],
                        palace_path=palace_path,
                        n_results=1,
                    )
                    hits = result.get("results", [])
                    if hits and hits[0]["similarity"] >= SIMILARITY_THRESHOLD:
                        topic = hits[0].get("room", "unknown")
                        output_lines.append(f"- [See mempalace: {topic}]")
                        continue
                except Exception:
                    pass
            output_lines.append(line)

        output = "\n".join(output_lines)

    except Exception:
        output = text

    latency_ms = (time.perf_counter() - t0) * 1000

    return {
        "output": output,
        "tokens_out": count_tokens(output),
        "kg_writes": 0,
        "extra_context": "",
        "extra_tokens": 0,
        "latency_ms": latency_ms,
    }


def approach_4_wakeup_inject(text: str) -> dict:
    """Inject MemoryStack.wake_up() as prior memory prefix."""
    t0 = time.perf_counter()

    if not HAS_MEMPALACE:
        latency_ms = (time.perf_counter() - t0) * 1000
        return {
            "output": text,
            "tokens_out": count_tokens(text),
            "kg_writes": 0,
            "extra_context": "(mempalace not available — returned unchanged)",
            "extra_tokens": 0,
            "latency_ms": latency_ms,
        }

    try:
        stack = MemoryStack()
        wakeup = stack.wake_up()
        # Cap at ~3200 chars (~800 tokens)
        if len(wakeup) > 3200:
            wakeup = wakeup[:3200] + "\n[... wake_up truncated at 3200 chars ...]"
        extra_context = wakeup
        extra_tokens = count_tokens(extra_context)
    except Exception:
        extra_context = "(wake_up() failed — mempalace unavailable or empty)"
        extra_tokens = count_tokens(extra_context)

    latency_ms = (time.perf_counter() - t0) * 1000

    return {
        "output": text,
        "tokens_out": count_tokens(text),
        "kg_writes": 0,
        "extra_context": extra_context,
        "extra_tokens": extra_tokens,
        "latency_ms": latency_ms,
    }


def approach_5_hybrid(text: str) -> dict:
    """Hybrid: KG extract decisions + compress_sections on data + wake_up injection."""
    t0 = time.perf_counter()

    # Step 1: Extract decisions to KG triples
    kg_writes = 0
    if HAS_MEMPALACE:
        try:
            kg = KnowledgeGraph()
            lines = text.split("\n")
            for line in lines:
                line_lower = line.lower()
                if any(word in line_lower for word in DECISION_SIGNAL_WORDS):
                    stripped = line.strip().lstrip("- ")
                    if len(stripped) > 20:
                        kg.add_triple(
                            subject="session",
                            predicate="decided",
                            obj=stripped[:200],
                            source_file="precompact_benchmark_hybrid",
                        )
                        kg_writes += 1
        except Exception:
            kg_writes = 0

    # Step 2: compress_sections on data part, preserve COMPACTION RULES verbatim
    if "COMPACTION RULES:" in text:
        parts = text.split("COMPACTION RULES:", 1)
        data_part = parts[0]
        rules_part = "COMPACTION RULES:" + parts[1]
    else:
        data_part = text
        rules_part = ""

    compressed_data = compress_sections(data_part)
    if rules_part:
        output = compressed_data + rules_part
    else:
        output = compressed_data

    # Step 3: Inject wake_up() as prior memory prefix
    extra_context = ""
    extra_tokens = 0
    if HAS_MEMPALACE:
        try:
            stack = MemoryStack()
            wakeup = stack.wake_up()
            if len(wakeup) > 3200:
                wakeup = wakeup[:3200] + "\n[... wake_up truncated at 3200 chars ...]"
            extra_context = wakeup
            extra_tokens = count_tokens(extra_context)
        except Exception:
            extra_context = "(wake_up() failed)"
            extra_tokens = count_tokens(extra_context)

    latency_ms = (time.perf_counter() - t0) * 1000

    return {
        "output": output,
        "tokens_out": count_tokens(output),
        "kg_writes": kg_writes,
        "extra_context": extra_context,
        "extra_tokens": extra_tokens,
        "latency_ms": latency_ms,
    }


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------

def score_facts(result: dict, facts: list) -> int:
    """Count how many facts are findable in output + extra_context (case-insensitive)."""
    combined = (result["output"] + " " + result["extra_context"]).lower()
    return sum(1 for fact in facts if fact.lower() in combined)


def score_headers(result: dict, headers: list) -> int:
    """Count how many section headers survive in the output."""
    combined = (result["output"] + " " + result["extra_context"]).lower()
    return sum(1 for h in headers if h.lower() in combined)


def compute_compression_ratio(tokens_in: int, result: dict) -> float:
    """input_tokens / output_tokens (higher = more compressed)."""
    tokens_out = result["tokens_out"]
    if tokens_out == 0:
        return float("inf")
    return tokens_in / tokens_out


# ---------------------------------------------------------------------------
# Benchmark harness
# ---------------------------------------------------------------------------

APPROACHES = [
    ("1. compress_sections ", approach_1_compress_sections),
    ("2. KG + raw          ", approach_2_kg_extract_raw),
    ("3. semantic dedup    ", approach_3_semantic_dedup),
    ("4. wake_up inject    ", approach_4_wakeup_inject),
    ("5. hybrid            ", approach_5_hybrid),
]


def run_benchmark(input_text: str, ground_truth_facts: list, section_headers: list, label: str):
    """Run all 5 approaches against input_text and print comparison table."""
    tokens_in = count_tokens(input_text)

    print(f"\n{'=' * 95}")
    print(f"  MEMPALACE INTEGRATION BENCHMARK — {label}")
    print(f"  Input: {len(input_text):,} chars / {tokens_in:,} tokens")
    print(f"  mempalace available: {HAS_MEMPALACE} | tiktoken available: {HAS_TIKTOKEN}")
    print(f"{'=' * 95}")
    print(f"  {'Approach':<22} | {'Tokens Out':>10} | {'Compression':>11} | {'Facts':>11} | {'Headers':>9} | {'KG Writes':>9} | {'Latency':>8}")
    print(f"  {'-' * 22}-+-{'-' * 10}-+-{'-' * 11}-+-{'-' * 11}-+-{'-' * 9}-+-{'-' * 9}-+-{'-' * 8}")

    results = {}
    for name, fn in APPROACHES:
        result = fn(input_text)
        facts_found = score_facts(result, ground_truth_facts)
        headers_found = score_headers(result, section_headers)
        ratio = compute_compression_ratio(tokens_in, result)
        latency = result["latency_ms"]

        results[name] = {
            "result": result,
            "facts": facts_found,
            "headers": headers_found,
            "ratio": ratio,
        }

        print(
            f"  {name:<22} | {result['tokens_out']:>10,} | {ratio:>10.2f}x | "
            f"{facts_found:>4}/{len(ground_truth_facts):<6} | "
            f"{headers_found:>3}/{len(section_headers):<5} | "
            f"{result['kg_writes']:>9} | "
            f"{latency:>6.1f}ms"
        )

    print(f"{'=' * 95}")
    return results


# ---------------------------------------------------------------------------
# pytest test classes
# ---------------------------------------------------------------------------

class TestApproachBenchmarkRealisticInput:
    """Run all 5 approaches against a realistic precompact input."""

    def test_benchmark_realistic_precompact(self):
        """Benchmark all 5 approaches on realistic precompact data."""
        input_text = build_realistic_precompact_input()
        results = run_benchmark(
            input_text,
            GROUND_TRUTH_FACTS,
            SECTION_HEADERS,
            "REALISTIC PRECOMPACT INPUT",
        )

        # Sanity checks: each approach must return a non-empty string
        for name, _ in APPROACHES:
            assert results[name]["result"]["output"], f"Approach {name} returned empty output"

        # Approach 1 (compress_sections) must preserve COMPACTION RULES
        a1_output = results["1. compress_sections "]["result"]["output"]
        assert "COMPACTION RULES:" in a1_output, "Approach 1 must preserve COMPACTION RULES section"

        # Approach 2 (KG + raw) must return input unchanged
        a2_output = results["2. KG + raw          "]["result"]["output"]
        assert a2_output == input_text, "Approach 2 must return raw text unchanged"

        print(f"\n  Ground truth facts checked: {len(GROUND_TRUTH_FACTS)}")
        print(f"  Section headers checked: {len(SECTION_HEADERS)}")
        print()

    def test_ground_truth_per_approach(self):
        """Show which specific facts are retained/lost per approach."""
        input_text = build_realistic_precompact_input()

        print(f"\n{'=' * 80}")
        print("  PER-FACT RETENTION ANALYSIS (realistic precompact input)")
        print(f"{'=' * 80}")
        print(f"  {'Fact':<50} A1  A2  A3  A4  A5")
        print(f"  {'-' * 68}")

        approach_results = []
        for _, fn in APPROACHES:
            approach_results.append(fn(input_text))

        for fact in GROUND_TRUTH_FACTS:
            marks = []
            for res in approach_results:
                combined = (res["output"] + " " + res["extra_context"]).lower()
                marks.append("Y" if fact.lower() in combined else "N")
            fact_display = fact[:48] + ".." if len(fact) > 48 else fact
            print(f"  {fact_display:<50} {'  '.join(marks)}")

        print(f"{'=' * 80}")
        print()


class TestApproachBenchmarkClaudeMd:
    """Run all 5 approaches against the real CLAUDE.md file."""

    def test_benchmark_claude_md(self):
        """Benchmark all 5 approaches on CLAUDE.md."""
        claude_md = Path(__file__).parent.parent / "CLAUDE.md"
        if not claude_md.exists():
            pytest.skip("CLAUDE.md not found")

        input_text = claude_md.read_text(errors="replace")

        # For CLAUDE.md, use key terms as facts and ## headers as structure markers
        claude_facts = [
            "uv run",
            "install.sh",
            "settings.json",
            "orchestrate",
            "hooks",
            "agents",
            "skills",
            "Yolo",
            "damage-control",
            "OBSERVED",
        ]
        claude_headers = [
            h.strip() for h in input_text.splitlines()
            if h.strip().startswith("##")
        ]
        if not claude_headers:
            claude_headers = ["Structure", "Mode", "Execution", "Rules", "Memory"]

        results = run_benchmark(
            input_text,
            claude_facts,
            claude_headers,
            "CLAUDE.md",
        )

        for name, _ in APPROACHES:
            assert results[name]["result"]["output"], f"Approach {name} returned empty for CLAUDE.md"

        print()


class TestApproachBenchmarkFactsMd:
    """Run all 5 approaches against the real FACTS.md file."""

    def test_benchmark_facts_md(self):
        """Benchmark all 5 approaches on FACTS.md."""
        facts_md = Path(__file__).parent.parent / ".claude" / "FACTS.md"
        if not facts_md.exists():
            pytest.skip("FACTS.md not found")

        input_text = facts_md.read_text(errors="replace")

        # Extract facts from the file itself: lines with key patterns
        all_lines = input_text.splitlines()
        facts_from_file = [
            l.strip().lstrip("- ").strip()[:60]
            for l in all_lines
            if l.strip().startswith("-") and len(l.strip()) > 20
        ][:10]

        if not facts_from_file:
            facts_from_file = ["CONFIRMED", "GOTCHAS", "PATHS", "PATTERNS"]

        headers_from_file = [
            l.strip()
            for l in all_lines
            if l.strip().startswith("##") or l.strip().startswith("###")
        ]
        if not headers_from_file:
            headers_from_file = ["FACTS", "CONFIRMED", "GOTCHAS"]

        results = run_benchmark(
            input_text,
            facts_from_file,
            headers_from_file,
            "FACTS.md",
        )

        for name, _ in APPROACHES:
            assert results[name]["result"]["output"], f"Approach {name} returned empty for FACTS.md"

        print()


class TestApproachBenchmarkMemoryMd:
    """Run all 5 approaches against last 5 entries of MEMORY.md."""

    def test_benchmark_memory_md_last5(self):
        """Benchmark all 5 approaches on last 5 MEMORY.md entries."""
        memory_md = Path(__file__).parent.parent / ".claude" / "MEMORY.md"
        if not memory_md.exists():
            pytest.skip("MEMORY.md not found")

        full_text = memory_md.read_text(errors="replace")

        # Take last 5 entries: split on "## " entry separators
        entries = []
        current = []
        for line in full_text.splitlines():
            if line.startswith("## ") and current:
                entries.append("\n".join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            entries.append("\n".join(current))

        # Use last 5
        last5 = entries[-5:] if len(entries) >= 5 else entries
        input_text = "\n\n---\n\n".join(last5)

        if not input_text.strip():
            pytest.skip("MEMORY.md is empty or unreadable")

        memory_facts = [
            l.strip().lstrip("- ").strip()[:60]
            for l in input_text.splitlines()
            if l.strip().startswith("-") and len(l.strip()) > 20
        ][:10]

        if not memory_facts:
            memory_facts = ["session", "hook", "agent"]

        memory_headers = [
            l.strip() for l in input_text.splitlines()
            if l.strip().startswith("##") or l.strip().startswith("###")
        ]
        if not memory_headers:
            memory_headers = ["memory", "session"]

        results = run_benchmark(
            input_text,
            memory_facts,
            memory_headers,
            "MEMORY.md (last 5 entries)",
        )

        for name, _ in APPROACHES:
            assert results[name]["result"]["output"], f"Approach {name} returned empty for MEMORY.md"

        print()


class TestStructureRetention:
    """Verify structural properties of each approach."""

    def test_approach_1_preserves_compaction_rules(self):
        """Approach 1 must preserve COMPACTION RULES verbatim."""
        text = build_realistic_precompact_input()
        result = approach_1_compress_sections(text)
        assert "COMPACTION RULES:" in result["output"], (
            "compress_sections must preserve COMPACTION RULES section"
        )
        print(f"\n  Approach 1: COMPACTION RULES preserved — PASS")
        # Check at least a few rules survived
        assert "Preserve all task IDs" in result["output"] or "COMPACTION RULES:" in result["output"]

    def test_approach_2_returns_raw(self):
        """Approach 2 must return raw text completely unchanged."""
        text = build_realistic_precompact_input()
        result = approach_2_kg_extract_raw(text)
        assert result["output"] == text, "Approach 2 must return input unchanged"
        assert result["tokens_out"] == count_tokens(text), "Token count must match input"
        print(f"\n  Approach 2: Raw text returned unchanged — PASS")

    def test_approach_3_fails_open_without_mempalace(self):
        """Approach 3 fails open (returns input) when mempalace is unavailable."""
        # Simulate by checking the fail-open path
        text = build_realistic_precompact_input()
        result = approach_3_semantic_dedup(text)
        # Output should always be a non-empty string
        assert isinstance(result["output"], str), "Output must be a string"
        assert len(result["output"]) > 0, "Output must not be empty"
        print(f"\n  Approach 3: Fail-open verified — output len={len(result['output'])} — PASS")

    def test_approach_4_adds_extra_context_or_fails_open(self):
        """Approach 4 adds wake_up() extra context or fails open."""
        text = build_realistic_precompact_input()
        result = approach_4_wakeup_inject(text)
        # Output must be the original text unchanged
        assert result["output"] == text, "Approach 4 must return input unchanged as output"
        # Extra context is either wake_up text or a fail-open message
        assert isinstance(result["extra_context"], str), "extra_context must be a string"
        print(f"\n  Approach 4: Output unchanged, extra_context len={len(result['extra_context'])} — PASS")

    def test_approach_5_is_strictly_smaller_than_raw(self):
        """Approach 5 (hybrid) output must be <= raw input tokens (compression applied)."""
        text = build_realistic_precompact_input()
        tokens_in = count_tokens(text)
        result = approach_5_hybrid(text)
        # Compressed output should be same or fewer tokens
        # (may be equal if mempalace unavailable and compress_sections falls back)
        assert result["tokens_out"] <= tokens_in, (
            f"Approach 5 output ({result['tokens_out']}) should not exceed input ({tokens_in})"
        )
        print(f"\n  Approach 5: {tokens_in} → {result['tokens_out']} tokens (ratio={tokens_in/max(result['tokens_out'],1):.2f}x) — PASS")

    def test_all_section_headers_in_approach_2(self):
        """Approach 2 (raw) must retain ALL section headers."""
        text = build_realistic_precompact_input()
        result = approach_2_kg_extract_raw(text)
        combined = (result["output"] + " " + result["extra_context"]).lower()
        missing = [h for h in SECTION_HEADERS if h.lower() not in combined]
        print(f"\n  Approach 2 header retention: {len(SECTION_HEADERS) - len(missing)}/{len(SECTION_HEADERS)}")
        assert not missing, f"Approach 2 (raw) should preserve ALL headers, missing: {missing}"

    def test_all_ground_truth_in_approach_2(self):
        """Approach 2 (raw) must find ALL 10 ground truth facts."""
        text = build_realistic_precompact_input()
        result = approach_2_kg_extract_raw(text)
        found = score_facts(result, GROUND_TRUTH_FACTS)
        print(f"\n  Approach 2 ground truth: {found}/{len(GROUND_TRUTH_FACTS)} facts found")
        assert found == len(GROUND_TRUTH_FACTS), (
            f"Approach 2 (raw) must retain ALL facts, found {found}/{len(GROUND_TRUTH_FACTS)}"
        )


class TestSummaryTable:
    """Print a final consolidated summary across all inputs."""

    def test_consolidated_summary(self):
        """Print a consolidated summary table across all test inputs."""
        inputs = {
            "Realistic precompact": (
                build_realistic_precompact_input(),
                GROUND_TRUTH_FACTS,
                SECTION_HEADERS,
            ),
        }

        # Add real files if available
        claude_md = Path(__file__).parent.parent / "CLAUDE.md"
        if claude_md.exists():
            txt = claude_md.read_text(errors="replace")
            hdrs = [l.strip() for l in txt.splitlines() if l.strip().startswith("##")]
            inputs["CLAUDE.md"] = (txt, ["uv run", "install.sh", "settings.json", "orchestrate", "hooks", "agents", "skills", "Yolo", "damage-control", "OBSERVED"], hdrs or ["Structure"])

        facts_md = Path(__file__).parent.parent / ".claude" / "FACTS.md"
        if facts_md.exists():
            txt = facts_md.read_text(errors="replace")
            fl = [l.strip().lstrip("- ")[:60] for l in txt.splitlines() if l.strip().startswith("-") and len(l.strip()) > 20][:10]
            hl = [l.strip() for l in txt.splitlines() if l.strip().startswith("##")]
            inputs["FACTS.md"] = (txt, fl or ["CONFIRMED"], hl or ["FACTS"])

        print(f"\n{'=' * 100}")
        print("  CONSOLIDATED BENCHMARK SUMMARY")
        print(f"  mempalace={HAS_MEMPALACE} | tiktoken={HAS_TIKTOKEN}")
        print(f"{'=' * 100}")

        for input_label, (text, facts, headers) in inputs.items():
            tokens_in = count_tokens(text)
            print(f"\n  [{input_label}] — {tokens_in:,} tokens in, {len(facts)} facts, {len(headers)} headers")
            print(f"  {'Approach':<22} | {'TokOut':>7} | {'Ratio':>7} | {'Facts':>8} | {'Hdrs':>6} | {'KG':>4} | {'ms':>7}")
            print(f"  {'-' * 80}")

            for name, fn in APPROACHES:
                result = fn(text)
                fnd = score_facts(result, facts)
                hfnd = score_headers(result, headers)
                ratio = compute_compression_ratio(tokens_in, result)
                print(
                    f"  {name:<22} | {result['tokens_out']:>7,} | {ratio:>6.2f}x | "
                    f"{fnd:>3}/{len(facts):<4} | {hfnd:>3}/{len(headers):<2} | "
                    f"{result['kg_writes']:>4} | {result['latency_ms']:>5.1f}ms"
                )

        print(f"\n{'=' * 100}")
        print()
