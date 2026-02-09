# Database Migration L-Thread

## Task
Migrate 100 database tables from old schema to new schema.

## Progress File
`_migration_status.json` - **READ THIS FIRST, ALWAYS**

## Anti-Loop Rules (CRITICAL)

### Rule 1: Read Progress File BEFORE EVERY ACTION
```bash
cat _migration_status.json
```

If file doesn't exist, create it:
```json
{
  "pending": ["table1", "table2", "table3", ..., "table100"],
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

---

## Context Sources

Before starting, autonomously gather context from:

```bash
# Read L-Thread pattern guide
cat ~/.claude/L_THREADS.md

# Read self-correcting patterns
cat ~/.claude/SELF_CORRECTING_AGENTS.md

# Read database schema (if exists)
cat DATABASE_SCHEMA.md 2>/dev/null || echo "No schema file found"

# Check migration history (if exists)
cat MIGRATION_HISTORY.md 2>/dev/null || echo "No migration history"
```

You now have all context needed to proceed.

---

## Implementation

### Step 1: Initialize Progress (First Run Only)

```python
import json
from pathlib import Path
from datetime import datetime

progress_file = Path('_migration_status.json')

if not progress_file.exists():
    # Get list of tables to migrate
    tables = [f'table{i}' for i in range(1, 101)]  # Replace with actual table discovery

    state = {
        'pending': tables,
        'completed': [],
        'failed': [],
        'metadata': {
            'started_at': datetime.now().isoformat(),
            'total_items': len(tables),
            'task': 'database_migration',
            'source_db': 'old_schema',
            'target_db': 'new_schema'
        }
    }

    progress_file.write_text(json.dumps(state, indent=2))
    print(f"Initialized progress file with {len(tables)} tables")
```

### Step 2: Main Migration Loop

```python
def migrate_tables():
    """Main migration loop with anti-loop protection"""

    while True:
        # ═══════════════════════════════════════════════════════
        # READ PROGRESS (every iteration)
        # ═══════════════════════════════════════════════════════
        with open('_migration_status.json') as f:
            state = json.load(f)

        # ═══════════════════════════════════════════════════════
        # EXIT CONDITION: No pending items
        # ═══════════════════════════════════════════════════════
        if len(state['pending']) == 0:
            generate_report(state)
            break

        # ═══════════════════════════════════════════════════════
        # GET NEXT ITEM
        # ═══════════════════════════════════════════════════════
        table = state['pending'][0]

        # ═══════════════════════════════════════════════════════
        # SKIP IF FAILED BEFORE (Anti-Loop Protection)
        # ═══════════════════════════════════════════════════════
        failed_items = [x['item'] for x in state['failed']]
        if table in failed_items:
            print(f"⚠️  Skipping {table} - previously failed")
            state['pending'].remove(table)
            save_progress(state)
            continue

        # ═══════════════════════════════════════════════════════
        # PROCESS ITEM
        # ═══════════════════════════════════════════════════════
        print(f"🔄 Migrating {table}...")

        try:
            # Perform migration
            migrate_single_table(table)

            # Verify migration
            verify_migration(table)

            # ═══════════════════════════════════════════════════
            # SUCCESS: Update state
            # ═══════════════════════════════════════════════════
            state['pending'].remove(table)
            state['completed'].append(table)
            save_progress(state)

            print(f"✅ {table} migrated successfully")

        except Exception as e:
            # ═══════════════════════════════════════════════════
            # FAILURE: Update state (NO RETRY)
            # ═══════════════════════════════════════════════════
            print(f"❌ {table} failed: {e}")

            state['pending'].remove(table)
            state['failed'].append({
                'item': table,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'attempts': 1
            })
            save_progress(state)

            # CRITICAL: Continue to next table (don't retry)
            continue


def save_progress(state):
    """Save progress with timestamp"""
    state['metadata']['last_update'] = datetime.now().isoformat()

    with open('_migration_status.json', 'w') as f:
        json.dump(state, f, indent=2)


def migrate_single_table(table_name):
    """Migrate a single table (implement your logic here)"""

    # Example implementation:
    # 1. Read old schema
    old_schema = get_table_schema('old_schema', table_name)

    # 2. Transform to new schema
    new_schema = transform_schema(old_schema)

    # 3. Create table in new schema
    execute_sql(new_schema['create_statement'])

    # 4. Copy data
    copy_table_data('old_schema', 'new_schema', table_name)

    # 5. Create indexes
    for index in new_schema['indexes']:
        execute_sql(index)


