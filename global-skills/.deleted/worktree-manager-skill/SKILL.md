---
name: worktree-manager-skill
version: 0.2.0
description: "This skill should be used when the user wants to create, remove, list, or manage worktrees with isolated .claude/settings.json, port isolation, and automatic cleanup. It provides complete git worktree lifecycle management for parallel development, handling create-worktree, list-worktrees, and remove-worktree operations."
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Worktree Manager Skill

Complete worktree lifecycle management for parallel development environments with isolated ports, `.claude/settings.json` configuration, and automatic cleanup.

## When to use this skill

Use this skill when the user wants to:
- **Create** a new worktree for parallel development (`/create-worktree`)
- **Remove** an existing worktree (`/remove-worktree`)
- **List** all worktrees and their status (`/list-worktrees`)
- **Check** worktree configuration or status
- **Manage** multiple parallel development environments

## Operations

### CREATE: `/create-worktree <feature-name> [port-offset]`

Creates a fully isolated git worktree with its own `.claude/settings.json`.

**What it does:**
1. **Validates feature name** (security gate -- blocks shell metacharacters, path traversal)
2. Creates git branch and worktree at `../PROJECT-feature-name/`
3. **Validates worktree path** stays within parent directory
4. Copies `.claude/settings.json` from parent with port adjustments
5. Creates isolated `.env` files with unique ports
6. Creates `.worktree-pids/` directory for safe process tracking
7. Installs dependencies
8. Reports access information

**Detailed steps:** See [OPERATIONS.md](OPERATIONS.md)

### LIST: `/list-worktrees`

Shows all worktrees with their configuration and status.

**What it shows:**
- All existing worktrees with paths and branches
- Port configuration (server + client)
- Service status (running/stopped with PIDs)
- Access URLs for each worktree

**Detailed steps:** See [OPERATIONS.md](OPERATIONS.md)

### REMOVE: `/remove-worktree <feature-name> [--force]`

Completely removes a worktree, stops services, and optionally deletes the branch.

**What it does:**
1. **Validates feature name** (security gate)
2. Stops running services using **PID file-based** safe shutdown (graceful SIGTERM first)
3. **Checks for uncommitted changes** and warns before removal
4. Removes git worktree (**graceful by default**, `--force` required for dirty worktrees)
5. Cleans up directory
6. Optionally deletes the git branch

**Safety defaults:**
- Refuses to remove worktrees with uncommitted changes unless `--force` is specified
- Uses SIGTERM before SIGKILL, with ownership verification on all process kills
- Never kills processes belonging to other users

**Detailed steps:** See [OPERATIONS.md](OPERATIONS.md)

## Isolated Configuration

Each worktree receives its own `.claude/settings.json` that is a copy of the parent project's config with port-specific adjustments:

```
Parent project (.claude/settings.json)
  - hooks reference __REPO_DIR__ paths (unchanged)
  - observability server URL: localhost:4000

Worktree (.claude/settings.json)
  - Same hooks (paths unchanged since they are absolute)
  - observability server URL: localhost:4010 (offset applied)
  - Any port references updated to worktree-specific ports
```

### Port Isolation Scheme

```
SERVER_PORT = 4000 + (offset * 10)
CLIENT_PORT = 5173 + (offset * 10)
```

| Environment | Offset | Server | Client |
|-------------|--------|--------|--------|
| Main repo   | 0      | 4000   | 5173   |
| Worktree 1  | 1      | 4010   | 5183   |
| Worktree 2  | 2      | 4020   | 5193   |
| Worktree 3  | 3      | 4030   | 5203   |

## Worktree Naming Convention

Worktrees are created as sibling directories to the project:
```
~/projects/my-app/                  # Main project
~/projects/my-app-feature-auth/     # Worktree for feature-auth
~/projects/my-app-fix-bug/          # Worktree for fix-bug
```

This keeps worktrees visible and easy to find, rather than nested inside `trees/`.

## Security

This skill enforces multiple security layers to prevent command injection, path traversal, and unsafe process management.

### Input Validation (scripts/validate_name.sh)

All feature names are validated **before** any shell or git command executes:

| Rule | Details |
|------|---------|
| **Allowed characters** | `a-z A-Z 0-9 . _ -` only |
| **Blocked characters** | `/`, spaces, `;`, `&`, `\|`, `$`, backticks, `(`, `)`, `{`, `}`, etc. |
| **Path traversal** | `..` sequences are blocked |
| **Hidden directories** | Leading `.` is blocked |
| **Length** | 2-50 characters |
| **Port offset** | Non-negative integer, max 99 |

### Path Containment

After computing the worktree directory path, it is validated to ensure it stays within the expected parent directory. This prevents path traversal even if name validation is bypassed.

### Safe Process Management

- **PID file tracking**: Processes started in worktrees are recorded in `.worktree-pids/*.pid`
- **Ownership verification**: Only kills processes owned by the current user
- **Graceful shutdown**: Sends SIGTERM first, waits up to 5 seconds, then SIGKILL only if needed
- **No blind kill -9**: Never pipes arbitrary `lsof` output to `kill -9`

### Force Operation Policy

- Worktree removal defaults to **graceful mode** (no `--force`)
- Uncommitted changes trigger a warning and abort unless `--force` is explicitly provided
- Branch deletion uses safe `-d` flag (fails on unmerged branches)

### Validation Script

The validation logic lives in `scripts/validate_name.sh` and can be sourced by any operation:

```bash
source scripts/validate_name.sh
validate_feature_name "$NAME" || exit 1
validate_worktree_path "$PATH" "$PARENT" || exit 1
validate_port_offset "$OFFSET" || exit 1
```

## Examples

See [EXAMPLES.md](EXAMPLES.md) for detailed usage examples.

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.

## Quick Reference

See [REFERENCE.md](REFERENCE.md) for command syntax and configuration details.
