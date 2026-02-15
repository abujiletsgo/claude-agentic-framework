#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Findings Store - Persistent storage for review findings.

Stores findings in ~/.claude/review_findings.json with append-only
semantics and status tracking (open, notified, resolved, wontfix).

Thread-safe via file locking (fcntl).
"""

import fcntl
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FINDINGS_DIR = Path.home() / ".claude"
FINDINGS_PATH = FINDINGS_DIR / "review_findings.json"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    """Finding severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class FindingStatus(str, Enum):
    """Finding lifecycle status."""
    OPEN = "open"              # Newly discovered
    NOTIFIED = "notified"      # Agent was told about it
    RESOLVED = "resolved"      # Fixed by agent or auto-fix
    WONTFIX = "wontfix"        # Acknowledged, not fixing


@dataclass
class Finding:
    """A single review finding."""
    id: str                          # Unique identifier (commit_hash:analyzer:index)
    commit_hash: str                 # Git commit that introduced the issue
    analyzer: str                    # Which analyzer found it (duplication, complexity, etc.)
    severity: str                    # Severity level
    title: str                       # Short description
    description: str                 # Detailed explanation
    file_path: str                   # File where the issue was found
    line_start: Optional[int] = None # Start line number
    line_end: Optional[int] = None   # End line number
    suggestion: str = ""             # Suggested fix
    status: str = "open"             # Current status
    created_at: str = ""             # ISO timestamp of creation
    notified_at: str = ""            # ISO timestamp of notification
    resolved_at: str = ""            # ISO timestamp of resolution
    metadata: dict = field(default_factory=dict)  # Extra data

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Store operations
# ---------------------------------------------------------------------------


def _ensure_dir():
    """Create findings directory if needed."""
    FINDINGS_DIR.mkdir(parents=True, exist_ok=True)


def _read_findings() -> list[dict]:
    """Read all findings from disk."""
    if not FINDINGS_PATH.exists():
        return []
    try:
        with open(FINDINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write_findings(findings: list[dict]) -> None:
    """Write findings to disk with file locking."""
    _ensure_dir()
    with open(FINDINGS_PATH, "w", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            json.dump(findings, f, indent=2, ensure_ascii=False)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def add_findings(new_findings: list[Finding]) -> int:
    """
    Add new findings to the store.

    Deduplicates by finding ID (commit_hash:analyzer:index).

    Returns count of newly added findings.
    """
    existing = _read_findings()
    existing_ids = {f.get("id") for f in existing}

    added = 0
    for finding in new_findings:
        if finding.id not in existing_ids:
            existing.append(asdict(finding))
            existing_ids.add(finding.id)
            added += 1

    if added > 0:
        _write_findings(existing)

    return added


def get_findings(
    status: Optional[str] = None,
    commit_hash: Optional[str] = None,
    analyzer: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """
    Query findings with optional filters.

    Args:
        status:      Filter by status (open, notified, resolved, wontfix)
        commit_hash: Filter by commit hash
        analyzer:    Filter by analyzer name
        severity:    Filter by severity level
        limit:       Maximum results to return

    Returns list of finding dicts.
    """
    findings = _read_findings()

    if status:
        findings = [f for f in findings if f.get("status") == status]
    if commit_hash:
        findings = [f for f in findings if f.get("commit_hash") == commit_hash]
    if analyzer:
        findings = [f for f in findings if f.get("analyzer") == analyzer]
    if severity:
        findings = [f for f in findings if f.get("severity") == severity]

    # Sort by created_at descending (newest first)
    findings.sort(key=lambda f: f.get("created_at", ""), reverse=True)

    return findings[:limit]


def get_unresolved_findings(limit: int = 50) -> list[dict]:
    """Get all findings that are open or notified (not yet resolved)."""
    findings = _read_findings()
    unresolved = [
        f for f in findings
        if f.get("status") in ("open", "notified")
    ]
    unresolved.sort(key=lambda f: f.get("created_at", ""), reverse=True)
    return unresolved[:limit]


def update_finding_status(
    finding_id: str,
    new_status: str,
) -> bool:
    """
    Update the status of a finding.

    Returns True if finding was found and updated.
    """
    findings = _read_findings()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for finding in findings:
        if finding.get("id") == finding_id:
            finding["status"] = new_status
            if new_status == "notified":
                finding["notified_at"] = now
            elif new_status == "resolved":
                finding["resolved_at"] = now
            _write_findings(findings)
            return True

    return False


def mark_as_notified(finding_ids: list[str]) -> int:
    """
    Batch mark findings as notified.

    Returns count of findings updated.
    """
    findings = _read_findings()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    updated = 0

    id_set = set(finding_ids)
    for finding in findings:
        if finding.get("id") in id_set and finding.get("status") == "open":
            finding["status"] = "notified"
            finding["notified_at"] = now
            updated += 1

    if updated > 0:
        _write_findings(findings)

    return updated


def get_findings_summary() -> dict:
    """Get summary statistics of all findings."""
    findings = _read_findings()

    summary = {
        "total": len(findings),
        "by_status": {},
        "by_severity": {},
        "by_analyzer": {},
    }

    for f in findings:
        status = f.get("status", "unknown")
        severity = f.get("severity", "unknown")
        analyzer = f.get("analyzer", "unknown")

        summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
        summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
        summary["by_analyzer"][analyzer] = summary["by_analyzer"].get(analyzer, 0) + 1

    return summary


def purge_resolved(older_than_days: int = 30) -> int:
    """
    Remove resolved/wontfix findings older than N days.

    Returns count of purged findings.
    """
    findings = _read_findings()
    now = datetime.now(timezone.utc)
    kept = []
    purged = 0

    for f in findings:
        if f.get("status") in ("resolved", "wontfix"):
            resolved_at = f.get("resolved_at", f.get("created_at", ""))
            if resolved_at:
                try:
                    ts = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
                    age_days = (now - ts).days
                    if age_days > older_than_days:
                        purged += 1
                        continue
                except (ValueError, TypeError):
                    pass
        kept.append(f)

    if purged > 0:
        _write_findings(kept)

    return purged
