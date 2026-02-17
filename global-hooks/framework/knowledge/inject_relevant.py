#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""
EVOLVE stage of the Knowledge Pipeline.

Hook: SessionStart
Retrieves relevant learnings from knowledge.db using FTS5 search
based on the current working directory and recent file context,
then injects them into the session via hookSpecificOutput.
"""

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude" / "knowledge_pipeline.yaml"
DB_DIR = Path.home() / ".claude" / "data" / "knowledge-db"
DB_PATH = DB_DIR / "knowledge.db"


def load_config():
    """Load pipeline config with safe defaults."""
    defaults = {
        "evolve": {
            "enabled": True,
            "max_injections": 5,
            "relevance_threshold": 0.6,
            "recency_boost": 0.2,
            "include_categories": ["LEARNED", "PATTERN", "INVESTIGATION"],
            "lookback_days": 30,
        }
    }
    if CONFIG_PATH.exists():
        try:
            import yaml
            with open(CONFIG_PATH, "r") as f:
                cfg = yaml.safe_load(f) or {}
            evolve = cfg.get("evolve", {})
            for k, v in evolve.items():
                defaults["evolve"][k] = v
        except Exception:
            pass
    return defaults["evolve"]


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_db():
    """Get database connection (read-only mode)."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ---------------------------------------------------------------------------
# Context gathering
# ---------------------------------------------------------------------------

def get_cwd_context():
    """Extract search context from the current working directory."""
    cwd = Path.cwd()
    terms = []

    # Directory name parts
    for part in cwd.parts[-3:]:
        # Split on common separators
        for word in part.replace("-", " ").replace("_", " ").replace(".", " ").split():
            if len(word) > 2 and word.lower() not in ("users", "home", "documents", "src", "lib"):
                terms.append(word.lower())

    # Check for common project files to infer project type
    project_indicators = {
        "package.json": ["javascript", "node", "npm"],
        "Cargo.toml": ["rust", "cargo"],
        "pyproject.toml": ["python", "pip"],
        "go.mod": ["golang", "go"],
        "pom.xml": ["java", "maven"],
        "Gemfile": ["ruby", "rails"],
        "CLAUDE.md": ["claude", "agentic"],
    }

    for filename, keywords in project_indicators.items():
        if (cwd / filename).exists():
            terms.extend(keywords)
            break

    # Check for recent git activity to get context
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-5", "--format=%s"],
            capture_output=True, text=True, timeout=5, cwd=str(cwd)
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                for word in line.split():
                    if len(word) > 3 and word.isalpha():
                        terms.append(word.lower())
    except Exception:
        pass

    return list(set(terms))[:15]  # Deduplicate and limit


def get_recent_files_context():
    """Get context from recently modified files in cwd."""
    terms = []
    cwd = Path.cwd()

    try:
        # Get recently modified files
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~5", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=str(cwd)
        )
        if result.returncode == 0:
            for filepath in result.stdout.strip().split("\n")[:10]:
                if filepath:
                    # Extract meaningful parts from file paths
                    p = Path(filepath)
                    terms.append(p.stem.lower())
                    if p.suffix:
                        terms.append(p.suffix.lstrip(".").lower())
    except Exception:
        pass

    return list(set(terms))[:10]


# ---------------------------------------------------------------------------
# Knowledge retrieval
# ---------------------------------------------------------------------------

