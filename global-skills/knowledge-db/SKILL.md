---
name: Knowledge Database
version: 0.1.0
description: "This skill should be used when the user asks about remembering things, knowledge management, searching past decisions, storing learnings, or persistent memory. It provides a SQLite FTS5-powered knowledge database for persistent memory across sessions."
---

# Knowledge Database (SQLite FTS5)

Persistent knowledge storage with full-text search for cross-session memory, decision tracking, and learning accumulation.

## Architecture

```
~/.claude/data/knowledge-db/
├── knowledge.db          # SQLite database with FTS5
└── backups/              # Auto-backups before migrations
```

## Database Schema

The database has three core tables:

### 1. knowledge_entries (main storage)
- `id`: Auto-increment primary key
- `category`: Entry type (decision, learning, pattern, error, context)
- `title`: Short title for the entry
- `content`: Full text content
- `tags`: Comma-separated tags for filtering
- `project`: Project name/path this applies to (NULL = global)
- `confidence`: 0.0-1.0 confidence score
- `source`: Where this knowledge came from (session, user, agent, hook)
- `created_at`: ISO timestamp
- `updated_at`: ISO timestamp
- `expires_at`: Optional expiration (NULL = never)

### 2. knowledge_fts (FTS5 virtual table)
- Full-text search index on title + content + tags
- Supports BM25 ranking
- Prefix queries and phrase matching

### 3. knowledge_relations (graph connections)
- `from_id`: Source entry
- `to_id`: Target entry  
- `relation_type`: Type of relation (related, contradicts, supersedes, depends_on)

## Operations

### Store Knowledge

```bash
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py store \
  --category "decision" \
  --title "Use SQLite FTS5 for knowledge storage" \
  --content "Chose SQLite FTS5 over alternatives because: zero dependencies, fast full-text search, single file portability, ACID compliant." \
  --tags "architecture,database,decision" \
  --project "claude-agentic-framework" \
  --confidence 0.95
```

### Search Knowledge

```bash
# Full-text search
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py search "SQLite FTS5"

# Search by category
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py search "hook patterns" --category pattern

# Search by project
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py search "deployment" --project vaultmind

# Search with tag filter
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py search "security" --tags "critical,vulnerability"
```

### Query Recent Knowledge

```bash
# Last 10 entries
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py recent --limit 10

# Recent decisions for a project
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py recent --category decision --project my-project
```

### Update Knowledge

```bash
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py update 42 \
  --content "Updated content here" \
  --confidence 0.8
```

### Expire/Archive Knowledge

```bash
# Mark as expired
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py expire 42

# Purge expired entries
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py purge-expired
```

### Export/Import

```bash
# Export knowledge as JSON (default limit: 10,000 entries)
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py export > knowledge-backup.json

# Export with custom limit
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py export --limit 50000 > knowledge-backup.json

# Import from JSON (file must be in ~/.claude/ or current directory)
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py import-json knowledge-backup.json
```

## Categories

| Category | Description | Example |
|----------|-------------|---------|
| `decision` | Architectural or design decisions | "Use FTS5 over Elasticsearch" |
| `learning` | Lessons learned from experience | "Always quote paths with spaces" |
| `pattern` | Reusable code/workflow patterns | "Circuit breaker pattern for hooks" |
| `error` | Known errors and their fixes | "uv run fails when no pyproject.toml" |
| `context` | Project context and background | "VaultMind has 9 agents" |
| `preference` | User preferences and conventions | "User prefers opus for planning" |

## Integration Points

### Session Start Hook
On session start, the hook can auto-load recent relevant knowledge:
```python
# In session_start.py
entries = search_knowledge(project=current_project, limit=5)
# Inject as context
```

### Pre-Compact Hook
Before context compaction, save important learnings:
```python
# In pre_compact.py
store_knowledge(
    category="context",
    title="Session context before compaction",
    content=summarize_session()
)
```

### Stop Hook
On task completion, extract and store learnings:
```python
# In stop.py
if task_completed:
    store_knowledge(category="learning", ...)
```

## Examples

### Example 1: Store a Decision

After making an architectural decision:
```bash
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py store \
  --category decision \
  --title "Hybrid hooks approach: command + prompt" \
  --content "Keep fast pattern matching via command hooks for <5ms checks. Add prompt hooks only for semantic validation that patterns cannot catch. This gives us both speed and intelligence." \
  --tags "hooks,architecture,performance" \
  --project "claude-agentic-framework"
```

### Example 2: Search Before Making a Decision

Before starting work, check existing knowledge:
```bash
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py search "hook architecture"
```

### Example 3: Track an Error Pattern

When encountering a recurring error:
```bash
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py store \
  --category error \
  --title "uv run timeout on large files" \
  --content "When uv run processes files >10MB, it can timeout. Workaround: increase timeout to 30s or chunk the input." \
  --tags "uv,timeout,workaround"
```

## Security

### File Permissions

All database and log files are created with **mode 600** (owner read/write only):

- `knowledge.db` -- SQLite database file
- `knowledge.jsonl` -- Append-only durability log

Permissions are enforced on every database open and every JSONL append operation.

### Import Path Restrictions

The `import-json` command validates file paths before reading. Imports are restricted to these directories:

| Allowed Directory | Purpose |
|-------------------|---------|
| `~/.claude/data/` | Primary data storage |
| `~/.claude/` | Claude configuration directory |
| Current working directory | Convenience for local files |

The following are blocked:

- **Path traversal**: Any path containing `..` is rejected
- **Absolute paths outside allowed dirs**: e.g., `/etc/passwd` is rejected
- **Non-regular files**: Directories, symlinks to disallowed locations, device files

Example of a blocked import:
```bash
# These will all fail with a validation error:
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py import-json /etc/passwd
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py import-json ../../etc/shadow
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py import-json /tmp/malicious.json
```

### Export Limits

The `export` command has a default limit of **10,000 entries** to prevent unbounded memory usage on large databases. Use `--limit N` to adjust:

```bash
# Default: max 10,000 entries
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py export

# Custom limit
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py export --limit 50000
```

A warning is printed to stderr when the limit is reached.

### FTS5 Tag Wildcards

Tag filters in `search` use SQL `LIKE` with `%` wildcards for substring matching. This means a tag filter of `sec` will match `security`, `insecure`, etc. This is by design for flexible filtering but be aware that:

- Tag filters are **substring matches**, not exact matches
- Use specific, full tag names for precise filtering (e.g., `--tags "security"` not `--tags "sec"`)
- The `%` character in user-provided tags is passed through to SQL LIKE -- this is harmless (it only widens the match) but may produce unexpected results
