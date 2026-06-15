# Knowledge DB — Schema Reference

## Table: knowledge_entries (main storage)

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-increment primary key |
| `category` | TEXT | Entry type: `decision`, `learning`, `pattern`, `error`, `context`, `preference` |
| `title` | TEXT | Short title for the entry |
| `content` | TEXT | Full text content |
| `tags` | TEXT | Comma-separated tags for filtering |
| `project` | TEXT | Project name/path this applies to (NULL = global) |
| `confidence` | REAL | 0.0–1.0 confidence score |
| `source` | TEXT | Origin: `session`, `user`, `agent`, `hook` |
| `created_at` | TEXT | ISO timestamp |
| `updated_at` | TEXT | ISO timestamp |
| `expires_at` | TEXT | Optional expiration (NULL = never expires) |

## Table: knowledge_fts (FTS5 virtual table)

Full-text search index over `title + content + tags`. Supports:
- BM25 ranking
- Prefix queries and phrase matching

## Table: knowledge_relations (graph connections)

| Column | Type | Description |
|--------|------|-------------|
| `from_id` | INTEGER | Source entry |
| `to_id` | INTEGER | Target entry |
| `relation_type` | TEXT | `related`, `contradicts`, `supersedes`, `depends_on` |

## Categories

| Category | Description | Example |
|----------|-------------|---------|
| `decision` | Architectural or design decisions | "Use FTS5 over Elasticsearch" |
| `learning` | Lessons learned from experience | "Always quote paths with spaces" |
| `pattern` | Reusable code/workflow patterns | "Circuit breaker pattern for hooks" |
| `error` | Known errors and their fixes | "uv run fails when no pyproject.toml" |
| `context` | Project context and background | "VaultMind has 9 agents" |
| `preference` | User preferences and conventions | "User prefers opus for planning" |
