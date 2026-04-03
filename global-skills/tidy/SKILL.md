---
name: tidy
version: 2.0.0
description: "Project-adaptive session-end cleanup and organization skill. Reads the project's CLAUDE.md structure to learn where files belong, then detects misplaced files of ALL types, enforces naming conventions, moves files to proper directories, archives obsolete content, and updates project docs. Works in any project — not just the framework repo. Use at end of session, before commit/push, or when user says 'clean up', 'organize', 'tidy up', 'fix file structure'."
user-invocable: true
---

# Tidy — Session Cleanup & Organization

**Project-adaptive** cleanup skill. Reads the project's `CLAUDE.md` (or `README.md`) structure section to learn where files belong, then detects misplaced files of ALL types, enforces naming conventions, archives stale content, and updates documentation. Works in any project — not hardcoded to one repo layout. Designed to run at session end or before commit/push.

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
4. **Never touch protected files in root** — The following always belong in root and must never be moved:
   - **Universal**: `README.md`, `CLAUDE.md`, `.gitignore`, `.DS_Store`, `Makefile`, `Dockerfile`, `justfile`, `LICENSE`
   - **Python**: `pyproject.toml`, `uv.lock`, `setup.py`, `setup.cfg`, `requirements.txt`, `*.toml` (root-level), `*.lock` (root-level)
   - **Rust**: `Cargo.toml`, `Cargo.lock`
   - **Node**: `package.json`, `package-lock.json`, `yarn.lock`, `tsconfig.json`
   - **Framework-specific**: `ADMIN.md`, `QUICKSTART.md`, `FRAMEWORK_REFERENCE.md`, `install.sh`, `uninstall.sh`
   - **Entry points**: any file explicitly listed in CLAUDE.md's structure as belonging in root (e.g., `bot.py`, `monitor.py`, `dashboard.py`, `app.py`, `main.py`, `manage.py`)
   - **Dotfiles**: any file starting with `.` (e.g., `.env`, `.editorconfig`, `.prettierrc`)
   
   During Project Layout Discovery (Phase 1), build the full protected list by merging these defaults with files the project's CLAUDE.md explicitly places in root.
5. **Never delete without archiving** — Obsolete files go to `archive/YYYY-MM-DD/` with a manifest, never straight to deletion.
6. **Atomic operations** — If any file move fails, roll back all moves in that batch. Use git stash as a safety net before applying.
9. **Always write a change log** — Every tidy run that modifies files MUST write a log to `logs/tidy/`. This is non-negotiable, even for `--apply` runs. Ensure `logs/` is in `.gitignore`.
7. **No silent overwrites** — If a destination file already exists, STOP and ask the user. Never overwrite.
8. **Separate move commits from edit commits** — If `/commit` follows `/tidy`, the move-only changes should be one commit. Content edits (doc updates) should be a separate commit. This preserves `git log --follow` history tracking.
9. **Scan CI/CD files** — Check `.github/workflows/`, `Makefile`, `Dockerfile`, `justfile` for references to moved files. Flag but don't auto-fix — CI changes need human review.

---

## Workflow

### Phase 1: Detect & Analyze

#### Project Layout Discovery

Before scanning for misplaced files, discover the project's intended structure. This makes `/tidy` work in ANY project, not just the framework repo.

**Step 1: Read the project's structure definition**

Check for a `## Structure` section in `CLAUDE.md` (preferred) or `README.md`:

```bash
# Try CLAUDE.md first, then README.md
for doc in CLAUDE.md README.md; do
  if [ -f "$doc" ]; then
    # Extract the Structure section (between ## Structure and the next ## heading)
    sed -n '/^## Structure/,/^## [^S]/p' "$doc" | head -80
    break
  fi
done
```

From the structure section, extract:
1. **Directory names and their purposes** (e.g., `src/strategy/` → strategy source files, `Data/` → data files, `docs/` → documentation)
2. **Files explicitly listed as root-level** (e.g., `bot.py`, `monitor.py`, `dashboard.py`, `app.py`, `analysis.py`) — these are protected
3. **File-to-directory routing map**: which file patterns belong in which directories

**Step 2: If no structure section exists, infer from existing directories**

