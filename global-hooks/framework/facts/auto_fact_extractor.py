#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
auto_fact_extractor.py - PostToolUse Hook (Layer 2: Episodic Memory Write)
===========================================================================

Extracts verifiable facts from tool interactions and updates FACTS.md.
This is the "encoding" phase of the episodic memory layer.

Strategy: pattern-based extraction only (no LLM calls — must be fast).
Conservative: only extracts high-confidence facts. Better 5 good than 50 mediocre.

Rules:
  Bash success + known pattern  → CONFIRMED fact
  Bash failure + known pattern  → GOTCHA fact
  Write to key file             → PATHS fact
  Repeated pattern detected     → PATTERNS fact

Does NOT extract: trivial commands (ls, cat, echo), read-only operations,
or commands already generically documented.

Exit: always 0 (never blocks)
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fact_manager import facts_path, add

# ---------------------------------------------------------------------------
# Rules: Bash successes → CONFIRMED
# Each tuple: (pattern_on_command, fact_text)
# ---------------------------------------------------------------------------
CONFIRMED_PATTERNS = [
    (r"\buv run\b", "Python executor is `uv run` (not python3/pip/poetry)"),
    (r"\bbash install\.sh\b", "`bash install.sh` regenerates config, symlinks, and docs from templates"),
    (r"\bpnpm\b", "JS package manager is `pnpm` (not npm/yarn)"),
    (r"\bbun run\b", "JS runtime/runner is `bun`"),
    (r"\bdocker compose\b", "Container orchestration: `docker compose` (not docker-compose)"),
    (r"\bmake\b.*build", "Build command is `make build`"),
    (r"\bcargo\b.*build", "Rust project — build with `cargo build`, run with `cargo run`"),
    (r"\bgo build\b", "Go project — build with `go build`"),
    (r"\bdeno\b", "JS runtime is `deno` (not node/bun)"),
]

# ---------------------------------------------------------------------------
# Rules: Bash failures (exit ≠ 0) → GOTCHA
# Each tuple: (pattern_on_output, fact_fn_or_text)
# fact_fn receives re.Match object, returns string
# ---------------------------------------------------------------------------
GOTCHA_PATTERNS = [
    (
        r"command not found[:\s]+(['\"`]?)(\S+)\1",
        lambda m: f"`{m.group(2)}` not installed — check PATH or use an alternative",
    ),
    (
        r"No module named ['\"]([^'\"]+)['\"]",
        lambda m: f"Python module `{m.group(1)}` missing — install with `uv add {m.group(1)}`",
    ),
    (
        r"Cannot find module ['\"]([^'\"]+)['\"]",
        lambda m: f"Node module `{m.group(1)}` missing — run package install first",
    ),
    (
        r"permission denied.*?(/\S+)",
        lambda m: f"Permission denied on `{m.group(1)}` — check chmod or sudo requirements",
    ),
    (
        r"address already in use.*?:(\d+)",
        lambda m: f"Port {m.group(1)} conflict — kill existing process before starting",
    ),
    (
        r"ENOENT.*?'([^']+)'",
        lambda m: f"File not found: `{m.group(1)}` — check path before referencing",
    ),
    (
        r"uv: command not found",
        "uv not installed — install with: curl -LsSf https://astral.sh/uv/install.sh | sh",
    ),
    (
        r"syntax error near unexpected token",
        "Shell syntax error — check for missing quotes or incorrect bash syntax",
    ),
    (
        r"error: could not find `Cargo.toml`",
        "Must be in a Rust crate directory to run cargo commands",
    ),
]

# ---------------------------------------------------------------------------
# Rules: Write tool → PATHS facts
# Only track architecturally significant paths
# ---------------------------------------------------------------------------
KEY_PATH_PATTERNS = [
    r"^\.claude/",
    r"^templates/",
    r"^global-hooks/",
    r"^global-agents/",
    r"^global-skills/",
    r"^global-commands/",
    r"^data/",
    r"^docs/",
    r"^scripts/",
    r"[Cc][Oo][Nn][Ff][Ii][Gg]\.",
    r"settings\.(json|yaml|toml)",
    r"pyproject\.toml$",
    r"Makefile$",
    r"Dockerfile$",
    r"\.env\.",
]

