#!/usr/bin/env python3
"""
Duplication Analyzer
====================

Detects copy-paste code within the changed files of a commit.
Uses token-based similarity detection with a sliding window approach.

Algorithm:
1. Tokenize added lines from the diff
2. Build N-gram fingerprints (configurable token window)
3. Compare fingerprints across all changed files
4. Report blocks with similarity above threshold
"""

import hashlib
import re
from dataclasses import dataclass
from typing import Optional

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from findings_store import Finding, Severity


@dataclass
class CodeBlock:
    """A block of code from a specific file."""
    file_path: str
    start_line: int
    end_line: int
    content: str
    tokens: list[str]


def tokenize(code: str) -> list[str]:
    """
    Tokenize code into meaningful tokens.

    Strips comments and whitespace, splits on boundaries.
    Produces normalized tokens for comparison.
    """
    # Remove single-line comments (Python, JS, Java, etc.)
    code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)

    # Remove multi-line comments
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
    code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)

    # Tokenize: split on word boundaries, operators, punctuation
    tokens = re.findall(r'[a-zA-Z_]\w*|[0-9]+(?:\.[0-9]+)?|[^\s\w]', code)

    # Normalize: lowercase identifiers
    return [t.lower() for t in tokens if t.strip()]


def compute_fingerprints(tokens: list[str], window_size: int = 50) -> dict[str, int]:
    """
    Compute fingerprints for token windows.

    Returns dict mapping fingerprint hash -> start token index.
    """
    fingerprints = {}
    if len(tokens) < window_size:
        return fingerprints

    for i in range(len(tokens) - window_size + 1):
        window = tokens[i:i + window_size]
        fp = hashlib.md5(" ".join(window).encode()).hexdigest()
        if fp not in fingerprints:
            fingerprints[fp] = i

    return fingerprints


def extract_added_blocks(diff_text: str) -> list[CodeBlock]:
    """
    Extract added code blocks from a unified diff.

    Parses diff hunks to identify contiguous blocks of added lines,
    tracking their file paths and line numbers.
    """
    blocks = []
    current_file = None
    current_lines: list[str] = []
    current_start = 0
    line_num = 0

    for line in diff_text.split("\n"):
        # New file in diff
        if line.startswith("+++ b/"):
            # Flush previous block
            if current_file and current_lines:
                content = "\n".join(current_lines)
                tokens = tokenize(content)
                if len(tokens) >= 10:  # Only blocks with meaningful content
                    blocks.append(CodeBlock(
                        file_path=current_file,
                        start_line=current_start,
                        end_line=current_start + len(current_lines) - 1,
                        content=content,
                        tokens=tokens,
                    ))
            current_file = line[6:]  # Strip "+++ b/"
            current_lines = []
            current_start = 0
            continue

        # Hunk header
        if line.startswith("@@"):
            # Flush previous block
            if current_file and current_lines:
                content = "\n".join(current_lines)
                tokens = tokenize(content)
                if len(tokens) >= 10:
                    blocks.append(CodeBlock(
                        file_path=current_file,
                        start_line=current_start,
                        end_line=current_start + len(current_lines) - 1,
                        content=content,
                        tokens=tokens,
                    ))
                current_lines = []

            # Parse new file line number from @@ -a,b +c,d @@
            match = re.search(r'\+(\d+)', line)
            if match:
                line_num = int(match.group(1))
                current_start = line_num
            continue

        # Added line
        if line.startswith("+") and not line.startswith("+++"):
            if not current_lines:
                current_start = line_num
            current_lines.append(line[1:])  # Strip leading +
            line_num += 1
            continue

        # Context or removed line
        if not line.startswith("-"):
            # Flush block on context lines (gap in additions)
            if current_file and current_lines:
                content = "\n".join(current_lines)
                tokens = tokenize(content)
                if len(tokens) >= 10:
                    blocks.append(CodeBlock(
                        file_path=current_file,
                        start_line=current_start,
                        end_line=current_start + len(current_lines) - 1,
                        content=content,
                        tokens=tokens,
                    ))
                current_lines = []
            line_num += 1

    # Flush final block
    if current_file and current_lines:
        content = "\n".join(current_lines)
        tokens = tokenize(content)
        if len(tokens) >= 10:
            blocks.append(CodeBlock(
                file_path=current_file,
                start_line=current_start,
                end_line=current_start + len(current_lines) - 1,
                content=content,
                tokens=tokens,
            ))

    return blocks


