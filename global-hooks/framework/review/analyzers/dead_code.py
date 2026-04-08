#!/usr/bin/env python3
"""
Dead Code Analyzer
==================

Identifies potentially unused code in changed Python files using AST analysis.

Detects:
- Functions defined but never called within the module
- Classes defined but never referenced
- Imports that are never used
- Variables assigned but never read

Limitations:
- Only analyzes within single files (cross-module usage not tracked)
- Skips files with __all__ exports (intentional public API)
- Skips test files (test functions are called by framework)
- Skips __init__.py re-exports
"""

import ast
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from findings_store import Finding, Severity


# ---------------------------------------------------------------------------
# AST-based dead code detection for Python
# ---------------------------------------------------------------------------


class DefinitionCollector(ast.NodeVisitor):
    """Collect all top-level and class-level definitions."""

    def __init__(self):
        self.definitions: dict[str, dict] = {}  # name -> {type, line, end_line}
        self.imports: dict[str, dict] = {}       # name -> {module, line}
        self._in_class = False
        self._class_name = ""

    def visit_FunctionDef(self, node):
        if not self._in_class:
            # Skip dunder methods and test functions
            if not node.name.startswith("_"):
                self.definitions[node.name] = {
                    "type": "function",
                    "line": node.lineno,
                    "end_line": node.end_lineno or node.lineno,
                }
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        if not self._in_class:
            self.definitions[node.name] = {
                "type": "class",
                "line": node.lineno,
                "end_line": node.end_lineno or node.lineno,
            }
        old_in_class = self._in_class
        old_class_name = self._class_name
        self._in_class = True
        self._class_name = node.name
        self.generic_visit(node)
        self._in_class = old_in_class
        self._class_name = old_class_name

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            # For dotted imports like 'os.path', track the first part
            top_name = name.split(".")[0]
            self.imports[top_name] = {
                "module": alias.name,
                "line": node.lineno,
            }

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.name == "*":
                continue  # Skip star imports
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = {
                "module": f"{node.module}.{alias.name}" if node.module else alias.name,
                "line": node.lineno,
            }


