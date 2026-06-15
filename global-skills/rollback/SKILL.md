---
name: rollback
description: Automated rollback after orchestration failure. Reads the plan file for GIT_ROLLBACK_BASE, reverts each changed file cleanly, and reports what was undone. Called by the orchestrator on escalation — also invocable manually.
user-invocable: true
---

Perform a clean rollback of changes made during a failed orchestration session.

## Step 1: Find the rollback base

Orchestration runs record their pre-work git hash at `~/.caf/orch/<orch_id>/rollback_base`.

If an orch_id is provided in args (e.g. `/rollback orch_1234567890`), read `~/.caf/orch/<orch_id>/rollback_base`.

If no orch_id, find the most recent run:
```bash
ls -td ~/.caf/orch/*/ 2>/dev/null | head -1   # newest orch dir
cat ~/.caf/orch/<orch_id>/rollback_base         # the GIT_ROLLBACK_BASE hash
```

Treat the single hash in `rollback_base` as `GIT_ROLLBACK_BASE` — the git hash recorded before work began. The `<orch_id>` directory name is the session id (used for cost reporting); `~/.caf/orch/<orch_id>/results/` shows what each builder changed.

## Step 2: Check current state

```bash
git status --short
git diff --stat HEAD
```

If the working tree is clean (no changes since rollback base), report: "No changes to roll back. Working tree is already clean."

## Step 3: Identify what changed

```bash
git diff --name-only {GIT_ROLLBACK_BASE}..HEAD
```

List the files. If more than 10 files changed, pause and show the list to the user before proceeding — this is a large rollback.

## Step 4: Execute rollback

**Preferred: per-file revert** (safer than `reset --hard` — preserves unrelated work)
```bash
git checkout {GIT_ROLLBACK_BASE} -- {file1} {file2} ...
```

Only use `git reset --hard {GIT_ROLLBACK_BASE}` if:
- The user explicitly asked for a full reset
- OR every changed file was part of the failed session (nothing unrelated was modified)

## Step 5: Report

```markdown
## Rollback Report

**Session**: {SESSION_ID}
**Rolled back to**: {GIT_ROLLBACK_BASE} ({git log --oneline -1 {GIT_ROLLBACK_BASE}})

### Files Restored
- /path/to/file — restored to pre-session state
[list]

### Files Preserved (unrelated changes)
- /path/to/file — not part of this session, left untouched
[list if any]

### State After Rollback
{git status --short output}

To redo from scratch: `/orchestrate "{original task}"`
```

## Notes

- If `GIT_ROLLBACK_BASE` is not found in any plan file, report this explicitly and suggest `git log --oneline -10` so the user can find the right hash manually
- Never force-push or touch any remote ref
- Never roll back CLAUDE.md, FACTS.md, or .claude/ directory contents — these are framework state, not session output
