#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
auto_skill_generator.py - Stop Hook (Auto Skill Generation)
============================================================

Fires at session end. Reads the session bundle (logged by context-bundle-logger)
to detect repeated multi-step patterns that could be automated as skills.

Detection rules:
  1. Same Grep->Read->Edit sequence on similar file types, 3+ times
  2. Same type of file created (Write) 3+ times with similar paths
  3. Same Bash commands run in sequence 3+ times

When a pattern is detected, generates a SKILL.md in:
  ~/.claude/skills/auto-generated/<skill-name>/SKILL.md

Constraints:
  - Max 1 skill per session
  - Deduplicates against previously generated skills
  - Only generates when pattern confidence is high (3+ occurrences)
  - Lightweight: reads bundle JSON + git diff, no subprocess calls beyond git

Exit: always 0 (never blocks)
"""

import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BUNDLES_DIR = Path.home() / ".claude" / "bundles"
SKILLS_DIR = Path.home() / ".claude" / "skills" / "auto-generated"
LOG_FILE = Path.home() / ".claude" / "data" / "auto_skills_log.jsonl"
HISTORY_FILE = Path.home() / ".claude" / "data" / "auto_skills_history.json"

# Minimum occurrences for a pattern to be considered skill-worthy
MIN_PATTERN_COUNT = 3
# Maximum skills to keep in auto-generated directory
MAX_AUTO_SKILLS = 20


def load_bundle(session_id: str) -> dict | None:
    """Load the session bundle for pattern analysis."""
    bundle_path = BUNDLES_DIR / f"{session_id}.json"
    if not bundle_path.exists():
        return None
    try:
        return json.loads(bundle_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def load_skill_history() -> dict:
    """Load history of previously generated skills to avoid duplicates."""
    if not HISTORY_FILE.exists():
        return {"generated_patterns": [], "skill_count": 0}
    try:
        return json.loads(HISTORY_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {"generated_patterns": [], "skill_count": 0}


def save_skill_history(history: dict) -> None:
    """Persist the skill history."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2))


