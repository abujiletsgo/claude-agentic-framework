#!/usr/bin/env python3
"""
fact_manager.py - Core library for FACTS.md (Layer 2: Episodic Memory)
=======================================================================

Manages per-project FACTS.md — the living fact sheet that prevents hallucination.
FACTS.md is the Episodic Memory layer: project-scoped, verified by execution,
injected at every session start as authoritative ground truth.

Layers:
  CONFIRMED — verified by execution, trust fully (confidence 1.0)
  GOTCHAS   — known failure modes, read before acting (confidence 0.9)
  PATHS     — key file paths and architecture (confidence 0.85)
  PATTERNS  — confirmed working command sequences (confidence 0.8)
  STALE     — contradicted or superseded, do not use (confidence 0.0)

Location: {project_root}/.claude/FACTS.md
"""

import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

FACTS_TEMPLATE = """\
# Project Facts
<!-- MANAGED: {project} | updated: {date} | layer: episodic -->
<!-- Injected at session start as authoritative ground truth. -->
<!-- Edit freely — hooks auto-maintain this file. -->

## ✓ CONFIRMED (execution-verified — trust fully)

## ⚠ GOTCHAS (known failure modes — read before acting)

## 📁 PATHS & ARCHITECTURE (key files, entry points, config)

## → PATTERNS (confirmed working sequences)

## ✗ STALE (superseded or disproven — do not use)
"""

SECTION_HEADERS = {
    "CONFIRMED": "## ✓ CONFIRMED",
    "GOTCHAS": "## ⚠ GOTCHAS",
    "PATHS": "## 📁 PATHS & ARCHITECTURE",
    "PATTERNS": "## → PATTERNS",
    "STALE": "## ✗ STALE",
}

STALE_PRUNE_DAYS = 90
DEDUP_THRESHOLD = 0.60  # Word overlap ratio for duplicate detection


def facts_path(cwd: str | None = None) -> Path:
    """Return path to FACTS.md for the current project."""
    return Path(cwd or os.getcwd()).resolve() / ".claude" / "FACTS.md"


def read(path: Path) -> str:
    """Read FACTS.md content, empty string if missing."""
    try:
        return path.read_text()
    except FileNotFoundError:
        return ""


