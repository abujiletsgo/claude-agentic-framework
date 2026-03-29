#!/usr/bin/env python3
"""Interactive review tool for blocked skills.

Allows users to review detailed findings, see context, and whitelist safe skills.
"""

import sys
from pathlib import Path
import json

# Add framework directory to path
framework_dir = Path.home() / "Documents" / "claude-agentic-framework" / "global-hooks" / "framework"
sys.path.insert(0, str(framework_dir))

from caddy.skill_auditor import SkillAuditor


WHITELIST_FILE = Path.home() / ".claude" / "skills-whitelist.json"


def load_whitelist():
    """Load the whitelist file."""
    if not WHITELIST_FILE.exists():
        return {"whitelisted_skills": [], "whitelisted_patterns": []}

    with open(WHITELIST_FILE, 'r') as f:
        return json.load(f)


def save_whitelist(whitelist):
    """Save the whitelist file."""
    WHITELIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WHITELIST_FILE, 'w') as f:
        json.dump(whitelist, f, indent=2, sort_keys=True)


def show_finding_context(skill_path: Path, file_path: str, line_num: int, description: str):
    """Show the context around a finding."""
    full_path = skill_path / file_path

    if not full_path.exists():
        print(f"   File not found: {file_path}")
        return

    try:
        with open(full_path, 'r') as f:
            lines = f.readlines()

        # Show 3 lines before and after
        start = max(0, line_num - 4)
        end = min(len(lines), line_num + 3)

        print(f"\n   Context from {file_path}:")
        print(f"   {'─' * 70}")
        for i in range(start, end):
            marker = ">>>" if i == line_num - 1 else "   "
            print(f"   {marker} {i+1:4d} │ {lines[i].rstrip()}")
        print(f"   {'─' * 70}")

    except Exception as e:
        print(f"   Could not read file: {e}")


def review_skill(skill_path: Path, skill_name: str, findings: dict):
    """Interactive review of a single skill."""
    print(f"\n{'=' * 80}")
    print(f"Reviewing: {skill_name}")
    print(f"Path: {skill_path}")
    print(f"{'=' * 80}\n")

    auditor = SkillAuditor()

    # Show summary
    critical_count = len(findings.get("critical", []))
    warning_count = len(findings.get("warning", []))
    info_count = len(findings.get("info", []))

    print(f"Summary:")
    print(f"  🚫 Critical: {critical_count}")
    print(f"  ⚠️  Warnings: {warning_count}")
    print(f"  ℹ️  Info: {info_count}")

    # Show detailed findings
    if critical_count > 0:
        print(f"\n🚫 CRITICAL Issues ({critical_count}):")
        for i, (file, line, desc) in enumerate(findings["critical"], 1):
            print(f"\n  {i}. {file}:{line}")
            print(f"     Issue: {desc}")
            show_finding_context(skill_path, file, line, desc)

    if warning_count > 0:
        print(f"\n⚠️  WARNING Issues ({warning_count}):")
        for i, (file, line, desc) in enumerate(findings["warning"], 1):
            print(f"\n  {i}. {file}:{line}")
            print(f"     Issue: {desc}")
            # Only show context for first 3 warnings
            if i <= 3:
                show_finding_context(skill_path, file, line, desc)
            elif i == 4:
                print(f"   ... and {warning_count - 3} more warnings (not shown)")
                break

    # Ask user what to do
    print(f"\n{'─' * 80}")
    print(f"\nOptions:")
    print(f"  [w] Whitelist this skill (mark as safe, ignore all findings)")
    print(f"  [r] Review next (skip this skill for now)")
    print(f"  [q] Quit review")

    while True:
        choice = input(f"\nYour choice [w/r/q]: ").lower().strip()

        if choice == 'w':
            return 'whitelist'
        elif choice == 'r':
            return 'skip'
        elif choice == 'q':
            return 'quit'
        else:
            print("Invalid choice. Please enter 'w', 'r', or 'q'.")


def main():
    """Main review workflow."""
    if len(sys.argv) < 2:
        print("Usage: review_blocked_skills.py <project_directory>")
        print("\nExample:")
        print("  cd ~/my-project")
        print("  python3 ~/Documents/claude-agentic-framework/scripts/review_blocked_skills.py .")
        return 1

    project_dir = Path(sys.argv[1]).resolve()
    skills_dir = project_dir / ".claude" / "skills"

    if not skills_dir.exists():
        print(f"No .claude/skills/ directory found in {project_dir}")
        return 0

    # Load whitelist
    whitelist = load_whitelist()
    whitelisted_skills = set(whitelist.get("whitelisted_skills", []))

    print("=" * 80)
    print("Blocked Skills Review")
    print("=" * 80)
    print(f"\nProject: {project_dir}")
    print(f"Whitelist: {WHITELIST_FILE}")
    print(f"Currently whitelisted: {len(whitelisted_skills)} skills")

    # Scan all skills
    auditor = SkillAuditor()
    blocked_skills = []

    for skill_path in skills_dir.iterdir():
        if not skill_path.is_dir():
            continue

        skill_name = skill_path.name

        # Skip if already whitelisted
        if skill_name in whitelisted_skills:
            continue

        findings = auditor.audit_skill(skill_path)

        if auditor.is_blocked(findings):
            blocked_skills.append((skill_path, skill_name, findings))

    if not blocked_skills:
        print("\n✅ No blocked skills found!")
        print("\nAll local skills are either:")
        print("  - Clean (no security issues)")
        print("  - Already whitelisted")
        return 0

    print(f"\nFound {len(blocked_skills)} blocked skill(s) to review.\n")

    # Review each blocked skill
    newly_whitelisted = []

    for skill_path, skill_name, findings in blocked_skills:
        result = review_skill(skill_path, skill_name, findings)

        if result == 'whitelist':
            whitelisted_skills.add(skill_name)
            newly_whitelisted.append(skill_name)
            print(f"\n✅ {skill_name} added to whitelist")
        elif result == 'quit':
            break

    # Save whitelist if changes were made
    if newly_whitelisted:
        whitelist["whitelisted_skills"] = sorted(whitelisted_skills)
        save_whitelist(whitelist)

        print(f"\n{'=' * 80}")
        print(f"Whitelist updated!")
        print(f"{'=' * 80}")
        print(f"\nNewly whitelisted ({len(newly_whitelisted)}):")
        for skill in newly_whitelisted:
            print(f"  ✅ {skill}")

        print(f"\nWhitelist saved to: {WHITELIST_FILE}")
        print(f"\nTo remove a skill from whitelist, edit the file manually.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
