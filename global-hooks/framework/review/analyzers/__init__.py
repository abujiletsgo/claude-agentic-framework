"""
Review Analyzers
================

Pluggable analysis modules for the continuous review system.
Each analyzer implements a common interface:

    def analyze(diff_text: str, changed_files: list[str], repo_root: str) -> list[Finding]

Available analyzers:
- duplication   - Token-based similarity detection
- complexity    - Cyclomatic complexity (McCabe-style)
- dead_code     - AST analysis for unused definitions
- architecture  - Pattern matching for structural violations
- test_coverage - Verify test coverage for changed code
"""
