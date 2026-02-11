# Worktree Usage Examples

Real-world examples demonstrating how to handle different worktree management scenarios.

## Example 1: Create a worktree for a feature

**User says:** "Create a worktree for add-auth"

**Your action:**

1. Validate input first:
   ```bash
   source scripts/validate_name.sh
   validate_feature_name "add-auth" || exit 1
   # OK: 'add-auth' passes validation
   ```

2. Detect project root and name:
   ```bash
   PROJECT_ROOT=$(git rev-parse --show-toplevel)
   PROJECT_NAME=$(basename "$PROJECT_ROOT")
   ```

3. Calculate next available port offset:
   ```bash
   EXISTING=$(git worktree list | wc -l | tr -d ' ')
   OFFSET=$EXISTING  # main counts as 1, so first worktree gets offset 1
   validate_port_offset "$OFFSET" || exit 1
   SERVER_PORT=$((4000 + OFFSET * 10))
   CLIENT_PORT=$((5173 + OFFSET * 10))
   ```

4. Create the worktree:
   ```bash
   WORKTREE_DIR="$(dirname "$PROJECT_ROOT")/${PROJECT_NAME}-add-auth"
   validate_worktree_path "$WORKTREE_DIR" "$(dirname "$PROJECT_ROOT")" || exit 1
   git worktree add "$WORKTREE_DIR" -b add-auth
   ```

5. Set up isolated .claude/settings.json:
   ```bash
   mkdir -p "$WORKTREE_DIR/.claude"
   cp "$PROJECT_ROOT/.claude/settings.json" "$WORKTREE_DIR/.claude/settings.json"
   # Update port references in the copied file
   ```

6. Create PID tracking directory:
   ```bash
   mkdir -p "$WORKTREE_DIR/.worktree-pids"
   ```

7. Report to user:
   > Created worktree for `add-auth`:
   > - Location: ~/projects/my-project-add-auth/
   > - Server port: 4010
   > - Client port: 5183
   > - Isolated .claude/settings.json: Yes

---

## Example 2: Create with specific port offset

**User says:** "Set up a worktree for hotfix-security with port offset 3"

**Your action:**
1. Validate both inputs:
   ```bash
   source scripts/validate_name.sh
   validate_feature_name "hotfix-security" || exit 1
   validate_port_offset "3" || exit 1
   ```
2. Use offset 3 directly (SERVER_PORT=4030, CLIENT_PORT=5203)
3. Create worktree at `../PROJECT-hotfix-security/`
4. Copy and adjust `.claude/settings.json`

**Result:** Worktree created with explicit ports, no auto-calculation needed.

---

## Example 3: Rejected feature names (security validation)

**User says:** "Create a worktree for feature/auth"

**Your response:**
> Cannot create worktree: invalid feature name `feature/auth`.
> Feature names can only contain: a-z A-Z 0-9 . _ -
> Slashes are not allowed. Try: `feature-auth` instead.

**More rejection examples:**

| Input | Reason | Suggestion |
|-------|--------|------------|
| `../escape` | Path traversal (`..`) | `escape` |
| `my feature` | Contains space | `my-feature` |
| `.hidden` | Starts with dot | `hidden` |
| `a` | Too short (min 2) | `aa` or a more descriptive name |
| `feat;echo hi` | Shell metacharacter (`;`) | `feat-echo-hi` |

---

## Example 4: List all worktrees

**User says:** "What worktrees do I have?"

**Your action:**

1. Run `git worktree list` to get all worktrees
2. For each non-main worktree, check:
   - Does `.claude/settings.json` exist? (isolated config)
   - Read `.env` files for port config
   - Check `lsof -i :PORT` for running services
   - Check `.worktree-pids/` for tracked processes

**Sample output:**
```
Worktree Overview

Main: ~/projects/my-project (main branch)
  Ports: 4000/5173
  .claude/settings.json: Yes (primary)
  Status: Running (PIDs: 1234, 5678)

Worktree: ~/projects/my-project-add-auth (add-auth branch)
  Ports: 4010/5183
  .claude/settings.json: Yes (isolated)
  Status: Stopped

Worktree: ~/projects/my-project-fix-bug (fix-bug branch)
  Ports: 4020/5193
  .claude/settings.json: Yes (isolated)
  Status: Running (PIDs: 9012, 3456)

Next available offset: 3
```

