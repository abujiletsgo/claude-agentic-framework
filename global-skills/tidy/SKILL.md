---
name: tidy
version: 1.0.0
description: "Session-end cleanup and organization skill. Detects misplaced files, enforces naming conventions, moves files to proper directories, archives obsolete content, and updates all project docs (CLAUDE.md, README.md, FACTS.md, MEMORY.md, PROJECT_CONTEXT.md). Use at end of session, before commit/push, or when user says 'clean up', 'organize', 'tidy up', 'fix file structure'."
user-invocable: true
---

# Tidy — Session Cleanup & Organization

Detects what changed this session, enforces the project's file structure and naming conventions, archives stale content, and updates all documentation to reflect the current state. Designed to run at session end or before commit/push.

## When to Use

- User says: "tidy up", "clean up the repo", "organize files", "fix the structure", `/tidy`
- Before committing/pushing significant changes (invoke manually or via `/tidy --pre-commit`)
- End of a session where new files/directories were created
- After scaffolding a new feature that added files in the wrong place
- When root directory has accumulated stray files

## Sub-commands

```
/tidy              # Full run: detect → organize → archive → update docs (dry-run first)
/tidy --apply      # Skip dry-run confirmation, apply immediately
/tidy --detect     # Only Phase 1: show what's misplaced, don't change anything
/tidy --docs-only  # Only Phase 4: update documentation without moving files
/tidy --archive    # Only Phase 3: archive obsolete content
/tidy --log        # Show the most recent tidy log (or list all logs)
```

---

## Safety Rules (CRITICAL)

1. **Dry-run by default** — Always show a full plan of changes before executing. Require explicit confirmation (or `--apply` flag) before moving/renaming/deleting anything.
2. **Git-aware moves** — Use `git mv` for tracked files so history is preserved. Never `mv` a tracked file.
3. **Reference scanning** — Before moving a file, grep for all references to its current path across the repo. Show broken-reference warnings in the plan. Update references automatically where safe (markdown links, YAML paths, settings.json paths).
4. **Never touch protected files in root** — These belong in root: `README.md`, `CLAUDE.md`, `ADMIN.md`, `QUICKSTART.md`, `FRAMEWORK_REFERENCE.md`, `install.sh`, `uninstall.sh`, `justfile`, `.gitignore`, `.DS_Store`. Do not move them.
5. **Never delete without archiving** — Obsolete files go to `archive/YYYY-MM-DD/` with a manifest, never straight to deletion.
6. **Atomic operations** — If any file move fails, roll back all moves in that batch. Use git stash as a safety net before applying.
9. **Always write a change log** — Every tidy run that modifies files MUST write a log to `logs/tidy/`. This is non-negotiable, even for `--apply` runs. Ensure `logs/` is in `.gitignore`.
7. **No silent overwrites** — If a destination file already exists, STOP and ask the user. Never overwrite.
8. **Separate move commits from edit commits** — If `/commit` follows `/tidy`, the move-only changes should be one commit. Content edits (doc updates) should be a separate commit. This preserves `git log --follow` history tracking.
9. **Scan CI/CD files** — Check `.github/workflows/`, `Makefile`, `Dockerfile`, `justfile` for references to moved files. Flag but don't auto-fix — CI changes need human review.

---

## Workflow

### Phase 1: Detect & Analyze

First, run the analyzer script to get a structured JSON report:

```bash
uv run global-skills/tidy/tidy_analyzer.py --verbose
```

This detects misplaced files, naming violations, untracked files, stale candidates, and doc count drift automatically.

For deeper analysis, also scan the repo manually. Run these in parallel:

**1a. Find misplaced files in root**
```bash
# List all files in root that don't belong there
ls -1 . | while read f; do
  # Skip known root files and directories
  case "$f" in
    README.md|CLAUDE.md|ADMIN.md|QUICKSTART.md|FRAMEWORK_REFERENCE.md) continue;;
    install.sh|uninstall.sh|justfile|.gitignore|.DS_Store|.git|.claude) continue;;
    apps|archive|data|docs|global-*|guides|scripts|templates|tests) continue;;
    *) echo "MISPLACED: $f";;
  esac
done
```

