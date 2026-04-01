"""
CAF Mode - Framework weight control.

Usage in any hook:
    from caf_mode import should_run

    if not should_run("caddy"):
        sys.exit(0)

Modes (set via ~/.claude/caf_mode or CAF_MODE env var):
    light  - Only essential hooks: damage-control, memory (auto_memory_writer,
             validate_facts, auto_fact_extractor). No Caddy, no RepoMap, no
             escalation, no dependency audit, no session locks.
    full   - Everything except RepoMap auto-injection. (DEFAULT)
    max    - All hooks enabled including RepoMap injection.

Hook categories:
    essential   - damage-control, pre_compact_preserve, post_compact_verify
    memory      - auto_memory_writer, validate_facts, auto_fact_extractor
    caddy       - analyze_request, auto_delegate
    monitoring  - auto_escalate, auto_dependency_audit, context-bundle-logger
    session     - session_lock_manager
    startup     - repo_map, auto_prime
    review      - auto_refine, auto_team_review, auto_review_team
    quality     - task_quality_gate, check_lthread_progress
"""

import os
from pathlib import Path

# Which hook categories run in which mode
MODE_HOOKS = {
    "light": {"essential", "memory"},
    "full":  {"essential", "memory", "caddy", "monitoring", "review", "quality", "session", "startup"},
    "max":   {"essential", "memory", "caddy", "monitoring", "review", "quality", "session", "startup", "repomap"},
}

# Map hook script names to categories
HOOK_CATEGORIES = {
    # essential (always on)
    "unified-damage-control": "essential",
    "pre_compact_preserve": "essential",
    "post_compact_verify": "essential",
    "circuit_breaker_wrapper": "essential",
    # memory
    "auto_memory_writer": "memory",
    "validate_facts": "memory",
    "auto_fact_extractor": "memory",
    # caddy
    "analyze_request": "caddy",
    "auto_delegate": "caddy",
    # monitoring
    "auto_escalate": "monitoring",
    "auto_dependency_audit": "monitoring",
    "context-bundle-logger": "monitoring",
    "auto_context_manager": "monitoring",
    "auto_error_analyzer": "monitoring",
    # session
    "session_lock_manager": "session",
    # startup
    "auto_prime": "startup",
    "session_startup": "startup",
    # review
    "auto_refine": "review",
    "auto_team_review": "review",
    "auto_review_team": "review",
    # quality
    "task_quality_gate": "quality",
    "check_lthread_progress": "quality",
    # repomap (only in max mode)
    "repo_map": "repomap",
}


def get_mode() -> str:
    """Get current CAF mode. Checks env var first, then flag file."""
    mode = os.environ.get("CAF_MODE", "").lower().strip()
    if mode in MODE_HOOKS:
        return mode

    flag_path = Path.home() / ".claude" / "caf_mode"
    if flag_path.exists():
        try:
            mode = flag_path.read_text().strip().lower()
            if mode in MODE_HOOKS:
                return mode
        except Exception:
            pass

    return "full"  # default


def should_run(hook_name: str) -> bool:
    """Check if a hook should run given the current CAF mode.

    Args:
        hook_name: The hook script name (without .py extension).
                   e.g., "analyze_request", "auto_escalate"

    Returns:
        True if the hook should run, False if it should skip.
    """
    mode = get_mode()
    category = HOOK_CATEGORIES.get(hook_name)

    if category is None:
        # Unknown hook - let it run (conservative)
        return True

    allowed_categories = MODE_HOOKS.get(mode, MODE_HOOKS["full"])
    return category in allowed_categories