def log_skill_event(event: dict) -> None:
    """Append an event to the auto skills log."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    event["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")


def ext_category(file_path: str) -> str:
    """Normalize file extension into a category."""
    ext = Path(file_path).suffix.lower()
    mapping = {
        ".py": "python", ".pyi": "python",
        ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
        ".ts": "typescript", ".tsx": "typescript",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".rb": "ruby",
        ".sh": "shell", ".bash": "shell", ".zsh": "shell",
        ".md": "markdown",
        ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
        ".html": "html", ".css": "css",
    }
    return mapping.get(ext, ext.lstrip(".") or "unknown")


def detect_grep_read_edit_pattern(operations: list[dict]) -> dict | None:
    """
    Detect repeated Grep->Read->Edit sequences on similar file types.

    Returns a pattern descriptor if 3+ matching sequences found, else None.
    """
    sequences: list[tuple[str, str]] = []  # (file_category, edit_file)
    i = 0
    while i < len(operations) - 2:
        op_a = operations[i]
        op_b = operations[i + 1]
        op_c = operations[i + 2]

        # Look for Read->Edit on same file (Grep is logged as Bash, not in bundle)
        if (op_b.get("tool") == "Read" and op_c.get("tool") == "Edit"
                and op_b.get("file") and op_c.get("file")
                and op_b["file"] == op_c["file"]):
            cat = ext_category(op_c["file"])
            sequences.append((cat, op_c["file"]))
            i += 3
            continue
        i += 1

    # Count by file category
    cat_counter = Counter(cat for cat, _ in sequences)
    for cat, count in cat_counter.most_common(1):
        if count >= MIN_PATTERN_COUNT:
            files = [f for c, f in sequences if c == cat]
            return {
                "type": "read-edit-loop",
                "category": cat,
                "count": count,
                "example_files": files[:5],
                "description": f"Repeatedly reading and editing {cat} files ({count} times)",
            }
    return None


def detect_repeated_file_creation(operations: list[dict]) -> dict | None:
    """
    Detect same type of file being written 3+ times.

    Returns pattern descriptor if found.
    """
    writes = [op for op in operations if op.get("tool") == "Write" and op.get("file")]

    # Group by (directory_depth_pattern, extension)
    patterns: dict[str, list[str]] = {}
    for op in writes:
        fp = Path(op["file"])
        cat = ext_category(op["file"])
        # Generalize path: replace specific names with wildcards
        parts = fp.parts
        if len(parts) >= 2:
            # Use parent dir name + extension as pattern key
            key = f"{parts[-2]}/{cat}"
        else:
            key = cat
        patterns.setdefault(key, []).append(op["file"])

    for key, files in patterns.items():
        if len(files) >= MIN_PATTERN_COUNT:
            return {
                "type": "repeated-creation",
                "category": key,
                "count": len(files),
                "example_files": files[:5],
                "description": f"Repeatedly creating {key} files ({len(files)} times)",
            }
    return None


def detect_repeated_edits_same_structure(operations: list[dict]) -> dict | None:
    """
    Detect repeated Edit operations with similar old_string/new_string patterns.

    For example: adding the same import, the same boilerplate, etc.
    """
    edits = [op for op in operations
             if op.get("tool") == "Edit" and op.get("old_string") and op.get("new_string")]

    if len(edits) < MIN_PATTERN_COUNT:
        return None

    # Group by similarity of the edit content (first 50 chars of new_string)
    edit_sigs: dict[str, list[dict]] = {}
    for ed in edits:
        # Create a rough signature from the edit
        new_prefix = ed["new_string"][:50].strip()
        if len(new_prefix) < 5:
            continue
        # Normalize whitespace for comparison
        sig = re.sub(r"\s+", " ", new_prefix)[:30]
        edit_sigs.setdefault(sig, []).append(ed)

    for sig, matching_edits in edit_sigs.items():
        if len(matching_edits) >= MIN_PATTERN_COUNT:
            files = list({ed.get("file", "?") for ed in matching_edits})
            return {
                "type": "repeated-edit",
                "category": "boilerplate-insertion",
                "count": len(matching_edits),
                "example_files": files[:5],
                "edit_signature": sig,
                "description": f"Same edit pattern applied {len(matching_edits)} times across files",
            }
    return None


def get_git_diff_patterns(cwd: str) -> dict | None:
    """
    Fallback: analyze git diff for patterns when no bundle is available.

    Detects if many files of the same type were modified with similar changes.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            capture_output=True, text=True, cwd=cwd, timeout=5,
        )
        if result.returncode != 0 or not result.stdout.strip():
            # Try committed changes
            result = subprocess.run(
                ["git", "diff", "--stat", "HEAD~1", "HEAD"],
                capture_output=True, text=True, cwd=cwd, timeout=5,
            )
        if result.returncode != 0 or not result.stdout.strip():
            return None

        lines = result.stdout.strip().splitlines()
        # Parse file names from stat output
        files_changed: list[str] = []
        for line in lines:
            if "|" in line:
                fname = line.split("|")[0].strip()
                files_changed.append(fname)

        if len(files_changed) < MIN_PATTERN_COUNT:
            return None

        # Check if many files of same type changed
        cat_counter = Counter(ext_category(f) for f in files_changed)
        for cat, count in cat_counter.most_common(1):
            if count >= MIN_PATTERN_COUNT and cat not in ("unknown", "markdown"):
                return {
                    "type": "bulk-modification",
                    "category": cat,
                    "count": count,
                    "example_files": [f for f in files_changed if ext_category(f) == cat][:5],
                    "description": f"Bulk-modified {count} {cat} files in one session",
                }
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        pass
    return None


def is_duplicate_pattern(pattern: dict, history: dict) -> bool:
    """Check if this pattern was already turned into a skill."""
    pattern_sig = f"{pattern['type']}:{pattern['category']}"
    return pattern_sig in history.get("generated_patterns", [])


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text[:50] or "unnamed"


