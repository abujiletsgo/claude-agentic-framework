---
name: worktree
version: 1.0.0
description: "Git worktree manager for running multiple Claude Code sessions on the same project simultaneously. Create, list, remove, and clean up worktrees with auto-generated paths and session-open instructions. Trigger when user says 'worktree', 'new session', 'parallel session', 'work on branch in parallel', or '/worktree'."
user-invocable: true
---

# Worktree — Parallel Session Manager

Manage git worktrees so you can run multiple Claude Code sessions on the same project at once — each on its own branch, in its own directory, with full isolation.

## Sub-commands

```
/worktree new <branch>        # Create a new worktree + branch, print open command
/worktree new <branch> <path> # Create at a specific path
/worktree list                # Show all worktrees with branch, path, status
/worktree remove <branch>     # Remove worktree by branch name (safe: checks for uncommitted work)
/worktree clean               # Prune stale/missing worktrees
/worktree status              # Show git status across all active worktrees
/worktree sprint <id>         # Create worktrees for all leads in a sprint, print launch commands
```

If invoked with no sub-command: run `/worktree list`.

---

## Sprint Integration

`/worktree sprint <id>` creates one worktree per lead role defined in the sprint's status.json.

### Behavior

1. Read `/tmp/caf_sprint/<id>/status.json` to get active lead roles
2. For each lead role, create a worktree:
   - Branch: `sprint/<id>/<role>` (e.g., `sprint/abc123/engineering-lead`)
   - Path: `/tmp/caf_sprint/<id>/worktrees/<role>`
3. Print launch commands for each worktree:
   ```
   cd /tmp/caf_sprint/<id>/worktrees/<role> && claude
   ```
4. If no sprint ID found or status.json missing, error with: "No active sprint '<id>'. Run /sprint first."

### Teardown

Sprint worktrees are cleaned up by `bin/tmux-sprint teardown <id>` — this command calls `git worktree remove` for each path under `/tmp/caf_sprint/<id>/worktrees/`. You can also clean them manually with `/worktree remove sprint/<id>/<role>`.

---

## Workflow

### `/worktree new <branch> [path]`

1. **Validate** — check the branch doesn't already have a worktree checked out:
   ```bash
   git worktree list --porcelain | grep "branch refs/heads/<branch>"
   ```
   If it does, stop and tell the user.

2. **Determine path** — if not provided, auto-generate a sibling directory:
   ```bash
   # Rule: ../$(basename $PWD)-<branch>
   # Example: project at ~/Documents/myapp → worktree at ~/Documents/myapp-feature-x
   REPO_ROOT=$(git rev-parse --show-toplevel)
   REPO_NAME=$(basename "$REPO_ROOT")
   PARENT=$(dirname "$REPO_ROOT")
   DEFAULT_PATH="$PARENT/$REPO_NAME-<branch>"
   ```
   Normalize branch name for use in path: replace `/` with `-`, strip leading `-`.

3. **Check if base branch exists** — if `<branch>` doesn't exist yet, create it from current HEAD:
   ```bash
   # If branch doesn't exist: create new branch in worktree
   git worktree add -b <branch> <path>

   # If branch already exists locally (no worktree yet): check it out
   git worktree add <path> <branch>
   ```

4. **Confirm and print open command**:
   ```
   Worktree created:
     Branch : feature-x
     Path   : /Users/you/Documents/myapp-feature-x

   Open a new Claude Code session there:
     claude --dir /Users/you/Documents/myapp-feature-x

   Or in a new terminal tab:
     cd /Users/you/Documents/myapp-feature-x && claude
   ```

---

### `/worktree list`

Run `git worktree list` and format the output as a clean table:

```bash
git worktree list
```

Format output as:
```
  #  Branch              Path                                    Status
  1  main (current)      /Users/you/Documents/myapp              clean
  2  feature-x           /Users/you/Documents/myapp-feature-x    2 modified
  3  hotfix-login        /Users/you/Documents/myapp-hotfix-login  clean
```

For each worktree, check status:
```bash
git -C <worktree-path> status --short 2>/dev/null | wc -l | tr -d ' '
```
- `0` → `clean`
- `N` → `N modified` (or staged/untracked)
- If path doesn't exist → `MISSING`

Run status checks in parallel across all worktrees.

---

### `/worktree remove <branch>`

1. **Find the worktree path** for the given branch:
   ```bash
   git worktree list --porcelain | awk '/^worktree/{path=$2} /^branch refs\/heads\/<branch>/{print path}'
   ```

2. **Safety check** — warn if there are uncommitted changes:
   ```bash
   CHANGES=$(git -C <path> status --short 2>/dev/null | wc -l | tr -d ' ')
   ```
   If `CHANGES > 0`: show the diff summary and ask the user to confirm before removing.

3. **Remove**:
   ```bash
   git worktree remove <path>
   ```
   If that fails (e.g., dirty worktree they confirmed removing): `git worktree remove --force <path>`

4. **Optionally delete the branch** — ask the user:
   ```
   Worktree removed. Delete the branch 'feature-x' too?
   (It still exists in the repo — you can reattach it later with /worktree new)
   ```
   If yes: `git branch -d <branch>` (use `-D` only if user confirms non-merged)

5. **Confirm**:
   ```
   Removed worktree: /Users/you/Documents/myapp-feature-x
   Branch 'feature-x' kept (or deleted).
   ```

---

### `/worktree clean`

Remove stale worktree entries (paths that no longer exist on disk):

```bash
git worktree prune --verbose
git worktree list
```

Show before/after count. Typical output:
```
Pruned 2 stale worktrees.
Active worktrees: 2 remaining.
```

---

### `/worktree status`

Show a brief `git status` for every worktree:

```bash
git worktree list --porcelain
```

For each worktree path, run in parallel:
```bash
git -C <path> status --short --branch 2>/dev/null
```

Output:
```
── main (/Users/you/Documents/myapp) ──────────────────
## main...origin/main
M  global-skills/worktree/SKILL.md

── feature-x (/Users/you/Documents/myapp-feature-x) ──
## feature-x (no upstream)
A  src/new-feature.py
```

---

## Rules

1. **Never remove the main/primary worktree** — `git worktree remove` on the main repo is not allowed. Detect and refuse: the main worktree is the one where `git rev-parse --git-dir` equals `.git` (not `.git/worktrees/...`).

2. **Always show the `claude --dir` open command** after creating a worktree — this is the whole point.

3. **Check for missing paths** in `/worktree list` — flag `MISSING` entries clearly and suggest `/worktree clean`.

4. **Never force-remove without confirmation** — if a worktree has uncommitted changes, show them and require explicit user confirmation.

5. **Branch naming** — if the user provides a branch with `/` (e.g. `feature/login`), use it as-is for the branch name but sanitize for the path (replace `/` → `-`).

---

## Examples

### Start a parallel feature session
```
User: /worktree new feature-auth
→ Creates branch 'feature-auth', worktree at ../myapp-feature-auth
→ Prints: claude --dir /Users/you/Documents/myapp-feature-auth
```

### See all active sessions
```
User: /worktree list
→ Table of all worktrees with branch, path, dirty/clean status
```

### Clean up after merging
```
User: /worktree remove feature-auth
→ Checks for uncommitted work (none)
→ Removes worktree
→ Asks: delete branch too?
```

### Fix a bug while mid-feature
```
User: /worktree new hotfix-crash
→ New worktree from main at ../myapp-hotfix-crash
→ Open second Claude session there, fix the bug, merge, /worktree remove hotfix-crash
→ Return to feature session uninterrupted
```