**1b. Find naming convention violations**
```bash
# Framework convention: kebab-case for directories, kebab-case for skill/agent/command dirs
# Check global-* subdirectories for violations
for dir in global-agents global-commands global-hooks global-skills; do
  find "$dir" -maxdepth 1 -type d | while read d; do
    base=$(basename "$d")
    if echo "$base" | grep -qE '[A-Z_]'; then
      echo "NAMING: $d (should be kebab-case)"
    fi
  done
done

# Check for files with spaces, uppercase, or underscores where kebab-case expected
find global-skills global-agents global-commands -maxdepth 2 -name '*[A-Z _]*' -not -name 'SKILL.md' -not -name 'README.md' -not -name '*.py' -not -name '__pycache__'
```

**1c. Detect new files from this session**
```bash
# Files created/modified in the current session (last 4 hours as heuristic)
find . -maxdepth 3 -newer .git/index -not -path './.git/*' -not -path './node_modules/*' -not -path './__pycache__/*' -type f 2>/dev/null

# Untracked files (strong signal for "new this session")
git ls-files --others --exclude-standard
```

**1d. Detect potentially obsolete files**
```bash
# Files not modified in 90+ days that aren't in archive/
find . -maxdepth 3 -type f -mtime +90 -not -path './.git/*' -not -path './archive/*' -not -path './node_modules/*' | head -20
```

Output a **Tidy Report**:
```
## Tidy Report

### Misplaced Files (root)
- `new_agent.md` → should be `global-agents/new-agent.md`
- `my_script.py` → should be `scripts/my-script.py`

### Naming Violations
- `global-skills/MySkill/` → should be `global-skills/my-skill/`

### New This Session (untracked)
- `global-agents/solve.md` (new)
- `global-skills/solve/SKILL.md` (new)

### Candidates for Archive
- `docs/old-migration-guide.md` (last modified 120 days ago)

### Reference Impact
- Moving `new_agent.md` would break 0 references
- Moving `my_script.py` would break 2 references:
  - `install.sh:45` — `source my_script.py`
  - `README.md:120` — `see my_script.py`
```

If `--detect` flag: stop here. Display report and exit.

---

### Phase 2: Organize & Rename

For each misplaced or misnamed file, determine the correct destination:

**Routing rules** (in priority order):
| File Pattern | Destination |
|---|---|
| `*.md` with agent frontmatter (`model:`, `description:`) | `global-agents/` |
| `*.md` with skill frontmatter (`name:`, `version:`) | `global-skills/<name>/SKILL.md` |
| `*.md` with command structure (`# /command`, `## Usage`) | `global-commands/` |
| `*.py` with hook patterns (`tool_input`, `hook_event`) | `global-hooks/framework/` (ask user for subdirectory) |
| `*.py` scripts/utilities | `scripts/` |
| `*.md` documentation/guides | `docs/` or `guides/` (ask if ambiguous) |
| `*.yaml`/`*.json` config | `data/` or `templates/` |
| `*.test.*`, `*_test.*`, `test_*` | `tests/` |

**Naming normalization**:
- Directories: `kebab-case` (lowercase, hyphens)
- Python files: `snake_case.py`
- Markdown files: `kebab-case.md` (except `README.md`, `SKILL.md`, `CLAUDE.md`)
- YAML/JSON: `kebab-case.yaml`

**For each move:**
1. Show: `source → destination` with reason
2. Scan for references: `grep -rn "source_filename" . --include='*.md' --include='*.py' --include='*.sh' --include='*.yaml' --include='*.json'`
3. List references that will be auto-updated
4. Flag references that need manual review (e.g., in compiled/binary files)

If not `--apply`: show the full plan and ask for confirmation.

**Execute moves:**
```bash
# Safety snapshot
git stash push -m "tidy-backup-$(date +%Y%m%d-%H%M%S)" --include-untracked

# For tracked files
git mv "old/path" "new/path"

# For untracked files
mkdir -p "$(dirname new/path)"
mv "old/path" "new/path"
git add "new/path"

# Update references
# For each reference found, use Edit tool to update the path
```

---

### Phase 3: Archive Obsolete Content

For files identified as obsolete:

1. Create dated archive directory:
   ```bash
   mkdir -p archive/$(date +%Y-%m-%d)
   ```

2. Move files with manifest:
   ```bash
   git mv "obsolete/file.md" "archive/$(date +%Y-%m-%d)/file.md"
   ```

