#!/usr/bin/env python3
"""
fact_kg_sync.py — Sync FACTS.md entries to mempalace Knowledge Graph.

Fail-open: if mempalace is unavailable, all functions return gracefully.
KG adds temporal validity to facts that FACTS.md lacks.

Usage:
    from fact_kg_sync import sync_fact_to_kg, invalidate_stale_facts
"""

import os
import re
import sys
from datetime import datetime


def _find_mempalace_site_packages():
    """Find mempalace venv site-packages regardless of Python version."""
    import glob
    base = os.path.expanduser("~/Documents/mempalace/.venv/lib")
    matches = glob.glob(os.path.join(base, "python3.*/site-packages"))
    return matches[0] if matches else None


def _get_kg():
    """Import and return a KnowledgeGraph instance. Returns None if unavailable."""
    try:
        venv_site = _find_mempalace_site_packages()
        if not venv_site:
            return None
        if venv_site not in sys.path:
            sys.path.insert(0, venv_site)
        from mempalace.knowledge_graph import KnowledgeGraph
        return KnowledgeGraph()
    except Exception:
        return None


def _parse_fact_triple(category: str, fact_text: str):
    """
    Extract (subject, predicate, object) from a fact line.

    Examples:
        CONFIRMED: "uv run required for Python execution" -> ("python_execution", "requires", "uv run")
        GOTCHAS: "Port 3000 already in use by another process" -> ("port_3000", "blocked_by", "another process")
        PATHS: "hooks config at templates/settings.json.template" -> ("hooks_config", "located_at", "templates/settings.json.template")
    """
    text = fact_text.strip().rstrip('.')

    # Try common patterns
    # "X requires Y" / "X required for Y"
    m = re.match(r'(.+?)\s+(?:requires?|needed? for)\s+(.+)', text, re.I)
    if m:
        return (m.group(2).strip()[:50], "requires", m.group(1).strip()[:50])

    # "X at/in/located at PATH"
    m = re.match(r'(.+?)\s+(?:at|in|located at|found at|lives at)\s+(.+)', text, re.I)
    if m:
        return (m.group(1).strip()[:50], "located_at", m.group(2).strip()[:80])

    # "X uses Y" / "X using Y"
    m = re.match(r'(.+?)\s+(?:uses?|using)\s+(.+)', text, re.I)
    if m:
        return (m.group(1).strip()[:50], "uses", m.group(2).strip()[:50])

    # "X blocked by Y" / "X fails because Y"
    m = re.match(r'(.+?)\s+(?:blocked by|fails? (?:because|due to|when))\s+(.+)', text, re.I)
    if m:
        return (m.group(1).strip()[:50], "blocked_by", m.group(2).strip()[:50])

    # "X is/are Y"
    m = re.match(r'(.+?)\s+(?:is|are)\s+(.+)', text, re.I)
    if m:
        return (m.group(1).strip()[:50], "is", m.group(2).strip()[:50])

    # Fallback: category as predicate, first few words as subject, rest as object
    words = text.split()
    if len(words) >= 3:
        mid = len(words) // 2
        subject = ' '.join(words[:mid])[:50]
        obj = ' '.join(words[mid:])[:50]
        predicate = category.lower()
        return (subject, predicate, obj)

    return (text[:50], category.lower(), "noted")


def sync_fact_to_kg(category: str, fact_text: str, date_str: str = None) -> bool:
    """
    Add a single fact to the knowledge graph.
    Returns True on success, False on failure (fail-open).
    """
    try:
        kg = _get_kg()
        if kg is None:
            return False

        subject, predicate, obj = _parse_fact_triple(category, fact_text)
        valid_from = date_str or datetime.now().strftime("%Y-%m-%d")

        kg.add_triple(
            subject=subject,
            predicate=predicate,
            obj=obj,
            valid_from=valid_from,
            source_file="FACTS.md",
        )
        return True
    except Exception:
        return False


def sync_all_facts(facts_path: str) -> int:
    """
    Parse FACTS.md and sync all current (non-STALE) facts to KG.
    Returns count of facts synced.
    """
    try:
        kg = _get_kg()
        if kg is None:
            return 0

        if not os.path.exists(facts_path):
            return 0

        with open(facts_path, 'r') as f:
            content = f.read()

        synced = 0
        current_category = None
        in_stale = False

        for line in content.split('\n'):
            stripped = line.strip()

            # Track sections
            if stripped.startswith('## '):
                section = stripped[3:].strip().upper()
                if 'STALE' in section:
                    in_stale = True
                    continue
                in_stale = False
                if 'CONFIRMED' in section:
                    current_category = 'CONFIRMED'
                elif 'GOTCHA' in section:
                    current_category = 'GOTCHAS'
                elif 'PATH' in section:
                    current_category = 'PATHS'
                elif 'PATTERN' in section:
                    current_category = 'PATTERNS'
                continue

            if in_stale or not current_category:
                continue

            # Parse fact lines: "- fact text [YYYY-MM-DD @author]"
            m = re.match(r'^- (.+?)(?:\s*\[(\d{4}-\d{2}-\d{2})\s+@.+?\])?\s*$', stripped)
            if m:
                fact_text = m.group(1).strip()
                date_str = m.group(2) or datetime.now().strftime("%Y-%m-%d")
                if sync_fact_to_kg(current_category, fact_text, date_str):
                    synced += 1

        return synced
    except Exception:
        return 0


def invalidate_stale_facts(stale_entries: list) -> int:
    """
    Mark stale fact entries as ended in the KG.
    stale_entries: list of (fact_text, date_str) tuples from FACTS.md STALE section.
    Returns count of facts invalidated.
    """
    try:
        kg = _get_kg()
        if kg is None:
            return 0

        invalidated = 0
        for fact_text, date_str in stale_entries:
            try:
                subject, predicate, obj = _parse_fact_triple("STALE", fact_text)
                kg.invalidate(subject, predicate, obj, ended=date_str)
                invalidated += 1
            except Exception:
                continue

        return invalidated
    except Exception:
        return 0
