# /ntask — Daily Task Intelligence Briefing (Global)

Cross-references Notion sprint board + current session activity + git log to generate a smart daily report with recommendations. Works in any project with `.claude/ntask-config.json`.

---

## Instructions

### Step 0 — Load project config

Read `.claude/ntask-config.json` in the current working directory. Extract:
- `data_source_id` → Notion collection ID
- `project_url` → Poly Quant (or other) project page URL
- `team` → name→userId map
- `default_assignee` → who to focus on by default

If no config found, tell the user: "No `.claude/ntask-config.json` found. See Poly Quant's as a template."

Parse any flags from `$ARGUMENTS` (`--who name`, `--team`, `--mine`, `--update`).

### Step 1 — Gather git + session activity

Run in parallel:

```bash
git log --since="midnight" --oneline --no-merges
```
```bash
git diff --stat HEAD~10 HEAD --diff-filter=AM 2>/dev/null | head -40
```

Also include: what you know was done THIS Claude Code session (from conversation context).

### Step 2 — Pull Notion board

Use `mcp__claude_ai_Notion__notion-search` with:
- `data_source_url` = `collection://{data_source_id}`
- `query` = ""
- `page_size` = 25

Collect all tasks linked to this project. Group by: active (🚧 ▶️ 👀 🔄) vs done (✅ ❌), and by assignee.

Default focus: `default_assignee`. Show team tasks in secondary section unless `--mine`.

### Step 3 — Cross-reference + report

```
━━━ ntask — {name} — {YYYY-MM-DD} ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅  DONE TODAY
    [tasks detected as complete from git/session, with evidence]

▶️  IN PROGRESS
    [tasks with active session/git activity]

📋  TODO — YOURS
    [your active board tasks with no recent activity]

📋  TODO — TEAM
    [other members' active tasks, brief]

💡  RECOMMENDATIONS
    → [specific, actionable — max 5]
    → "X is due today and untouched — work on this next?"
    → "You worked on Y this session — should it be on the board?"
    → "Z has been 🚧 for 3+ days — stalled?"
    → "Ask [name] about W — due today, no activity"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Want me to update Notion to match? e.g. "mark X done", "add Y to board"
```

### Step 4 — Offer to sync

After report: offer to update statuses or create missing tasks. Execute via Notion MCP if user says yes.

---

## Flags

| Flag | Behavior |
|------|----------|
| `--who name` | Focus on a different team member |
| `--team` | Full team view |
| `--mine` | Only your tasks |
| `--update` | Auto-apply obvious status updates |
