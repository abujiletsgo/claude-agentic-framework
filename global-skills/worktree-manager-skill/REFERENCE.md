# Worktree Quick Reference

Technical details, command syntax, and configuration reference.

## Command Syntax

### Create Worktree
```
/create-worktree <feature-name> [port-offset]
```

**Parameters:**
- `feature-name` (required) - Name for the feature branch and worktree directory
  - Allowed: `a-z A-Z 0-9 . _ -` only
  - Length: 2-50 characters
  - No leading dots, no `..`, no `/`, no shell metacharacters
- `port-offset` (optional) - Port offset number, 0-99 (default: auto-calculated)

**Examples:**
```
/create-worktree add-auth
/create-worktree fix-bug 3
```

**Rejected names** (validation will block these):
```
feature/auth     # contains /
my feature       # contains space
../escape        # path traversal
.hidden          # leading dot
a                # too short
```

### List Worktrees
```
/list-worktrees
```

**Parameters:** None

**Output includes:**
- Worktree paths and branches
- Port configurations
- Service status with PIDs
- Whether .claude/settings.json is isolated
- Access URLs
- Quick management commands

### Remove Worktree
```
/remove-worktree <feature-name> [--force]
```

**Parameters:**
- `feature-name` (required) - Name of the worktree to remove (same naming rules as create)
- `--force` (optional) - Force removal even with uncommitted changes

**Behavior:**
- Default (no `--force`): Checks for uncommitted changes and aborts if found
- With `--force`: Warns about uncommitted changes but proceeds with removal
- Process shutdown: Uses SIGTERM first, SIGKILL only as fallback, with ownership checks

**Examples:**
```
/remove-worktree add-auth           # Graceful (aborts if dirty)
/remove-worktree add-auth --force   # Force (removes even if dirty)
```

---

## Port Allocation

### Port Calculation Formula
```
SERVER_PORT = 4000 + (offset * 10)
CLIENT_PORT = 5173 + (offset * 10)
```

### Port Map

| Environment | Offset | Server Port | Client Port |
|-------------|--------|-------------|-------------|
| Main Repo   | 0      | 4000        | 5173        |
| Worktree 1  | 1      | 4010        | 5183        |
| Worktree 2  | 2      | 4020        | 5193        |
| Worktree 3  | 3      | 4030        | 5203        |
| Worktree 4  | 4      | 4040        | 5213        |
| Worktree 5  | 5      | 4050        | 5223        |

### Auto-calculated Offsets
When no port offset is specified, the system:
1. Lists existing worktrees via `git worktree list`
2. Counts non-main worktrees
3. Uses (count + 1) as the new offset

---

## Directory Structure

### Worktree Placement (sibling directories)
```
~/projects/
  my-project/                    # Main repo (offset 0)
    .claude/settings.json        # Main config
    .env
    apps/server/
    apps/client/
  my-project-feature-auth/       # Worktree (offset 1)
    .claude/settings.json        # Isolated config (ports adjusted)
    .worktree-pids/              # PID files for safe process management
      server.pid                 # Tracked server process
      client.pid                 # Tracked client process
    .env                         # Copied from main
    apps/server/.env             # SERVER_PORT=4010
    apps/client/.env             # VITE_PORT=5183
  my-project-fix-bug/            # Worktree (offset 2)
    .claude/settings.json        # Isolated config (ports adjusted)
    .worktree-pids/              # PID files for safe process management
    .env
    apps/server/.env             # SERVER_PORT=4020
    apps/client/.env             # VITE_PORT=5193
```

### Legacy Placement (trees/ subdirectory)
Some existing worktrees may use the older `trees/` convention:
```
my-project/
  trees/
    feature-auth/
    fix-bug/
```

The remove command checks both locations.

---

## Configuration Files

### .claude/settings.json (Worktree-specific)

Copied from the parent project with port adjustments applied:

```json
{
  "permissions": { "..." },
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run /path/to/framework/global-hooks/observability/send_event.py ...",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

Port references within the settings.json (e.g., `AGENT_SERVER_URL` environment variables in hook configs) are updated to use the worktree-specific ports.

### .env (Root - copied from parent)
Contains API keys and shared configuration. Copied as-is from the main project.

### apps/server/.env (Worktree-specific)
```env
SERVER_PORT=<calculated SERVER_PORT>
DB_PATH=events.db
```

### apps/client/.env (Worktree-specific)
```env
VITE_PORT=<calculated CLIENT_PORT>
VITE_API_URL=http://localhost:<calculated SERVER_PORT>
VITE_WS_URL=ws://localhost:<calculated SERVER_PORT>/stream
VITE_MAX_EVENTS_TO_DISPLAY=100
```

---

## Isolation Features

Each worktree has:

| Feature | Isolation Level | Notes |
|---------|----------------|-------|
| **File System** | Complete | Separate working directory |
| **Ports** | Complete | Unique port allocation per offset |
| **.claude/settings.json** | Complete | Own config with adjusted ports |
| **Environment** | Complete | Own .env files |
| **Database** | Complete | Own events.db (relative path) |
| **Process Tracking** | Complete | Own .worktree-pids/ directory |
| **Dependencies** | Complete | Own node_modules |
| **Git History** | Shared | Same repository |
| **Git Config** | Shared | Same git settings |
| **Framework Hooks** | Shared | Same hook scripts (absolute paths) |

---

## Parallel Development Workflow

```bash
# 1. Main development in primary workspace
cd ~/projects/my-project

# 2. Create worktree for a feature
/create-worktree add-auth

# 3. In a separate terminal, open Claude Code in the worktree
cd ~/projects/my-project-add-auth
claude

# 4. Work on feature independently
# Both instances can run simultaneously with different ports

# 5. When done, merge back from main project
cd ~/projects/my-project
git merge add-auth

# 6. Clean up worktree
/remove-worktree add-auth
```

---

## Best Practices

### When to Create Worktrees
- Testing multiple features simultaneously
- Reviewing PRs while working on features
- Hot-fixing production while developing
- Running integration tests in isolation
- Comparing behavior between branches

### When NOT to Create Worktrees
- Simple branch switching (use `git checkout`)
- Temporary file viewing (use `git show`)
- Quick edits (stash and switch)

### Cleanup Recommendations
- Remove worktrees when feature is merged
- Do not let unused worktrees accumulate
- Regular audit with `/list-worktrees`
- Free up ports for active development

### Naming Conventions
- Use descriptive feature names: `add-auth`, `fix-login-bug`, `refactor-api`
- **Allowed characters only**: `a-z A-Z 0-9 . _ -`
- **Blocked**: `/`, spaces, shell metacharacters, `..`, leading dots
- **Length**: 2-50 characters
- Keep names concise but meaningful
- Match your team's branch naming scheme
- Validate with: `bash scripts/validate_name.sh "my-name"`
