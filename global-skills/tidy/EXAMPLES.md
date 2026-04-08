# Tidy Skill — Examples & Reference

## Examples

### Example 1: End of Session Cleanup

User: `/tidy`

1. Phase 1 detects `solve.md` in root (should be `global-agents/solve.md`)
2. Phase 1 detects `global-skills/solve/` was added but CLAUDE.md skill count is stale
3. Shows dry-run plan:
   ```
   MOVE: solve.md -> global-agents/solve.md (agent frontmatter detected)
   UPDATE: CLAUDE.md -- skill count 9->10, agent count 8->9
   UPDATE: README.md -- regenerate via generate_docs.py
   ```
4. User confirms -> executes moves and doc updates
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
   - `src/` -> Python source, `Data/` -> data files, `docs/` -> documentation
   - `bot.py`, `monitor.py`, `dashboard.py`, `app.py`, `analysis.py` are root entry points (protected)
   - `assets/` -> CSS files, `deploy/` -> deployment files
2. Phase 1 scans ALL root files and detects:
   ```
   MISPLACED: backtest_results_2026-03-15.csv -> Data/ (data file, Tier 2 heuristic)
   MISPLACED: strategy_report.html -> analysis/ (report, Tier 2 heuristic)
   MISPLACED: debug_output.txt -> docs/ or logs/ (ask user)
   MISPLACED: pnl_chart.png -> analysis/ (visualization, Tier 2 heuristic)
   CLEANUP: __pycache__/ (4 found) -> delete
   CLEANUP: src/strategy/__pycache__/ -> delete
   PROTECTED: bot.py (listed in CLAUDE.md as root entry point -- skip)
   PROTECTED: pyproject.toml (universal protected -- skip)
   ```
3. Shows dry-run plan, user confirms
4. Moves files, deletes `__pycache__/` dirs, updates CLAUDE.md structure if needed
5. Skips framework-specific steps (no `global-*` dirs, no `settings.json.template`, no `model_tiers.yaml`)

### Example 6: Project Without CLAUDE.md

User: `/tidy` (in a project with no CLAUDE.md)

1. **Project Layout Discovery**: No CLAUDE.md found, falls back to directory inference:
   - `src/` exists -> Python source goes there
   - `tests/` exists -> test files go there
   - `data/` exists -> data files go there
   - No `analysis/` or `reports/` -> would need to create or ask user
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
| **Archive pit** -- archived files still referenced by tests | MEDIUM | Before archiving, check `tests/` directory for references. Archived files get excluded via manifest, not deletion. |
| **Overwriting existing file at destination** | MEDIUM | Check destination exists before every move. STOP and ask on conflict -- never overwrite. |
| **User runs `--apply` and regrets it** | LOW | `git stash push --include-untracked` backup created before any changes. Show restore command: `git stash pop`. |
| **Naming convention disagrees with user intent** | LOW | Show proposed names in dry-run. User can reject individual moves. |
| **Doc generator fails or doesn't exist** | LOW | Fall back to manual section updates. Never leave docs half-updated -- atomic doc updates or rollback. |
| **Bash scripts with hardcoded relative paths** | MEDIUM | Grep `.sh` files for moved filenames. Bash path breaks silently with no compiler warning -- flag prominently. |
