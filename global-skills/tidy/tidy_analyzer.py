#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""
tidy_analyzer.py — File organization analyzer for the /tidy skill
=================================================================

Scans the repo and produces a JSON report of:
  - Misplaced files (files in root that belong elsewhere)
  - Naming convention violations (non-kebab-case dirs, etc.)
  - New/untracked files from the current session
  - Obsolete file candidates (no references, old modification date)
  - Stale doc counts (CLAUDE.md counts vs actual)

Usage:
  uv run global-skills/tidy/tidy_analyzer.py [--json] [--verbose]

Output: JSON report to stdout (default) or human-readable with --verbose.
Exit: always 0 (informational only, never blocks).
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True
).strip())

# Files that legitimately belong in the project root
ROOT_ALLOWLIST = {
    "README.md", "CLAUDE.md", "ADMIN.md", "QUICKSTART.md",
    "FRAMEWORK_REFERENCE.md", "install.sh", "uninstall.sh",
    "justfile", ".gitignore", ".DS_Store", ".python-version",
    "pyproject.toml", "package.json", "Cargo.toml", "go.mod",
    "LICENSE", "LICENSE.md", "CHANGELOG.md", "CONTRIBUTING.md",
    "Makefile", "Dockerfile", "docker-compose.yml",
    "requirements.txt", "setup.py", "setup.cfg",
}

# Directories that legitimately belong in root
ROOT_DIR_ALLOWLIST = {
    ".git", ".claude", ".github", ".vscode",
    "apps", "archive", "data", "docs", "guides", "scripts",
    "templates", "tests", "node_modules", "__pycache__",
    "global-agents", "global-commands", "global-hooks",
    "global-skills", "global-status-lines",
    "src", "lib", "pkg", "cmd", "internal", "vendor",
    "dist", "build", "out", ".next", "target",
}