---

## Example 5: Remove a worktree (graceful)

**User says:** "Remove the add-auth worktree"

**Your action:**

1. Validate input:
   ```bash
   source scripts/validate_name.sh
   validate_feature_name "add-auth" || exit 1
   ```
2. Find worktree directory and validate path
3. Check for uncommitted changes:
   ```bash
   cd "$WORKTREE_DIR" && git status --porcelain
   # If clean: proceed
   # If dirty: warn and abort (suggest --force)
   ```
4. Stop services safely using PID files:
   ```bash
   PID_DIR="$WORKTREE_DIR/.worktree-pids"
   # Read each .pid file, verify ownership, SIGTERM first, wait, SIGKILL if needed
   ```
5. Remove the git worktree (graceful, no --force):
   ```bash
   git worktree remove "$WORKTREE_DIR"
   git worktree prune
   ```
6. Optionally delete the branch:
   ```bash
   git branch -d add-auth
   ```

**Sample response (clean worktree):**
> Removed worktree `add-auth`:
> - Stopped services on ports 4010/5183
> - Removed directory ~/projects/my-project-add-auth/
> - Branch `add-auth` deleted (was fully merged)
> - Ports 4010/5183 are now free

---

## Example 6: Remove a worktree with uncommitted changes

**User says:** "Remove the fix-bug worktree"

**Your response (worktree is dirty):**
> WARNING: Worktree `fix-bug` has 3 uncommitted change(s).
> To preserve your work, commit or stash changes first.
> To force removal (losing changes), use: `/remove-worktree fix-bug --force`

**User says:** "Remove the fix-bug worktree --force"

**Your action:**
1. Validate input
2. Warn about uncommitted changes but proceed with FORCE_REMOVE=true
3. Stop services safely
4. Remove worktree with `--force`

**Response:**
> FORCE removal of worktree `fix-bug`:
> - WARNING: 3 uncommitted changes were discarded
> - Stopped services on ports 4020/5193
> - Removed directory ~/projects/my-project-fix-bug/
> - Branch `fix-bug` kept (has unmerged changes)

---

## Example 7: Multiple worktrees for parallel work

**User says:** "I need worktrees for feature-a, feature-b, and feature-c"

**Your action:**
Validate all names first, then create three worktrees sequentially:

```bash
source scripts/validate_name.sh
for name in feature-a feature-b feature-c; do
    validate_feature_name "$name" || exit 1
done
```

1. `/create-worktree feature-a` -> offset 1, ports 4010/5183
2. `/create-worktree feature-b` -> offset 2, ports 4020/5193
3. `/create-worktree feature-c` -> offset 3, ports 4030/5203

Each gets its own `.claude/settings.json` with the correct port references.

---

## Example 8: Full parallel development workflow

**User says:** "I want to work on auth in parallel while keeping main running"

**Complete workflow:**

```bash
# In main terminal - main project is already running
cd ~/projects/my-project

# Create worktree (validation happens automatically)
/create-worktree add-auth

# In a NEW terminal
cd ~/projects/my-project-add-auth
claude  # Start Claude Code - it uses the isolated .claude/settings.json

# Work on auth feature...
# Both terminals run independently with different ports

# When done, back in main terminal
cd ~/projects/my-project
git merge add-auth
/remove-worktree add-auth
```

---

## Pattern Recognition

### Create Keywords
- "create", "new", "setup", "make", "start", "initialize"
- "I need a worktree for..."
- "Set up a parallel environment..."

### List Keywords
- "list", "show", "display", "what", "which", "status", "check", "view"
- "What worktrees do I have?"
- "Show me my environments..."

### Remove Keywords
- "remove", "delete", "cleanup", "destroy", "stop", "kill", "terminate"
- "Clean up the...", "I don't need..."
- "Get rid of...", "Delete the..."

### Force Keywords (for remove)
- "--force", "force", "forcefully", "even with changes"
- "I don't care about changes", "discard changes"
