# Tidy Change-Log Format

Log location: `logs/tidy/YYYY-MM-DD-HHMMSS.md`

```bash
mkdir -p logs/tidy
```

Write with the Write tool using this template:

```markdown
# Tidy Log — YYYY-MM-DD HH:MM:SS

## Session Info
- **Git branch**: (current branch)
- **Git stash ref**: `tidy-backup-YYYYMMDD-HHMMSS` (from Phase 2 safety snapshot)
- **Commit before tidy**: (short SHA from `git rev-parse --short HEAD`)

## Actions Performed

### Files Moved
| # | Source | Destination | Method | References Updated |
|---|--------|-------------|--------|--------------------|
| 1 | `old/path.md` | `new/path.md` | `git mv` | 3 |

### Files Renamed
| # | Old Name | New Name | Reason |
|---|----------|----------|--------|
| 1 | `MySkill/` | `my-skill/` | kebab-case convention |

### Files Archived
| # | Source | Archive Path | Reason |
|---|--------|-------------|--------|
| 1 | `docs/old-guide.md` | `archive/2026-04-01/old-guide.md` | 120d stale, 0 refs |

### Documentation Updated
- `CLAUDE.md` — skill count 9→10, agent count 8→9
- `README.md` — regenerated via generate_docs.py
- `FACTS.md` — added 2 PATHS entries

### References Auto-Updated
| # | File | Line | Old Reference | New Reference |
|---|------|------|---------------|---------------|
| 1 | `install.sh` | 45 | `my_script.py` | `scripts/my-script.py` |

## Rollback

To undo ALL changes from this tidy run:
\```bash
# Option 1: Full rollback via stash (if no commits made yet)
git checkout -- .
git stash pop

# Option 2: Revert to pre-tidy commit
git reset --soft <pre-tidy-sha>

# Option 3: Selective — reverse a single move
git mv "new/path.md" "old/path.md"
\```

## Warnings
- (any references that couldn't be auto-updated)
- (any CI/CD files that need manual review)
```

## Rules

1. **Always write the log** — even on `--apply` runs with no dry-run confirmation.
2. **Log before validation** — so if validation catches a problem, the log already exists for debugging.
3. **Include the git stash ref** — this is the fastest rollback path.
4. **Empty sections are fine** — if nothing was archived, keep the "Files Archived" header with "(none)" so the log format is consistent.
5. **Never delete old logs** — they accumulate in `logs/tidy/` as a full history. The directory should be gitignored (add to `.gitignore` if not present).
6. **Print the log path** — at the end of the tidy run, always show: `Log saved to: logs/tidy/YYYY-MM-DD-HHMMSS.md`
