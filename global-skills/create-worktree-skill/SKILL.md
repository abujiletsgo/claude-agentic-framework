---
name: create-worktree-skill
version: 0.1.0
description: "DEPRECATED: This skill should be used only as a redirect to worktree-manager-skill. It redirects to the consolidated worktree manager for creating, listing, and removing git worktrees with isolated .claude/settings.json and port isolation."
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Create Worktree Skill (Deprecated)

This skill has been consolidated into the **worktree-manager-skill**.

## Redirect

For all worktree operations, use the worktree-manager-skill which provides:

- **Create**: `/create-worktree <feature-name> [port-offset]`
- **List**: `/list-worktrees`
- **Remove**: `/remove-worktree <feature-name>`

The worktree-manager-skill includes:
- Isolated `.claude/settings.json` per worktree with port adjustments
- Port isolation (SERVER_PORT and CLIENT_PORT auto-calculated)
- Automatic cleanup on removal
- Full lifecycle management

See [worktree-manager-skill](../worktree-manager-skill/SKILL.md) for complete documentation.
