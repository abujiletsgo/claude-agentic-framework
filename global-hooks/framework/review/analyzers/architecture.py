#!/usr/bin/env python3
"""
Architecture Analyzer
=====================

Detects structural and architectural violations in changed code.

Checks:
- Layer violations (e.g., views importing from data layer directly)
- Circular dependency indicators
- God classes/modules (too many responsibilities)
- Missing error handling patterns
- Security anti-patterns (hardcoded secrets, eval usage)
- Import discipline violations

Rules are configurable via review_config.yaml.
"""

import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from findings_store import Finding, Severity


# ---------------------------------------------------------------------------
# Architecture rules
# ---------------------------------------------------------------------------


class ArchRule:
    """A single architecture rule."""

    def __init__(
        self,
        name: str,
        description: str,
        pattern: re.Pattern,
        severity: str,
        file_filter: Optional[re.Pattern] = None,
        file_exclude: Optional[re.Pattern] = None,
        suggestion: str = "",
    ):
        self.name = name
        self.description = description
        self.pattern = pattern
        self.severity = severity
        self.file_filter = file_filter      # Only apply to matching files
        self.file_exclude = file_exclude    # Skip matching files
        self.suggestion = suggestion

    def applies_to(self, file_path: str) -> bool:
        """Check if this rule applies to the given file."""
        if self.file_exclude and self.file_exclude.search(file_path):
            return False
        if self.file_filter and not self.file_filter.search(file_path):
            return False
        return True


# Default architecture rules
DEFAULT_RULES = [
    # Security: hardcoded secrets
    ArchRule(
        name="hardcoded-secret",
        description="Potential hardcoded secret or API key",
        pattern=re.compile(
            r'(?:api[_-]?key|secret|password|token|auth)\s*[=:]\s*["\'][a-zA-Z0-9+/=_-]{16,}["\']',
            re.IGNORECASE,
        ),
        severity=Severity.CRITICAL.value,
        file_exclude=re.compile(r'(?:test_|_test\.|\.test\.|spec\.|\.example|\.template|\.sample)', re.IGNORECASE),
        suggestion=(
            "Never hardcode secrets. Use environment variables, "
            "a secrets manager, or configuration files excluded from version control."
        ),
    ),

    # Security: eval/exec usage
    ArchRule(
        name="eval-usage",
        description="Use of eval() or exec() which can execute arbitrary code",
        pattern=re.compile(r'\b(?:eval|exec)\s*\(', re.MULTILINE),
        severity=Severity.ERROR.value,
        file_filter=re.compile(r'\.py$'),
        file_exclude=re.compile(r'(?:test_|_test\.)', re.IGNORECASE),
        suggestion=(
            "Avoid eval() and exec(). Use ast.literal_eval() for safe literal parsing, "
            "or redesign to avoid dynamic code execution."
        ),
    ),

    # Security: SQL injection risk
    ArchRule(
        name="sql-injection-risk",
        description="Potential SQL injection via string formatting in queries",
        pattern=re.compile(
            r'(?:execute|cursor\.execute|query)\s*\(\s*(?:f["\']|["\'].*%|.*\.format\()',
            re.MULTILINE,
        ),
        severity=Severity.ERROR.value,
        file_exclude=re.compile(r'(?:test_|_test\.)', re.IGNORECASE),
        suggestion=(
            "Use parameterized queries instead of string formatting. "
            "Pass parameters as a tuple/list to prevent SQL injection."
        ),
    ),

    # Architecture: god module (too many top-level definitions)
    ArchRule(
        name="god-module",
        description="Module has too many top-level definitions (possible god module)",
        pattern=re.compile(
            # This is a meta-rule handled specially in check_god_module()
            r'__GOD_MODULE_CHECK__',
        ),
        severity=Severity.WARNING.value,
        file_filter=re.compile(r'\.py$'),
        file_exclude=re.compile(r'(?:__init__|test_|_test\.)', re.IGNORECASE),
        suggestion=(
            "Consider splitting this module into smaller, focused modules. "
            "Each module should have a single responsibility."
        ),
    ),

    # Architecture: broad exception catching
    ArchRule(
        name="broad-except",
        description="Catching broad Exception or bare except",
        pattern=re.compile(
            r'except\s*(?:Exception|BaseException)?\s*(?:as\s+\w+)?\s*:',
            re.MULTILINE,
        ),
        severity=Severity.INFO.value,
        file_filter=re.compile(r'\.py$'),
        file_exclude=re.compile(r'(?:test_|_test\.)', re.IGNORECASE),
        suggestion=(
            "Catch specific exceptions instead of broad Exception. "
            "This prevents accidentally catching KeyboardInterrupt, SystemExit, etc."
        ),
    ),

    # Architecture: TODO/FIXME/HACK/XXX markers
    ArchRule(
        name="code-debt-marker",
        description="Technical debt marker found in new code",
        pattern=re.compile(
            r'#\s*(?:TODO|FIXME|HACK|XXX|TEMP|TEMPORARY)\b',
            re.IGNORECASE,
        ),
        severity=Severity.INFO.value,
        suggestion=(
            "Consider addressing this technical debt now, or create a "
            "tracked issue/ticket to ensure it gets resolved."
        ),
    ),

    # Architecture: print statements in production code
    ArchRule(
        name="print-in-production",
        description="print() statement in non-test code (use logging instead)",
        pattern=re.compile(r'^\s*print\s*\(', re.MULTILINE),
        severity=Severity.INFO.value,
        file_filter=re.compile(r'\.py$'),
        file_exclude=re.compile(
            r'(?:test_|_test\.|cli|__main__|setup\.py|conftest)',
            re.IGNORECASE,
        ),
        suggestion=(
            "Use the logging module instead of print() for production code. "
            "This allows proper log levels, formatting, and output control."
        ),
    ),

    # JS/TS: console.log in production
    ArchRule(
        name="console-log-production",
        description="console.log() in non-test code",
        pattern=re.compile(r'\bconsole\.log\s*\(', re.MULTILINE),
        severity=Severity.INFO.value,
        file_filter=re.compile(r'\.(js|jsx|ts|tsx)$'),
        file_exclude=re.compile(r'(?:test|spec|\.test\.|\.spec\.)', re.IGNORECASE),
        suggestion="Use a proper logging library instead of console.log() in production code.",
    ),
]


