#!/usr/bin/env python3
"""CLI tool to audit a single local skill directory for security issues.

Usage:
    audit_local_skill.py <skill_directory>

Example:
    audit_local_skill.py .claude/skills/my-custom-skill/

Exit codes:
    0 - Clean (no issues)
    1 - Warnings detected
    2 - Critical issues detected (skill should be blocked)
"""

import sys
from pathlib import Path

# Add framework directory to path
framework_dir = Path.home() / "Documents" / "claude-agentic-framework" / "global-hooks" / "framework"
sys.path.insert(0, str(framework_dir))

from caddy.skill_auditor import SkillAuditor


def main():
    if len(sys.argv) < 2:
        print("Usage: audit_local_skill.py <skill_directory>", file=sys.stderr)
        return 1

    skill_path = Path(sys.argv[1]).resolve()

    if not skill_path.exists():
        print(f"Error: Skill directory does not exist: {skill_path}", file=sys.stderr)
        return 2

    if not skill_path.is_dir():
        print(f"Error: Not a directory: {skill_path}", file=sys.stderr)
        return 2

    skill_name = skill_path.name
    auditor = SkillAuditor()

    # Run audit
    findings = auditor.audit_skill(skill_path)

    # Determine severity
    critical_count = len(findings.get("critical", []))
    warning_count = len(findings.get("warning", []))
    info_count = len(findings.get("info", []))

    # Print results
    if critical_count > 0:
        print(f"🚫 {skill_name}: BLOCKED")
        print(f"   Critical: {critical_count}, Warnings: {warning_count}, Info: {info_count}")
        if findings["critical"]:
            print("   Critical Issues:")
            for file, line, desc in findings["critical"][:3]:  # Show first 3
                print(f"   - {file}:{line} - {desc}")
            if critical_count > 3:
                print(f"   ... and {critical_count - 3} more")
        print("   Note: .md files may show false positives from documentation examples")
        return 2

    elif warning_count > 0:
        print(f"⚠️  {skill_name}: WARNINGS")
        print(f"   Warnings: {warning_count}, Info: {info_count}")
        if findings["warning"]:
            print("   Warning Issues:")
            for file, line, desc in findings["warning"][:3]:  # Show first 3
                print(f"   - {file}:{line} - {desc}")
        return 1

    elif info_count > 0:
        print(f"ℹ️  {skill_name}: INFO")
        print(f"   Info: {info_count}")
        return 0

    else:
        print(f"✅ {skill_name}: CLEAN")
        return 0


if __name__ == "__main__":
    sys.exit(main())
