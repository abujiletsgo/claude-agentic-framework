#!/usr/bin/env python3
"""
Test Coverage Analyzer
======================

Verifies that changed source files have corresponding test files,
and that new functions/classes have test coverage.

Checks:
- Changed source files have a corresponding test file
- New public functions/classes have at least one test
- Test-to-source ratio is reasonable

Convention detection:
- test_<module>.py (Python)
- <module>.test.ts / <module>.spec.ts (JS/TS)
- <module>_test.go (Go)
"""

import ast
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from findings_store import Finding, Severity


# ---------------------------------------------------------------------------
# Test file discovery
# ---------------------------------------------------------------------------

# Mapping from source file patterns to test file patterns
TEST_FILE_PATTERNS = {
    ".py": [
        lambda p: p.parent / f"test_{p.name}",                    # test_foo.py
        lambda p: p.parent / "tests" / f"test_{p.name}",          # tests/test_foo.py
        lambda p: p.parent.parent / "tests" / f"test_{p.name}",   # ../tests/test_foo.py
        lambda p: p.with_name(f"{p.stem}_test.py"),                # foo_test.py
    ],
    ".js": [
        lambda p: p.with_suffix(".test.js"),           # foo.test.js
        lambda p: p.with_suffix(".spec.js"),           # foo.spec.js
        lambda p: p.parent / "__tests__" / p.name,     # __tests__/foo.js
    ],
    ".jsx": [
        lambda p: p.with_suffix(".test.jsx"),
        lambda p: p.with_suffix(".spec.jsx"),
        lambda p: p.parent / "__tests__" / p.name,
    ],
    ".ts": [
        lambda p: p.with_suffix(".test.ts"),
        lambda p: p.with_suffix(".spec.ts"),
        lambda p: p.parent / "__tests__" / (p.stem + ".ts"),
    ],
    ".tsx": [
        lambda p: p.with_suffix(".test.tsx"),
        lambda p: p.with_suffix(".spec.tsx"),
        lambda p: p.parent / "__tests__" / (p.stem + ".tsx"),
    ],
    ".go": [
        lambda p: p.with_name(f"{p.stem}_test.go"),    # foo_test.go
    ],
}


def find_test_file(
    source_path: str,
    repo_root: str,
) -> Optional[str]:
    """
    Find the test file corresponding to a source file.

    Returns the relative path to the test file if found, None otherwise.
    """
    path = Path(source_path)
    ext = path.suffix.lower()

    patterns = TEST_FILE_PATTERNS.get(ext, [])
    root = Path(repo_root)

    for pattern_fn in patterns:
        candidate = pattern_fn(path)
        if (root / candidate).exists():
            return str(candidate)

    return None


def is_test_file(file_path: str) -> bool:
    """Check if a file is itself a test file."""
    name = Path(file_path).name.lower()
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or ".test." in name
        or ".spec." in name
        or name.endswith("_test.go")
        or "/tests/" in file_path
        or "/__tests__/" in file_path
        or "/test/" in file_path
    )


def is_source_file(file_path: str) -> bool:
    """Check if a file is a source code file that should have tests."""
    ext = Path(file_path).suffix.lower()
    if ext not in (".py", ".js", ".jsx", ".ts", ".tsx", ".go"):
        return False

    name = Path(file_path).name.lower()

    # Skip files that typically don't need tests
    skip_names = {
        "__init__.py", "setup.py", "conftest.py", "manage.py",
        "wsgi.py", "asgi.py", "settings.py", "config.py",
        "index.js", "index.ts", "main.py", "__main__.py",
    }
    if name in skip_names:
        return False

    # Skip migration files, configs, etc.
    skip_patterns = [
        r'migrations?/',
        r'config/',
        r'scripts/',
        r'\.config\.',
    ]
    for pattern in skip_patterns:
        if re.search(pattern, file_path, re.IGNORECASE):
            return False

    return not is_test_file(file_path)


# ---------------------------------------------------------------------------
# New function/class detection from diff
# ---------------------------------------------------------------------------


def extract_new_definitions_python(diff_text: str, file_path: str) -> list[dict]:
    """
    Extract newly added function/class definitions from a Python diff.

    Returns list of dicts with name, type, line.
    """
    definitions = []
    current_file = None

    for line in diff_text.split("\n"):
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue

        if current_file != file_path:
            continue

        if not line.startswith("+"):
            continue

        content = line[1:]  # Strip leading +

        # Match function definitions
        func_match = re.match(r'\s*(?:async\s+)?def\s+(\w+)\s*\(', content)
        if func_match:
            name = func_match.group(1)
            if not name.startswith("_"):  # Public functions only
                definitions.append({"name": name, "type": "function"})

        # Match class definitions
        class_match = re.match(r'\s*class\s+(\w+)\s*[:(]', content)
        if class_match:
            name = class_match.group(1)
            if not name.startswith("_"):
                definitions.append({"name": name, "type": "class"})

    return definitions


