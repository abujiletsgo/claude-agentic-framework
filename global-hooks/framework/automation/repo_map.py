#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "tree-sitter>=0.23.0",
#   "tree-sitter-python>=0.23.0",
#   "tree-sitter-javascript>=0.23.0",
#   "tree-sitter-typescript>=0.23.0",
# ]
# ///
"""
RepoMap - TreeSitter Symbol Index for Large Repositories (SessionStart Hook)
=============================================================================

Automatically generates a ranked symbol index when a project has > 200 source
files. Runs at session start; exits silently if the project is small.

Behavior:
  - Counts .py, .js, .ts, .tsx, .rs, .go, .java files in cwd
  - If count < 200: exit 0 silently (zero overhead for small repos)
  - If count >= 200:
      - Check ~/.claude/REPO_MAP.md for valid cached version (git hash match)
      - If cache valid: inject cached map as additionalContext
      - If stale/missing: parse with tree-sitter, build + cache map, inject

Output:
  JSON with {"hookSpecificOutput": {"additionalContext": "<map content>"}}
  Written to stdout so Claude Code injects it into the session context.

Exit: Always 0 (never blocks)
"""

import ast
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SOURCE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".rs", ".go", ".java"}
THRESHOLD = 200
CACHE_PATH = Path.home() / ".claude" / "REPO_MAP.md"
MAX_FILES_PER_LANGUAGE = 150  # Cap to keep map useful, not overwhelming
MAX_SYMBOLS_PER_FILE = 20     # Cap symbols per file


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def count_source_files(root: Path) -> int:
    """Count source files without loading them. Fast."""
    count = 0
    skip_dirs = {
        ".git", "node_modules", "__pycache__", ".venv", "venv",
        "dist", "build", ".next", ".nuxt", "target", ".tox",
        "*.egg-info", ".mypy_cache", ".pytest_cache",
    }
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip directories in-place
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fname in filenames:
            if Path(fname).suffix in SOURCE_EXTENSIONS:
                count += 1
                if count > THRESHOLD + 1000:
                    return count  # Short-circuit
    return count


def collect_source_files(root: Path) -> dict[str, list[Path]]:
    """Collect source files grouped by extension."""
    skip_dirs = {
        ".git", "node_modules", "__pycache__", ".venv", "venv",
        "dist", "build", ".next", ".nuxt", "target", ".tox",
    }
    files_by_ext: dict[str, list[Path]] = defaultdict(list)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        dp = Path(dirpath)
        for fname in filenames:
            p = dp / fname
            if p.suffix in SOURCE_EXTENSIONS:
                files_by_ext[p.suffix].append(p)
    return dict(files_by_ext)


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def get_git_hash(root: Path) -> str:
    """Get current git commit hash, or a file-count fallback."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=root, timeout=3
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return f"no-git-{datetime.now(timezone.utc).strftime('%Y%m%d')}"


def read_cache_hash(cache_path: Path) -> str | None:
    """Read git hash from cache file header."""
    try:
        with open(cache_path) as f:
            first_line = f.readline().strip()
        m = re.match(r"<!-- GIT_HASH: ([a-f0-9]+) -->", first_line)
        return m.group(1) if m else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Python symbol extraction (ast fallback — always available)
# ---------------------------------------------------------------------------

def extract_python_ast(source: str) -> list[str]:
    """Extract class/function signatures using Python's built-in ast."""
    symbols = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return symbols

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append(f"`{node.name}` (class)")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Build param list (names only, no defaults/annotations for brevity)
            args = node.args
            params = [a.arg for a in args.args]
            if args.vararg:
                params.append(f"*{args.vararg.arg}")
            if args.kwarg:
                params.append(f"**{args.kwarg.arg}")
            parent = getattr(node, "_parent_class", None)
            if parent:
                symbols.append(f"`{parent}.{node.name}({', '.join(params)})`")
            else:
                symbols.append(f"`{node.name}({', '.join(params)})`")

    # Re-walk to attach parent class names to methods
    symbols = []
    class_stack = []

    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node):
            symbols.append(f"`{node.name}` (class)")
            class_stack.append(node.name)
            self.generic_visit(node)
            class_stack.pop()

        def visit_FunctionDef(self, node):
            args = node.args
            params = [a.arg for a in args.args]
            if args.vararg:
                params.append(f"*{args.vararg.arg}")
            if args.kwarg:
                params.append(f"**{args.kwarg.arg}")
            sig = f"{node.name}({', '.join(params)})"
            if class_stack:
                symbols.append(f"`{class_stack[-1]}.{sig}`")
            else:
                symbols.append(f"`{sig}`")
            self.generic_visit(node)

        visit_AsyncFunctionDef = visit_FunctionDef

    Visitor().visit(tree)
    return symbols[:MAX_SYMBOLS_PER_FILE]


