# Context Management System

**Version**: 2.0
**Purpose**: Two-hook pipeline for surviving Claude Code's automatic context compaction

---

## Overview

Claude Code compacts context automatically at ~95%. The two-hook pipeline ensures
critical state is preserved through compaction without modifying the transcript
(which hooks cannot do).

```
[PostToolUse @ 70%+]        [PreCompact @ 95%]
auto_context_manager.py  →  pre_compact_preserve.py
  detect cold tasks           read summaries from disk
  write summaries to disk     inject into compaction prompt
  (idempotent)                (structured, verbatim)
```

---

## Hook 1: auto_context_manager.py

**Event**: PostToolUse (Bash | Write | Edit)
**Frequency**: Every 10 assistant turns
**Threshold**: 70%+ context usage

### What It Does

1. Estimates context usage from transcript character count
2. Finds **cold tasks**: completed TaskCreate tasks not referenced in 20+ turns
3. For each cold task, extracts from transcript:
   - Files modified (Edit/Write calls in that task's turn range)
   - Bash commands run
   - Short assistant text messages (outcomes/decisions)
   - Error messages encountered
4. Writes a structured JSON summary to disk
5. Skips tasks that already have a summary (idempotent)

### Cold Task Definition

A task is cold when ALL of these are true:
- Status = `completed` (via TaskUpdate)
- Completed more than `TURNS_UNTIL_COLD` (20) assistant turns ago
- Subject string does not appear in the last 20 turns of transcript

### Summary File Format

**Location**: `~/.claude/data/compressed_context/{md5(session_id:task_id)}.json`

```json
{
  "session_id": "abc-123-def-456",
  "task_id": "1",
  "subject": "Implement OAuth2 login flow",
  "start_turn": 5,
  "end_turn": 18,
  "compressed_at": "2026-02-17T14:30:00",
  "files_modified": [
    "src/auth/oauth2.py",
    "src/middleware/auth.py"
  ],
  "commands_run": [
    "pytest tests/test_auth.py -v",
    "git diff src/auth/"
  ],
  "key_outcomes": [
    "decided to use PKCE flow for public clients",
    "changed JWT algorithm from RS256 to HS256"
  ],
  "errors_resolved": [
    "AssertionError: JWT signature invalid — fixed by switching to HS256"
  ]
}
```

### Configuration Constants

```python
TURNS_UNTIL_COLD = 20       # Turns without mention before task is cold
CONTEXT_THRESHOLD = 70      # % context usage before pre-compression starts
CHECK_FREQUENCY = 10        # Only run every N assistant turns
```

---

## Hook 2: pre_compact_preserve.py

**Event**: PreCompact
**Frequency**: Every compaction (auto or manual)
**Threshold**: N/A — fires whenever Claude Code compacts

### What It Does

Reads the transcript and injects a structured preservation block into the
compaction prompt as `additionalContext`. The compaction model uses this
to retain critical state instead of reconstructing it from old history.

### Preserved Sections

| Section | Source | Cap |
|---------|--------|-----|
| Active/in-progress tasks | TaskCreate + TaskUpdate (ID-correlated) | 10 |
| Modified files | Write/Edit tool calls | 20 |
| Test commands | Bash calls matching pytest/jest/etc | 5 unique |
| Key decisions | Assistant text with decision-signal keywords | 15 |
| Recent errors | Bash tool results with error signals | 8 |
| Git diff stat | `git diff --stat HEAD` | full |
| Pre-computed summaries | Files from `auto_context_manager.py` | all |

### Task ID Correlation

Tasks are tracked by correlating:
1. `tool_use` block: `{id: "toolu_xxx", name: "TaskCreate", input: {subject: "..."}}`
2. `tool_result` block: `{tool_use_id: "toolu_xxx", content: '{"taskId": "1"}'}`

This builds a `task_id → subject` map, which is then cross-referenced with
`TaskUpdate` calls. This avoids the bug of comparing IDs to subjects directly.

### Injection Format

```
═══ COMPACTION PRESERVATION INSTRUCTIONS ═══
Trigger: auto
The following context MUST be preserved verbatim:

📋 ACTIVE / IN-PROGRESS TASKS:
  • Fix context manager transcript key bug

📝 FILES MODIFIED THIS SESSION:
  • /src/auth/oauth2.py
  • /tests/test_auth.py

🧠 KEY DECISIONS MADE:
  • decided to use PKCE flow for public clients
  • chose HS256 over RS256 for simplicity in single-server setup

⚠️ RECENT ERRORS:
  • `pytest tests/` → FAILED tests/test_auth.py — AssertionError: expected 200 got 401

📦 GIT DIFF STAT:
  src/auth/oauth2.py | 24 ++++--
  1 file changed, 18 insertions(+), 6 deletions(-)

📁 PRE-COMPUTED TASK SUMMARIES (use verbatim — already compressed):
  ▸ Task: Implement OAuth2 login flow
    Files: src/auth/oauth2.py, src/middleware/auth.py
    → decided to use PKCE flow for public clients
    → changed JWT algorithm from RS256 to HS256

COMPACTION RULES:
  1. Include ALL active/in-progress tasks with their current status
  2. Include the complete modified files list
  3. Preserve all key decisions — these explain WHY things were done
  4. Note any unresolved errors so work can resume correctly
  5. Keep the git diff summary so the state of changes is clear
  6. For PRE-COMPUTED SUMMARIES: use them verbatim, do not re-summarize
  7. Preserve next steps and in-progress work state
  8. Do NOT discard any pending/in-progress task context
```

---

## Pipeline Interaction

```
Session start
    │
    ├─ [Turn 10, 70% ctx] auto_context_manager fires
    │    └─ Task "OAuth2 login" is cold → writes summary to disk
    │
    ├─ [Turn 20, 75% ctx] auto_context_manager fires
    │    └─ No new cold tasks → exits silently
    │
    ├─ [Turn 28, 95% ctx] Claude Code triggers compaction
    │    └─ pre_compact_preserve fires
    │         ├─ Active tasks: ["Fix context manager bug"]
    │         ├─ Modified files: [oauth2.py, auto_context_manager.py]
    │         ├─ Key decisions: ["decided to use PKCE flow"]
    │         ├─ Recent errors: ["pytest FAILED — AssertionError"]
    │         ├─ Git diff stat: "2 files changed, 318 insertions"
    │         └─ Pre-computed: ["OAuth2 login" summary from disk]
    │
    └─ Compaction runs with full preservation block
         └─ Work continues with context intact
```

---

## Limitations

| Limitation | Detail |
|------------|--------|
| Cannot prevent hitting 95% | Hooks cannot delete transcript messages |
| Summaries are hints | Compaction model is guided but not forced |
| Key decision extraction is heuristic | Keyword + bullet-point pattern matching |
| No LLM compression | Summaries are structured extraction, not semantic compression |

**For very long sessions**: Use `/rlm` to keep primary context thin via delegation. That is more reliable than any compaction recovery strategy.

---

## Storage Locations

| Path | Purpose |
|------|---------|
| `~/.claude/data/compressed_context/*.json` | Pre-computed task summaries |
| `~/.claude/data/context_queue/{session_id}_state.json` | Last check turn per session |

---

## Maintenance

```bash
# View pre-computed summaries for current session
ls -lh ~/.claude/data/compressed_context/

# Clear all summaries (forces re-computation next session)
rm ~/.claude/data/compressed_context/*.json

# Reset context manager check state
rm ~/.claude/data/context_queue/*_state.json
```
