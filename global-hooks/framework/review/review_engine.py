#!/usr/bin/env python3
"""
Review Engine - Core orchestration for continuous review.

Coordinates analyzer execution, finding collection, circuit breaker
integration, and knowledge DB storage.

Usage:
    engine = ReviewEngine(commit_hash="abc123", repo_root="/path/to/repo")
    results = engine.run()
"""

import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Local imports
sys.path.insert(0, str(Path(__file__).parent))
from findings_store import Finding, Severity, add_findings, get_findings_summary

# Analyzer imports
from analyzers import duplication, complexity, dead_code, architecture, test_coverage


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_PATH = Path.home() / ".claude" / "review_config.yaml"
REVIEW_LOG_PATH = Path.home() / ".claude" / "logs" / "review.log"

# Circuit breaker hook name for review system
REVIEW_HOOK_NAME = "review_engine"

# Maximum diff size to process (prevent OOM on massive commits)
MAX_DIFF_BYTES = 1_000_000  # 1MB


@dataclass
class ReviewConfig:
    """Review system configuration."""
    enabled: bool = True
    background: bool = True
    analysis_types: list[str] = None
    complexity_threshold: int = 10
    duplication_tokens: int = 50
    duplication_similarity: float = 0.6
    god_module_threshold: int = 20
    file_length_threshold: int = 500
    exclude_patterns: list[str] = None
    max_findings_per_analyzer: int = 20

    def __post_init__(self):
        if self.analysis_types is None:
            self.analysis_types = [
                "duplication", "complexity", "dead_code",
                "architecture", "test_coverage",
            ]
        if self.exclude_patterns is None:
            self.exclude_patterns = [
                "**/test/**", "**/tests/**", "**/node_modules/**",
                "**/migrations/**", "**/.git/**", "**/vendor/**",
                "**/dist/**", "**/build/**",
            ]


def load_review_config(config_path: Optional[Path] = None) -> ReviewConfig:
    """Load review configuration from YAML file."""
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        return ReviewConfig()

    try:
        import yaml
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
        return ReviewConfig(
            enabled=data.get("enabled", True),
            background=data.get("background", True),
            analysis_types=data.get("analysis_types"),
            complexity_threshold=data.get("complexity_threshold", 10),
            duplication_tokens=data.get("duplication_tokens", 50),
            duplication_similarity=data.get("duplication_similarity", 0.6),
            god_module_threshold=data.get("god_module_threshold", 20),
            file_length_threshold=data.get("file_length_threshold", 500),
            exclude_patterns=data.get("exclude_patterns"),
            max_findings_per_analyzer=data.get("max_findings_per_analyzer", 20),
        )
    except Exception:
        return ReviewConfig()


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def get_commit_diff(commit_hash: str, repo_root: str) -> Optional[str]:
    """Get the unified diff for a commit."""
    try:
        result = subprocess.run(
            ["git", "diff", f"{commit_hash}~1", commit_hash],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=30,
        )
        if result.returncode == 0:
            diff = result.stdout
            if len(diff.encode("utf-8")) > MAX_DIFF_BYTES:
                return None  # Too large, skip
            return diff

        # For initial commits (no parent), diff against empty tree
        result = subprocess.run(
            ["git", "diff", "--root", commit_hash],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=30,
        )
        if result.returncode == 0:
            diff = result.stdout
            if len(diff.encode("utf-8")) > MAX_DIFF_BYTES:
                return None
            return diff
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def get_commit_message(commit_hash: str, repo_root: str) -> str:
    """Get the commit message."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%B", commit_hash],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def get_changed_files(commit_hash: str, repo_root: str) -> list[str]:
    """Get list of files changed in a commit."""
    try:
        result = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash],
            capture_output=True,
            text=True,
            cwd=repo_root,
            timeout=10,
        )
        if result.returncode == 0:
            return [f for f in result.stdout.strip().split("\n") if f]
    except (subprocess.TimeoutExpired, OSError):
        pass
    return []


def get_repo_root() -> Optional[str]:
    """Get the git repository root of the current directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def should_exclude_file(file_path: str, patterns: list[str]) -> bool:
    """Check if a file matches any exclusion pattern."""
    from fnmatch import fnmatch
    for pattern in patterns:
        if fnmatch(file_path, pattern):
            return True
    return False


# ---------------------------------------------------------------------------
# Review Engine
# ---------------------------------------------------------------------------