def verify_migration(table_name):
    """Verify migration was successful"""

    # Count rows in both schemas
    old_count = execute_sql(f"SELECT COUNT(*) FROM old_schema.{table_name}")[0][0]
    new_count = execute_sql(f"SELECT COUNT(*) FROM new_schema.{table_name}")[0][0]

    if old_count != new_count:
        raise Exception(f"Row count mismatch: old={old_count}, new={new_count}")

    print(f"   Verified {new_count} rows")


def generate_report(state):
    """Generate final migration report"""

    total = state['metadata']['total_items']
    completed = len(state['completed'])
    failed = len(state['failed'])

    print("\n" + "="*60)
    print("DATABASE MIGRATION REPORT")
    print("="*60)
    print(f"Total Tables: {total}")
    print(f"Completed: {completed} ({completed/total*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)")

    if state['failed']:
        print("\n❌ Failed Tables:")
        for item in state['failed']:
            print(f"   • {item['item']}: {item['error']}")

    print(f"\nStarted: {state['metadata']['started_at']}")
    print(f"Finished: {datetime.now().isoformat()}")
    print("="*60)


# Run migration
migrate_tables()
```

---

## Execution Commands

### Headless Mode (Recommended for L-Threads)
```bash
# Run with auto-continue (up to 50 turns)
claude -p "long-migration.md" --max-turns 50 --auto-continue
```

### Interactive Mode
```bash
claude

# In conversation:
> Load and execute long-migration.md
```

### Background Mode (24/7 Execution)
```bash
# Run in background
nohup claude -p "long-migration.md" --max-turns 200 > migration.log 2>&1 &

# Check progress anytime
cat _migration_status.json | jq

# Watch log
tail -f migration.log

# Check process
ps aux | grep claude
```

---

## Monitoring

### Check Progress File
```bash
# Pretty print progress
cat _migration_status.json | jq

# Count items
echo "Pending: $(cat _migration_status.json | jq '.pending | length')"
echo "Completed: $(cat _migration_status.json | jq '.completed | length')"
echo "Failed: $(cat _migration_status.json | jq '.failed | length')"
```

### Mission Control Dashboard
```bash
# Start Mission Control
cd ~/Documents/claude-code-hooks-multi-agent-observability
./scripts/start-system.sh

# View at http://localhost:5173
# Shows real-time L-Thread progress
```

---

## Resume After Crash

If the agent crashes or is interrupted:

```bash
# Simply re-run the same command
claude -p "long-migration.md" --max-turns 50

# The progress file ensures it picks up where it left off
# Already completed tables are skipped
# Failed tables are skipped (anti-loop)
# Only pending tables are processed
```

---

## Troubleshooting

### Problem: Agent keeps retrying failed table

**Diagnosis**: Not reading progress file before each iteration

**Fix**: Ensure progress file is read at start of while loop:
```python
while True:
    # MUST be first line in loop
    with open('_migration_status.json') as f:
        state = json.load(f)
```

### Problem: Progress file not updating

**Diagnosis**: Not calling `save_progress()` after each item

**Fix**: Call save after both success and failure:
```python
try:
    migrate_single_table(table)
    state['completed'].append(table)
    save_progress(state)  # ← Must call
except Exception as e:
    state['failed'].append({...})
    save_progress(state)  # ← Must call
```

### Problem: Agent exits before completion

**Diagnosis**: Wrong exit condition

**Fix**: Only exit when `pending` is empty:
```python
if len(state['pending']) == 0:  # Not when all succeed
    break
```

---

## Success Criteria

After execution, you should have:

- ✅ `_migration_status.json` with `pending: []`
- ✅ High completion rate (90%+)
- ✅ Failed items documented (with error messages)
- ✅ No correction loops (each item attempted once)
- ✅ Full report generated

---

## Notes

- Progress file is the **source of truth** (not agent memory)
- Failed items are **skipped** (investigate manually later)
- Each item attempted **exactly once** (no retries)
- Resumable at any point (crash-safe)
- Scales to 1000s of items

---

**📊 L-Thread Pattern: External Memory + Anti-Loop Rules = Reliable Long-Running Operations**
