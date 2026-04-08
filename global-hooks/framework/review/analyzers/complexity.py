#!/usr/bin/env python3
"""
Complexity Analyzer
===================

Detects overly complex functions in changed files using
McCabe-style cyclomatic complexity analysis via Python AST.

For non-Python files, uses a heuristic branch-counting approach
based on control flow keywords.

Complexity = (number of decision points) + 1
Decision points: if, elif, for, while, except, and, or, case, ?:
"""

import ast
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from findings_store import Finding, Severity


# ---------------------------------------------------------------------------
# Python AST-based complexity
# ---------------------------------------------------------------------------


class ComplexityVisitor(ast.NodeVisitor):
    """AST visitor that computes McCabe cyclomatic complexity per function."""

    def __init__(self):
        self.functions: list[dict] = []
        self._current_complexity = 0
        self._current_name = ""
        self._current_start = 0
        self._current_end = 0

    def _visit_function(self, node):
        """Visit a function/method definition."""
        # Save outer state
        outer_complexity = self._current_complexity
        outer_name = self._current_name
        outer_start = self._current_start
        outer_end = self._current_end

        self._current_complexity = 1  # Base complexity
        self._current_name = node.name
        self._current_start = node.lineno
        self._current_end = node.end_lineno or node.lineno

        # Visit body
        self.generic_visit(node)

        # Record function
        self.functions.append({
            "name": self._current_name,
            "complexity": self._current_complexity,
            "line_start": self._current_start,
            "line_end": self._current_end,
        })

        # Restore outer state
        self._current_complexity = outer_complexity
        self._current_name = outer_name
        self._current_start = outer_start
        self._current_end = outer_end

    def visit_FunctionDef(self, node):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._visit_function(node)

    # Decision points that increase complexity
    def visit_If(self, node):
        self._current_complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self._current_complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self._current_complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self._current_complexity += 1
        self.generic_visit(node)

    def visit_With(self, node):
        self._current_complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        # Each 'and' / 'or' adds a decision point
        self._current_complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_IfExp(self, node):
        # Ternary expression: x if cond else y
        self._current_complexity += 1
        self.generic_visit(node)

    def visit_comprehension(self, node):
        # List/dict/set comprehensions with conditions
        self._current_complexity += len(node.ifs)
        self.generic_visit(node)

    def visit_Match(self, node):
        # Python 3.10+ match/case
        self._current_complexity += len(node.cases)
        self.generic_visit(node)


