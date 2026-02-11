#!/usr/bin/env -S uv run --script
# /// script
# dependencies = []
# ///
"""SessionStart hook: Verify skills haven't been tampered with.

Compares current skill file hashes against the stored skills.lock file.
Reports warnings for any modified, missing, or new files but does NOT
block execution -- this is an advisory check only.

Exit codes:
    0 -- always (this hook never blocks)

Output:
    JSON with result="continue" and optional warning message.
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def hash_file(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def collect_current_files(skill_path: Path) -> Dict[str, str]:
    """Collect hashes of all files currently in a skill directory."""
    files = {}
    if not skill_path.exists():
        return files

    # Resolve symlinks to get actual directory
    resolved = skill_path.resolve()
    if not resolved.is_dir():
        return files

    for filepath in sorted(resolved.rglob("*")):
        if filepath.is_file():
            rel_path = filepath.relative_to(resolved)
            parts = rel_path.parts
            # Skip hidden files and caches (same exclusions as generator)
            if any(part.startswith(".") for part in parts):
                continue
            if any(part == "__pycache__" for part in parts):
                continue
            if filepath.suffix in (".pyc", ".pyo"):
                continue
            files[str(rel_path)] = hash_file(filepath)

    return files


def verify_skill(
    skill_name: str,
    skill_lock: Dict[str, Any],
    skills_dir: Path,
) -> List[str]:
    """Verify a single skill against its lock data.

    Returns a list of warning strings (empty if everything matches).
    """
    warnings = []
    skill_path = skills_dir / skill_name

    if not skill_path.exists():
        warnings.append(f"  MISSING SKILL: {skill_name}")
        return warnings

    expected_files = skill_lock.get("files", {})
    current_files = collect_current_files(skill_path)

    # Check for modified or missing files
    for rel_path, expected_hash in sorted(expected_files.items()):
        if rel_path not in current_files:
            warnings.append(f"  DELETED: {skill_name}/{rel_path}")
        elif current_files[rel_path] != expected_hash:
            warnings.append(f"  MODIFIED: {skill_name}/{rel_path}")

    # Check for new files not in lock
    for rel_path in sorted(current_files):
        if rel_path not in expected_files:
            warnings.append(f"  NEW FILE: {skill_name}/{rel_path}")

    return warnings


def verify_skills() -> Dict[str, Any]:
    """Verify all skills integrity against skills.lock.

    Returns a hook result dict.
    """
    lock_path = Path.home() / ".claude" / "skills.lock"

    if not lock_path.exists():
        # No lock file yet -- skip verification (first run or not generated)
        return {"result": "continue"}

    # Load lock file
    try:
        with open(lock_path) as f:
            lock_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return {
            "result": "continue",
            "message": f"Warning: Could not read skills.lock: {e}",
        }

    # Validate lock file format
    if "version" not in lock_data or "skills" not in lock_data:
        return {
            "result": "continue",
            "message": "Warning: Invalid skills.lock format",
        }

    # Determine skills directory
    # Prefer the source directory recorded in the lock file (the repo's global-skills/)
    # since that is what was hashed. Fall back to ~/.claude/skills/ if not available.
    skills_dir = None
    if "skills_dir" in lock_data:
        candidate = Path(lock_data["skills_dir"])
        if candidate.is_dir():
            skills_dir = candidate

    if skills_dir is None:
        candidate = Path.home() / ".claude" / "skills"
        if candidate.is_dir():
            skills_dir = candidate

    if skills_dir is None:
        return {
            "result": "continue",
            "message": "Warning: Skills directory not found for verification",
        }

    # Verify each locked skill
    all_warnings: List[str] = []
    skills_checked = 0
    skills_ok = 0

    for skill_name, skill_lock in sorted(lock_data["skills"].items()):
        skills_checked += 1
        skill_warnings = verify_skill(skill_name, skill_lock, skills_dir)
        if skill_warnings:
            all_warnings.extend(skill_warnings)
        else:
            skills_ok += 1

    # Check for unlocked skills (present on disk but not in lock file)
    if skills_dir.is_dir():
        for skill_path in sorted(skills_dir.iterdir()):
            resolved = skill_path.resolve() if skill_path.is_symlink() else skill_path
            if resolved.is_dir() and not skill_path.name.startswith("."):
                if skill_path.name not in lock_data["skills"]:
                    all_warnings.append(f"  UNLOCKED SKILL: {skill_path.name}")

    # Build result
    if all_warnings:
        warning_text = "\n".join(all_warnings)
        message = (
            f"SKILL INTEGRITY WARNING "
            f"({skills_ok}/{skills_checked} skills OK)\n"
            f"\n{warning_text}\n"
            f"\nRun: python3 scripts/generate_skills_lock.py to update"
        )
        return {
            "result": "continue",
            "message": message,
            "hookSpecificOutput": {
                "statusMessage": f"Skills integrity: {len(all_warnings)} issue(s) found",
            },
        }

    return {
        "result": "continue",
        "hookSpecificOutput": {
            "statusMessage": f"Skills integrity: {skills_ok}/{skills_checked} OK",
        },
    }


if __name__ == "__main__":
    result = verify_skills()
    print(json.dumps(result))
    sys.exit(0)
