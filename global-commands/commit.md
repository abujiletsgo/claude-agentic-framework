# /commit - Smart Commit

Stage changes and create a commit with a conventional commit message.

## Usage
```
/commit                    # Auto-detect changes, generate message
/commit "message"          # Use provided message
/commit --amend            # Amend the previous commit
/commit --scope "module"   # Prefix with scope: feat(module): ...
```

## Implementation

When the user runs `/commit`:

1. **Inspect changes**:
   ```bash
   git status
   git diff --staged --stat
   git diff --stat
   ```

2. **Stage files** (if nothing staged):
   - Show the user what would be staged
   - Stage relevant files (avoid credentials, large binaries)
   - Never use `git add -A` without user confirmation

3. **Generate commit message** using Conventional Commits format:
   ```
   <type>(<scope>): <description>

   <body - what and why, not how>

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
   ```

   Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

4. **Show the message** to the user and ask for confirmation before committing

5. **Commit**:
   ```bash
   git commit -m "<message>"
   ```

6. **Show result**:
   ```bash
   git log --oneline -1
   ```

## Rules
- Never force push
- Never skip hooks (no --no-verify)
- Never amend unless explicitly requested
- Always show what will be committed before doing it
- Warn if staging sensitive files (credentials, keys, secrets)