```bash
# Discover project layout from existing directories
ls -1d */ 2>/dev/null | while read dir; do
  dir="${dir%/}"
  case "$dir" in
    src)       echo "ROUTE: *.py source → src/" ;;
    analysis)  echo "ROUTE: analysis scripts/results → analysis/" ;;
    docs)      echo "ROUTE: documentation → docs/" ;;
    tests)     echo "ROUTE: test files → tests/" ;;
    Data|data) echo "ROUTE: data files (*.csv, *.parquet, *.xlsx) → $dir/" ;;
    logs)      echo "ROUTE: log files → logs/" ;;
    assets|images) echo "ROUTE: images/media → $dir/" ;;
    reports|output) echo "ROUTE: output/reports → $dir/" ;;
    scripts)   echo "ROUTE: utility scripts → scripts/" ;;
    deploy)    echo "ROUTE: deployment files → deploy/" ;;
    # Framework-specific directories
    global-agents|global-skills|global-commands|global-hooks) echo "ROUTE: framework $dir → $dir/" ;;
    apps|guides|templates|archive) echo "ROUTE: $dir content → $dir/" ;;
  esac
done
```

**Step 3: Build the protected files list**

Merge universal defaults + project-specific root files from CLAUDE.md:

```bash
# Universal protected files (always safe in root)
PROTECTED="README.md CLAUDE.md .gitignore .DS_Store Makefile Dockerfile justfile LICENSE"
PROTECTED="$PROTECTED pyproject.toml uv.lock setup.py setup.cfg requirements.txt"
PROTECTED="$PROTECTED Cargo.toml Cargo.lock package.json package-lock.json yarn.lock tsconfig.json"
# Framework-specific
PROTECTED="$PROTECTED ADMIN.md QUICKSTART.md FRAMEWORK_REFERENCE.md install.sh uninstall.sh"

# Add files from CLAUDE.md that are explicitly listed at root level
# (Parse the structure section for files without a directory prefix)
# Example: bot.py, monitor.py, dashboard.py, app.py, analysis.py
```

Store the routing map and protected list for use in Phase 2.

---

#### Detection Scans

If a `tidy_analyzer.py` script exists for the project, run it first:

```bash
# Framework-specific analyzer (only if it exists)
[ -f global-skills/tidy/tidy_analyzer.py ] && uv run global-skills/tidy/tidy_analyzer.py --verbose
```

Then scan the repo manually. Run these in parallel:

**1a. Find ALL misplaced files in root**

Scan every file type — not just `.py` and `.md`:

```bash
# Find ALL files in root that aren't directories, dotfiles, or protected
ls -1 . | while read f; do
  [ -d "$f" ] && continue              # Skip directories
  [[ "$f" == .* ]] && continue          # Skip dotfiles
  
  # Skip universal protected files
  case "$f" in
    README.md|CLAUDE.md|.gitignore|Makefile|Dockerfile|justfile|LICENSE) continue;;
    pyproject.toml|uv.lock|setup.py|setup.cfg|requirements.txt) continue;;
    Cargo.toml|Cargo.lock|package.json|package-lock.json|yarn.lock|tsconfig.json) continue;;
    ADMIN.md|QUICKSTART.md|FRAMEWORK_REFERENCE.md|install.sh|uninstall.sh) continue;;
    *.toml|*.lock) continue;;           # Root-level config files
  esac
  
  # Skip files explicitly listed in CLAUDE.md structure as root files
  # (populated from Project Layout Discovery above)
  # Example: bot.py, monitor.py, dashboard.py, app.py, analysis.py
  
  # Report as misplaced with file type info
  mime=$(file -b --mime-type "$f" 2>/dev/null || echo "unknown")
  echo "MISPLACED: $f (type: $mime)"
done
```

**1b. Find naming convention violations**

Adapt to project type — only check framework conventions in framework repos:

```bash
# Framework convention check (only if global-* dirs exist)
if ls -d global-agents global-skills global-commands global-hooks 2>/dev/null | head -1 >/dev/null; then
  for dir in global-agents global-commands global-hooks global-skills; do
    [ -d "$dir" ] || continue
    find "$dir" -maxdepth 1 -type d | while read d; do
      base=$(basename "$d")
      if echo "$base" | grep -qE '[A-Z_]'; then
        echo "NAMING: $d (should be kebab-case)"
      fi
    done
  done

  find global-skills global-agents global-commands -maxdepth 2 -name '*[A-Z _]*' \
    -not -name 'SKILL.md' -not -name 'README.md' -not -name '*.py' -not -name '__pycache__' 2>/dev/null
fi

# Universal: find __pycache__ directories (always safe to flag)
find . -maxdepth 4 -type d -name '__pycache__' -not -path './.git/*' 2>/dev/null
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

### Project Type
- Layout source: CLAUDE.md `## Structure` section (or inferred from directories)
- Detected directories: src/, Data/, docs/, tests/, deploy/, assets/
- Protected root files: bot.py, monitor.py, dashboard.py, app.py, analysis.py, ...