3. Write `archive/YYYY-MM-DD/MANIFEST.md`:
   ```markdown
   # Archive — YYYY-MM-DD

   ## Archived Files
   - `file.md` — Reason: not referenced in 90+ days, superseded by X

   ## How to Restore
   git mv "archive/YYYY-MM-DD/file.md" "original/path/file.md"
   ```

If `--archive` flag: only run this phase.

---

### Phase 4: Update Documentation

After file moves and archiving, update all docs that reference the project structure. Run these updates in parallel where possible:

**4a. CLAUDE.md** — Update the `## Structure` section:
```bash
# Recount hooks, agents, commands, skills
agent_count=$(ls -1 global-agents/*.md 2>/dev/null | wc -l | tr -d ' ')
command_count=$(ls -1 global-commands/*.md 2>/dev/null | wc -l | tr -d ' ')
skill_count=$(ls -1d global-skills/*/SKILL.md 2>/dev/null | wc -l | tr -d ' ')
# Update counts in CLAUDE.md Structure section
```
- Update file counts and directory listings
- Add any new directories that were created
- Update naming conventions if new patterns were established

**4b. README.md** — Regenerate via the framework's doc generator:
```bash
# If scripts/generate_docs.py exists, use it
uv run scripts/generate_docs.py
```
If the generator doesn't cover new content, manually update relevant sections.

**4c. PROJECT_CONTEXT.md** — Update the cached context:
- If `/prime` skill exists, suggest running `/prime --force` to regenerate
- Otherwise, update the directory structure and file counts manually

**4d. FACTS.md** — Add/update structural facts:
```
CONFIRMED: [date] — New skill/agent/hook added: <name> at <path>
PATHS: [date] — <name> moved from <old> to <new>
```
- Remove stale PATHS entries that reference old locations

**4e. MEMORY.md** — Add session summary entry:
```
- [Tidy: YYYY-MM-DD](memory_file.md) — Moved N files, archived M, updated K docs
```

**4f. model_tiers.yaml** — If new agents were added, check they have a model tier entry.

**4g. settings.json.template** — If hooks were moved, update their paths in the template:
```bash
# Verify all hook paths in template still resolve
grep -oP '__REPO_DIR__/[^"]+' templates/settings.json.template | while read p; do
  resolved="${p/__REPO_DIR__/.}"
  [ -f "$resolved" ] || echo "BROKEN HOOK PATH: $p"
done
```

If `--docs-only` flag: only run this phase.

---

### Phase 5: Write Change Log

After all moves, archives, and doc updates — **before** validation — write a timestamped log so every action is traceable and reversible.

**Log location**: `logs/tidy/YYYY-MM-DD-HHMMSS.md`

```bash
mkdir -p logs/tidy
```

**Log format** (write with the Write tool):

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

**Rules for the log:**
1. **Always write the log** — even on `--apply` runs with no dry-run confirmation.
2. **Log before validation** — so if validation catches a problem, the log already exists for debugging.
3. **Include the git stash ref** — this is the fastest rollback path.
4. **Empty sections are fine** — if nothing was archived, keep the "Files Archived" header with "(none)" so the log format is consistent.
5. **Never delete old logs** — they accumulate in `logs/tidy/` as a full history. The directory should be gitignored (add to `.gitignore` if not present).
6. **Print the log path** — at the end of the tidy run, always show: `Log saved to: logs/tidy/YYYY-MM-DD-HHMMSS.md`

---

### Phase 6: Validation

After all changes:

1. **Verify no broken references**:
   ```bash
   # Re-scan for any references to old paths
   for old_path in $MOVED_FILES; do
     hits=$(grep -rn "$old_path" . --include='*.md' --include='*.py' --include='*.sh' --include='*.yaml' --include='*.json' | grep -v archive/ | wc -l)
     [ "$hits" -gt 0 ] && echo "STILL REFERENCED: $old_path ($hits hits)"
   done
   ```

2. **Verify hook paths resolve**:
   ```bash
   grep -oP '__REPO_DIR__/[^"]+' templates/settings.json.template | while read p; do
     resolved="${p/__REPO_DIR__/.}"
     [ -f "$resolved" ] || echo "BROKEN: $p"
   done
   ```

3. **Verify git status is clean** (no unexpected changes):
   ```bash
   git status --short
   git diff --stat
   ```

