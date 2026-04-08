# Damage Control

Security hook system that blocks or requires confirmation for destructive operations before they execute.

## What It Does

`unified-damage-control.py` intercepts three tool types:

| Tool | What it checks |
|------|---------------|
| `Bash` | Command string against `bashToolPatterns` |
| `Edit` | Target file path against `zeroAccessPaths` and `readOnlyPaths` |
| `Write` | Target file path against `zeroAccessPaths` and `readOnlyPaths` |

When a match is found:
- **Hard block**: Exits with code 2, stderr fed back to Claude as explanation
- **Confirmation required** (`ask: true`): Outputs a `permissionDecision: ask` response, Claude prompts the user

## Pattern File

All patterns are defined in `patterns.yaml`. The hook reads this file at runtime — no reinstall needed after editing patterns.

```
global-hooks/damage-control/
├── unified-damage-control.py    ← The hook
├── patterns.yaml                ← Pattern definitions (edit this)
└── README.md
```

### Pattern Sections

**`bashToolPatterns`**: Regex patterns matched against the full Bash command string.

```yaml
bashToolPatterns:
  - pattern: '\brm\s+(-[^\s]*)*-[rRf]'
    reason: rm with recursive or force flags

  # Add ask: true for confirmation instead of hard block:
  - pattern: '\bgit\s+stash\s+drop\b'
    reason: Permanently deletes a stash
    ask: true
```

**`zeroAccessPaths`**: Files/directories that cannot be read, written, or deleted. Absolute paths or glob patterns.

```yaml
zeroAccessPaths:
  - "~/.ssh/"
  - ".env"
  - ".env.*"
  - "*.pem"
```

**`readOnlyPaths`**: Files/directories that can be read but not written or deleted.

```yaml
readOnlyPaths:
  - "package-lock.json"
  - "*.lock"
  - "node_modules/"
```

**`noDeletePaths`**: Files/directories that can be read and written but not deleted (Bash tool only).

```yaml
noDeletePaths:
  - "~/.claude/"
  - "CLAUDE.md"
  - "README.md"
```

## What Is Currently Blocked

### Destructive File Operations (hard block)
- `rm -rf`, `rm -r`, `rm --force`, `sudo rm`
- `rmdir --ignore-fail-on-non-empty`

### Permission Escalation (hard block)
- `chmod 777` (world writable)
- Recursive `chown` to root

### Git Destructive Operations (hard block)
- `git reset --hard`
- `git push --force` (but NOT `--force-with-lease`)
- `git push -f`
- `git clean -fd`
- `git filter-branch`
- `git stash clear`
- `git reflog expire`
- `git gc --prune=now`

### Git Operations (confirmation required)
- `git checkout -- .` — discards uncommitted changes
- `git restore .` — discards uncommitted changes
- `git stash drop` — deletes a stash
- `git branch -D` — force-deletes branch
- `git push origin --delete` — deletes remote branch

### Shell Obfuscation (hard block)
- `eval ` — bypasses all pattern matching
- `bash -c ` — string commands bypass pattern matching
- `base64 -d | bash` — encoded command execution
- `find ... -delete` — mass file deletion
- `curl ... | bash` — arbitrary code download/execution
- `python -c "...os.remove..."` — Python destruction
- `xargs ... rm` — mass deletion via piping

### Cloud Destructive Operations (hard block)
AWS, GCP, Firebase, Vercel, Netlify, Cloudflare, Docker, Kubernetes, Heroku, Fly.io, DigitalOcean — see `patterns.yaml` for the full list.

### Database Operations (hard block)
- `TRUNCATE TABLE`, `DROP TABLE`, `DROP DATABASE`
- `DELETE FROM table;` (without WHERE clause)
- `redis-cli FLUSHALL`, `redis-cli FLUSHDB`
- `MongoDB dropDatabase`
- `dropdb`, `mysqladmin drop`

### Infrastructure Teardown (hard block)
- `terraform destroy`
- `pulumi destroy`
- `serverless remove`

## Adding Custom Patterns

Add to `bashToolPatterns` in `patterns.yaml`:

```yaml
bashToolPatterns:
  # Hard block — never allow
  - pattern: '\bmy_dangerous_command\b'
    reason: Description of why this is dangerous

  # Soft block — ask for confirmation
  - pattern: '\bmy_risky_command\b'
    reason: Description of the risk
    ask: true
```

The `pattern` field is a Python regex. Test it:
```bash
python3 -c "import re; print(bool(re.search(r'\bmy_pattern\b', 'test my_pattern here')))"
```

To add a zero-access path:
```yaml
zeroAccessPaths:
  - "path/to/sensitive/file"   # Exact path
  - "*.secret"                 # Glob pattern
  - "~/.config/myapp/"         # Home-relative
```

## Protected Files

`patterns.yaml` itself is in `readOnlyPaths` — the damage control system protects itself from being accidentally overwritten. To modify it, you must do so directly in an editor (not via Claude Code's Write/Edit tools).

## Testing

Simulate a Bash hook call:
```bash
echo '{"tool_name": "Bash", "tool_input": {"command": "rm -rf /tmp/test"}}' | \
  uv run global-hooks/damage-control/unified-damage-control.py
# Should exit 2 with explanation
```

Simulate a Write hook call:
```bash
echo '{"tool_name": "Write", "tool_input": {"file_path": "/home/user/.ssh/id_rsa", "content": "test"}}' | \
  uv run global-hooks/damage-control/unified-damage-control.py
# Should exit 2: zero-access path
```
