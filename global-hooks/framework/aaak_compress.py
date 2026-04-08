#!/usr/bin/env python3
"""
aaak_compress.py — AAAK Dialect wrapper for CAF hooks.

Provides fail-open AAAK compression: if mempalace is not installed
or compression fails, returns the original text unchanged.

Usage:
    from aaak_compress import compress, compress_sections, compress_with_stats
"""

import json
import os
import sys
from datetime import datetime


def _find_mempalace_site_packages():
    """Find mempalace venv site-packages regardless of Python version."""
    import glob
    base = os.path.expanduser("~/Documents/mempalace/.venv/lib")
    matches = glob.glob(os.path.join(base, "python3.*/site-packages"))
    return matches[0] if matches else None


def _get_dialect():
    """Import and return a Dialect instance. Returns None if unavailable."""
    try:
        venv_site = _find_mempalace_site_packages()
        if not venv_site:
            return None
        if venv_site not in sys.path:
            sys.path.insert(0, venv_site)
        from mempalace.dialect import Dialect
        return Dialect()
    except Exception:
        return None


def compress(text: str, metadata: dict = None) -> str:
    """
    Compress text using AAAK dialect. Fail-open: returns original on any error.
    """
    if not text or len(text) < 50:
        return text
    try:
        dialect = _get_dialect()
        if dialect is None:
            return text
        return dialect.compress(text, metadata=metadata)
    except Exception:
        return text


def compress_sections(text: str) -> str:
    """
    Compress a multi-section text block (like pre_compact output).
    Preserves section headers verbatim. Only compresses body paragraphs.
    Sections are detected by lines starting with ===, ---, ##, or [ALLCAPS].
    """
    if not text or len(text) < 100:
        return text
    try:
        dialect = _get_dialect()
        if dialect is None:
            return text

        lines = text.split("\n")
        result = []
        current_body = []

        def _flush_body():
            if not current_body:
                return
            body_text = "\n".join(current_body)
            if len(body_text.strip()) > 80:
                compressed = dialect.compress(body_text)
                result.append(compressed)
            else:
                result.append(body_text)
            current_body.clear()

        for line in lines:
            stripped = line.strip()
            is_header = (
                stripped.startswith("===")
                or stripped.startswith("---")
                or stripped.startswith("##")
                or (stripped.startswith("[") and stripped.endswith("]") and stripped.isupper())
                or (stripped.startswith("**") and stripped.endswith("**"))
            )
            if is_header:
                _flush_body()
                result.append(line)
            else:
                current_body.append(line)

        _flush_body()
        return "\n".join(result)
    except Exception:
        return text


def compress_with_stats(text: str, metadata: dict = None) -> tuple:
    """
    Compress text and return (compressed_text, stats_dict).
    Stats: {original_tokens, compressed_tokens, ratio, original_chars, compressed_chars}
    On failure: returns (original_text, {}).
    """
    if not text or len(text) < 50:
        return text, {}
    try:
        dialect = _get_dialect()
        if dialect is None:
            return text, {}
        compressed = dialect.compress(text, metadata=metadata)
        stats = dialect.compression_stats(text, compressed)
        return compressed, stats
    except Exception:
        return text, {}


def log_compression_stats(stats: dict, context: str = "unknown"):
    """Append compression stats to ~/.claude/data/aaak_stats.jsonl."""
    if not stats:
        return
    try:
        stats_dir = os.path.expanduser("~/.claude/data")
        os.makedirs(stats_dir, exist_ok=True)
        stats_file = os.path.join(stats_dir, "aaak_stats.jsonl")
        entry = {
            "timestamp": datetime.now().isoformat(),
            "context": context,
            **stats,
        }
        with open(stats_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass
