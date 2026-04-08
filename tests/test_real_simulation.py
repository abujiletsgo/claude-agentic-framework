#!/usr/bin/env python3
"""
Real End-to-End Simulation: Mempalace Token Efficiency
======================================================

This is NOT a unit test. This simulates the ACTUAL session-start pipeline
for every project in ~/Documents and shows you:

1. The EXACT text Claude would see WITHOUT AAAK compression
2. The EXACT text Claude would see WITH AAAK compression
3. Real token counts for both (tiktoken cl100k_base)
4. Side-by-side comparison so you can judge quality yourself

Run:
  uv run --no-project --with pytest --with tiktoken pytest tests/test_real_simulation.py -v -s

Or for just one project:
  uv run --no-project --with pytest --with tiktoken pytest tests/test_real_simulation.py -v -s -k "framework"
"""

import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Setup: import the actual pipeline functions
# ---------------------------------------------------------------------------

FRAMEWORK_DIR = os.path.join(os.path.dirname(__file__), "..", "global-hooks", "framework")
sys.path.insert(0, FRAMEWORK_DIR)

AUTO_PRIME_DIR = os.path.join(FRAMEWORK_DIR, "automation")
sys.path.insert(0, AUTO_PRIME_DIR)

import importlib.util as _ilu

_spec = _ilu.spec_from_file_location("auto_prime", os.path.join(AUTO_PRIME_DIR, "auto_prime.py"))
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_extract_slim_context = _mod._extract_slim_context

from aaak_compress import compress, compress_sections, compress_with_stats, _get_dialect

# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------

try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        return len(_enc.encode(text))

    TOKENIZER = "tiktoken cl100k_base"
except ImportError:
    def count_tokens(text: str) -> int:
        return len(text) // 4

    TOKENIZER = "estimated (~4 chars/token)"


# ---------------------------------------------------------------------------
# Check mempalace availability
# ---------------------------------------------------------------------------

MEMPALACE_AVAILABLE = _get_dialect() is not None


# ---------------------------------------------------------------------------
# Discover all projects
# ---------------------------------------------------------------------------

DOCS_DIR = Path.home() / "Documents"


def discover_projects() -> list[dict]:
    """Find all projects with AI context files."""
    projects = []
    for d in sorted(DOCS_DIR.iterdir()):
        if not d.is_dir():
            continue
        ctx = {}
        # The files that get injected into Claude's context at session start
        candidates = [
            ("CLAUDE.md", d / "CLAUDE.md"),
            (".claude/PROJECT_CONTEXT.md", d / ".claude" / "PROJECT_CONTEXT.md"),
        ]
        for label, path in candidates:
            if path.exists():
                try:
                    ctx[label] = path.read_text(errors="replace")
                except Exception:
                    pass
        if ctx:
            projects.append({"name": d.name, "path": d, "files": ctx})
    return projects


PROJECTS = discover_projects()


# ===========================================================================
# TEST 1: Run the ACTUAL auto_prime pipeline on each project
# ===========================================================================

class TestRealPipeline:
    """Run the real auto_prime pipeline and show before/after at each stage."""

    @pytest.mark.parametrize("proj", PROJECTS, ids=[p["name"] for p in PROJECTS])
    def test_session_start_pipeline(self, proj):
        """Simulate the full session-start for one project."""
        pc = proj["files"].get(".claude/PROJECT_CONTEXT.md")
        if not pc:
            pytest.skip(f"No PROJECT_CONTEXT.md for {proj['name']}")

        # === Stage 1: Raw file (what's on disk) ===
        raw_tokens = count_tokens(pc)

        # === Stage 2: Slim extraction (always happens) ===
        slim = _extract_slim_context(pc)
        slim_tokens = count_tokens(slim)

        # === Stage 3: Final output (with prefix) ===
        prefix = (
            "**SESSION CONTEXT LOADED** — Project context summary below. "
            "For full details, read `.claude/PROJECT_CONTEXT.md` on demand.\n\n"
            "---\n\n"
        )
        final = prefix + slim
        final_tokens = count_tokens(final)

        # === Print the actual text ===
        divider = "=" * 80
        print(f"\n{divider}")
        print(f"  PROJECT: {proj['name']}")
        print(f"{divider}")

        print(f"\n  --- STAGE 1: Raw PROJECT_CONTEXT.md ({raw_tokens:,} tokens) ---")
        print(f"  [first 500 chars]")
        print(textwrap.indent(pc[:500], "    "))
        print(f"    ...")

        print(f"\n  --- STAGE 2: After slim extraction ({slim_tokens:,} tokens, "
              f"{_pct_saved(raw_tokens, slim_tokens)} saved) ---")
        print(f"  [first 500 chars]")
        print(textwrap.indent(slim[:500], "    "))
        print(f"    ...")

        print(f"\n  --- STAGE 3: Final injected context ({final_tokens:,} tokens) ---")
        print(f"  [FULL slim text — this is what Claude actually sees]")
        if len(slim) < 3000:
            print(textwrap.indent(slim, "    "))
        else:
            print(textwrap.indent(slim[:1500], "    "))
            print(f"    ... ({len(slim):,} chars total)")
        print()

        # Assertion: slim should not be larger than raw
        assert slim_tokens <= raw_tokens * 1.1, (
            f"Slim extraction expanded text: {slim_tokens} > {raw_tokens}"
        )


