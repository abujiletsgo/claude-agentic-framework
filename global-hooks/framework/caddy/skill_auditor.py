#!/usr/bin/env python3
"""Skill security auditor for Caddy.

Scans skill directories for dangerous patterns before Caddy recommends them.
Critical issues block skill recommendations; warnings are surfaced to the user.
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple


class SkillAuditor:
    """Audit skills for security issues."""

    # Dangerous patterns to detect
    CRITICAL_PATTERNS = [
        (r'curl.*\|.*bash', "Curl pipe bash (arbitrary code execution)"),
        (r'curl.*\|.*sh', "Curl pipe sh (arbitrary code execution)"),
        (r'wget.*\|.*bash', "Wget pipe bash (arbitrary code execution)"),
        (r'eval\s*\(', "eval() call (code injection risk)"),
        (r'exec\s*\(', "exec() call (code injection risk)"),
        (r'os\.system\s*\(', "os.system() call (shell injection risk)"),
        (r'subprocess.*shell=True', "subprocess with shell=True (injection risk)"),
    ]

    WARNING_PATTERNS = [
        (r'rm\s+-rf', "Recursive delete (data loss risk)"),
        (r'\.ssh/', "SSH key access"),
        (r'\.env', "Environment file access"),
        (r'\.aws/', "AWS credentials access"),
        (r'\.config/', "Config directory access"),
        (r'api[_-]?key', "API key handling (potential leak)"),
        (r'password', "Password handling (potential leak)"),
        (r'secret', "Secret handling (potential leak)"),
        (r'kill\s+-9', "Force kill (process termination)"),
        (r'chmod\s+777', "Insecure permissions"),
    ]

    INFO_PATTERNS = [
        (r'http://[^/]+', "Unencrypted HTTP request"),
        (r'TODO|FIXME|HACK', "Code debt markers"),
    ]

    # File extensions to skip (binary/non-text)
    SKIP_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg',
        '.pdf', '.zip', '.tar', '.gz', '.bz2',
        '.woff', '.woff2', '.ttf', '.eot',
        '.mp3', '.mp4', '.wav', '.avi',
        '.pyc', '.pyo', '.so', '.dylib', '.dll',
    }

    # Note: .md files are scanned because they often contain executable code blocks.
    # This may produce false positives when patterns appear in documentation prose.
    # Review findings to distinguish between actual code and documentation examples.

    def audit_skill(self, skill_path: Path) -> Dict[str, List[Tuple[str, int, str]]]:
        """Audit a skill directory for security issues.

        Args:
            skill_path: Path to the skill directory to scan.

        Returns:
            Dictionary with 'critical', 'warning', and 'info' keys,
            each containing a list of (relative_path, line_number, description) tuples.
        """
        findings: Dict[str, List[Tuple[str, int, str]]] = {
            "critical": [],
            "warning": [],
            "info": [],
        }

        if not skill_path.exists() or not skill_path.is_dir():
            return findings

        # Scan all files in the skill directory
        for filepath in skill_path.rglob('*'):
            if not filepath.is_file():
                continue

            # Skip binary files by extension
            if filepath.suffix.lower() in self.SKIP_EXTENSIONS:
                continue

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (UnicodeDecodeError, PermissionError, OSError):
                continue

            rel_path = str(filepath.relative_to(skill_path))

            for pattern, description in self.CRITICAL_PATTERNS:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_num = content[:match.start()].count('\n') + 1
                    findings["critical"].append((rel_path, line_num, description))

            for pattern, description in self.WARNING_PATTERNS:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_num = content[:match.start()].count('\n') + 1
                    findings["warning"].append((rel_path, line_num, description))

            for pattern, description in self.INFO_PATTERNS:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_num = content[:match.start()].count('\n') + 1
                    findings["info"].append((rel_path, line_num, description))

        return findings

    def format_report(self, skill_name: str, findings: Dict[str, List[Tuple[str, int, str]]]) -> str:
        """Format audit findings into a human-readable report.

        Args:
            skill_name: Name of the skill that was audited.
            findings: Dictionary of findings from audit_skill().

        Returns:
            Formatted multi-line report string.
        """
        lines = [f"## Security Audit: {skill_name}"]

        if findings["critical"]:
            lines.append("\n### CRITICAL Issues")
            for file, line, desc in findings["critical"]:
                lines.append(f"- {file}:{line} - {desc}")

        if findings["warning"]:
            lines.append("\n### WARNING")
            for file, line, desc in findings["warning"]:
                lines.append(f"- {file}:{line} - {desc}")

        if findings["info"]:
            lines.append("\n### INFO")
            for file, line, desc in findings["info"]:
                lines.append(f"- {file}:{line} - {desc}")

        if not any(findings.values()):
            lines.append("\nNo security issues detected.")

        return "\n".join(lines)

    def is_blocked(self, findings: Dict[str, List[Tuple[str, int, str]]]) -> bool:
        """Check if a skill should be blocked based on findings.

        Args:
            findings: Dictionary of findings from audit_skill().

        Returns:
            True if the skill has critical issues and should be blocked.
        """
        return len(findings.get("critical", [])) > 0

    def summary(self, findings: Dict[str, List[Tuple[str, int, str]]]) -> str:
        """Return a one-line summary of findings.

        Args:
            findings: Dictionary of findings from audit_skill().

        Returns:
            One-line summary string.
        """
        counts = {k: len(v) for k, v in findings.items()}
        if counts["critical"]:
            return f"BLOCKED: {counts['critical']} critical, {counts['warning']} warnings"
        elif counts["warning"]:
            return f"WARN: {counts['warning']} warnings, {counts['info']} info"
        elif counts["info"]:
            return f"OK: {counts['info']} info items"
        return "CLEAN: no issues"
