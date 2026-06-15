# Memory Audit Procedure

Audits `~/.claude/projects/<slug>/memory/` for stale state, contradictions, and inflated numbers. Preserves lessons learned, removes operational state that rots.

## Step 1: Find memory directory and list files

```bash
eval "$(~/.claude/skills/gstack/bin/gstack-slug 2>/dev/null)"
MEMDIR="$HOME/.claude/projects/${SLUG}/memory"
ls -lt "$MEMDIR"/*.md 2>/dev/null
```

If the directory doesn't exist or is empty, skip this phase silently.

## Step 2: Classify each file (skip MEMORY.md itself)

- **STALE** — type=project, >7 days old, describes live running state (what's running, specific bot configs, dashboard URLs). Rewrite: strip state claims, keep any embedded lessons or architecture facts.
- **CONTRADICTED** — file A says X is valid, file B says X is dead. Keep the more recent verdict. Add one redirect line to the older file.
- **INFLATED NUMBERS** — stores simulation PnL numbers without noting they're unvalidated or from an inflated model. Add a caveat noting the source and reliability.
- **DUPLICATE LESSON** — same lesson in two files. Merge into one, redirect the other.
- **VALID** — timeless feedback, confirmed dead-ends, stable facts. Leave unchanged.

## Step 3: Rewrite stale/wrong files in place

- Keep frontmatter (name/description/type), update description to match new content
- Strip project state claims
- Preserve all lessons, bug fixes, dead-end records
- One-line redirect if superseded: `See [correct_file.md] for current state.`

## Step 4: Write new memories from this session

If the session produced new validated findings, dead-end confirmations, or corrected prior beliefs — write them as new memory files using the standard frontmatter format (type: feedback for lessons, project for state, reference for external resources).

## Step 5: Rebuild MEMORY.md index

Rewrite MEMORY.md with accurate one-line entries for every active memory file. Group by: Current State / Confirmed Edges / Dead Ends / Strategy Lessons / Reference Facts / Process. Remove entries pointing to superseded files.

## Output

Print: `N files audited, N rewritten, N added, N redirected.`