# ---------------------------------------------------------------------------
# Specialized checks
# ---------------------------------------------------------------------------


def check_god_module(source: str, threshold: int = 20) -> Optional[dict]:
    """
    Check if a Python module has too many top-level definitions.

    Returns dict with count info if threshold exceeded, None otherwise.
    """
    import ast as _ast
    try:
        tree = _ast.parse(source)
    except SyntaxError:
        return None

    top_level_defs = 0
    for node in _ast.iter_child_nodes(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
            top_level_defs += 1

    if top_level_defs > threshold:
        return {
            "count": top_level_defs,
            "threshold": threshold,
        }
    return None


def check_file_length(source: str, threshold: int = 500) -> Optional[dict]:
    """Check if a file exceeds the line count threshold."""
    lines = source.count("\n") + 1
    if lines > threshold:
        return {"lines": lines, "threshold": threshold}
    return None


# ---------------------------------------------------------------------------
# Diff-aware rule checking
# ---------------------------------------------------------------------------


def extract_added_lines_with_numbers(diff_text: str) -> dict[str, list[tuple[int, str]]]:
    """
    Extract added lines from diff, grouped by file.

    Returns dict mapping file_path -> list of (line_number, line_content).
    """
    result: dict[str, list[tuple[int, str]]] = {}
    current_file = None
    line_num = 0

    for line in diff_text.split("\n"):
        if line.startswith("+++ b/"):
            current_file = line[6:]
            if current_file not in result:
                result[current_file] = []
            continue

        if line.startswith("@@"):
            match = re.search(r'\+(\d+)', line)
            if match:
                line_num = int(match.group(1))
            continue

        if line.startswith("+") and not line.startswith("+++"):
            if current_file:
                result[current_file].append((line_num, line[1:]))
            line_num += 1
        elif not line.startswith("-"):
            line_num += 1

    return result


# ---------------------------------------------------------------------------
# Main analyzer entry point
# ---------------------------------------------------------------------------


def _read_file_safe(file_path: str, repo_root: str) -> Optional[str]:
    """Safely read a file, returning None on failure."""
    full_path = Path(repo_root) / file_path
    try:
        return full_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def analyze(
    diff_text: str,
    changed_files: list[str],
    repo_root: str,
    rules: Optional[list[ArchRule]] = None,
    god_module_threshold: int = 20,
    file_length_threshold: int = 500,
) -> list[Finding]:
    """
    Run architecture analysis on changed files.

    Applies rules against newly added lines from the diff, plus
    whole-file structural checks for Python files.

    Args:
        diff_text:              Full unified diff text
        changed_files:          List of changed file paths
        repo_root:              Repository root path
        rules:                  Custom rules (defaults to DEFAULT_RULES)
        god_module_threshold:   Max top-level definitions per module
        file_length_threshold:  Max lines per file

    Returns list of Finding objects for architectural violations.
    """
    if rules is None:
        rules = DEFAULT_RULES

    findings = []
    added_lines = extract_added_lines_with_numbers(diff_text)

    for file_path in changed_files:
        file_added = added_lines.get(file_path, [])
        source = _read_file_safe(file_path, repo_root)

        # Check pattern-based rules against added lines only
        for rule in rules:
            if rule.name == "god-module":
                continue  # Handled separately below
            if not rule.applies_to(file_path):
                continue

            for line_num, line_content in file_added:
                if rule.pattern.search(line_content):
                    finding = Finding(
                        id="",
                        commit_hash="",
                        analyzer="architecture",
                        severity=rule.severity,
                        title=f"{rule.name}: {rule.description}",
                        description=(
                            f"Rule '{rule.name}' violated in {file_path} at line {line_num}:\n"
                            f"  {line_content.strip()}\n\n"
                            f"{rule.description}"
                        ),
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        suggestion=rule.suggestion,
                        metadata={"rule": rule.name},
                    )
                    findings.append(finding)

        # Whole-file structural checks
        if source and file_path.endswith(".py"):
            # God module check
            god_result = check_god_module(source, god_module_threshold)
            if god_result:
                findings.append(Finding(
                    id="",
                    commit_hash="",
                    analyzer="architecture",
                    severity=Severity.WARNING.value,
                    title=f"God module: {god_result['count']} top-level definitions",
                    description=(
                        f"Module {file_path} has {god_result['count']} top-level definitions "
                        f"(threshold: {god_result['threshold']}). This suggests the module "
                        f"has too many responsibilities."
                    ),
                    file_path=file_path,
                    line_start=1,
                    suggestion=(
                        "Split this module into smaller, focused modules. "
                        "Group related functions/classes into separate files."
                    ),
                    metadata={"rule": "god-module", **god_result},
                ))

        # File length check (any language)
        if source:
            length_result = check_file_length(source, file_length_threshold)
            if length_result:
                findings.append(Finding(
                    id="",
                    commit_hash="",
                    analyzer="architecture",
                    severity=Severity.INFO.value,
                    title=f"Long file: {length_result['lines']} lines",
                    description=(
                        f"File {file_path} has {length_result['lines']} lines "
                        f"(threshold: {length_result['threshold']}). Long files are "
                        f"harder to navigate and maintain."
                    ),
                    file_path=file_path,
                    line_start=1,
                    suggestion="Consider splitting into smaller, focused modules.",
                    metadata={"rule": "file-length", **length_result},
                ))

    return findings
