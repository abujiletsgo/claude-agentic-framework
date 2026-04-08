#!/bin/bash
# validate_name.sh - Input validation for worktree feature names
#
# Prevents command injection and path traversal by enforcing strict
# naming rules before any git or shell operations.
#
# Usage:
#   source scripts/validate_name.sh
#   validate_feature_name "my-feature" || exit 1
#
# Or standalone:
#   bash scripts/validate_name.sh "my-feature"

# Validate feature name for safety against command injection and path traversal.
# Returns 0 on valid input, 1 on invalid input with error message to stderr.
validate_feature_name() {
    local name="$1"

    # Reject empty input
    if [ -z "$name" ]; then
        echo "ERROR: Feature name is required" >&2
        return 1
    fi

    # Check allowed characters: alphanumeric, dots, underscores, hyphens only
    if ! [[ "$name" =~ ^[a-zA-Z0-9._-]+$ ]]; then
        echo "ERROR: Invalid feature name '$name'. Use only: a-z A-Z 0-9 . _ -" >&2
        echo "  Rejected characters: spaces, /, \\, \`, \$, ;, &, |, (, ), {, }, <, >, !, ?, *, ~, #, etc." >&2
        return 1
    fi

    # Block path traversal patterns
    if [[ "$name" == *".."* ]]; then
        echo "ERROR: Path traversal detected in feature name ('..'' is not allowed)" >&2
        return 1
    fi

    # Block hidden file/directory patterns (leading dot)
    if [[ "$name" == .* ]]; then
        echo "ERROR: Feature name must not start with a dot" >&2
        return 1
    fi

    # Block null bytes via printf check (bash truncates at null bytes in variables,
    # so the regex check above is the primary defense; this is a belt-and-suspenders check)
    local byte_len
    byte_len=$(printf '%s' "$name" | wc -c | tr -d ' ')
    if [ "$byte_len" -ne "${#name}" ]; then
        echo "ERROR: Null byte or encoding anomaly detected in feature name" >&2
        return 1
    fi

    # Length check: reasonable maximum to prevent filesystem issues
    if [ "${#name}" -gt 50 ]; then
        echo "ERROR: Feature name too long (${#name} chars, max 50)" >&2
        return 1
    fi

    # Length check: minimum length
    if [ "${#name}" -lt 2 ]; then
        echo "ERROR: Feature name too short (min 2 chars)" >&2
        return 1
    fi

    return 0
}

# Validate that a resolved worktree path stays within the expected parent directory.
# Prevents path traversal even if the name validation is somehow bypassed.
# Args: $1 = worktree directory path, $2 = expected parent directory
validate_worktree_path() {
    local worktree_dir="$1"
    local parent_dir="$2"

    # Resolve to absolute paths (without following symlinks for the target)
    local resolved_parent
    resolved_parent="$(cd "$parent_dir" 2>/dev/null && pwd -P)"

    if [ -z "$resolved_parent" ]; then
        echo "ERROR: Parent directory does not exist: $parent_dir" >&2
        return 1
    fi

    # Normalize the worktree path to resolve symlinks (e.g., /tmp -> /private/tmp on macOS)
    # The worktree directory may not exist yet, so resolve its parent and append the leaf.
    local normalized_worktree
    local wt_parent wt_leaf
    wt_parent="$(dirname "$worktree_dir")"
    wt_leaf="$(basename "$worktree_dir")"
    if [ -d "$wt_parent" ]; then
        normalized_worktree="$(cd "$wt_parent" && pwd -P)/$wt_leaf"
    else
        # Parent does not exist either; try GNU realpath -m if available
        normalized_worktree="$(realpath -m "$worktree_dir" 2>/dev/null)"
        if [ -z "$normalized_worktree" ]; then
            # Last resort: use the path as-is
            normalized_worktree="$worktree_dir"
        fi
    fi

    # Verify the worktree path starts with the parent path
    if [[ "$normalized_worktree" != "$resolved_parent/"* ]]; then
        echo "ERROR: Worktree path escapes parent directory" >&2
        echo "  Resolved worktree: $normalized_worktree" >&2
        echo "  Expected parent:   $resolved_parent" >&2
        return 1
    fi

    return 0
}

# Validate port offset is a safe numeric value.
# Args: $1 = port offset
validate_port_offset() {
    local offset="$1"

    # Must be a non-negative integer
    if ! [[ "$offset" =~ ^[0-9]+$ ]]; then
        echo "ERROR: Port offset must be a non-negative integer, got: '$offset'" >&2
        return 1
    fi

    # Reasonable range (0-99 gives ports up to 4990/6163)
    if [ "$offset" -gt 99 ]; then
        echo "ERROR: Port offset too large ($offset, max 99)" >&2
        return 1
    fi

    return 0
}

# If run directly (not sourced), validate the argument
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    if [ $# -eq 0 ]; then
        echo "Usage: $0 <feature-name> [port-offset]" >&2
        exit 1
    fi

    validate_feature_name "$1" || exit 1

    if [ -n "$2" ]; then
        validate_port_offset "$2" || exit 1
    fi

    echo "OK: '$1' is a valid feature name"
    exit 0
fi
