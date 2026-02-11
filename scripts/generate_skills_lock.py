#!/usr/bin/env python3
"""Generate skills.lock with SHA-256 hashes of all skill files.

Scans the global-skills/ directory, computes SHA-256 hashes for every file
in each skill directory, and writes a lock file to ~/.claude/skills.lock.
This lock file is used by the verify_skills.py hook to detect tampering.

Usage:
    python3 scripts/generate_skills_lock.py
    # or via justfile:
    just skills-lock
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def hash_file(filepath: Path) -> str:
    """Compute SHA-256 hash of a file, reading in 8KB chunks."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def hash_skill(skill_dir: Path) -> Dict[str, Any]:
    """Hash all files in a skill directory recursively.

    Returns a dict with:
        - files: mapping of relative path -> SHA-256 hash
        - file_count: total number of files hashed
    """
    files = {}

    for filepath in sorted(skill_dir.rglob("*")):
        if filepath.is_file():
            # Skip hidden files and common non-essential files
            rel_path = filepath.relative_to(skill_dir)
            parts = rel_path.parts
            if any(part.startswith(".") for part in parts):
                continue
            if any(part == "__pycache__" for part in parts):
                continue
            if filepath.suffix in (".pyc", ".pyo"):
                continue

            files[str(rel_path)] = hash_file(filepath)

    return {"files": files, "file_count": len(files)}


def generate_lock(skills_dir: Path, output_path: Path) -> bool:
    """Generate skills.lock for all skills in the given directory.

    Args:
        skills_dir: Path to the global-skills/ directory.
        output_path: Path where the lock file will be written.

    Returns:
        True if lock file was generated successfully, False otherwise.
    """
    if not skills_dir.is_dir():
        print(f"Error: Skills directory not found: {skills_dir}", file=sys.stderr)
        return False

    lock_data = {
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "skills_dir": str(skills_dir),
        "skills": {},
    }

    skill_count = 0
    total_files = 0

    for skill_path in sorted(skills_dir.iterdir()):
        if skill_path.is_dir() and not skill_path.name.startswith("."):
            skill_name = skill_path.name
            skill_data = hash_skill(skill_path)
            lock_data["skills"][skill_name] = skill_data
            skill_count += 1
            total_files += skill_data["file_count"]

    # Compute an overall checksum of all individual file hashes
    # This provides a quick "has anything changed" check
    all_hashes = []
    for skill_name in sorted(lock_data["skills"]):
        for file_path in sorted(lock_data["skills"][skill_name]["files"]):
            all_hashes.append(lock_data["skills"][skill_name]["files"][file_path])

    overall = hashlib.sha256(":".join(all_hashes).encode()).hexdigest()
    lock_data["overall_checksum"] = overall

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(lock_data, f, indent=2, sort_keys=True)

    print(f"Generated {output_path}")
    print(f"  Skills: {skill_count}")
    print(f"  Total files: {total_files}")
    print(f"  Overall checksum: {overall[:16]}...")
    return True


if __name__ == "__main__":
    # Default paths
    repo_dir = Path(__file__).resolve().parent.parent
    skills_dir = repo_dir / "global-skills"
    output = Path.home() / ".claude" / "skills.lock"

    # Allow override via command-line arguments
    if len(sys.argv) > 1:
        skills_dir = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output = Path(sys.argv[2])

    success = generate_lock(skills_dir, output)
    sys.exit(0 if success else 1)