def generate_skill(pattern: dict) -> tuple[str, str]:
    """
    Generate a SKILL.md for the detected pattern.

    Returns (skill_name, skill_content).
    """
    ptype = pattern["type"]
    category = pattern["category"]
    count = pattern["count"]
    example_files = pattern.get("example_files", [])
    description = pattern["description"]

    # Build skill name
    if ptype == "read-edit-loop":
        skill_name = f"auto-edit-{slugify(category)}-files"
        instructions = _build_read_edit_skill(category, example_files, count)
    elif ptype == "repeated-creation":
        skill_name = f"auto-create-{slugify(category)}"
        instructions = _build_creation_skill(category, example_files, count)
    elif ptype == "repeated-edit":
        skill_name = f"auto-patch-{slugify(category)}"
        edit_sig = pattern.get("edit_signature", "")
        instructions = _build_patch_skill(category, example_files, count, edit_sig)
    elif ptype == "bulk-modification":
        skill_name = f"auto-bulk-{slugify(category)}"
        instructions = _build_bulk_skill(category, example_files, count)
    else:
        skill_name = f"auto-{slugify(ptype)}-{slugify(category)}"
        instructions = _build_generic_skill(pattern)

    frontmatter = (
        "---\n"
        f"name: {skill_name}\n"
        f"description: \"Auto-generated skill: {description}\"\n"
        "user-invocable: true\n"
        "model: sonnet\n"
        "---\n"
    )

    content = frontmatter + "\n" + instructions
    return skill_name, content


def _build_read_edit_skill(category: str, examples: list, count: int) -> str:
    example_list = "\n".join(f"  - `{f}`" for f in examples[:3])
    return f"""# Auto Edit {category.title()} Files

Auto-generated from a session where {count} {category} files were read and edited
in sequence. This skill automates that workflow.

## Detected Pattern

The session showed a repeated Read -> Edit loop on {category} files:
{example_list}

## Workflow

1. **Identify target files**: Use Glob to find {category} files matching the pattern
2. **Read each file**: Examine the current content
3. **Apply the edit**: Make the required modification
4. **Verify**: Ensure the edit was applied correctly

## When to Use

- When you need to apply the same type of change across multiple {category} files
- When performing bulk updates to {category} file structure or content

## Notes

- Always read the file before editing to confirm context
- Verify each edit individually rather than batch-applying blindly
- If the edit pattern varies significantly between files, handle manually
"""


def _build_creation_skill(category: str, examples: list, count: int) -> str:
    example_list = "\n".join(f"  - `{f}`" for f in examples[:3])
    return f"""# Auto Create {category.title()} Files

Auto-generated from a session where {count} files of type `{category}` were created.

## Detected Pattern

Multiple files were created with a similar structure:
{example_list}

## Workflow

1. **Determine target path**: Follow the naming convention from the examples above
2. **Generate content**: Use the established template/structure
3. **Write the file**: Create with proper formatting
4. **Validate**: Ensure the new file fits the project structure

## Template

Based on the detected pattern, new files should follow the convention
established by the examples. Examine one of the example files to extract
the template before creating new ones.

## When to Use

- When creating new files that follow the same convention as the examples
- When scaffolding out new modules or components of this type
"""


def _build_patch_skill(category: str, examples: list, count: int, edit_sig: str) -> str:
    example_list = "\n".join(f"  - `{f}`" for f in examples[:3])
    return f"""# Auto Patch {category.title()}

Auto-generated from a session where the same edit pattern was applied {count} times.

## Detected Pattern

A consistent edit was applied across files:
{example_list}

Edit signature (truncated): `{edit_sig}`

## Workflow

1. **Find target files**: Use Grep to locate files needing this patch
2. **Read each file**: Confirm the edit applies
3. **Apply the patch**: Use Edit with the established old_string/new_string pattern
4. **Verify**: Run tests or linting after each batch

## When to Use

- When the same boilerplate or structural change needs to be applied across files
- When migrating code patterns (imports, API calls, config entries)

## Caution

- Always verify the edit context before applying -- the same string may appear
  in different semantic contexts
- Run the project's test suite after applying patches
"""


