# Knowledge Pipeline

Persistent cross-session learning via SQLite FTS5. Three scripts form a complete pipeline: inject at start, extract during, store at end.

## Overview

```
Session starts  →  inject_relevant.py   INJECT past learnings into context
Work happens    →  extract_learnings.py EXTRACT insights from tool outputs
Session ends    →  store_learnings.py   STORE extracted insights to SQLite DB
```

This creates a feedback loop: each session contributes learnings, and future sessions benefit from them automatically.

## Scripts

### 1. inject_relevant.py (SessionStart)

**What it does**: Searches the FTS5 index for learnings relevant to the current project and injects them as `additionalContext` at session start.

**Relevance search**:
- Extracts search terms from the current working directory path
- Terms from recent git activity (branch name, recent commit messages)
- FTS5 full-text search across `content` and `tags` columns
- Ranked by relevance score + recency boost

**Output format** (injected into context):
```
[Knowledge] Relevant learnings from past sessions:

1. [PATTERN] When using uv run with hook scripts, always include the script
   header block with dependencies. Missing this causes import errors.
   Source: PostToolUse/Bash

2. [LEARNED] Circuit breaker state files are stored per-script in
   ~/.claude/circuit_breakers/. Delete the file to reset a stuck breaker.
   Source: PostToolUse/Bash
```

**Configuration** (`~/.claude/knowledge_pipeline.yaml`):
```yaml
evolve:
  enabled: true
  max_injections: 5            # Max learnings to inject per session
  relevance_threshold: 0.6     # Minimum relevance score (0.0–1.0)
  recency_boost: 0.2           # Boost factor for recent learnings
  include_categories:          # Which categories to inject
    - LEARNED
    - PATTERN
    - INVESTIGATION
  lookback_days: 30            # Only consider learnings from this many days back
```

### 2. extract_learnings.py (PostToolUse)

**What it does**: Fires after every `Bash`, `Write`, or `Edit` tool call. Analyzes the tool output for extractable insights.

**What gets extracted**:
- Error messages and their solutions (when a subsequent Bash succeeds after a failure)
- New patterns discovered (e.g., API usage, config format)
- Investigation results (findings from research or debugging)
- Configuration gotchas

**Output**: Stores extracted learnings in session memory (not yet persisted — that happens at `store_learnings.py`).

**Circuit breaker**: Wrapped in `circuit_breaker_wrapper.py`. If it fails 3 times in a row, it disables itself for 60s.

### 3. store_learnings.py (Stop)

**What it does**: At session end, writes all learnings extracted by `extract_learnings.py` to the SQLite database. Also triggers FTS5 index rebuild.

**Persistence**: Only at Stop event — learnings are not written mid-session. This batches writes and avoids partial writes from interrupted sessions.

## Database

**Location**: `~/.claude/data/knowledge-db/knowledge.db`

**Schema**:
```sql
CREATE TABLE learnings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,          -- ISO 8601 UTC
    session_id  TEXT,
    project     TEXT,                   -- inferred from cwd basename
    category    TEXT,                   -- LEARNED | PATTERN | INVESTIGATION
    content     TEXT NOT NULL,          -- the learning text
    tags        TEXT,                   -- comma-separated
    source_tool TEXT                    -- which tool triggered extraction
);

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE learnings_fts USING fts5(
    content,
    tags,
    content='learnings',
    content_rowid='id'
);
```

**Categories**:
- `LEARNED` — concrete facts discovered during a session
- `PATTERN` — recurring patterns or best practices observed
- `INVESTIGATION` — findings from research or debugging

## Manual Queries

Direct SQLite access:
```bash
# Count all learnings
sqlite3 ~/.claude/data/knowledge-db/knowledge.db "SELECT count(*) FROM learnings;"

# Full-text search
sqlite3 ~/.claude/data/knowledge-db/knowledge.db \
  "SELECT content FROM learnings_fts WHERE learnings_fts MATCH 'circuit breaker' LIMIT 5;"

# Recent learnings
sqlite3 ~/.claude/data/knowledge-db/knowledge.db \
  "SELECT timestamp, category, content FROM learnings ORDER BY timestamp DESC LIMIT 10;"

# By project
sqlite3 ~/.claude/data/knowledge-db/knowledge.db \
  "SELECT content FROM learnings WHERE project = 'claude-agentic-framework' LIMIT 10;"
```

Or use the `knowledge-db` skill for guided queries:
```
/knowledge-db search "circuit breaker"
/knowledge-db add "Important pattern: always stub hooks before deleting"
```

## Tuning

If inject_relevant is injecting irrelevant or too many learnings:
- Reduce `max_injections` (fewer learnings per session)
- Increase `relevance_threshold` (stricter matching)
- Reduce `lookback_days` (only recent learnings)

If nothing is being injected:
- Check DB has entries: `sqlite3 ~/.claude/data/knowledge-db/knowledge.db "SELECT count(*) FROM learnings;"`
- Reduce `relevance_threshold` to 0.0 to force all matches
- Check if `enabled: true` in config

## Hook Registration

Both `extract_learnings.py` and `store_learnings.py` are registered in `templates/settings.json.template`.
`inject_relevant.py` runs at `SessionStart`.

To disable the pipeline entirely, set `enabled: false` in `~/.claude/knowledge_pipeline.yaml` for the relevant stage.
