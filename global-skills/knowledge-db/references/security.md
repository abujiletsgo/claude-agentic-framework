# Knowledge DB — Security Reference

## File Permissions

All database and log files are created with **mode 600** (owner read/write only):

- `knowledge.db` — SQLite database file
- `knowledge.jsonl` — Append-only durability log

Permissions are enforced on every database open and every JSONL append operation.

## Import Path Restrictions

The `import-json` command validates file paths before reading. Imports are restricted to:

| Allowed Directory | Purpose |
|-------------------|---------|
| `~/.claude/data/` | Primary data storage |
| `~/.claude/` | Claude configuration directory |
| Current working directory | Convenience for local files |

Blocked:

- **Path traversal**: Any path containing `..` is rejected
- **Absolute paths outside allowed dirs**: e.g., `/etc/passwd` is rejected
- **Non-regular files**: Directories, symlinks to disallowed locations, device files

Examples of blocked imports:
```bash
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py import-json /etc/passwd
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py import-json ../../etc/shadow
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py import-json /tmp/malicious.json
```

## Export Limits

The `export` command has a default limit of **10,000 entries** to prevent unbounded memory usage. Use `--limit N` to adjust:

```bash
# Default: max 10,000 entries
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py export

# Custom limit
uv run ~/.claude/skills/knowledge-db/scripts/knowledge_cli.py export --limit 50000
```

A warning is printed to stderr when the limit is reached.

## FTS5 Tag Wildcards

Tag filters in `search` use SQL `LIKE` with `%` wildcards for substring matching. Behavior:

- Tag filters are **substring matches**, not exact matches — `sec` matches `security`, `insecure`, etc.
- Use full tag names for precise filtering (`--tags "security"`, not `--tags "sec"`)
- The `%` character in user-provided tags passes through to SQL LIKE — harmless (widens match only) but may produce unexpected results