def analyze_python_complexity(source: str) -> list[dict]:
    """
    Analyze Python source code for function complexity.

    Returns list of dicts with name, complexity, line_start, line_end.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    visitor = ComplexityVisitor()
    visitor.visit(tree)
    return visitor.functions


# ---------------------------------------------------------------------------
# Heuristic complexity for non-Python files
# ---------------------------------------------------------------------------

# Control flow keywords by language family
CONTROL_FLOW_PATTERNS = {
    # C-family: JS, TS, Java, C, C++, Go, Rust
    "c_family": re.compile(
        r'\b(?:if|else\s+if|elif|for|while|catch|case|&&|\|\||switch)\b'
        r'|(?<!\w)\?(?=.*:)',  # ternary operator
        re.MULTILINE,
    ),
    # Ruby
    "ruby": re.compile(
        r'\b(?:if|elsif|unless|for|while|until|when|rescue)\b',
        re.MULTILINE,
    ),
    # Shell
    "shell": re.compile(
        r'\b(?:if|elif|for|while|until|case)\b',
        re.MULTILINE,
    ),
}

# File extension to language family mapping
EXT_TO_FAMILY = {
    ".js": "c_family", ".jsx": "c_family", ".ts": "c_family", ".tsx": "c_family",
    ".java": "c_family", ".c": "c_family", ".cpp": "c_family", ".h": "c_family",
    ".go": "c_family", ".rs": "c_family", ".cs": "c_family", ".swift": "c_family",
    ".kt": "c_family", ".scala": "c_family",
    ".rb": "ruby",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell",
}

# Function definition patterns by language family
FUNCTION_PATTERNS = {
    "c_family": re.compile(
        r'(?:(?:public|private|protected|static|async|export|default)\s+)*'
        r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>|'
        r'(\w+)\s*\([^)]*\)\s*\{)',
        re.MULTILINE,
    ),
    "ruby": re.compile(r'def\s+(\w+)', re.MULTILINE),
    "shell": re.compile(r'(?:function\s+)?(\w+)\s*\(\)', re.MULTILINE),
}


def analyze_heuristic_complexity(
    source: str,
    file_ext: str,
) -> list[dict]:
    """
    Heuristic complexity analysis for non-Python files.

    Splits source into function-like blocks and counts control flow keywords.
    Returns list of dicts with name, complexity, line_start, line_end.
    """
    family = EXT_TO_FAMILY.get(file_ext)
    if not family:
        return []

    pattern = CONTROL_FLOW_PATTERNS.get(family)
    func_pattern = FUNCTION_PATTERNS.get(family)
    if not pattern or not func_pattern:
        return []

    lines = source.split("\n")
    results = []

    # Find function boundaries (simplified: look for function starts)
    func_starts = []
    for match in func_pattern.finditer(source):
        name = next((g for g in match.groups() if g), "anonymous")
        line_num = source[:match.start()].count("\n") + 1
        func_starts.append((name, line_num, match.start()))

    if not func_starts:
        # Treat entire file as one block
        complexity = len(pattern.findall(source)) + 1
        if complexity > 1:
            results.append({
                "name": "<module>",
                "complexity": complexity,
                "line_start": 1,
                "line_end": len(lines),
            })
        return results

    # Analyze each function region
    for i, (name, start_line, start_pos) in enumerate(func_starts):
        if i + 1 < len(func_starts):
            end_pos = func_starts[i + 1][2]
            end_line = func_starts[i + 1][1] - 1
        else:
            end_pos = len(source)
            end_line = len(lines)

        func_source = source[start_pos:end_pos]
        complexity = len(pattern.findall(func_source)) + 1

        results.append({
            "name": name,
            "complexity": complexity,
            "line_start": start_line,
            "line_end": end_line,
        })

    return results


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
    complexity_threshold: int = 10,
) -> list[Finding]:
    """
    Run complexity analysis on changed files.

    Args:
        diff_text:            Full unified diff text (unused, we read files directly)
        changed_files:        List of changed file paths relative to repo root
        repo_root:            Repository root path
        complexity_threshold: Complexity score above which to report

    Returns list of Finding objects for overly complex functions.
    """
    findings = []

    for file_path in changed_files:
        ext = Path(file_path).suffix.lower()
        source = _read_file_safe(file_path, repo_root)
        if not source:
            continue

        # Choose analysis method
        if ext == ".py":
            functions = analyze_python_complexity(source)
        else:
            functions = analyze_heuristic_complexity(source, ext)

        for func in functions:
            if func["complexity"] > complexity_threshold:
                # Determine severity
                ratio = func["complexity"] / complexity_threshold
                if ratio >= 3.0:
                    severity = Severity.CRITICAL.value
                elif ratio >= 2.0:
                    severity = Severity.ERROR.value
                elif ratio >= 1.5:
                    severity = Severity.WARNING.value
                else:
                    severity = Severity.INFO.value

                finding = Finding(
                    id="",  # Set by review engine
                    commit_hash="",  # Set by review engine
                    analyzer="complexity",
                    severity=severity,
                    title=(
                        f"High complexity in {func['name']}() "
                        f"(score: {func['complexity']}, threshold: {complexity_threshold})"
                    ),
                    description=(
                        f"Function '{func['name']}' in {file_path} has cyclomatic complexity "
                        f"of {func['complexity']}, exceeding the threshold of {complexity_threshold}.\n"
                        f"Lines: {func['line_start']}-{func['line_end']}\n\n"
                        f"High complexity makes code harder to understand, test, and maintain. "
                        f"Consider breaking this function into smaller, focused functions."
                    ),
                    file_path=file_path,
                    line_start=func["line_start"],
                    line_end=func["line_end"],
                    suggestion=(
                        f"Refactor '{func['name']}' to reduce complexity:\n"
                        f"- Extract helper functions for distinct logical blocks\n"
                        f"- Use early returns to reduce nesting\n"
                        f"- Consider the Strategy pattern for complex branching\n"
                        f"- Replace nested conditionals with guard clauses"
                    ),
                    metadata={
                        "function_name": func["name"],
                        "complexity_score": func["complexity"],
                        "threshold": complexity_threshold,
                    },
                )
                findings.append(finding)

    return findings