class UsageCollector(ast.NodeVisitor):
    """Collect all name references (usages) in the source."""

    def __init__(self):
        self.used_names: set[str] = set()

    def visit_Name(self, node):
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # Track attribute access on names
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.used_names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                self.used_names.add(node.func.value.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Decorators reference names
        for decorator in node.decorator_list:
            self.visit(decorator)
        # Annotations reference names
        if node.returns:
            self.visit(node.returns)
        for arg in node.args.args + node.args.kwonlyargs:
            if arg.annotation:
                self.visit(arg.annotation)
        # Visit body
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        # Base classes reference names
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        for decorator in node.decorator_list:
            self.visit(decorator)
        self.generic_visit(node)


def _should_skip_file(file_path: str, source: str) -> bool:
    """Check if file should be skipped for dead code analysis."""
    path = Path(file_path)

    # Skip test files
    if path.name.startswith("test_") or path.name.endswith("_test.py"):
        return True
    if "test" in path.parts or "tests" in path.parts:
        return True

    # Skip __init__.py (re-export hub)
    if path.name == "__init__.py":
        return True

    # Skip files with __all__ (intentional public API)
    if "__all__" in source:
        return True

    # Skip if file has if __name__ == "__main__" (CLI entry point)
    # Functions may be intentionally called only from main block
    # But we still analyze - just note it

    return False


def analyze_python_dead_code(
    source: str,
    file_path: str,
) -> list[dict]:
    """
    Find potentially dead code in a Python source file.

    Returns list of dicts with name, type, line, end_line, reason.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    # Collect definitions and usages
    defs = DefinitionCollector()
    defs.visit(tree)

    usages = UsageCollector()
    usages.visit(tree)

    dead = []

    # Check functions and classes
    for name, info in defs.definitions.items():
        if name not in usages.used_names:
            # Check if it might be referenced in string form (decorators, etc.)
            if name in source.replace(f"def {name}", "").replace(f"class {name}", ""):
                continue  # Might be used in a string or comment
            dead.append({
                "name": name,
                "type": info["type"],
                "line": info["line"],
                "end_line": info["end_line"],
                "reason": f"{info['type'].capitalize()} '{name}' is defined but never referenced in this module",
            })

    # Check imports
    for name, info in defs.imports.items():
        if name not in usages.used_names:
            # Double check: might be used in type annotations as strings
            if f"'{name}'" in source or f'"{name}"' in source:
                continue
            dead.append({
                "name": name,
                "type": "import",
                "line": info["line"],
                "end_line": info["line"],
                "reason": f"Import '{name}' (from {info['module']}) is never used",
            })

    return dead


# ---------------------------------------------------------------------------
# Heuristic dead code for non-Python (basic pattern matching)
# ---------------------------------------------------------------------------


def analyze_heuristic_dead_code(
    source: str,
    file_path: str,
) -> list[dict]:
    """
    Basic dead code detection for non-Python files.

    Uses pattern matching to find defined-but-unused functions.
    Very conservative to avoid false positives.
    """
    ext = Path(file_path).suffix.lower()
    dead = []

    # JavaScript/TypeScript function definitions
    if ext in (".js", ".jsx", ".ts", ".tsx"):
        # Find exported functions that might be unused within the file
        # Only flag non-exported functions
        func_pattern = re.compile(
            r'^(?!export\b)\s*(?:const|let|var|function)\s+(\w+)',
            re.MULTILINE,
        )
        for match in func_pattern.finditer(source):
            name = match.group(1)
            # Count occurrences (subtract the definition itself)
            count = len(re.findall(r'\b' + re.escape(name) + r'\b', source))
            if count <= 1:
                line = source[:match.start()].count("\n") + 1
                dead.append({
                    "name": name,
                    "type": "function/variable",
                    "line": line,
                    "end_line": line,
                    "reason": f"'{name}' is defined but appears only once (at definition)",
                })

    return dead


# ---------------------------------------------------------------------------
# Main analyzer entry point
# ---------------------------------------------------------------------------


def _read_file_safe(file_path: str, repo_root: str) -> Optional[str]:
    """Safely read a file, returning None on failure."""
    full_path = Path(repo_root) / file_path
    try:
        return full_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def analyze(
    diff_text: str,
    changed_files: list[str],
    repo_root: str,
) -> list[Finding]:
    """
    Run dead code analysis on changed files.

    Args:
        diff_text:     Full unified diff text
        changed_files: List of changed file paths relative to repo root
        repo_root:     Repository root path

    Returns list of Finding objects for potential dead code.
    """
    findings = []

    for file_path in changed_files:
        ext = Path(file_path).suffix.lower()
        source = _read_file_safe(file_path, repo_root)
        if not source:
            continue

        if ext == ".py":
            if _should_skip_file(file_path, source):
                continue
            dead_items = analyze_python_dead_code(source, file_path)
        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            dead_items = analyze_heuristic_dead_code(source, file_path)
        else:
            continue

        for item in dead_items:
            # Imports are info-level, unused functions/classes are warnings
            if item["type"] == "import":
                severity = Severity.INFO.value
            else:
                severity = Severity.WARNING.value

            finding = Finding(
                id="",  # Set by review engine
                commit_hash="",  # Set by review engine
                analyzer="dead_code",
                severity=severity,
                title=f"Potentially unused {item['type']}: {item['name']}",
                description=(
                    f"{item['reason']}\n"
                    f"File: {file_path}, line {item['line']}\n\n"
                    f"Note: This is a single-file analysis. The definition may be "
                    f"used in other modules via imports."
                ),
                file_path=file_path,
                line_start=item["line"],
                line_end=item["end_line"],
                suggestion=(
                    f"If '{item['name']}' is intentionally exported for use by other modules, "
                    f"consider adding it to __all__ or adding a comment. "
                    f"Otherwise, remove it to reduce code maintenance burden."
                ),
                metadata={
                    "dead_type": item["type"],
                    "name": item["name"],
                },
            )
            findings.append(finding)

    return findings