### Misplaced Files (root)
- `results_2026-03-15.csv` → should be `Data/` (data file)
- `backtest_report.html` → should be `analysis/` or `reports/` (report)
- `new_agent.md` → should be `global-agents/new-agent.md` (framework agent)
- `my_script.py` → should be `scripts/my-script.py` (utility script)

### Cleanup Targets
- `__pycache__/` (3 found) → delete
- `*.pyc` (5 found) → delete

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

For each misplaced or misnamed file, determine the correct destination using a three-tier routing system:

#### Tier 1: CLAUDE.md-Informed Routing (highest priority)

If Project Layout Discovery found a `## Structure` section, use it. The structure section defines where files belong in THIS project. Examples:

- If CLAUDE.md says `src/strategy/` contains strategy files → route strategy `.py` files there
- If CLAUDE.md says `Data/cache/` contains parquet files → route `.parquet` files there
- If CLAUDE.md says `docs/` contains documentation → route `.md` docs there
- If CLAUDE.md says `assets/` contains CSS files → route `.css` files there
- If CLAUDE.md says `deploy/` contains Docker files → route `Dockerfile.*` there

#### Tier 2: Extension-Based Heuristics (universal defaults)

For file types not covered by CLAUDE.md, use these universal heuristics. Target the first existing directory in each list:

| File Pattern | Target Directory (first existing) | Notes |
|---|---|---|
| `*.csv`, `*.parquet`, `*.xlsx`, `*.xls` | `Data/` → `data/` → `output/` | Data files |
| `*.json` (results/output, not config) | `analysis/` → `output/` → `data/` | Config `.json` stays in root (see protected) |
| `*.html` (reports) | `analysis/` → `reports/` → `output/` | Report/visualization output |
| `*.txt` (reports/output) | `docs/` → `reports/` → `output/` | Not READMEs or config |
| `*.png`, `*.jpg`, `*.jpeg`, `*.svg`, `*.gif` | `analysis/` → `assets/` → `images/` → `static/` | Visualization/media files |
| `*.log` | `logs/` | Log files always go to logs/ |
| `*.pdf` | `docs/` → `reports/` → `output/` | Document/report PDFs |
| `__pycache__/`, `*.pyc` | **DELETE** | Always safe to remove — never move |
| `.DS_Store` (in subdirs) | **DELETE** | macOS artifact — safe to remove everywhere |
| `*.test.*`, `*_test.*`, `test_*` | `tests/` | Test files |

#### Tier 3: Framework-Specific Routing (only in framework repos)

These rules apply only when `global-agents/`, `global-skills/`, etc. directories exist:

| File Pattern | Destination |
|---|---|
| `*.md` with agent frontmatter (`model:`, `description:`) | `global-agents/` |
| `*.md` with skill frontmatter (`name:`, `version:`) | `global-skills/<name>/SKILL.md` |
| `*.md` with command structure (`# /command`, `## Usage`) | `global-commands/` |
| `*.py` with hook patterns (`tool_input`, `hook_event`) | `global-hooks/framework/` (ask user for subdirectory) |
| `*.py` scripts/utilities | `scripts/` |
| `*.md` documentation/guides | `docs/` or `guides/` (ask if ambiguous) |
| `*.yaml`/`*.json` config | `data/` or `templates/` |

#### Routing Decision Flow

For each misplaced file:
1. **Check Tier 1**: Does CLAUDE.md's structure section indicate where this file type goes? → Use that.
2. **Check Tier 2**: Does the extension match a universal heuristic? → Use the first existing target directory.
3. **Check Tier 3**: Is this a framework repo with `global-*` dirs? → Use framework-specific rules.
4. **Ambiguous**: If no rule matches or multiple rules conflict → **ask the user**. Never guess.

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

Adapt to the project type:
```bash
# Framework repo: recount hooks, agents, commands, skills
if [ -d global-agents ]; then
  agent_count=$(ls -1 global-agents/*.md 2>/dev/null | wc -l | tr -d ' ')
  command_count=$(ls -1 global-commands/*.md 2>/dev/null | wc -l | tr -d ' ')
  skill_count=$(ls -1d global-skills/*/SKILL.md 2>/dev/null | wc -l | tr -d ' ')
fi

# Any project: update directory listings and file counts
# If files were moved into new directories, add those directories to the Structure section
# If files were removed from directories, update counts
```
- Update file counts and directory listings to reflect moves
- Add any new directories that were created during tidy
- For non-framework projects: update the structure tree if files were moved to new locations