# ---------------------------------------------------------------------------
# Tree-sitter extraction
# ---------------------------------------------------------------------------

def extract_with_treesitter(file_path: Path) -> list[str]:
    """Extract symbols using tree-sitter. Returns [] on any failure."""
    ext = file_path.suffix
    try:
        if ext == ".py":
            import tree_sitter_python as tspython
            from tree_sitter import Language, Parser
            PY_LANGUAGE = Language(tspython.language())
            parser = Parser(PY_LANGUAGE)
            source = file_path.read_bytes()
            tree = parser.parse(source)
            return _extract_python_ts(tree.root_node, source)

        elif ext in (".js", ".jsx"):
            import tree_sitter_javascript as tsjs
            from tree_sitter import Language, Parser
            JS_LANGUAGE = Language(tsjs.language())
            parser = Parser(JS_LANGUAGE)
            source = file_path.read_bytes()
            tree = parser.parse(source)
            return _extract_js_ts(tree.root_node, source)

        elif ext in (".ts", ".tsx"):
            import tree_sitter_typescript as tsts
            from tree_sitter import Language, Parser
            if ext == ".tsx":
                TS_LANGUAGE = Language(tsts.language_tsx())
            else:
                TS_LANGUAGE = Language(tsts.language_typescript())
            parser = Parser(TS_LANGUAGE)
            source = file_path.read_bytes()
            tree = parser.parse(source)
            return _extract_js_ts(tree.root_node, source)

    except Exception:
        pass

    # Fallback for Python
    if ext == ".py":
        try:
            return extract_python_ast(file_path.read_text(errors="replace"))
        except Exception:
            pass

    return []