# Standard directories and what goes in them
ROUTING_RULES = {
    "global-agents": {
        "patterns": [r"model:", r"description:.*agent"],
        "extensions": [".md"],
        "description": "Agent definitions with model: frontmatter",
    },
    "global-skills": {
        "patterns": [r"name:.*\n.*version:", r"user-invocable:"],
        "extensions": [".md"],
        "description": "Skill definitions with name/version frontmatter",
    },
    "global-commands": {
        "patterns": [r"^# /\w+", r"## Usage\n```"],
        "extensions": [".md"],
        "description": "Command definitions starting with # /command",
    },
    "scripts": {
        "patterns": [],
        "extensions": [".py", ".sh", ".ts", ".js"],
        "description": "Utility scripts and automation",
    },
    "docs": {
        "patterns": [],
        "extensions": [".md", ".html", ".pdf"],
        "description": "Documentation files",
    },
    "data": {
        "patterns": [],
        "extensions": [".yaml", ".yml", ".json", ".csv", ".sqlite", ".db"],
        "description": "Configuration and data files",
    },
    "tests": {
        "patterns": [r"test_", r"_test\.", r"\.test\.", r"\.spec\."],
        "extensions": [".py", ".js", ".ts"],
        "description": "Test files",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_git(*args: str) -> str:
    """Run a git command and return stdout."""
    try:
        return subprocess.check_output(
            ["git", *args], text=True, stderr=subprocess.DEVNULL, cwd=REPO_ROOT
        ).strip()
    except subprocess.CalledProcessError:
        return ""


def is_kebab_case(name: str) -> bool:
    """Check if a name follows kebab-case convention."""
    return bool(re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', name))


def count_references(filename: str) -> int:
    """Count how many files reference a given filename."""
    try:
        result = subprocess.check_output(
            ["grep", "-rl", filename, str(REPO_ROOT),
             "--include=*.md", "--include=*.py", "--include=*.sh",
             "--include=*.yaml", "--include=*.json", "--include=*.ts",
             "--include=*.js"],
            text=True, stderr=subprocess.DEVNULL
        )
        # Subtract self-references
        lines = [l for l in result.strip().split("\n") if l and filename not in l]
        return len(lines)
    except subprocess.CalledProcessError:
        return 0


def detect_file_type(filepath: Path) -> str | None:
    """Detect what routing category a file belongs to based on content and extension."""
    ext = filepath.suffix.lower()
    name = filepath.name.lower()

    # Test files (check name patterns first)
    for pattern in ROUTING_RULES["tests"]["patterns"]:
        if re.search(pattern, name):
            return "tests"

    # Read first 500 chars for content-based detection
    content = ""
    try:
        content = filepath.read_text(errors="ignore")[:500]
    except (OSError, PermissionError):
        pass

    # Agent detection
    if ext == ".md" and re.search(r'^model:', content, re.MULTILINE):
        return "global-agents"

    # Skill detection
    if ext == ".md" and re.search(r'^name:', content, re.MULTILINE) and re.search(r'^version:', content, re.MULTILINE):
        return "global-skills"

    # Command detection
    if ext == ".md" and re.search(r'^# /\w+', content, re.MULTILINE):
        return "global-commands"

    # Extension-based fallback
    if ext in (".py", ".sh"):
        return "scripts"
    if ext in (".yaml", ".yml", ".json") and ext != "":
        return "data"
    if ext in (".md", ".html", ".pdf"):
        return "docs"

    return None


def normalize_name(name: str, is_dir: bool = False) -> str:
    """Convert a name to the project's naming convention."""
    base, ext = os.path.splitext(name) if not is_dir else (name, "")

    # Special files that keep their casing
    if name in ("README.md", "SKILL.md", "CLAUDE.md", "ADMIN.md",
                "QUICKSTART.md", "FRAMEWORK_REFERENCE.md", "CHANGELOG.md",
                "LICENSE", "LICENSE.md", "CONTRIBUTING.md", "Makefile",
                "Dockerfile", "MANIFEST.md"):
        return name

    if ext == ".py":
        # Python files: snake_case
        normalized = re.sub(r'[- ]', '_', base).lower()
        normalized = re.sub(r'_+', '_', normalized)
        return normalized + ext
    else:
        # Everything else: kebab-case
        normalized = re.sub(r'[_ ]', '-', base).lower()
        normalized = re.sub(r'-+', '-', normalized)
        return normalized + ext


# ---------------------------------------------------------------------------
# Analysis phases
# ---------------------------------------------------------------------------

def find_misplaced_root_files() -> list[dict]:
    """Find files in project root that don't belong there."""
    issues = []
    for item in REPO_ROOT.iterdir():
        if item.name.startswith(".") and item.name not in ROOT_ALLOWLIST:
            continue
        if item.is_dir():
            if item.name not in ROOT_DIR_ALLOWLIST and not item.name.startswith("."):
                issues.append({
                    "path": item.name,
                    "type": "misplaced_dir",
                    "suggestion": None,
                    "reason": f"Directory '{item.name}' doesn't match known root directories",
                })
        elif item.is_file():
            if item.name not in ROOT_ALLOWLIST:
                dest = detect_file_type(item)
                suggestion = f"{dest}/{normalize_name(item.name)}" if dest else None
                issues.append({
                    "path": item.name,
                    "type": "misplaced_file",
                    "suggested_destination": suggestion,
                    "detected_type": dest,
                    "references": count_references(item.name),
                    "reason": f"File doesn't belong in project root",
                })
    return issues


def find_naming_violations() -> list[dict]:
    """Find directories and files that violate naming conventions."""
    issues = []
    check_dirs = ["global-agents", "global-commands", "global-hooks", "global-skills"]

    for dir_name in check_dirs:
        dir_path = REPO_ROOT / dir_name
        if not dir_path.exists():
            continue

        for item in dir_path.iterdir():
            if item.is_dir() and item.name != "__pycache__":
                if not is_kebab_case(item.name):
                    issues.append({
                        "path": str(item.relative_to(REPO_ROOT)),
                        "type": "naming_violation",
                        "current": item.name,
                        "suggested": normalize_name(item.name, is_dir=True),
                        "reason": "Directory should be kebab-case",
                    })
    return issues


def find_untracked_files() -> list[dict]:
    """Find new untracked files."""
    untracked = run_git("ls-files", "--others", "--exclude-standard")
    if not untracked:
        return []

    results = []
    for line in untracked.split("\n"):
        if line.strip():
            fp = REPO_ROOT / line.strip()
            results.append({
                "path": line.strip(),
                "type": "untracked",
                "detected_type": detect_file_type(fp) if fp.exists() else None,
            })
    return results


def find_stale_files(days: int = 90) -> list[dict]:
    """Find files not modified in N+ days that might be obsolete."""
    cutoff = datetime.now() - timedelta(days=days)
    results = []

    skip_dirs = {".git", "archive", "node_modules", "__pycache__", ".claude"}
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        rel_root = Path(root).relative_to(REPO_ROOT)

        # Only go 3 levels deep
        if len(rel_root.parts) > 3:
            dirs.clear()
            continue

        for f in files:
            fp = Path(root) / f
            try:
                mtime = datetime.fromtimestamp(fp.stat().st_mtime)
                if mtime < cutoff:
                    rel_path = str(fp.relative_to(REPO_ROOT))
                    refs = count_references(f)
                    if refs == 0:  # Only flag files with 0 references
                        results.append({
                            "path": rel_path,
                            "type": "stale_candidate",
                            "last_modified": mtime.isoformat()[:10],
                            "days_old": (datetime.now() - mtime).days,
                            "references": refs,
                        })
            except OSError:
                pass

    return results[:20]  # Cap at 20 to avoid noise


def check_doc_counts() -> dict:
    """Compare CLAUDE.md declared counts vs actual filesystem counts."""
    actual = {}

    # Count agents
    agents_dir = REPO_ROOT / "global-agents"
    if agents_dir.exists():
        actual["agents"] = len([f for f in agents_dir.glob("*.md") if f.name != "README.md"])

    # Count commands
    cmds_dir = REPO_ROOT / "global-commands"
    if cmds_dir.exists():
        actual["commands"] = len(list(cmds_dir.glob("*.md")))

    # Count skills
    skills_dir = REPO_ROOT / "global-skills"
    if skills_dir.exists():
        actual["skills"] = len(list(skills_dir.glob("*/SKILL.md")))

    # Count hooks (from settings template — count hook entries with "type": "command")
    template = REPO_ROOT / "templates" / "settings.json.template"
    if template.exists():
        try:
            content = template.read_text()
            # Count occurrences of "type": "command" which marks actual hook entries
            actual["hooks"] = len(re.findall(r'"type"\s*:\s*"command"', content))
        except OSError:
            pass

    # Parse CLAUDE.md for declared counts
    declared = {}
    claude_md = REPO_ROOT / "CLAUDE.md"
    if claude_md.exists():
        try:
            text = claude_md.read_text()
            # Look for patterns like "9 agents" or "agents (9)"
            for key in ("agents", "commands", "skills", "hooks"):
                m = re.search(rf'(\d+)\s+{key}', text)
                if m:
                    declared[key] = int(m.group(1))
                else:
                    m = re.search(rf'{key}.*?(\d+)', text, re.IGNORECASE)
                    if m:
                        declared[key] = int(m.group(1))
        except OSError:
            pass

    stale = {}
    for key in actual:
        if key in declared and actual[key] != declared[key]:
            stale[key] = {
                "declared": declared.get(key),
                "actual": actual[key],
                "drift": actual[key] - declared.get(key, 0),
            }

    return {"actual": actual, "declared": declared, "stale": stale}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    verbose = "--verbose" in sys.argv

    report = {
        "timestamp": datetime.now().isoformat()[:19],
        "repo_root": str(REPO_ROOT),
        "misplaced": find_misplaced_root_files(),
        "naming_violations": find_naming_violations(),
        "untracked": find_untracked_files(),
        "stale_candidates": find_stale_files(),
        "doc_counts": check_doc_counts(),
    }

    # Summary stats
    report["summary"] = {
        "misplaced_count": len(report["misplaced"]),
        "naming_violation_count": len(report["naming_violations"]),
        "untracked_count": len(report["untracked"]),
        "stale_count": len(report["stale_candidates"]),
        "docs_stale": len(report["doc_counts"].get("stale", {})),
        "total_issues": (
            len(report["misplaced"]) +
            len(report["naming_violations"]) +
            len(report["stale_candidates"]) +
            len(report["doc_counts"].get("stale", {}))
        ),
    }

    if verbose:
        print_human_readable(report)
    else:
        print(json.dumps(report, indent=2))


def print_human_readable(report: dict):
    """Print a formatted human-readable report."""
    s = report["summary"]
    print(f"{'='*60}")
    print(f"  TIDY REPORT — {report['timestamp']}")
    print(f"{'='*60}")

    if s["total_issues"] == 0 and s["untracked_count"] == 0:
        print("\n  All clean! No issues found.\n")
        return

    if report["misplaced"]:
        print(f"\n## Misplaced Files ({len(report['misplaced'])})")
        for item in report["misplaced"]:
            dest = item.get("suggested_destination", "?")
            refs = item.get("references", 0)
            print(f"  - {item['path']} → {dest} ({refs} references)")

    if report["naming_violations"]:
        print(f"\n## Naming Violations ({len(report['naming_violations'])})")
        for item in report["naming_violations"]:
            print(f"  - {item['path']} → {item['suggested']}")

    if report["untracked"]:
        print(f"\n## Untracked Files ({len(report['untracked'])})")
        for item in report["untracked"]:
            dtype = item.get("detected_type", "unknown")
            print(f"  - {item['path']} (type: {dtype})")

    if report["stale_candidates"]:
        print(f"\n## Archive Candidates ({len(report['stale_candidates'])})")
        for item in report["stale_candidates"]:
            print(f"  - {item['path']} ({item['days_old']}d old, {item['references']} refs)")

    stale_docs = report["doc_counts"].get("stale", {})
    if stale_docs:
        print(f"\n## Stale Doc Counts")
        for key, info in stale_docs.items():
            print(f"  - {key}: CLAUDE.md says {info['declared']}, actual is {info['actual']} (drift: {info['drift']:+d})")

    print(f"\n{'='*60}")
    print(f"  Total issues: {s['total_issues']} | Untracked: {s['untracked_count']}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