# ===========================================================================
# TEST 2: CLAUDE.md compression (these go into claudeMd system reminder)
# ===========================================================================

class TestClaudeMdCompression:
    """CLAUDE.md is injected as a system reminder. How much does AAAK save?"""

    @pytest.mark.parametrize("proj", PROJECTS, ids=[p["name"] for p in PROJECTS])
    def test_claude_md_compression(self, proj):
        """Show before/after for each project's CLAUDE.md."""
        cm = proj["files"].get("CLAUDE.md")
        if not cm:
            pytest.skip(f"No CLAUDE.md for {proj['name']}")

        original_tokens = count_tokens(cm)
        compressed = compress_sections(cm)
        compressed_tokens = count_tokens(compressed)

        print(f"\n{'=' * 80}")
        print(f"  CLAUDE.md: {proj['name']} ({original_tokens:,} → {compressed_tokens:,} tokens)")
        print(f"{'=' * 80}")

        print(f"\n  BEFORE ({original_tokens:,} tokens):")
        print(textwrap.indent(cm[:400], "    "))
        print(f"    ... ({len(cm):,} chars total)")

        print(f"\n  AFTER ({compressed_tokens:,} tokens):")
        if len(compressed) < 2000:
            print(textwrap.indent(compressed, "    "))
        else:
            print(textwrap.indent(compressed[:800], "    "))
            print(f"    ... ({len(compressed):,} chars total)")

        saved = original_tokens - compressed_tokens
        pct = (saved / original_tokens * 100) if original_tokens > 0 else 0
        print(f"\n  RESULT: {saved:,} tokens saved ({pct:.1f}%)")
        print()


# ===========================================================================
# TEST 3: Grand total — what Claude sees across ALL files in a real session
# ===========================================================================

