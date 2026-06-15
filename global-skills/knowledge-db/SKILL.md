---
name: knowledge-db
version: 0.2.0
description: "This skill should be used when the user asks about remembering things, knowledge management, searching past decisions, storing learnings, or persistent memory. It provides a SQLite FTS5-powered knowledge database for persistent memory across sessions."
scope: framework
---

> **Framework-only**: This skill is part of the Claude Agentic Framework infrastructure. It requires `~/.claude/data/knowledge-db/` and `~/.claude/skills/knowledge-db/scripts/knowledge_cli.py`.

# Knowledge Database (SQLite FTS5)

Persistent knowledge storage with full-text search for cross-session memory, decision tracking, and learning accumulation.

## Architecture

```
~/.claude/data/knowledge-db/
├── knowledge.db          # SQLite database with FTS5
└── backups/              # Auto-backups before migrations
```

## Database Schema

Three core tables: `knowledge_entries` (main storage with category/title/content/tags/project/confidence/source/timestamps), `knowledge_fts` (FTS5 virtual table for BM25 full-text search over title+content+tags), and `knowledge_relations` (typed graph edges between entries).

See [references/schema.md](references/schema.md) for full column definitions and the category taxonomy.

## When to Use This vs. FACTS.md

- **knowledge-db**: Structured, searchable, long-lived knowledge. Use for decisions, reusable patterns, error records, project context. Survives context compaction by design.
- **FACTS.md**: Flat in-file memory for the current session's verified facts. Fast to read, not searchable, not relational.

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

### Update / Expire / Export

```bash
# Update an entry
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py update 42 \
  --content "Updated content here" \
  --confidence 0.8

# Mark as expired
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py expire 42

# Purge expired entries
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py purge-expired

# Export knowledge as JSON (default limit: 10,000 entries)
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py export > knowledge-backup.json

# Import from JSON (file must be in ~/.claude/ or current directory)
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py import-json knowledge-backup.json
```

## Examples

### Store a Decision

```bash
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py store \
  --category decision \
  --title "Hybrid hooks approach: command + prompt" \
  --content "Keep fast pattern matching via command hooks for <5ms checks. Add prompt hooks only for semantic validation that patterns cannot catch. This gives us both speed and intelligence." \
  --tags "hooks,architecture,performance" \
  --project "claude-agentic-framework"
```

### Search Before Making a Decision

```bash
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py search "hook architecture"
```

### Track an Error Pattern

```bash
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py store \
  --category error \
  --title "uv run timeout on large files" \
  --content "When uv run processes files >10MB, it can timeout. Workaround: increase timeout to 30s or chunk the input." \
  --tags "uv,timeout,workaround"
```

## Security

DB and log files are created mode 600. The `import-json` command enforces path allowlist (`~/.claude/`, cwd) and rejects path traversal and non-regular files. `export` defaults to 10,000-entry limit. FTS5 tag filters use SQL `LIKE` substring matching — use full tag names for precision.

See [references/security.md](references/security.md) for the full allowlist table, blocked-path examples, export limit details, and FTS5 wildcard behavior.

## Hook Integration

The knowledge DB can be called from session_start, pre_compact, and stop hooks to auto-load context, save pre-compaction learnings, and record task completions. See [references/integration.md](references/integration.md) for illustrative pseudocode (these are examples, not the authoritative hook implementations).

## Resources

- **CLI**: `scripts/knowledge_cli.py` — all operations above are thin wrappers around this script; run with `--help` for the full option list
- **Schema + categories**: [references/schema.md](references/schema.md)
- **Security + import rules**: [references/security.md](references/security.md)
- **Hook integration examples**: [references/integration.md](references/integration.md)