4. **Show summary**:
   ```
   ## Tidy Complete

   - Files moved: N
   - Files renamed: N
   - Files archived: N
   - References updated: N
   - Docs updated: CLAUDE.md, README.md, FACTS.md
   - Broken references remaining: 0
   - Log saved to: logs/tidy/YYYY-MM-DD-HHMMSS.md

   To rollback: see logs/tidy/YYYY-MM-DD-HHMMSS.md → Rollback section
   Run `git diff --stat` to review all changes.
   Ready to commit with: /commit
   ```

---

## Examples

### Example 1: End of Session Cleanup

User: `/tidy`

1. Phase 1 detects `solve.md` in root (should be `global-agents/solve.md`)
2. Phase 1 detects `global-skills/solve/` was added but CLAUDE.md skill count is stale
3. Shows dry-run plan:
   ```
   MOVE: solve.md → global-agents/solve.md (agent frontmatter detected)
   UPDATE: CLAUDE.md — skill count 9→10, agent count 8→9
   UPDATE: README.md — regenerate via generate_docs.py
   ```
4. User confirms → executes moves and doc updates
5. Shows summary: 1 file moved, 0 archived, 3 docs updated

### Example 2: Pre-Commit Quick Tidy

User: `/tidy --apply`

1. Skips confirmation, directly applies all safe changes
2. Moves misplaced files, updates docs, shows summary
3. User runs `/commit` immediately after

### Example 3: Docs-Only Refresh

User: `/tidy --docs-only`

1. Skips file moves and archiving
2. Recounts agents, skills, commands, hooks
3. Updates CLAUDE.md structure section, README.md, PROJECT_CONTEXT.md
4. Shows what was updated

### Example 4: Detect Only (Safe Audit)

User: `/tidy --detect`

1. Scans entire repo
2. Shows full Tidy Report with all issues found
3. Makes zero changes
4. User can then selectively fix issues

---

## Integration with /commit

When running `/commit`, consider suggesting `/tidy` first if:
- There are untracked files in root
- New directories were created outside standard structure
- File counts in CLAUDE.md are stale

The recommended flow is:
```
/tidy           # Clean up and update docs
/commit         # Commit the organized state
```

---

## Potential Issues & Mitigations (Research-Backed)

| Issue | Severity | Mitigation |
|---|---|---|
| **Broken Python imports** after move | CRITICAL | Scan for `import` and `from ... import` statements referencing the file. Run `ruff check` or `pyright` post-move if available. Flag all import references in dry-run. |
| **Broken TS/JS imports** after move | CRITICAL | Check `tsconfig.json` path aliases, `webpack.config.js`, `package.json` exports. Grep for relative imports. |
| **Hook path invalidation** in settings.json | CRITICAL | After moving any hook file, grep `settings.json.template` for old path. Auto-update `__REPO_DIR__` paths. Require `bash install.sh` after hook moves. |
| **Git history lost** on move+edit in same commit | HIGH | **Commit pure moves separately from edits.** Use `git mv` only. If content changes are also needed, do them in a follow-up commit. |
| **Stale references in .claude/ context files** | HIGH | ARCHITECTURE.md, FACTS.md, PROJECT_CONTEXT.md, MEMORY.md all contain paths. Scan and update all of them. |
| **CI/CD path breakage** | HIGH | Scan `.github/workflows/`, `Makefile`, `Dockerfile`, `justfile` for moved paths. Flag but don't auto-fix CI files. |
| **Archive pit** — archived files still referenced by tests | MEDIUM | Before archiving, check `tests/` directory for references. Archived files get excluded via manifest, not deletion. |
| **Overwriting existing file at destination** | MEDIUM | Check destination exists before every move. STOP and ask on conflict — never overwrite. |
| **User runs `--apply` and regrets it** | LOW | `git stash push --include-untracked` backup created before any changes. Show restore command: `git stash pop`. |
| **Naming convention disagrees with user intent** | LOW | Show proposed names in dry-run. User can reject individual moves. |
| **Doc generator fails or doesn't exist** | LOW | Fall back to manual section updates. Never leave docs half-updated — atomic doc updates or rollback. |
| **Bash scripts with hardcoded relative paths** | MEDIUM | Grep `.sh` files for moved filenames. Bash path breaks silently with no compiler warning — flag prominently. |