**4b. README.md** — Update if it references project structure:
```bash
# Framework: use doc generator if available
[ -f scripts/generate_docs.py ] && uv run scripts/generate_docs.py

# Any project: if README.md has a structure/layout section, update it to match reality
```
If the generator doesn't exist or doesn't cover new content, manually update relevant sections.

**4c. PROJECT_CONTEXT.md** — Update the cached context (if it exists):
- If `/prime` skill exists, suggest running `/prime --force` to regenerate
- Otherwise, update the directory structure and file counts manually
- Skip silently if this file doesn't exist in the project

**4d. FACTS.md** — Add/update structural facts (if it exists):
```
CONFIRMED: [date] — New skill/agent/hook added: <name> at <path>
PATHS: [date] — <name> moved from <old> to <new>
```
- Remove stale PATHS entries that reference old locations
- Skip silently if this file doesn't exist in the project

**4e. MEMORY.md** — Add session summary entry (if it exists):
```
- [Tidy: YYYY-MM-DD](memory_file.md) — Moved N files, archived M, updated K docs
```
- Skip silently if this file doesn't exist in the project

**4f. model_tiers.yaml** — If new agents were added, check they have a model tier entry. (Framework-only — skip if file doesn't exist.)

**4g. settings.json.template** — If hooks were moved, update their paths in the template (framework-only):
```bash
# Only if the template exists
if [ -f templates/settings.json.template ]; then
  grep -oP '__REPO_DIR__/[^"]+' templates/settings.json.template | while read p; do
    resolved="${p/__REPO_DIR__/.}"
    [ -f "$resolved" ] || echo "BROKEN HOOK PATH: $p"
  done
fi
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

2. **Verify hook paths resolve** (framework-only — skip if template doesn't exist):
   ```bash
   if [ -f templates/settings.json.template ]; then
     grep -oP '__REPO_DIR__/[^"]+' templates/settings.json.template | while read p; do
       resolved="${p/__REPO_DIR__/.}"
       [ -f "$resolved" ] || echo "BROKEN: $p"
     done
   fi
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

### Example 5: Non-Framework Project (e.g., Python Trading Engine)

User: `/tidy` (in a project like `/Users/tomkwon/Documents/rn1/`)

1. **Project Layout Discovery**: Reads `CLAUDE.md` `## Structure` section, learns:
   - `src/` → Python source, `Data/` → data files, `docs/` → documentation
   - `bot.py`, `monitor.py`, `dashboard.py`, `app.py`, `analysis.py` are root entry points (protected)
   - `assets/` → CSS files, `deploy/` → deployment files
2. Phase 1 scans ALL root files and detects:
   ```
   MISPLACED: backtest_results_2026-03-15.csv → Data/ (data file, Tier 2 heuristic)
   MISPLACED: strategy_report.html → analysis/ (report, Tier 2 heuristic)
   MISPLACED: debug_output.txt → docs/ or logs/ (ask user)
   MISPLACED: pnl_chart.png → analysis/ (visualization, Tier 2 heuristic)
   CLEANUP: __pycache__/ (4 found) → delete
   CLEANUP: src/strategy/__pycache__/ → delete
   PROTECTED: bot.py (listed in CLAUDE.md as root entry point — skip)
   PROTECTED: pyproject.toml (universal protected — skip)
   ```
3. Shows dry-run plan, user confirms
4. Moves files, deletes `__pycache__/` dirs, updates CLAUDE.md structure if needed
5. Skips framework-specific steps (no `global-*` dirs, no `settings.json.template`, no `model_tiers.yaml`)

### Example 6: Project Without CLAUDE.md

User: `/tidy` (in a project with no CLAUDE.md)

1. **Project Layout Discovery**: No CLAUDE.md found, falls back to directory inference:
   - `src/` exists → Python source goes there
   - `tests/` exists → test files go there
   - `data/` exists → data files go there
   - No `analysis/` or `reports/` → would need to create or ask user
2. Phase 1 detects stray files using Tier 2 heuristics
3. For files with no clear destination, asks user before proposing a move
4. Proceeds with standard Phase 2-6 workflow

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
