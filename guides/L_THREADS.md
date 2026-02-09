# L-Threads: Long-Running Threads with Anti-Loop Protection

## The Problem

**Agent Correction Loops**: When agents fail, they often retry the same approach repeatedly, burning tokens until timeout.

Example loop:
```
1. Agent writes code
2. Tests fail
3. Agent tries same fix
4. Tests fail again
5. Agent tries same fix again
6. ... loop until token budget exhausted
```

**Cost**: $50-100 per failed loop, 20-60 minutes wasted

---

## The Solution: Progress File Pattern

**Core Principle**: **External Memory** (persistent state file) prevents loops by tracking what's been tried.

**Pattern**: Use a JSON file to track pending/completed/failed items, read it before every action, skip failed items.

---

## L-Thread Architecture

### 1. Progress File (External Memory)

**File**: `_migration_status.json` (underscore prefix = tool-owned)

```json
{
  "pending": ["table1", "table2", "table3"],
  "completed": ["table0"],
  "failed": [
    {
      "item": "table4",
      "error": "Column mismatch",
      "attempts": 3,
      "last_attempt": "2026-02-10T10:30:00Z"
    }
  ],
  "metadata": {
    "started_at": "2026-02-10T09:00:00Z",
    "last_update": "2026-02-10T10:30:00Z",
    "total_items": 5,
    "success_rate": 0.2
  }
}
```

### 2. Anti-Loop Rules (CRITICAL)

#### Rule 1: Read Before Acting
```python
# ALWAYS read progress file first
with open('_migration_status.json') as f:
    state = json.load(f)

# Check if item already failed
if item in [x['item'] for x in state['failed']]:
    print(f"Skipping {item} - previously failed")
    continue
```

#### Rule 2: Skip Failed Items
```python
# NEVER retry failed items
# Move to next pending item instead
for item in state['pending']:
    if item not in failed_items:
        process(item)  # Only process if not failed
```

#### Rule 3: Update State Immediately
```python
# Update AFTER each item (success or fail)
def update_progress(item, status):
    state = read_progress()

    if status == 'success':
        state['pending'].remove(item)
        state['completed'].append(item)
    elif status == 'failed':
        state['pending'].remove(item)
        state['failed'].append({
            'item': item,
            'error': last_error,
            'attempts': 1,
            'timestamp': datetime.now().isoformat()
        })

    state['metadata']['last_update'] = datetime.now().isoformat()
    write_progress(state)
```

#### Rule 4: Exit Condition
```python
# Exit when no pending items (not when all succeed)
if len(state['pending']) == 0:
    print(f"Migration complete: {len(state['completed'])} succeeded, {len(state['failed'])} failed")
    sys.exit(0)
```

---

## L-Thread Prompt Template

### File: `long-migration.md`

```markdown
# Database Migration L-Thread

## Task
Migrate 100 database tables from old schema to new schema.

## Progress File
`_migration_status.json` - READ THIS FIRST, ALWAYS

## Anti-Loop Rules (CRITICAL)

### Rule 1: Read Progress File BEFORE EVERY ACTION
```bash
cat _migration_status.json
```

If file doesn't exist, create it:
```json
{
  "pending": ["table1", "table2", ..., "table100"],
  "completed": [],
  "failed": []
}
```

### Rule 2: NEVER Retry Failed Items
If an item is in `failed` array, **SKIP IT**. Move to next pending item.

### Rule 3: Update State Immediately After Each Item
- Success: Move from `pending` to `completed`
- Failure: Move from `pending` to `failed` (with error details)
- NEVER leave item in `pending` after processing

### Rule 4: Exit When No Pending Items
When `pending` array is empty, stop. Report final stats.

## Workflow

### Step 1: Initialize (First Run Only)
```python
import json
from pathlib import Path

progress_file = Path('_migration_status.json')

if not progress_file.exists():
    state = {
        'pending': [f'table{i}' for i in range(1, 101)],
        'completed': [],
        'failed': [],
        'metadata': {
            'started_at': datetime.now().isoformat(),
            'total_items': 100
        }
    }
    progress_file.write_text(json.dumps(state, indent=2))
