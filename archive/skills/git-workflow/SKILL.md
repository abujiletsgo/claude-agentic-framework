---
name: Git Workflow
version: 0.1.0
description: "This skill should be used when the user needs help with git operations, merge conflicts, branch management, or commit cleanup. It provides advanced git workflow management including branching strategies, merge conflict resolution, interactive rebase guidance, and commit hygiene."
---

# Git Workflow Skill

Advanced git operations, branching strategies, conflict resolution, and commit hygiene best practices.

## When to Use

- User asks: "fix merge conflict", "rebase", "clean up commits", "branch strategy"
- Complex git operations (cherry-pick, bisect, reflog recovery)
- Setting up branching strategies
- Commit message standardization

## Branching Strategies

### Trunk-Based Development (Recommended for small teams)
```
main ─────────────────────────────────
  └── feature/short-lived (1-2 days) ──┘
```

### Git Flow (For release-based projects)
```
main ────────────────────────────────
develop ─────────────────────────────
  └── feature/xxx ──┘  └── release/x.y ──┘
```

## Commit Message Convention

```
type(scope): subject

body (optional)

footer (optional)
```

Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build

## Common Operations

### Merge Conflict Resolution
1. Identify conflicted files: `git status`
2. Read each conflict marker
3. Understand both sides (ours vs theirs)
4. Choose correct resolution
5. Stage and commit

### Interactive Rebase (for commit cleanup)
```bash
git rebase -i HEAD~N
# Use: pick, squash, reword, drop, edit
```

### Cherry-Pick
```bash
git cherry-pick <commit-hash>
# With conflict: resolve, then git cherry-pick --continue
```

### Recovery with Reflog
```bash
git reflog  # Find the lost commit
git checkout <hash>  # Or git cherry-pick <hash>
```

### Bisect (find regression)
```bash
git bisect start
git bisect bad  # Current commit is bad
git bisect good <known-good-hash>
# Test each commit, mark good/bad
git bisect reset  # When done
```

## Examples

### Example 1: Clean Up Messy Commits
User: "Clean up my last 5 commits before PR"

1. Review commits: `git log --oneline -5`
2. Guide through interactive rebase
3. Squash related commits
4. Reword messages to conventional format

### Example 2: Resolve Merge Conflict
User: "Help me fix this merge conflict"

1. `git status` to see conflicted files
2. Read each file's conflict markers
3. Understand context from both branches
4. Suggest resolution preserving both changes where possible
