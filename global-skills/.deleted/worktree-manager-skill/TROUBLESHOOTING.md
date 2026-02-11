# Worktree Troubleshooting Guide

Common issues and their solutions when managing worktrees.

## Issue 1: Branch already checked out

**Error:** `fatal: 'feature-name' is already checked out at '/path/to/worktree'`

**Cause:** Each branch can only be checked out in one worktree at a time.

**Solution:**
1. Check existing worktrees: `git worktree list`
2. Remove the existing worktree first: `/remove-worktree feature-name`
3. Then recreate: `/create-worktree feature-name`

---

## Issue 2: Port conflicts

**Symptoms:** Services fail to start or bind to ports.

**Diagnosis:**
```bash
lsof -i :4010  # Check if server port is in use
lsof -i :5183  # Check if client port is in use
```

**Solutions:**
- Use an explicit port offset: `/create-worktree feature-name 5`
- Stop processes on conflicting ports safely (verify ownership first):
  ```bash
  # Check what is using the port
  lsof -i :4010
  # If it belongs to you, send graceful shutdown
  PID=$(lsof -ti :4010)
  kill "$PID"        # SIGTERM (graceful)
  sleep 2
  kill -0 "$PID" 2>/dev/null && kill -9 "$PID"  # SIGKILL only if still running
  ```
- List worktrees to see port allocation: `/list-worktrees`
- Check `.worktree-pids/` directory for tracked PIDs

---

## Issue 3: Missing .claude/settings.json in worktree

**Symptoms:** Claude Code in the worktree does not pick up hooks or permissions.

**Cause:** Worktree was created manually without the skill, or settings were not copied.

**Solution:**
```bash
# Copy from main project
mkdir -p WORKTREE_DIR/.claude
cp PROJECT_ROOT/.claude/settings.json WORKTREE_DIR/.claude/settings.json

# Update port references if needed
# Replace 4000 with worktree's SERVER_PORT
# Replace 5173 with worktree's CLIENT_PORT
```

---

## Issue 4: Worktree directory exists but git does not recognize it

**Symptoms:** Directory exists but `git worktree list` does not show it.

**Cause:** Incomplete removal or manual deletion of the `.git` file in the worktree.

**Solution:**
```bash
# Prune stale worktree metadata
git worktree prune

# If directory is orphaned, remove it manually
rm -rf /path/to/orphaned-worktree
```

---

## Issue 5: Cannot remove worktree (uncommitted changes)

**Error:** `fatal: cannot remove: worktree has uncommitted changes`

**Solutions:**
1. Commit or stash changes in the worktree first (preferred)
2. Use the `--force` flag explicitly: `/remove-worktree feature-name --force`

The `/remove-worktree` command defaults to **graceful removal** and will warn about uncommitted changes. Force removal requires explicit `--force` to prevent accidental data loss.

---

## Issue 6: Dependencies not installing

**Symptoms:** `node_modules` missing, import errors when running.

**Solution:**
```bash
# Navigate to worktree and install manually
cd /path/to/worktree
npm install

# For monorepo structures
cd /path/to/worktree/apps/server && npm install
cd /path/to/worktree/apps/client && npm install
```

---

## Issue 7: Hooks not firing in worktree

**Symptoms:** Claude Code hooks (damage control, observability, etc.) do not run.

**Cause:** `.claude/settings.json` not present in worktree, or paths are incorrect.

**Diagnosis:**
1. Check if `.claude/settings.json` exists in the worktree root
2. Verify hook paths point to the framework repo (absolute paths with `__REPO_DIR__` already resolved)
3. Verify the hook scripts are executable

**Solution:**
Re-copy settings.json from the main project and verify paths are absolute (not relative).

---

## Issue 8: Worktree and main repo have different node_modules

**This is expected behavior.** Each worktree has its own `node_modules` to ensure complete isolation. If you need them synchronized, run `npm install` in the worktree after updating `package.json`.

---

## Issue 9: Feature name rejected by validation

**Error:** `ERROR: Invalid feature name 'my-name'. Use only: a-z A-Z 0-9 . _ -`

**Cause:** Feature names are validated to prevent command injection and path traversal. Characters like `/`, spaces, `;`, `&`, `$`, and backticks are blocked.

**Solutions:**
- Replace slashes with hyphens: `feature/auth` -> `feature-auth`
- Replace spaces with hyphens: `my feature` -> `my-feature`
- Remove special characters: `fix(bug)` -> `fix-bug`
- Ensure name is 2-50 characters long

**Validation script:** `scripts/validate_name.sh`
```bash
# Test a name before using it
bash scripts/validate_name.sh "my-feature-name"
```

---

## General Debugging Approach

When a user reports any issue:

1. **Gather information**
   - Run `git worktree list` to see all worktrees
   - Check which worktree has the problem
   - Read its `.claude/settings.json` and `.env` files

2. **Diagnose**
   - Check service status via `lsof -i :PORT`
   - Verify configuration files exist and have correct values
   - Look for error patterns in the output

3. **Resolve**
   - Use the appropriate operation (create/remove/list)
   - Verify the fix worked
   - Explain what happened

4. **Prevent**
   - Suggest using `/list-worktrees` regularly
   - Recommend cleanup of unused worktrees
   - Note any configuration issues for future reference

---

## Quick Diagnostic Checklist

When troubleshooting, verify:

- [ ] Was the feature name validated? (`bash scripts/validate_name.sh "name"`)
- [ ] Does worktree directory exist?
- [ ] Is worktree path within expected parent directory?
- [ ] Is git aware of it? (`git worktree list`)
- [ ] Does `.claude/settings.json` exist in worktree?
- [ ] Are ports configured in `.env` files?
- [ ] Are services running? (`lsof -i :PORT`)
- [ ] Does `.worktree-pids/` directory exist with valid PID files?
- [ ] Are dependencies installed? (check `node_modules`)
- [ ] Are hook paths absolute and valid?
