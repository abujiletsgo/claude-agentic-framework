#!/usr/bin/env python3
"""
Inject Always-Loaded Skills — SessionStart Hook

Scans global-skills/*/SKILL.md for files with `always-loaded: true` in their
YAML frontmatter and injects their content into the session context so they
are available in every conversation without explicit invocation.

Exit codes: 0 always (never block session start)
"""

import json
import re
import sys
from pathlib import Path


def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter fields as a flat string→string dict."""
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    fields = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fields[key.strip()] = val.strip()
    return fields


def main() -> None:
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception:
        hook_input = {}

    cwd = hook_input.get("cwd", ".")
    repo_root = Path(cwd).resolve()
    skills_dir = repo_root / "global-skills"

    if not skills_dir.exists():
        print(json.dumps({}))
        return

    injected: list[str] = []

    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        try:
            content = skill_file.read_text(encoding="utf-8")
        except Exception:
            continue

        meta = parse_frontmatter(content)
        if meta.get("always-loaded", "").lower() not in ("true", "yes", "1"):
            continue

        name = meta.get("name", skill_file.parent.name)
        injected.append(f"## Always-Loaded Skill: `{name}`\n\n{content}")

    if not injected:
        print(json.dumps({}))
        return

    context = (
        "**ALWAYS-LOADED SKILLS** — the following skills are pre-loaded into every session:\n\n"
        + "\n\n---\n\n".join(injected)
    )

    # session_startup.py collects "message" keys and merges them into additionalContext
    print(json.dumps({"message": context}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write(f"inject_always_loaded_skills error (non-blocking): {e}\n")
        print(json.dumps({}))
    sys.exit(0)