def _node_text(node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _extract_python_ts(root, source: bytes) -> list[str]:
    """Extract Python symbols from tree-sitter parse tree."""
    symbols = []
    class_stack = []

    def walk(node):
        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = _node_text(name_node, source)
                symbols.append(f"`{name}` (class)")
                class_stack.append(name)
                for child in node.children:
                    walk(child)
                class_stack.pop()
                return

        elif node.type in ("function_definition", "decorated_definition"):
            fn_node = node if node.type == "function_definition" else None
            if node.type == "decorated_definition":
                for child in node.children:
                    if child.type == "function_definition":
                        fn_node = child
                        break
            if fn_node:
                name_node = fn_node.child_by_field_name("name")
                params_node = fn_node.child_by_field_name("parameters")
                if name_node:
                    name = _node_text(name_node, source)
                    params = _node_text(params_node, source) if params_node else "()"
                    # Strip type annotations for brevity
                    params = re.sub(r":\s*[^,)]+", "", params)
                    params = re.sub(r"\s*=\s*[^,)]+", "", params)
                    if class_stack:
                        symbols.append(f"`{class_stack[-1]}.{name}{params}`")
                    else:
                        symbols.append(f"`{name}{params}`")

        for child in node.children:
            walk(child)

    walk(root)
    return symbols[:MAX_SYMBOLS_PER_FILE]


def _extract_js_ts(root, source: bytes) -> list[str]:
    """Extract JS/TS symbols from tree-sitter parse tree."""
    symbols = []

    def walk(node):
        # Class declarations
        if node.type in ("class_declaration", "class"):
            name_node = node.child_by_field_name("name")
            if name_node:
                name = _node_text(name_node, source)
                symbols.append(f"`{name}` (class)")

        # Function declarations
        elif node.type in ("function_declaration", "function"):
            name_node = node.child_by_field_name("name")
            params_node = node.child_by_field_name("parameters")
            if name_node:
                name = _node_text(name_node, source)
                params = _node_text(params_node, source) if params_node else "()"
                symbols.append(f"`{name}{params}`")

        # Arrow function / variable assigned function
        elif node.type in ("lexical_declaration", "variable_declaration"):
            for child in node.children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    value_node = child.child_by_field_name("value")
                    if name_node and value_node and value_node.type in (
                        "arrow_function", "function"
                    ):
                        name = _node_text(name_node, source)
                        params_node = value_node.child_by_field_name("parameters")
                        params = _node_text(params_node, source) if params_node else "()"
                        symbols.append(f"`{name}{params}`")

        # Method definitions
        elif node.type == "method_definition":
            name_node = node.child_by_field_name("name")
            params_node = node.child_by_field_name("parameters")
            if name_node:
                name = _node_text(name_node, source)
                params = _node_text(params_node, source) if params_node else "()"
                symbols.append(f"`{name}{params}`")

        # TypeScript interface/type declarations
        elif node.type in ("interface_declaration", "type_alias_declaration"):
            name_node = node.child_by_field_name("name")
            if name_node:
                name = _node_text(name_node, source)
                kind = "interface" if node.type == "interface_declaration" else "type"
                symbols.append(f"`{name}` ({kind})")

        for child in node.children:
            walk(child)

    walk(root)
    return symbols[:MAX_SYMBOLS_PER_FILE]


# ---------------------------------------------------------------------------
# PageRank-lite: frequency-based symbol ranking
# ---------------------------------------------------------------------------

def build_reference_index(all_symbols: dict[str, list[str]], all_sources: dict[str, str]) -> dict[str, int]:
    """
    Count how many times each symbol name appears across the entire codebase.
    Simple frequency count (not full PageRank) — fast and good enough.
    """
    ref_counts: dict[str, int] = defaultdict(int)

    # Extract bare symbol names
    def bare_name(sym: str) -> str:
        """Extract the identifier name from a symbol string."""
        # Patterns: `ClassName` (class), `func(params)`, `Class.method(params)`
        m = re.match(r"`([^`(]+)", sym)
        if m:
            name = m.group(1)
            # For methods, use just the method name
            return name.split(".")[-1]
        return sym

    symbol_names = {}
    for path, syms in all_symbols.items():
        for sym in syms:
            name = bare_name(sym)
            symbol_names[name] = symbol_names.get(name, 0)  # register

    # Count references across all source files
    combined = "\n".join(all_sources.values())
    for name in symbol_names:
        if len(name) < 3:
            continue  # Skip trivial names
        # Word-boundary match
        pattern = rf"\b{re.escape(name)}\b"
        try:
            ref_counts[name] = len(re.findall(pattern, combined))
        except Exception:
            ref_counts[name] = 0

    return ref_counts


def rank_symbols(symbols: list[str], ref_counts: dict[str, int]) -> list[str]:
    """Sort symbols by reference count, add star rating."""
    def score(sym: str) -> int:
        m = re.match(r"`([^`(]+)", sym)
        if m:
            name = m.group(1).split(".")[-1]
            return ref_counts.get(name, 0)
        return 0

    ranked = sorted(symbols, key=score, reverse=True)

    # Add star suffix for high-frequency symbols
    result = []
    for sym in ranked:
        s = score(sym)
        if s >= 20:
            result.append(f"{sym} ★★★")
        elif s >= 10:
            result.append(f"{sym} ★★")
        elif s >= 5:
            result.append(f"{sym} ★")
        else:
            result.append(sym)
    return result


# ---------------------------------------------------------------------------
# Map generation
# ---------------------------------------------------------------------------

def generate_repo_map(root: Path, file_count: int) -> str:
    """Parse source files and generate a ranked symbol map."""
    files_by_ext = collect_source_files(root)

    # Prioritize Python, then TS/TSX, then JS — cap per language
    priority_order = [".py", ".ts", ".tsx", ".js", ".go", ".rs", ".java"]
    selected_files: list[Path] = []
    for ext in priority_order:
        files = files_by_ext.get(ext, [])
        # Sort by path depth (shallower = more important) then alphabetically
        files.sort(key=lambda p: (len(p.parts), str(p)))
        selected_files.extend(files[:MAX_FILES_PER_LANGUAGE])

    # Extract symbols from each file
    all_symbols: dict[str, list[str]] = {}
    all_sources: dict[str, str] = {}

    for fpath in selected_files:
        try:
            source = fpath.read_text(errors="replace")
            all_sources[str(fpath)] = source
        except Exception:
            continue
        syms = extract_with_treesitter(fpath)
        if syms:
            rel = str(fpath.relative_to(root))
            all_symbols[rel] = syms

    if not all_symbols:
        return f"## Repository Symbol Map ({file_count} source files)\n\n*No symbols extracted.*\n"

    # Build reference index for ranking
    ref_counts = build_reference_index(all_symbols, all_sources)

    # Generate the map
    lines = [f"## Repository Symbol Map ({file_count} source files)\n"]
    for rel_path, syms in sorted(all_symbols.items()):
        ranked = rank_symbols(syms, ref_counts)
        lines.append(f"\n### {rel_path}")
        for sym in ranked[:15]:  # Max 15 per file in output
            lines.append(f"- {sym}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

def write_cache(cache_path: Path, git_hash: str, file_count: int, map_content: str) -> None:
    """Write the repo map to cache with metadata header."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = (
        f"<!-- GIT_HASH: {git_hash} -->\n"
        f"<!-- FILES: {file_count} -->\n"
        f"<!-- GENERATED: {now} -->\n\n"
    )
    cache_path.write_text(header + map_content)


def read_cache_content(cache_path: Path) -> str:
    """Read map content from cache (strips header lines)."""
    text = cache_path.read_text()
    lines = text.splitlines(keepends=True)
    # Skip the 4 header lines (3 HTML comments + 1 blank)
    return "".join(lines[4:])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _log(msg):
    try:
        import datetime
        with open("/tmp/claude_startup_debug.log", "a") as f:
            f.write(f"{datetime.datetime.now().isoformat()} [repomap] {msg}\n")
    except Exception:
        pass


def main() -> None:
    _log("main() started")
    try:
        root = Path.cwd()
        file_count = count_source_files(root)

        if file_count < THRESHOLD:
            # Small repo — silent exit, no overhead
            sys.exit(0)

        git_hash = get_git_hash(root)

        # Check cache validity
        map_content: str | None = None
        if CACHE_PATH.exists():
            cached_hash = read_cache_hash(CACHE_PATH)
            if cached_hash and cached_hash == git_hash:
                map_content = read_cache_content(CACHE_PATH)

        # Cache miss — regenerate
        if map_content is None:
            map_content = generate_repo_map(root, file_count)
            write_cache(CACHE_PATH, git_hash, file_count, map_content)

        # Output hook context injection
        output = {
            "hookSpecificOutput": {
                "additionalContext": (
                    f"[RepoMap] Large repository detected ({file_count} source files). "
                    f"Ranked symbol index (top symbols by reference frequency):\n\n"
                    f"{map_content}"
                )
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    except Exception:
        # Never block the session
        sys.exit(0)


if __name__ == "__main__":
    main()
