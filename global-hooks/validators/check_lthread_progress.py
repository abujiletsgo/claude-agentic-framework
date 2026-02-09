#!/usr/bin/env python3
"""
L-Thread Progress Checker (Non-Blocking)

This hook reports L-Thread progress but NEVER blocks agent completion.

Unlike other quality gates (tests, coverage, security), L-Threads should run
to completion even if some items fail. The progress file tracks failures.

Usage:
    Automatically called on Stop/SubagentStop events if configured in settings.json
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def find_progress_file():
    """Find L-Thread progress file in current directory

    Pattern: _*_status.json (underscore prefix)
    Examples: _migration_status.json, _refactor_status.json
    """
    cwd = Path.cwd()
    progress_files = list(cwd.glob('_*_status.json'))

    if not progress_files:
        # No L-Thread detected, pass silently
        return None

    # Return first match (typically only one per directory)
    return progress_files[0]


def calculate_duration(state):
    """Calculate duration from started_at to now"""
    try:
        started = datetime.fromisoformat(state['metadata']['started_at'])
        now = datetime.now()
        duration = now - started

        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except:
        return "unknown"


def check_progress():
    """Check L-Thread progress and report (never block)"""

    progress_file = find_progress_file()

    if not progress_file:
        # No L-Thread running, pass silently
        print(json.dumps({
            'quality_gate_passed': True,
            'message': 'No L-Thread detected'
        }))
        sys.exit(0)

    # Read progress state
    try:
        with open(progress_file) as f:
            state = json.load(f)
    except Exception as e:
        # Can't read progress file, but don't block
        print(json.dumps({
            'quality_gate_passed': True,
            'error': f'Could not read progress file: {e}',
            'message': 'L-Thread progress file exists but unreadable'
        }))
        sys.exit(0)

    # Extract metrics
    total = state['metadata'].get('total_items', 0)
    completed = len(state.get('completed', []))
    failed = len(state.get('failed', []))
    pending = len(state.get('pending', []))

    success_rate = (completed / total * 100) if total > 0 else 0
    failure_rate = (failed / total * 100) if total > 0 else 0

    duration = calculate_duration(state)
    task_name = state['metadata'].get('task', 'unknown')

    # Build report message
    if pending == 0:
        # L-Thread completed
        status = "✅ COMPLETE"
        message = f"L-Thread '{task_name}' completed: {completed}/{total} succeeded ({success_rate:.1f}%), {failed} failed ({failure_rate:.1f}%)"
    else:
        # L-Thread in progress
        status = "🔄 IN PROGRESS"
        message = f"L-Thread '{task_name}': {completed}/{total} completed ({success_rate:.1f}%), {pending} pending, {failed} failed"

    # Report progress (ALWAYS PASS - never block)
    result = {
        'quality_gate_passed': True,  # ← CRITICAL: Always pass
        'info': {
            'status': status,
            'task': task_name,
            'total': total,
            'completed': completed,
            'failed': failed,
            'pending': pending,
            'success_rate': f"{success_rate:.1f}%",
            'failure_rate': f"{failure_rate:.1f}%",
            'duration': duration,
            'progress_file': str(progress_file)
        },
        'message': message
    }

    # Add failed items detail if any
    if failed > 0 and state.get('failed'):
        result['info']['failed_items'] = [
            {
                'item': item['item'],
                'error': item.get('error', 'Unknown error')[:100]  # Truncate long errors
            }
            for item in state['failed'][:5]  # Show first 5 failures
        ]

    print(json.dumps(result, indent=2))
    sys.exit(0)  # Exit 0 = pass (never block)


if __name__ == '__main__':
    check_progress()