def init(path: Path, project: str) -> str:
    """Create FACTS.md from template. Returns the content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    content = FACTS_TEMPLATE.format(project=project, date=today)
    path.write_text(content)
    return content


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_-]+", text.lower()))


def _is_duplicate(entry: str, section_text: str) -> bool:
    """Fuzzy duplicate check against existing entries in a section."""
    ew = _words(entry)
    if not ew:
        return False
    for line in section_text.splitlines():
        if not line.strip().startswith("- "):
            continue
        lw = _words(line)
        if not lw:
            continue
        overlap = len(ew & lw) / max(len(ew), len(lw))
        if overlap >= DEDUP_THRESHOLD:
            return True
    return False


def add(path: Path, category: str, entry: str, project: str = "unknown") -> bool:
    """
    Add a fact to the specified category.
    Returns True if added, False if duplicate or error.
    """
    content = read(path)
    if not content:
        content = init(path, project)

    header = SECTION_HEADERS.get(category)
    if not header:
        return False

    h_idx = content.find(header)
    if h_idx == -1:
        return False

    # Find section end (next ## header or EOF)
    after_h = content[h_idx + len(header):]
    next_h = re.search(r"\n## ", after_h)
    if next_h:
        section_end = h_idx + len(header) + next_h.start()
    else:
        section_end = len(content)

    section = content[h_idx:section_end]

    if _is_duplicate(entry, section):
        return False

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_entry = f"- {entry} [{today}]"

    new_section = section.rstrip() + f"\n{new_entry}\n"
    new_content = (
        content[:h_idx]
        + new_section
        + content[section_end:]
    )
    # Update header timestamp
    new_content = re.sub(
        r"<!-- MANAGED: [^|]+ \| updated: [0-9-]+ \|",
        f"<!-- MANAGED: {project} | updated: {today} |",
        new_content,
    )
    path.write_text(new_content)
    return True


def move_to_stale(path: Path, pattern: str) -> bool:
    """Move a matching entry to the STALE section. Returns True if moved."""
    content = read(path)
    if not content:
        return False

    lines = content.splitlines()
    stale_idx = None
    entry_idx = None
    entry_line = None

    for i, line in enumerate(lines):
        if "## ✗ STALE" in line:
            stale_idx = i
        elif (
            stale_idx is None
            and line.strip().startswith("- ")
            and pattern.lower() in line.lower()
        ):
            entry_idx = i
            entry_line = line

    if entry_idx is None or stale_idx is None:
        return False

    # Remove from current location
    lines.pop(entry_idx)
    if entry_idx < stale_idx:
        stale_idx -= 1

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stale_entry = entry_line.rstrip() + f" [stale:{today}]"
    lines.insert(stale_idx + 1, stale_entry)
    path.write_text("\n".join(lines))
    return True


def prune_stale(path: Path) -> int:
    """Remove STALE entries older than STALE_PRUNE_DAYS. Returns count removed."""
    content = read(path)
    if not content:
        return 0

    threshold = datetime.now(timezone.utc) - timedelta(days=STALE_PRUNE_DAYS)
    lines = content.splitlines()
    in_stale = False
    filtered = []
    removed = 0

    for line in lines:
        if "## ✗ STALE" in line:
            in_stale = True
            filtered.append(line)
            continue

        if in_stale and line.strip().startswith("- "):
            date_m = re.search(r"\[(?:stale:)?(\d{4}-\d{2}-\d{2})", line)
            if date_m:
                try:
                    entry_date = datetime.strptime(
                        date_m.group(1), "%Y-%m-%d"
                    ).replace(tzinfo=timezone.utc)
                    if entry_date < threshold:
                        removed += 1
                        continue
                except ValueError:
                    pass

        filtered.append(line)

    if removed > 0:
        path.write_text("\n".join(filtered))

    return removed


def get_for_injection(path: Path, max_chars: int = 3000) -> str:
    """
    Get FACTS.md content formatted for context injection.
    Prioritizes: CONFIRMED > GOTCHAS > PATHS > PATTERNS > STALE(excluded).
    """
    content = read(path)
    if not content:
        return ""

    # Drop the STALE section from injection — it's noise
    stale_idx = content.find("## ✗ STALE")
    if stale_idx != -1:
        content = content[:stale_idx].rstrip()

    # Remove sections with only placeholder/empty content
    # (sections with no "- " entries)
    def _has_entries(section_text: str) -> bool:
        return bool(re.search(r"^- .+", section_text, re.MULTILINE))

    parts = re.split(r"(## [^\n]+\n)", content)
    result_parts = []
    i = 0
    while i < len(parts):
        if parts[i].startswith("## "):
            body = parts[i + 1] if i + 1 < len(parts) else ""
            if _has_entries(body):
                result_parts.append(parts[i] + body)
            i += 2
        else:
            result_parts.append(parts[i])
            i += 1

    result = "".join(result_parts).rstrip()
    if not result:
        return ""

    return result[:max_chars] if len(result) > max_chars else result


def count_facts(path: Path) -> dict[str, int]:
    """Count facts per category."""
    content = read(path)
    if not content:
        return {}

    counts = {}
    for cat, header in SECTION_HEADERS.items():
        section_start = content.find(header)
        if section_start == -1:
            counts[cat] = 0
            continue
        after = content[section_start + len(header):]
        next_h = re.search(r"\n## ", after)
        section = after[: next_h.start()] if next_h else after
        counts[cat] = len(re.findall(r"^- .+", section, re.MULTILINE))

    return counts