```

### Step 2: Main Loop
```python
while True:
    # READ PROGRESS (every iteration)
    with open('_migration_status.json') as f:
        state = json.load(f)

    # EXIT CONDITION
    if len(state['pending']) == 0:
        print(f"Complete: {len(state['completed'])} success, {len(state['failed'])} failed")
        break

    # GET NEXT ITEM
    item = state['pending'][0]

    # SKIP IF FAILED BEFORE
    if item in [x['item'] for x in state['failed']]:
        state['pending'].remove(item)
        save_progress(state)
        continue

    # PROCESS ITEM
    try:
        migrate_table(item)

        # SUCCESS: Update state
        state['pending'].remove(item)
        state['completed'].append(item)
        save_progress(state)

    except Exception as e:
        # FAILURE: Update state
        state['pending'].remove(item)
        state['failed'].append({
            'item': item,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        save_progress(state)

        # CONTINUE to next item (no retry)
        continue
```

### Step 3: Report
```python
def generate_report():
    with open('_migration_status.json') as f:
        state = json.load(f)

    print("Migration Report")
    print(f"Total: {state['metadata']['total_items']}")
    print(f"Completed: {len(state['completed'])} ({len(state['completed'])/state['metadata']['total_items']*100:.1f}%)")
    print(f"Failed: {len(state['failed'])} ({len(state['failed'])/state['metadata']['total_items']*100:.1f}%)")

    if state['failed']:
        print("\nFailed Items:")
        for item in state['failed']:
            print(f"  - {item['item']}: {item['error']}")
```

## Stop Hook Integration

This L-Thread should run until completion without quality gate interruption.

Configure in `.claude/settings.json`:
```json
{
  "hooks": {
    "Stop": [
      {
        "command": "uv run ~/.claude/hooks/validators/check_lthread_progress.py",
        "description": "Check L-Thread progress (no blocking)"
      }
    ]
  }
}
```

The validator reports progress but never blocks:
```python
#!/usr/bin/env python3
import json
import sys

# Read progress
with open('_migration_status.json') as f:
    state = json.load(f)

# Report (but don't block)
print(json.dumps({
    'quality_gate_passed': True,  # Always pass
    'info': {
        'pending': len(state['pending']),
        'completed': len(state['completed']),
        'failed': len(state['failed'])
    },
    'message': f"L-Thread progress: {len(state['completed'])} done, {len(state['pending'])} pending"
}))
```

## Execution

### Headless Mode (Recommended)
```bash
# Run up to 50 turns without human input
claude -p "long-migration.md" --max-turns 50 --auto-continue
```

### Interactive Mode
```bash
claude
> Load long-migration.md and execute
```

### Background Mode
```bash
# Run in background, check status anytime
nohup claude -p "long-migration.md" --max-turns 100 > migration.log 2>&1 &

# Check progress
tail -f migration.log

# Or read progress file
cat _migration_status.json | jq
```

## Autonomous Context Gathering

The L-Thread prompt should self-load relevant context:

```markdown
## Context Sources

Before starting, read these files:
1. `~/.claude/SELF_CORRECTING_AGENTS.md` - Validation patterns
2. `~/.claude/AGENT_TEAMS.md` - Multi-agent patterns
3. `DATABASE_SCHEMA.md` - Migration details
4. `MIGRATION_HISTORY.md` - Previous migrations

Use Grep/Read tools to gather context autonomously.
```

Example in prompt:
```markdown
## Setup

### Step 0: Gather Context
```bash
# Read self-correcting agent patterns
cat ~/.claude/SELF_CORRECTING_AGENTS.md

# Read database schema
cat DATABASE_SCHEMA.md

# Check previous migrations
cat MIGRATION_HISTORY.md
```

You now have all context needed to proceed.
```

---

## Real-World Example: Database Migration

### Scenario
Migrate 100 tables from MySQL to PostgreSQL, with different column types and constraints.

### L-Thread Prompt: `postgres-migration.md`

```markdown
# PostgreSQL Migration L-Thread

## Task
Migrate 100 MySQL tables to PostgreSQL.

## Progress File
`_postgres_migration_status.json`

## Anti-Loop Rules
1. Read progress file BEFORE every table
2. NEVER retry failed tables
3. Update state AFTER each table (success or fail)
4. Exit when pending array is empty

## Context
Read these before starting:
- `MYSQL_SCHEMA.sql` - Source schema
- `POSTGRES_REQUIREMENTS.md` - Target requirements
- `~/.claude/L_THREADS.md` - This guide

## Implementation

### Initialize Progress
```python
import json
from pathlib import Path

# Get table list from MySQL
tables = get_mysql_tables()  # Returns ['users', 'orders', ...]

progress_file = Path('_postgres_migration_status.json')
if not progress_file.exists():
    state = {
        'pending': tables,
        'completed': [],
        'failed': [],
        'metadata': {
            'started_at': datetime.now().isoformat(),
            'total_tables': len(tables),
            'source': 'mysql',
            'target': 'postgres'
        }
    }
    progress_file.write_text(json.dumps(state, indent=2))
```

### Migration Loop
```python
def migrate():
    while True:
        # READ progress
        state = json.loads(Path('_postgres_migration_status.json').read_text())

        # EXIT if done
        if not state['pending']:
            generate_report()
            break

        # NEXT table
        table = state['pending'][0]

        # SKIP if failed before
        failed_tables = [x['item'] for x in state['failed']]
        if table in failed_tables:
            state['pending'].remove(table)
            save_state(state)
            continue

        # MIGRATE
        try:
            print(f"Migrating {table}...")

            # Get MySQL schema
            mysql_schema = get_table_schema('mysql', table)

            # Convert to PostgreSQL
            pg_schema = convert_schema(mysql_schema)

            # Create table
            execute_postgres(pg_schema)

            # Copy data
            copy_data('mysql', 'postgres', table)

            # Verify
            verify_migration(table)

            # SUCCESS
            state['pending'].remove(table)
            state['completed'].append(table)
            save_state(state)
            print(f"✓ {table} migrated")

        except Exception as e:
            # FAILURE (no retry)
            print(f"✗ {table} failed: {e}")
            state['pending'].remove(table)
            state['failed'].append({
                'item': table,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            save_state(state)
            # CONTINUE to next table

def save_state(state):
    state['metadata']['last_update'] = datetime.now().isoformat()
    Path('_postgres_migration_status.json').write_text(json.dumps(state, indent=2))

migrate()
```

### Report
```python
def generate_report():
    state = json.loads(Path('_postgres_migration_status.json').read_text())

    print("\n" + "="*60)
    print("PostgreSQL Migration Report")
    print("="*60)
    print(f"Total Tables: {state['metadata']['total_tables']}")
    print(f"Completed: {len(state['completed'])} ({len(state['completed'])/state['metadata']['total_tables']*100:.1f}%)")
    print(f"Failed: {len(state['failed'])} ({len(state['failed'])/state['metadata']['total_tables']*100:.1f}%)")

    if state['failed']:
        print("\nFailed Tables:")
        for item in state['failed']:
            print(f"  ✗ {item['item']}: {item['error']}")

    print(f"\nDuration: {calculate_duration(state)}")
    print("="*60)
```

## Execution
```bash
# Run migration (up to 200 turns for 100 tables)
claude -p "postgres-migration.md" --max-turns 200 --auto-continue
```
```
```

---

## L-Thread vs Regular Agent

### Regular Agent (No Progress File)
```
Attempt 1: Migrate table1 → FAIL
Attempt 2: Migrate table1 (same approach) → FAIL
Attempt 3: Migrate table1 (same approach) → FAIL
...
Attempt 20: Migrate table1 (same approach) → FAIL

Result: $50 burned, 0 tables migrated
```

### L-Thread (With Progress File)
```
Read progress → table1 pending
Attempt: Migrate table1 → FAIL
Update progress → table1 moved to failed
Read progress → table2 pending
Attempt: Migrate table2 → SUCCESS
Update progress → table2 moved to completed
Read progress → table3 pending
...

Result: $10 spent, 99/100 tables migrated (skipped 1 failed)
```

---

## Stop Hook Configuration

### File: `~/.claude/hooks/validators/check_lthread_progress.py`

```python
#!/usr/bin/env python3
"""L-Thread Progress Checker (Non-Blocking)"""

import json
import sys
from pathlib import Path

def find_progress_file():
    """Find _*_status.json in current directory"""
    cwd = Path.cwd()
    progress_files = list(cwd.glob('_*_status.json'))

    if not progress_files:
        # No L-Thread detected
        print(json.dumps({
            'quality_gate_passed': True,
            'message': 'No L-Thread progress file found'
        }))
        sys.exit(0)

    return progress_files[0]

def check_progress():
    progress_file = find_progress_file()

    with open(progress_file) as f:
        state = json.load(f)

    total = state['metadata'].get('total_items', 0)
    completed = len(state['completed'])
    failed = len(state['failed'])
    pending = len(state['pending'])

    success_rate = completed / total if total > 0 else 0

    # Report progress (never block)
    print(json.dumps({
        'quality_gate_passed': True,  # Always pass
        'info': {
            'total': total,
            'completed': completed,
            'failed': failed,
            'pending': pending,
            'success_rate': f"{success_rate*100:.1f}%"
        },
        'message': f"L-Thread: {completed}/{total} completed ({success_rate*100:.1f}% success)"
    }))

    sys.exit(0)

if __name__ == '__main__':
    check_progress()
```

### Add to `~/.claude/settings.json`

```json
{
  "hooks": {
    "Stop": [
      {
        "command": "uv run ~/.claude/hooks/validators/run_tests.py",
        "description": "Run tests (blocks if failed)"
      },
      {
        "command": "uv run ~/.claude/hooks/validators/check_coverage.py",
        "description": "Check coverage (blocks if <80%)"
      },
      {
        "command": "uv run ~/.claude/hooks/validators/check_lthread_progress.py",
        "description": "Report L-Thread progress (non-blocking)"
      }
    ]
  }
}
```

**Key Difference**: L-Thread hook **reports but never blocks** (always exits 0)

---

## Mission Control Integration

L-Threads show up in Mission Control dashboard with special visualization:

### Progress Bar
```
┌──────────────────────────────────────────┐
│ L-Thread: postgres-migration             │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░ 85% (85/100)      │
│ ✓ Completed: 85                          │
│ ✗ Failed: 5                              │
│ ⧗ Pending: 10                            │
│ Duration: 45 minutes                     │
└──────────────────────────────────────────┘
```

### Event Stream
```
10:00:00 - Read _postgres_migration_status.json
10:00:01 - Processing table: users
10:00:15 - Tool: Bash (migrate users table)
10:00:20 - Success: users migrated
10:00:21 - Update _postgres_migration_status.json
10:00:22 - Read _postgres_migration_status.json
10:00:23 - Processing table: orders
...
```

---

## Best Practices

### 1. Progress File Naming
- **Pattern**: `_<task>_status.json`
- **Examples**: `_migration_status.json`, `_refactor_status.json`, `_test_gen_status.json`
- **Prefix**: Underscore `_` indicates tool-owned (not user-edited)

### 2. State Structure
```json
{
  "pending": [],      // Items not yet processed
  "completed": [],    // Successfully processed
  "failed": [         // Failed items (with details)
    {
      "item": "...",
      "error": "...",
      "attempts": 1,
      "timestamp": "..."
    }
  ],
  "metadata": {       // Additional context
    "started_at": "...",
    "total_items": 100,
    "...": "..."
  }
}
```

### 3. Error Handling
```python
try:
    process_item(item)
    mark_success(item)
except Exception as e:
    mark_failed(item, str(e))
    # CRITICAL: Don't raise, continue to next item
    continue
```

### 4. Atomic Updates
```python
def update_progress(item, status, error=None):
    # Read-modify-write as single operation
    with FileLock('_status.json.lock'):
        state = read_progress()

        state['pending'].remove(item)
        if status == 'success':
            state['completed'].append(item)
        else:
            state['failed'].append({'item': item, 'error': error})

        write_progress(state)
```

### 5. Resumability
```bash
# Run stopped mid-way
claude -p "long-migration.md" --max-turns 50

# Resume from where it left off
claude -p "long-migration.md" --max-turns 50
# Automatically picks up from progress file
```

---

## Success Metrics

### Before L-Threads (Regular Agents)
```
Task: Migrate 100 tables
Failures: 5 tables fail
Outcome: Agent loops on first failure, burns $50, migrates 0 tables
Time: 60 minutes wasted
```

### After L-Threads (Progress File Pattern)
```
Task: Migrate 100 tables
Failures: 5 tables fail
Outcome: Agent skips failed tables, migrates 95 tables
Cost: $12 (only for actual work)
Time: 45 minutes productive work
Success Rate: 95%
```

### Key Improvements
- ✅ **0% loop rate** (no retries on failed items)
- ✅ **95% completion rate** (skip failures, continue rest)
- ✅ **76% cost reduction** ($50 → $12)
- ✅ **100% resumability** (crash-safe via progress file)

---

## Use Cases

### 1. Database Migrations
- Migrate 1000s of tables
- Skip failed tables (investigate later)
- Resume after interruption

### 2. Bulk Refactoring
- Refactor 500 files
- Skip files with syntax errors
- Continue rest of codebase

### 3. Test Generation
- Generate tests for 200 modules
- Skip modules with complex logic
- Cover 90% of codebase

### 4. Documentation Generation
- Document 100 API endpoints
- Skip deprecated endpoints
- Update all active docs

### 5. Security Scanning
- Scan 1000s of files
- Skip binaries
- Report all vulnerabilities

---

## Summary

**L-Threads = Long-Running Threads with Anti-Loop Protection**

### Core Pattern
1. **Progress File** (`_status.json`) - External memory
2. **Read Before Act** - Always check state first
3. **Skip Failed Items** - Never retry failures
4. **Update Immediately** - Write state after each item
5. **Exit When Empty** - Stop when `pending` array is empty

### Benefits
- ✅ No correction loops (skip failures)
- ✅ Crash-safe (resume from progress file)
- ✅ Cost-efficient (only pay for work done)
- ✅ High completion rate (95%+ typical)
- ✅ Observable (Mission Control integration)

### Integration with Steps 1-14
- **Step 11 (Agent Teams)**: L-Threads can spawn agent teams per item
- **Step 12 (Z-Threads)**: L-Threads are a specialized Z-Thread pattern
- **Step 13 (Mission Control)**: L-Thread progress visible in dashboard
- **Step 14 (Generative UI)**: Progress bar renders as HTML

---

**🎯 L-Threads enable long-running autonomous operations without correction loops!** ⚡

**The complete Elite Agentic Engineering stack now includes loop-safe execution.** 🔄

---

**Guide Version**: 1.0.0
**Last Updated**: 2026-02-10
**Status**: ✅ COMPLETE