def _build_bulk_skill(category: str, examples: list, count: int) -> str:
    example_list = "\n".join(f"  - `{f}`" for f in examples[:3])
    return f"""# Auto Bulk Modify {category.title()} Files

Auto-generated from a session where {count} {category} files were modified.

## Detected Pattern

A large number of {category} files were changed in one session:
{example_list}
{"  ... and more" if count > 3 else ""}

## Workflow

1. **Identify scope**: Use Glob/Grep to find all files needing modification
2. **Plan changes**: Determine the common transformation
3. **Apply systematically**: Process each file with Read -> Edit
4. **Verify**: Run tests after completing all modifications

## When to Use

- When performing codebase-wide refactoring of {category} files
- When updating conventions, imports, or patterns across the project
"""


def _build_generic_skill(pattern: dict) -> str:
    return f"""# Auto-Generated Skill

Auto-generated from detected session pattern.

## Detected Pattern

- Type: {pattern['type']}
- Category: {pattern['category']}
- Occurrences: {pattern['count']}
- Description: {pattern['description']}

## Workflow

Follow the pattern detected in the session. Examine the example files
for the specific transformation needed.

## Example Files

{chr(10).join(f"- `{f}`" for f in pattern.get('example_files', [])[:5])}
"""


def prune_old_skills() -> None:
    """Remove oldest auto-generated skills if over the limit."""
    if not SKILLS_DIR.exists():
        return
    skill_dirs = sorted(
        SKILLS_DIR.iterdir(),
        key=lambda d: d.stat().st_mtime if d.is_dir() else 0,
    )
    while len(skill_dirs) > MAX_AUTO_SKILLS:
        oldest = skill_dirs.pop(0)
        if oldest.is_dir():
            for f in oldest.iterdir():
                f.unlink(missing_ok=True)
            oldest.rmdir()


def main():
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        data = {}

    session_id = data.get("session_id", "")
    cwd = data.get("cwd", os.getcwd())

    # Load the session bundle for pattern analysis
    bundle = load_bundle(session_id) if session_id else None

    detected_pattern = None

    if bundle and bundle.get("operations"):
        ops = bundle["operations"]
        # Try each detector in priority order (most specific first)
        detected_pattern = (
            detect_repeated_edits_same_structure(ops)
            or detect_grep_read_edit_pattern(ops)
            or detect_repeated_file_creation(ops)
        )

    # Fallback: analyze git diff if no bundle pattern found
    if not detected_pattern:
        detected_pattern = get_git_diff_patterns(cwd)

    if not detected_pattern:
        # No pattern worth automating -- exit silently
        print(json.dumps({}))
        sys.exit(0)

    # Check for duplicates
    history = load_skill_history()
    if is_duplicate_pattern(detected_pattern, history):
        log_skill_event({
            "event": "duplicate_skipped",
            "pattern": detected_pattern["type"],
            "category": detected_pattern["category"],
            "session_id": session_id,
        })
        print(json.dumps({}))
        sys.exit(0)

    # Generate the skill
    skill_name, skill_content = generate_skill(detected_pattern)
    skill_dir = SKILLS_DIR / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text(skill_content)

    # Update history
    pattern_sig = f"{detected_pattern['type']}:{detected_pattern['category']}"
    history.setdefault("generated_patterns", []).append(pattern_sig)
    history["skill_count"] = history.get("skill_count", 0) + 1
    save_skill_history(history)

    # Log the generation
    log_skill_event({
        "event": "skill_generated",
        "skill_name": skill_name,
        "skill_path": str(skill_path),
        "pattern": detected_pattern,
        "session_id": session_id,
    })

    # Prune old skills if needed
    prune_old_skills()

    # Report to stderr (visible in hook output)
    print(
        f"[Auto Skill Generator] New skill created: {skill_name}\n"
        f"  Pattern: {detected_pattern['description']}\n"
        f"  Location: {skill_path}",
        file=sys.stderr,
    )

    print(json.dumps({}))
    sys.exit(0)


if __name__ == "__main__":
    main()
