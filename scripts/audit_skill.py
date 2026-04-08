#!/usr/bin/env python3
"""CLI tool to audit a skill for security issues.

Usage:
    python3 audit_skill.py <skill-name>

Searches for the skill in:
    1. global-skills/ (framework skills)
    2. ~/.claude/skills/ (user-installed skills)

Exit codes:
    0 - No critical issues found
    1 - Critical issues found (or skill not found)
"""

import sys
from pathlib import Path

# Add the caddy module directory so we can import SkillAuditor
_framework_dir = Path(__file__).resolve().parent.parent / "global-hooks" / "framework" / "caddy"
sys.path.insert(0, str(_framework_dir))

from skill_auditor import SkillAuditor


def find_skill(skill_name: str) -> Path | None:
    """Locate a skill directory by name.

    Args:
        skill_name: Name of the skill to find.

    Returns:
        Path to the skill directory, or None if not found.
    """
    candidates = [
        Path(__file__).resolve().parent.parent / "global-skills" / skill_name,
        Path.home() / ".claude" / "skills" / skill_name,
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: audit_skill.py <skill-name>")
        print()
        print("Examples:")
        print("  audit_skill.py security-scanner")
        print("  audit_skill.py code-review")
        sys.exit(1)

    skill_name = sys.argv[1]
    skill_path = find_skill(skill_name)

    if skill_path is None:
        print(f"Skill not found: {skill_name}")
        print()
        print("Searched in:")
        print(f"  - {Path(__file__).resolve().parent.parent / 'global-skills' / skill_name}")
        print(f"  - {Path.home() / '.claude' / 'skills' / skill_name}")
        sys.exit(1)

    print(f"Auditing: {skill_path}")
    print()

    auditor = SkillAuditor()
    findings = auditor.audit_skill(skill_path)
    report = auditor.format_report(skill_name, findings)

    print(report)
    print()
    print(f"Summary: {auditor.summary(findings)}")

    sys.exit(1 if findings["critical"] else 0)


if __name__ == "__main__":
    main()