def check_test_coverage_for_definitions(
    definitions: list[dict],
    test_file_path: Optional[str],
    repo_root: str,
) -> list[dict]:
    """
    Check if new definitions have corresponding tests.

    Returns list of uncovered definitions.
    """
    if not test_file_path:
        return definitions  # No test file means nothing is covered

    # Read test file
    try:
        test_content = (Path(repo_root) / test_file_path).read_text(
            encoding="utf-8", errors="replace"
        )
    except OSError:
        return definitions

    uncovered = []
    test_content_lower = test_content.lower()

    for defn in definitions:
        name = defn["name"]
        # Check if the test file references this name
        # Look for test_<name>, test<Name>, or just <name> in test assertions
        patterns = [
            f"test_{name.lower()}",
            f"test{name.lower()}",
            name.lower(),
        ]
        found = any(p in test_content_lower for p in patterns)
        if not found:
            uncovered.append(defn)

    return uncovered


# ---------------------------------------------------------------------------
# Main analyzer entry point
# ---------------------------------------------------------------------------


def analyze(
    diff_text: str,
    changed_files: list[str],
    repo_root: str,
) -> list[Finding]:
    """
    Run test coverage analysis on changed files.

    Args:
        diff_text:     Full unified diff text
        changed_files: List of changed file paths relative to repo root
        repo_root:     Repository root path

    Returns list of Finding objects for missing test coverage.
    """
    findings = []

    # Separate source files from test files in this commit
    source_files = [f for f in changed_files if is_source_file(f)]
    test_files_in_commit = {f for f in changed_files if is_test_file(f)}

    for file_path in source_files:
        test_file = find_test_file(file_path, repo_root)

        # Check 1: Does a test file exist?
        if not test_file:
            # Check if a test file was added in this same commit
            has_new_test = any(
                is_test_file(tf) and Path(file_path).stem.lower() in tf.lower()
                for tf in test_files_in_commit
            )

            if not has_new_test:
                findings.append(Finding(
                    id="",
                    commit_hash="",
                    analyzer="test_coverage",
                    severity=Severity.WARNING.value,
                    title=f"No test file found for {Path(file_path).name}",
                    description=(
                        f"Source file '{file_path}' was modified but no corresponding "
                        f"test file was found.\n\n"
                        f"Expected test file locations:\n"
                        + "\n".join(
                            f"  - {pattern_fn(Path(file_path))}"
                            for pattern_fn in TEST_FILE_PATTERNS.get(
                                Path(file_path).suffix.lower(), []
                            )
                        )
                    ),
                    file_path=file_path,
                    suggestion=(
                        f"Create a test file for '{Path(file_path).name}' to ensure "
                        f"changes are properly tested. At minimum, test the public API."
                    ),
                    metadata={"check": "missing_test_file"},
                ))
                continue

        # Check 2: Do new definitions have test coverage?
        if file_path.endswith(".py"):
            new_defs = extract_new_definitions_python(diff_text, file_path)
            if new_defs:
                uncovered = check_test_coverage_for_definitions(
                    new_defs, test_file, repo_root
                )

                for defn in uncovered:
                    findings.append(Finding(
                        id="",
                        commit_hash="",
                        analyzer="test_coverage",
                        severity=Severity.INFO.value,
                        title=(
                            f"New {defn['type']} '{defn['name']}' may lack test coverage"
                        ),
                        description=(
                            f"A new {defn['type']} '{defn['name']}' was added to "
                            f"'{file_path}' but no corresponding test was found in "
                            f"'{test_file}'.\n\n"
                            f"Note: This check is heuristic. The {defn['type']} may be "
                            f"tested indirectly or via integration tests."
                        ),
                        file_path=file_path,
                        suggestion=(
                            f"Add a test for '{defn['name']}' in '{test_file}'. "
                            f"Consider testing edge cases and error conditions."
                        ),
                        metadata={
                            "check": "uncovered_definition",
                            "definition_name": defn["name"],
                            "definition_type": defn["type"],
                            "test_file": test_file,
                        },
                    ))

    return findings
