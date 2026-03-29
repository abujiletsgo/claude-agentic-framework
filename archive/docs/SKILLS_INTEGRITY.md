# Skills Integrity Checking

The skills.lock system detects unauthorized or accidental modifications to skill files. It works by computing SHA-256 hashes of every file in every skill directory and storing them in a lock file. On session start, the verification hook compares current file hashes against the lock file and reports any discrepancies.

## How It Works

### Lock File Generation

The generator (`scripts/generate_skills_lock.py`) scans the `global-skills/` directory and produces `~/.claude/skills.lock` containing:

- **version**: Lock file format version (currently `1.0.0`)
- **generated_at**: UTC timestamp of generation
- **skills_dir**: Absolute path to the source skills directory
- **skills**: Per-skill mapping of relative file paths to SHA-256 hashes
- **overall_checksum**: Single SHA-256 hash derived from all individual file hashes

### Verification Hook

The hook (`global-hooks/framework/security/verify_skills.py`) runs on `SessionStart` and checks:

1. **Modified files** -- hash differs from lock file
2. **Deleted files** -- present in lock but missing on disk
3. **New files** -- present on disk but not in lock
4. **Missing skills** -- entire skill directory absent
5. **Unlocked skills** -- skill directory present but not in lock file

The hook never blocks execution. It reports warnings as advisory messages.

## Usage

### Generate the Lock File

```bash
# Via justfile (recommended)
just skills-lock

# Direct invocation
python3 scripts/generate_skills_lock.py

# Custom paths
python3 scripts/generate_skills_lock.py /path/to/skills /path/to/output.lock
```

### Verify Skills Manually

```bash
# Via justfile
just skills-verify

# Direct invocation
uv run global-hooks/framework/security/verify_skills.py
```

### Automatic Verification

When registered as a `SessionStart` hook in `settings.json`, verification runs automatically at the start of every Claude session. Add to the `SessionStart` hooks array in `templates/settings.json.template`:

```json
{
  "type": "command",
  "command": "uv run __REPO_DIR__/global-hooks/framework/security/verify_skills.py",
  "timeout": 5,
  "statusMessage": "Verifying skills integrity..."
}
```

## When to Regenerate

Run `just skills-lock` after any of the following:

- Adding a new skill to `global-skills/`
- Modifying any file within an existing skill
- Removing a skill
- After running `install.sh` if skills were updated
- After pulling changes that modify skills

## Handling Warnings

### MODIFIED warning

A file's content has changed since the lock was generated. If the change was intentional (you edited the skill), regenerate the lock. If unexpected, investigate the file for unauthorized changes.

### DELETED warning

A file listed in the lock no longer exists on disk. If you intentionally removed it, regenerate the lock. If unexpected, restore the file from version control.

### NEW FILE warning

A file exists on disk that is not recorded in the lock. This could be a legitimately added file (regenerate the lock) or an injected file (investigate and remove).

### MISSING SKILL warning

An entire skill directory is absent. Verify the symlinks are intact (`ls -la ~/.claude/skills/`) and re-run `install.sh` if needed.

### UNLOCKED SKILL warning

A skill directory exists but has no entry in the lock file. This typically happens after adding a new skill without regenerating the lock. Run `just skills-lock` to include it.

## File Locations

| File | Location |
|------|----------|
| Generator script | `scripts/generate_skills_lock.py` |
| Verification hook | `global-hooks/framework/security/verify_skills.py` |
| Lock file | `~/.claude/skills.lock` |
| Skills source | `global-skills/` (repo) |
| Skills symlinks | `~/.claude/skills/` (installed) |

## Integration with Caddy Skill Auditing

The skills integrity system works alongside the Caddy skill auditor. While `skills.lock` detects unauthorized file changes (tamper detection), the skill auditor scans file contents for security patterns (vulnerability detection). Together they provide:

1. **Tamper detection**: `skills.lock` catches unauthorized modifications
2. **Vulnerability detection**: `audit_skill.py` finds dangerous patterns in skill code
3. **Continuous monitoring**: Both run automatically (session start for integrity, on-demand for auditing)

For a complete security workflow:
```bash
# After modifying or adding skills:
just skills-lock        # Update integrity hashes
just audit-all-skills   # Scan for vulnerabilities
just skills-verify      # Confirm integrity
```

## Security Notes

- The lock file itself is not cryptographically signed. It relies on filesystem permissions for protection.
- The verification hook follows symlinks, so it checks the actual file content regardless of whether skills are symlinked or copied.
- Hidden files, `__pycache__` directories, and `.pyc`/`.pyo` files are excluded from hashing to avoid false positives from runtime artifacts.
- The overall_checksum field provides a quick way to detect any change without comparing individual files.

## Related Documentation

- [SECURITY_BEST_PRACTICES.md](SECURITY_BEST_PRACTICES.md) -- Comprehensive security guide
- [2026_UPGRADE_GUIDE.md](2026_UPGRADE_GUIDE.md) -- Security improvements in the 2026 upgrade
- `global-agents/caddy.md` -- Caddy meta-orchestrator with skill auditing section