def search_knowledge(conn, search_terms, config):
    """Search knowledge database using FTS5 with BM25 ranking."""
    if not search_terms:
        return []

    categories = config.get("include_categories", ["LEARNED", "PATTERN", "INVESTIGATION"])
    max_results = config.get("max_injections", 5)
    lookback_days = config.get("lookback_days", 30)

    # Build FTS query (OR-based for broad matching)
    query = " OR ".join(search_terms[:10])

    # Calculate lookback date
    cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    # Build category filter
    cat_placeholders = ",".join(["?" for _ in categories])

    try:
        sql = (
            "SELECT e.id, e.category, e.title, e.content, e.tags, "
            "e.confidence, e.created_at, e.source, rank "
            "FROM knowledge_fts f "
            "JOIN knowledge_entries e ON f.rowid = e.id "
            "WHERE knowledge_fts MATCH ? "
            f"AND e.category IN ({cat_placeholders}) "
            "AND e.created_at > ? "
            "AND (e.expires_at IS NULL OR e.expires_at > ?) "
            "ORDER BY rank "
            f"LIMIT ?"
        )
        params = [query] + categories + [cutoff, now_iso(), max_results * 2]
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        pass

    # Fallback: recent entries without FTS
    try:
        sql = (
            "SELECT id, category, title, content, tags, confidence, created_at, source "
            "FROM knowledge_entries "
            f"WHERE category IN ({cat_placeholders}) "
            "AND created_at > ? "
            "AND (expires_at IS NULL OR expires_at > ?) "
            "ORDER BY created_at DESC "
            f"LIMIT ?"
        )
        params = categories + [cutoff, now_iso(), max_results]
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def rank_and_filter(results, config):
    """Apply recency boost and relevance threshold, return top N."""
    max_injections = config.get("max_injections", 5)
    recency_boost = config.get("recency_boost", 0.2)

    scored = []
    now = datetime.now(timezone.utc)

    for r in results:
        # Base score from BM25 rank (rank is negative, more negative = better)
        bm25_score = abs(r.get("rank", 0)) if r.get("rank") else 0.5

        # Recency boost: newer entries get a boost
        try:
            created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            age_days = (now - created).total_seconds() / 86400
            # Exponential decay: recent items get full boost, older items less
            age_factor = max(0, 1 - (age_days / 30))
            recency_score = recency_boost * age_factor
        except Exception:
            recency_score = 0

        # Confidence boost
        confidence = r.get("confidence", 0.5)

        # Combined score
        total_score = bm25_score + recency_score + (confidence * 0.1)
        r["_score"] = total_score
        scored.append(r)

    # Sort by score descending
    scored.sort(key=lambda x: x["_score"], reverse=True)

    return scored[:max_injections]


def format_injection(learnings):
    """Format learnings as a context injection string."""
    if not learnings:
        return ""

    lines = ["## Relevant Knowledge from Previous Sessions", ""]

    for entry in learnings:
        category = entry.get("category", "LEARNED")
        content = entry.get("content", "")
        # Strip the "Context: ..." suffix we added during storage
        if "\n\nContext: " in content:
            content = content.split("\n\nContext: ")[0]
        confidence = entry.get("confidence", 0.5)
        tags = entry.get("tags", "")

        confidence_label = "high" if confidence >= 0.7 else "medium" if confidence >= 0.4 else "low"
        lines.append(
            f"- **{category}** ({confidence_label} confidence): {content}"
        )
        if tags:
            lines.append(f"  _Tags: {tags}_")

    lines.append("")
    lines.append(
        "_Knowledge auto-injected by the knowledge pipeline. "
        f"{len(learnings)} relevant entries found._"
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    config = load_config()

    if not config.get("enabled", True):
        sys.exit(0)

    # Get database connection
    conn = get_db()
    if conn is None:
        sys.exit(0)

    try:
        # Gather search context
        cwd_terms = get_cwd_context()
        file_terms = get_recent_files_context()
        all_terms = list(set(cwd_terms + file_terms))

        if not all_terms:
            # No context available, fall back to recent learnings
            all_terms = ["learned", "pattern", "workflow"]

        # Search knowledge database
        results = search_knowledge(conn, all_terms, config)

        if not results:
            sys.exit(0)

        # Rank and filter
        top_learnings = rank_and_filter(results, config)

        if not top_learnings:
            sys.exit(0)

        # Format as context injection
        injection_text = format_injection(top_learnings)

        if injection_text:
            output = {
                "hookSpecificOutput": {
                    "additionalContext": injection_text
                }
            }
            print(json.dumps(output))

    finally:
        conn.close()

    sys.exit(0)


if __name__ == "__main__":
    main()