def find_duplicates(
    blocks: list[CodeBlock],
    min_tokens: int = 50,
    similarity_threshold: float = 0.6,
) -> list[tuple[CodeBlock, CodeBlock, float]]:
    """
    Find duplicate code blocks using fingerprint comparison.

    Returns list of (block_a, block_b, similarity_ratio) tuples.
    """
    duplicates = []

    for i in range(len(blocks)):
        for j in range(i + 1, len(blocks)):
            a = blocks[i]
            b = blocks[j]

            # Skip if either block is too small
            if len(a.tokens) < min_tokens or len(b.tokens) < min_tokens:
                continue

            # Compute fingerprints
            fp_a = compute_fingerprints(a.tokens, min(min_tokens, len(a.tokens)))
            fp_b = compute_fingerprints(b.tokens, min(min_tokens, len(b.tokens)))

            if not fp_a or not fp_b:
                continue

            # Calculate similarity as Jaccard index of fingerprint sets
            set_a = set(fp_a.keys())
            set_b = set(fp_b.keys())
            intersection = set_a & set_b
            union = set_a | set_b

            if union:
                similarity = len(intersection) / len(union)
                if similarity >= similarity_threshold:
                    duplicates.append((a, b, similarity))

    return duplicates


def analyze(
    diff_text: str,
    changed_files: list[str],
    repo_root: str,
    min_tokens: int = 50,
    similarity_threshold: float = 0.6,
) -> list[Finding]:
    """
    Run duplication analysis on a commit diff.

    Args:
        diff_text:            Full unified diff text
        changed_files:        List of changed file paths
        repo_root:            Repository root path
        min_tokens:           Minimum token count for duplication check
        similarity_threshold: Similarity ratio threshold (0.0-1.0)

    Returns list of Finding objects for detected duplications.
    """
    blocks = extract_added_blocks(diff_text)

    if len(blocks) < 2:
        return []  # Need at least 2 blocks to compare

    duplicates = find_duplicates(blocks, min_tokens, similarity_threshold)

    findings = []
    for idx, (block_a, block_b, similarity) in enumerate(duplicates):
        pct = int(similarity * 100)

        # Determine severity based on similarity
        if similarity >= 0.9:
            severity = Severity.ERROR.value
        elif similarity >= 0.7:
            severity = Severity.WARNING.value
        else:
            severity = Severity.INFO.value

        finding = Finding(
            id="",  # Will be set by review engine
            commit_hash="",  # Will be set by review engine
            analyzer="duplication",
            severity=severity,
            title=f"Code duplication detected ({pct}% similar)",
            description=(
                f"Similar code blocks found:\n"
                f"  Block A: {block_a.file_path} lines {block_a.start_line}-{block_a.end_line} "
                f"({len(block_a.tokens)} tokens)\n"
                f"  Block B: {block_b.file_path} lines {block_b.start_line}-{block_b.end_line} "
                f"({len(block_b.tokens)} tokens)\n"
                f"  Similarity: {pct}%"
            ),
            file_path=block_a.file_path,
            line_start=block_a.start_line,
            line_end=block_a.end_line,
            suggestion=(
                "Consider extracting the duplicated logic into a shared "
                "function or module to reduce maintenance burden."
            ),
            metadata={
                "other_file": block_b.file_path,
                "other_line_start": block_b.start_line,
                "other_line_end": block_b.end_line,
                "similarity_pct": pct,
                "tokens_a": len(block_a.tokens),
                "tokens_b": len(block_b.tokens),
            },
        )
        findings.append(finding)

    return findings