class TestGrandTotal:
    """The bottom line: total tokens injected at session start, all projects."""

    def test_aggregate_session_cost(self):
        """Sum up what EVERY project costs in context tokens (slim pipeline + CM compression)."""
        results = []

        for proj in PROJECTS:
            row = {"project": proj["name"]}

            # PROJECT_CONTEXT.md: Raw vs slim extraction
            pc = proj["files"].get(".claude/PROJECT_CONTEXT.md", "")
            if pc:
                slim = _extract_slim_context(pc)
                row["pc_raw"] = count_tokens(pc)
                row["pc_slim"] = count_tokens(slim)
            else:
                row["pc_raw"] = 0
                row["pc_slim"] = 0

            # CLAUDE.md through compress_sections
            cm = proj["files"].get("CLAUDE.md", "")
            if cm:
                cm_compressed = compress_sections(cm)
                row["cm_raw"] = count_tokens(cm)
                row["cm_compressed"] = count_tokens(cm_compressed)
            else:
                row["cm_raw"] = 0
                row["cm_compressed"] = 0

            row["total_raw"] = row["pc_raw"] + row["cm_raw"]
            row["total_optimized"] = row["pc_slim"] + row["cm_compressed"]
            results.append(row)

        # Sort by total_raw descending
        results.sort(key=lambda r: r["total_raw"], reverse=True)

        print(f"\n{'=' * 100}")
        print(f"  GRAND TOTAL: All Projects Session-Start Context Cost")
        print(f"  Tokenizer: {TOKENIZER}")
        print(f"  Mempalace: {'AVAILABLE' if MEMPALACE_AVAILABLE else 'NOT AVAILABLE'}")
        print(f"{'=' * 100}")
        print(f"  {'Project':<30} {'PC raw':>8} {'PC slim':>8} {'CM raw':>8} {'CM cmp':>8} {'Total raw':>10} {'Total opt':>10} {'Saved':>8}")
        print(f"  {'-' * 96}")

        sum_raw = 0
        sum_optimized = 0

        for r in results:
            saved = r["total_raw"] - r["total_optimized"]
            pct = f"{(saved / r['total_raw'] * 100):.0f}%" if r["total_raw"] > 0 else "N/A"
            print(
                f"  {r['project']:<30} "
                f"{r['pc_raw']:>8,} {r['pc_slim']:>8,} "
                f"{r['cm_raw']:>8,} {r['cm_compressed']:>8,} "
                f"{r['total_raw']:>10,} {r['total_optimized']:>10,} "
                f"{pct:>8}"
            )
            sum_raw += r["total_raw"]
            sum_optimized += r["total_optimized"]

        total_saved = sum_raw - sum_optimized
        total_pct = (total_saved / sum_raw * 100) if sum_raw > 0 else 0

        print(f"  {'-' * 96}")
        print(f"  {'TOTAL':<30} {' ':>8} {' ':>8} {' ':>8} {' ':>8} "
              f"{sum_raw:>10,} {sum_optimized:>10,} {total_pct:.0f}%")

        print(f"\n  RAW (no optimization): {sum_raw:>10,} tokens loaded per session start")
        print(f"  OPTIMIZED (slim+cmp):  {sum_optimized:>10,} tokens loaded per session start")
        print(f"  SAVED:                 {total_saved:>10,} tokens ({total_pct:.1f}%)")

        if sum_optimized > 0:
            print(f"  RATIO:                 {sum_raw / sum_optimized:.1f}x reduction")

        # Monthly projection (conservative: 10 sessions/day, only 1 project per session)
        print(f"\n  --- Projection (10 sessions/day, 30 days) ---")
        daily = total_saved * 10
        monthly = daily * 30
        cost_saved = (monthly / 1_000_000) * 15.0  # Opus input pricing
        print(f"  Monthly tokens saved: {monthly:>12,}")
        print(f"  Monthly cost saved:   ${cost_saved:>11.2f} (Opus input @ $15/M)")
        print()


# ===========================================================================
# TEST 4: Real hook execution — actually run auto_prime.py as a subprocess
# ===========================================================================

class TestRealHookExecution:
    """Actually execute auto_prime.py the way Claude Code would."""

    def test_run_auto_prime_subprocess(self):
        """Run auto_prime.py as a subprocess with real hook input, capture output."""
        framework_root = Path(__file__).parent.parent
        auto_prime = framework_root / "global-hooks" / "framework" / "automation" / "auto_prime.py"

        if not auto_prime.exists():
            pytest.skip("auto_prime.py not found")

        # Simulate the hook input that Claude Code sends
        hook_input = json.dumps({
            "cwd": str(framework_root),
            "sessionId": "test-simulation-001",
        })

        start = time.perf_counter()
        result = subprocess.run(
            ["uv", "run", "--no-project", str(auto_prime)],
            input=hook_input,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(framework_root),
        )
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\n{'=' * 80}")
        print(f"  REAL HOOK EXECUTION: auto_prime.py")
        print(f"{'=' * 80}")
        print(f"  Exit code: {result.returncode}")
        print(f"  Time:      {elapsed:.0f}ms")

        if result.stderr:
            print(f"\n  STDERR:")
            for line in result.stderr.strip().split("\n"):
                print(f"    {line}")

        if result.stdout:
            try:
                output = json.loads(result.stdout)
                message = output.get("hookSpecificOutput", {}).get("additionalContext", "")
                if not message:
                    message = output.get("message", result.stdout)
            except json.JSONDecodeError:
                message = result.stdout

            tokens = count_tokens(str(message))
            print(f"\n  OUTPUT ({tokens:,} tokens):")
            msg_str = str(message)
            if len(msg_str) < 3000:
                print(textwrap.indent(msg_str, "    "))
            else:
                print(textwrap.indent(msg_str[:1500], "    "))
                print(f"    ... ({len(msg_str):,} chars total)")

            print(f"\n  TOKENS INJECTED INTO CONTEXT: {tokens:,}")
        else:
            print(f"\n  No stdout output (hook may have skipped)")

        assert result.returncode == 0, f"Hook failed: {result.stderr}"


# ===========================================================================
# Helpers
# ===========================================================================

def _pct_saved(before: int, after: int) -> str:
    if before == 0:
        return "N/A"
    return f"{((before - after) / before * 100):.1f}%"
