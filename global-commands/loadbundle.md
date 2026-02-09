---
description: Restore agent intelligence from a previous session bundle (0% token waste)
allowed-tools: Bash, Read
---

# Load Context Bundle

**Purpose:** "Re-hydrate" agent from a previous session's context bundle. Instantly restore what files were read and modified without replaying conversation history.

---

## What is a Context Bundle?

A Context Bundle is a **"save game" for your agent's brain**:
- Logs every file read, edit, write during a session
- Stored in `~/.claude/bundles/<session-id>.json`
- Lightweight (<100KB even for heavy sessions)
- Restores agent intelligence with **0% token waste**

---

## Usage

### List Available Bundles
```bash
# See what sessions you can restore from
ls -lh ~/.claude/bundles/
```

### Load a Specific Bundle
```
/loadbundle <session-id>
```

Example:
```
/loadbundle abc123def456
```

### Load Most Recent Bundle
```
/loadbundle latest
```

---

## What This Command Does

### Step 1: Locate Bundle
Find the bundle file for the specified session:
```bash
cat ~/.claude/bundles/<session-id>.json
```

### Step 2: Parse Bundle
Extract key information:
- **Files Read**: List of all files the previous agent read
- **Files Modified**: List of all files edited/written
- **Operations Summary**: Read count, edit count, write count
- **Timeline**: When operations occurred

### Step 3: Restore Context (Intelligently)

**Don't do this** ❌:
```
# Re-read every single file (token waste)
for file in files_read:
    Read(file)
```

**Do this instead** ✅:
```
# Generate compact summary of previous session
Summary:
- Session worked on: [file1, file2, file3]
- Key operations: X reads, Y edits, Z writes
- Files modified: [list]
- Last active: [timestamp]

Recommendation: If you need details from these files, read them now.
Otherwise, you're primed with the knowledge that previous agent had context on these areas.
```

### Step 4: Report to User

Provide a concise restoration report:

```markdown
## Context Bundle Restored

**Session**: abc123def456
**Created**: 2026-02-10 14:30:22
**Last Updated**: 2026-02-10 15:45:10

### Previous Session Activity
- **Files Read**: 23 files
- **Files Modified**: 8 files
- **Operations**: 145 total (95 reads, 35 edits, 15 writes)

### Key Areas of Work
- `src/auth/` - Authentication system (12 operations)
- `src/api/routes/` - API endpoints (8 operations)
- `tests/` - Test files (5 operations)

### Files Modified
- `src/auth/jwt.js` - Edited
- `src/auth/middleware.js` - Edited
- `src/api/routes/user.js` - Written
- `tests/auth.test.js` - Written

### 💡 Restoration Complete
Agent now "remembers" the previous session's work area.

**Token Usage**: ~500 tokens (vs 50,000+ if re-reading all files)

### Next Steps
Run `/prime` if you need broader project context, or start working immediately - you have the previous agent's "memory".
```

---

## Bundle Format

Bundles are structured JSON:

```json
{
  "session_id": "abc123",
  "created_at": "2026-02-10T14:30:22",
  "last_updated": "2026-02-10T15:45:10",
  "operations": [
    {
      "timestamp": "2026-02-10T14:32:15",
      "tool": "Read",
      "file": "src/auth/jwt.js",
      "action": "read"
    },
    {
      "timestamp": "2026-02-10T14:35:42",
      "tool": "Edit",
      "file": "src/auth/jwt.js",
      "action": "edit",
      "old_string": "const secret = ...",
      "new_string": "const secret = process.env..."
    }
  ],
  "files_read": ["src/auth/jwt.js", "src/auth/middleware.js", ...],
  "files_modified": ["src/auth/jwt.js", "tests/auth.test.js"],
  "summary": {
    "read_count": 95,
    "edit_count": 35,
    "write_count": 15,
    "total_operations": 145
  }
}
```

---

## Token Economics

### Without Bundles (Fragile)
```
Terminal crashes → Start new session
Must re-read 50 files = 50,000 tokens
Agent has no memory of previous work
```

### With Bundles (Resilient)
```
Terminal crashes → Start new session
/loadbundle previous-session
Reads summary only = 500 tokens
Agent instantly "remembers" previous work
Token savings: 99%
```

---

## When to Use

✅ **Use /loadbundle when:**
- Resuming work after terminal crash
- Switching machines (sync bundles via git/cloud)
- Starting new day's work on same project
- Agent hit context limit and need to start fresh
- Want to restore specific session's "knowledge"

❌ **Don't use when:**
- Starting work on completely new project
- Previous session isn't relevant to current task
- You want fresh perspective (don't load old context)

---

## Advanced: Bundle Management

### Cleanup Old Bundles
```bash
# Remove bundles older than 30 days
find ~/.claude/bundles/ -name "*.json" -mtime +30 -delete
```

### Sync Bundles Across Machines
```bash
# Add to git (if using private repo)
git add ~/.claude/bundles/<session-id>.json
git commit -m "Save context bundle"
git push

# On other machine
git pull
/loadbundle <session-id>
```

### Merge Bundles (Advanced)
If you have multiple related sessions, you could create a command to merge their bundles for comprehensive restoration.

---

## Integration with Elite Context Engineering

**The Complete Stack**:

1. **Strip Global Context** - Save 10-20% permanently
2. **On-Demand Priming** (`/prime`) - Load project context when needed
3. **Sub-Agent Delegation** (`/research`) - Preserve context during heavy tasks
4. **Context Bundles** (`/loadbundle`) - Restore agent intelligence across sessions

**Result**: Your agent is **resilient, efficient, and infinitely scalable**.

---

## Success Criteria

After using `/loadbundle`:
- ✅ Agent knows what previous agent worked on
- ✅ Token usage: < 1,000 (vs 50,000+ re-reading files)
- ✅ Context restored in seconds
- ✅ Can immediately continue work without re-orientation
- ✅ Portable across machines

You've achieved **persistent agent intelligence**.