@dataclass
class ReviewResult:
    """Result of a review run."""
    commit_hash: str
    findings: list[Finding]
    findings_added: int
    duration_seconds: float
    analyzers_run: list[str]
    errors: list[str]

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class ReviewEngine:
    """
    Core review engine that orchestrates analysis of a commit.

    Integrates with:
    - Circuit breaker (prevents review loops)
    - Knowledge DB (stores patterns and learnings)
    - Findings store (persists review findings)
    """

    def __init__(
        self,
        commit_hash: str,
        repo_root: Optional[str] = None,
        config: Optional[ReviewConfig] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.commit_hash = commit_hash
        self.repo_root = repo_root or get_repo_root() or "."
        self.config = config or load_review_config()
        self.logger = logger or self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Set up review logger."""
        logger = logging.getLogger("review_engine")
        logger.setLevel(logging.INFO)

        REVIEW_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(REVIEW_LOG_PATH)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        ))
        logger.addHandler(handler)
        return logger

    def run(self) -> ReviewResult:
        """
        Execute the review pipeline.

        Returns ReviewResult with all findings and metadata.
        """
        start_time = time.monotonic()
        all_findings: list[Finding] = []
        analyzers_run: list[str] = []
        errors: list[str] = []

        self.logger.info(f"Starting review for commit {self.commit_hash[:8]}")

        # Check circuit breaker
        if not self._check_circuit_breaker():
            self.logger.info("Circuit breaker open, skipping review")
            return ReviewResult(
                commit_hash=self.commit_hash,
                findings=[],
                findings_added=0,
                duration_seconds=time.monotonic() - start_time,
                analyzers_run=[],
                errors=["Circuit breaker open, review skipped"],
            )

        # Get commit data
        diff_text = get_commit_diff(self.commit_hash, self.repo_root)
        if diff_text is None:
            msg = f"Could not get diff for commit {self.commit_hash[:8]} (too large or error)"
            self.logger.warning(msg)
            self._record_circuit_breaker_failure(msg)
            return ReviewResult(
                commit_hash=self.commit_hash,
                findings=[],
                findings_added=0,
                duration_seconds=time.monotonic() - start_time,
                analyzers_run=[],
                errors=[msg],
            )

        changed_files = get_changed_files(self.commit_hash, self.repo_root)
        if not changed_files:
            self.logger.info("No changed files, skipping review")
            return ReviewResult(
                commit_hash=self.commit_hash,
                findings=[],
                findings_added=0,
                duration_seconds=time.monotonic() - start_time,
                analyzers_run=[],
                errors=[],
            )

        # Filter excluded files
        changed_files = [
            f for f in changed_files
            if not should_exclude_file(f, self.config.exclude_patterns)
        ]

        if not changed_files:
            self.logger.info("All changed files excluded by config")
            return ReviewResult(
                commit_hash=self.commit_hash,
                findings=[],
                findings_added=0,
                duration_seconds=time.monotonic() - start_time,
                analyzers_run=[],
                errors=[],
            )

        commit_msg = get_commit_message(self.commit_hash, self.repo_root)
        self.logger.info(
            f"Reviewing {len(changed_files)} files. "
            f"Commit: {commit_msg[:80]}"
        )

        # Run each enabled analyzer
        analyzer_map = {
            "duplication": self._run_duplication,
            "complexity": self._run_complexity,
            "dead_code": self._run_dead_code,
            "architecture": self._run_architecture,
            "test_coverage": self._run_test_coverage,
        }

        for analyzer_name in self.config.analysis_types:
            if analyzer_name not in analyzer_map:
                self.logger.warning(f"Unknown analyzer: {analyzer_name}")
                continue

            try:
                findings = analyzer_map[analyzer_name](diff_text, changed_files)

                # Cap findings per analyzer
                if len(findings) > self.config.max_findings_per_analyzer:
                    findings = findings[:self.config.max_findings_per_analyzer]

                # Set commit hash and generate IDs
                for idx, finding in enumerate(findings):
                    finding.commit_hash = self.commit_hash
                    finding.id = f"{self.commit_hash[:8]}:{analyzer_name}:{idx}"

                all_findings.extend(findings)
                analyzers_run.append(analyzer_name)
                self.logger.info(
                    f"  {analyzer_name}: {len(findings)} findings"
                )

            except Exception as e:
                error_msg = f"Analyzer '{analyzer_name}' failed: {e}"
                self.logger.error(error_msg)
                errors.append(error_msg)

        # Store findings
        findings_added = 0
        if all_findings:
            findings_added = add_findings(all_findings)
            self.logger.info(f"Stored {findings_added} new findings")

        # Store patterns in knowledge DB
        self._store_to_knowledge_db(all_findings)

        # Record circuit breaker success
        self._record_circuit_breaker_success()

        duration = time.monotonic() - start_time
        self.logger.info(
            f"Review complete: {len(all_findings)} findings, "
            f"{findings_added} new, {duration:.1f}s"
        )

        return ReviewResult(
            commit_hash=self.commit_hash,
            findings=all_findings,
            findings_added=findings_added,
            duration_seconds=duration,
            analyzers_run=analyzers_run,
            errors=errors,
        )

    # -------------------------------------------------------------------
    # Analyzer runners
    # -------------------------------------------------------------------

    def _run_duplication(
        self, diff_text: str, changed_files: list[str]
    ) -> list[Finding]:
        return duplication.analyze(
            diff_text,
            changed_files,
            self.repo_root,
            min_tokens=self.config.duplication_tokens,
            similarity_threshold=self.config.duplication_similarity,
        )

    def _run_complexity(
        self, diff_text: str, changed_files: list[str]
    ) -> list[Finding]:
        return complexity.analyze(
            diff_text,
            changed_files,
            self.repo_root,
            complexity_threshold=self.config.complexity_threshold,
        )

    def _run_dead_code(
        self, diff_text: str, changed_files: list[str]
    ) -> list[Finding]:
        return dead_code.analyze(
            diff_text,
            changed_files,
            self.repo_root,
        )

    def _run_architecture(
        self, diff_text: str, changed_files: list[str]
    ) -> list[Finding]:
        return architecture.analyze(
            diff_text,
            changed_files,
            self.repo_root,
            god_module_threshold=self.config.god_module_threshold,
            file_length_threshold=self.config.file_length_threshold,
        )

    def _run_test_coverage(
        self, diff_text: str, changed_files: list[str]
    ) -> list[Finding]:
        return test_coverage.analyze(
            diff_text,
            changed_files,
            self.repo_root,
        )

    # -------------------------------------------------------------------
    # Circuit breaker integration
    # -------------------------------------------------------------------

    def _check_circuit_breaker(self) -> bool:
        """Check if review is allowed by circuit breaker."""
        try:
            cb_dir = Path(__file__).parent.parent / "guardrails"
            sys.path.insert(0, str(cb_dir))
            from circuit_breaker import CircuitBreaker
            from hook_state_manager import HookStateManager
            from config_loader import load_config

            config = load_config()
            state_mgr = HookStateManager(config.get_state_file_path())
            cb = CircuitBreaker(state_mgr, config)
            result = cb.should_execute(REVIEW_HOOK_NAME)
            return result.should_execute
        except Exception as e:
            self.logger.debug(f"Circuit breaker check failed (allowing): {e}")
            return True  # Allow if circuit breaker unavailable

    def _record_circuit_breaker_success(self) -> None:
        """Record successful review with circuit breaker."""
        try:
            cb_dir = Path(__file__).parent.parent / "guardrails"
            sys.path.insert(0, str(cb_dir))
            from circuit_breaker import CircuitBreaker
            from hook_state_manager import HookStateManager
            from config_loader import load_config

            config = load_config()
            state_mgr = HookStateManager(config.get_state_file_path())
            cb = CircuitBreaker(state_mgr, config)
            cb.record_success(REVIEW_HOOK_NAME)
        except Exception:
            pass

    def _record_circuit_breaker_failure(self, error: str) -> None:
        """Record failed review with circuit breaker."""
        try:
            cb_dir = Path(__file__).parent.parent / "guardrails"
            sys.path.insert(0, str(cb_dir))
            from circuit_breaker import CircuitBreaker
            from hook_state_manager import HookStateManager
            from config_loader import load_config

            config = load_config()
            state_mgr = HookStateManager(config.get_state_file_path())
            cb = CircuitBreaker(state_mgr, config)
            cb.record_failure(REVIEW_HOOK_NAME, error)
        except Exception:
            pass

    # -------------------------------------------------------------------
    # Knowledge DB integration
    # -------------------------------------------------------------------

    def _store_to_knowledge_db(self, findings: list[Finding]) -> None:
        """Store significant findings as patterns in the knowledge DB."""
        if not findings:
            return

        try:
            knowledge_dir = Path(__file__).parent.parent / "knowledge"
            sys.path.insert(0, str(knowledge_dir))
            from knowledge_db import add_knowledge

            # Group findings by analyzer for pattern detection
            by_analyzer: dict[str, int] = {}
            for f in findings:
                by_analyzer[f.analyzer] = by_analyzer.get(f.analyzer, 0) + 1

            # Store aggregated patterns (not individual findings)
            for analyzer_name, count in by_analyzer.items():
                if count >= 3:  # Only store if pattern is significant
                    add_knowledge(
                        content=(
                            f"Review pattern: {count} {analyzer_name} findings "
                            f"in commit {self.commit_hash[:8]}. "
                            f"This may indicate a recurring code quality issue."
                        ),
                        tag="PATTERN",
                        context="review",
                        metadata={
                            "analyzer": analyzer_name,
                            "finding_count": count,
                            "commit": self.commit_hash,
                        },
                    )

            # Store critical/error findings as investigations
            for f in findings:
                if f.severity in (Severity.CRITICAL.value, Severity.ERROR.value):
                    add_knowledge(
                        content=(
                            f"Review finding ({f.severity}): {f.title} "
                            f"in {f.file_path}. {f.description[:200]}"
                        ),
                        tag="INVESTIGATION",
                        context="review",
                        metadata={
                            "finding_id": f.id,
                            "analyzer": f.analyzer,
                            "file": f.file_path,
                            "commit": self.commit_hash,
                        },
                    )

        except Exception as e:
            self.logger.debug(f"Knowledge DB storage failed: {e}")