# Commands to skip entirely (too generic, no project-specific value)
SKIP_CMD_PATTERNS = [
    r"^(ls|ll|cat|echo|pwd|cd|which|type|env|printenv|date|whoami|id)\b",
    r"^git (status|log|diff|show|branch|fetch)\b",
    r"^(grep|rg|find|awk|sed|head|tail|wc)\b",
    r"^(curl|wget)\s+https?://",
    r"^(python3?|node|npm) -[cV]",
]


def should_skip_cmd(cmd: str) -> bool:
    return any(re.match(p, cmd.strip()) for p in SKIP_CMD_PATTERNS)


def extract_from_bash(
    cmd: str, output: str, is_error: bool
) -> list[tuple[str, str]]:
    """Extract facts from a Bash tool call."""
    facts = []

    # Skip trivial commands for CONFIRMED extraction only.
    # For errors (is_error=True), still check GOTCHA patterns — a failed
    # "generic" command can still reveal useful failure modes.
    if should_skip_cmd(cmd) and not is_error:
        return facts

    if not is_error:
        # Success: check for CONFIRMED patterns
        for pattern, fact in CONFIRMED_PATTERNS:
            if re.search(pattern, cmd):
                facts.append(("CONFIRMED", fact))
                break  # One confirmed fact per command
    else:
        # Failure: check for GOTCHA patterns in combined output
        for pattern, fact_or_fn in GOTCHA_PATTERNS:
            m = re.search(pattern, output, re.IGNORECASE)
            if m:
                fact = fact_or_fn(m) if callable(fact_or_fn) else fact_or_fn
                facts.append(("GOTCHAS", fact))
                break  # One gotcha per error

    return facts


def extract_from_write(file_path: str, cwd: str) -> list[tuple[str, str]]:
    """Extract PATHS facts from a Write tool call."""
    facts = []

    try:
        rel = str(Path(file_path).relative_to(cwd))
    except ValueError:
        rel = file_path

    for pattern in KEY_PATH_PATTERNS:
        if re.search(pattern, rel):
            # Only note files that are non-obvious (not generic src/index.ts)
            facts.append(("PATHS", f"Key file: `{rel}`"))
            break

    return facts


def get_project_name(cwd: str) -> str:
    return Path(cwd).resolve().name


def get_git_author(cwd: str) -> str:
    """Get git user.name for attribution tagging. Falls back to email username."""
    try:
        r = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True, text=True, cwd=cwd, timeout=3
        )
        name = r.stdout.strip()
        if name:
            return name
        r2 = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True, text=True, cwd=cwd, timeout=3
        )
        email = r2.stdout.strip()
        if email:
            return email.split("@")[0]
    except Exception:
        pass
    return ""


def main():
    try:
        data = json.loads(sys.stdin.read())
        tool = data.get("tool_name", "")
        inp = data.get("tool_input", {}) or {}
        resp = data.get("tool_response", {})
        cwd = data.get("cwd", os.getcwd())

        project = get_project_name(cwd)
        path = facts_path(cwd)
        author = get_git_author(cwd)

        facts: list[tuple[str, str]] = []

        if tool == "Bash":
            cmd = inp.get("command", "")
            if isinstance(resp, dict):
                output = resp.get("output", "")
                is_error = bool(resp.get("isError", False))
            else:
                output = str(resp)
                is_error = False
            facts = extract_from_bash(cmd, output, is_error)

        elif tool == "Write":
            file_path = inp.get("file_path", "")
            if file_path:
                facts = extract_from_write(file_path, cwd)

        for category, entry in facts:
            add(path, category, entry, project, author)

    except Exception as e:
        print(f"auto_fact_extractor error: {e}", file=sys.stderr)

    print(json.dumps({"result": "continue"}))
    sys.exit(0)


if __name__ == "__main__":
    main()
