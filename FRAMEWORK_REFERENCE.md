# Framework Reference

> Complete technical reference for the Claude Agentic Framework. Start here if you are installing for the first time.

---

## 1. Architecture Overview

The Claude Agentic Framework is a hook-driven orchestration layer that sits between the user and Claude Code. Every interaction flows through a pipeline of Python scripts triggered by Claude Code's hook system.

### How Claude Code Hooks Work

Claude Code executes hook scripts at defined lifecycle events and passes JSON data via stdin. Hooks write JSON to stdout to influence Claude's behavior, or exit 0 to silently pass through.

```
User types prompt
       │
       ▼
UserPromptSubmit hooks fire
  └─ analyze_request.py   → classifies task, injects Caddy analysis into context
  └─ auto_delegate.py     → routes to strategy (direct / orchestrate / rlm / fusion)
       │
       ▼
Claude processes the prompt (with injected context)
       │
       ▼
PreToolUse hooks fire (before each tool call)
  └─ session_lock_manager.py   → file conflict detection (Read/Edit/Write)
  └─ unified-damage-control.py → blocks destructive commands (Bash/Edit/Write)
  └─ auto_review_team.py       → coordination hook (Bash)
       │
       ▼
Tool executes
       │
       ▼
PostToolUse hooks fire (after each tool call)
  └─ session_lock_manager.py    → unlock
  └─ context-bundle-logger.py   → snapshot session state
  └─ auto_cost_warnings.py      → budget alert
  └─ auto_error_analyzer.py     → analyze Bash failures
  └─ auto_refine.py             → trigger refine on writes
  └─ auto_dependency_audit.py   → check deps on writes
  └─ auto_context_manager.py    → context health
  └─ auto_voice_notifications.py → macOS say() on completion
  └─ auto_team_review.py        → team review after writes
  └─ extract_learnings.py       → extract knowledge from session
       │
       ▼
Session ends → Stop hooks fire
  └─ session_lock_manager.py    → cleanup
  └─ check_lthread_progress.py  → validate L-thread state
  └─ store_learnings.py         → persist knowledge to SQLite
       │
       ▼
Session starts → SessionStart hooks fire
  └─ session_startup.py         → runs 4 sub-hooks:
       ├─ session lock init
       ├─ skills integrity verification (SHA-256)
       ├─ documentation validation
       └─ auto-prime cache loading
  └─ inject_relevant.py         → inject relevant past learnings from DB
  └─ repo_map.py                → inject symbol index for large repos (≥200 files)
       │
       ▼
Context compaction → PreCompact hook fires
  └─ pre_compact_preserve.py    → preserve task state through compaction
```

### Hook JSON Protocol

**Input** (stdin to hook script):
```json
{
  "tool_name": "Bash",
  "tool_input": {"command": "git status"},
  "session_id": "abc123",
  "hook_event_name": "PreToolUse"
}
```

**Output** (stdout from hook script, to inject context):
```json
{
  "hookSpecificOutput": {
    "additionalContext": "Text injected into Claude's context"
  }
}
```

**Output** (to block a tool call):
```json
{
  "permissionDecision": "deny",
  "reason": "Command matches destructive pattern: rm -rf"
}
```

**Exit codes**:
- `0` — allow (or output JSON as above)
- `2` — block (stderr is shown to Claude as explanation)

---

## 2. Complete Hook Inventory

All 22 hooks, their events, matchers, timeouts, and purposes.

### SessionStart (3 hooks)

| Script | Timeout | Circuit Breaker | Purpose |
|--------|---------|-----------------|---------|
| `framework/session/session_startup.py` | 10s | No | Session initialization: lock manager, skills integrity, doc validation, prime cache |
| `framework/knowledge/inject_relevant.py` | 8s | No | Inject relevant past learnings from SQLite FTS5 DB |
| `framework/automation/repo_map.py` | 30s | No | Generate/inject ranked symbol index for repos with ≥200 source files |

### PreToolUse (3 hooks)

| Script | Matcher | Timeout | Circuit Breaker | Purpose |
|--------|---------|---------|-----------------|---------|
| `framework/session/session_lock_manager.py` | Read\|Edit\|Write | 5s | No | Detect file conflicts between concurrent sessions |
| `damage-control/unified-damage-control.py` | Bash\|Edit\|Write | 5s | No | Block destructive commands; protect sensitive paths |
| `framework/automation/auto_review_team.py` | Bash | 5s | Yes | Coordinate auto-review team spawning |

### PostToolUse (10 hooks)

| Script | Matcher | Timeout | Circuit Breaker | Purpose |
|--------|---------|---------|-----------------|---------|
| `framework/session/session_lock_manager.py` | (any) | 5s | No | Release file locks |
| `framework/context-bundle-logger.py` | Bash\|Write\|Edit | 8s | Yes | Snapshot session state to bundle file |
| `framework/automation/auto_cost_warnings.py` | * | 5s | Yes | Warn when API costs exceed threshold |
| `framework/automation/auto_error_analyzer.py` | Bash | 8s | Yes | Analyze Bash failures, suggest fixes |
| `framework/automation/auto_refine.py` | Write\|Edit | 6s | Yes | Trigger `/refine` on new writes |
| `framework/automation/auto_dependency_audit.py` | Write\|Edit | 15s | Yes | Check for vulnerable/outdated deps |
| `framework/context/auto_context_manager.py` | Bash\|Write\|Edit | 5s | Yes | Monitor context health, trigger compaction |
| `framework/notifications/auto_voice_notifications.py` | Bash\|Write\|Edit | 5s | Yes | macOS voice alerts on completion/errors |
| `framework/automation/auto_team_review.py` | Write\|Edit | 5s | Yes | Spawn team review after significant writes |
| `framework/knowledge/extract_learnings.py` | Bash\|Write\|Edit | 5s | Yes | Extract learnings from session for later storage |

### Stop (3 hooks)

| Script | Timeout | Circuit Breaker | Purpose |
|--------|---------|-----------------|---------|
| `framework/session/session_lock_manager.py` | 5s | No | Clean up all file locks for this session |
| `framework/validators/check_lthread_progress.py` | 5s | No | Validate L-thread (RLM) completed successfully |
| `framework/knowledge/store_learnings.py` | 5s | No | Persist extracted learnings to SQLite |

### PreCompact (1 hook)

| Script | Timeout | Circuit Breaker | Purpose |
|--------|---------|-----------------|---------|
| `framework/context/pre_compact_preserve.py` | 10s | No | Preserve task list state, file paths, and decisions through context compaction |

### UserPromptSubmit (2 hooks)

| Script | Timeout | Circuit Breaker | Purpose |
|--------|---------|-----------------|---------|
| `framework/caddy/analyze_request.py` | 10s | No | Classify prompt on 4 dimensions; suggest skills and strategy |
| `framework/caddy/auto_delegate.py` | 3s | No | Inject delegation recommendation into context |

---

## 3. Caddy Classifier

Caddy (the request classifier) runs on every `UserPromptSubmit` event. It classifies the user's prompt on 4 dimensions and recommends an execution strategy.

### Classification Dimensions

| Dimension | Values | Description |
|-----------|--------|-------------|
| `complexity` | simple / moderate / complex / massive | Scale of the task |
| `task_type` | implement / fix / refactor / research / test / review / document / deploy / plan | Nature of the work |
| `quality` | standard / high / critical | Consequence of errors |
| `scope` | focused / moderate / broad / unknown | How many files/areas are affected |

### Classification Flow

```
User prompt arrives
       │
       ▼
Keyword classification (instant, always runs)
  ─ Match against COMPLEXITY_SIGNALS, TASK_TYPE_SIGNALS, etc.
  ─ Estimate confidence score (0.0–1.0)
       │
       ├─ confidence >= 0.65 → use keyword result
       │
       └─ confidence < 0.65 → Haiku semantic fallback
             ─ Call claude-haiku-4-5 with structured prompt
             ─ Returns JSON classification with reasoning
             ─ Uses Haiku's self-reported confidence
       │
       ▼
Strategy selection via select_strategy()
       │
       ▼
Skill detection (keyword match against known skills)
       │
       ▼
Skill security audit (scan detected skills for dangerous patterns)
       │
       ▼
Output: additionalContext injected into Claude's session
```

### Strategy Routing Table

| Complexity | Quality | Scope | Task Type | Strategy |
|------------|---------|-------|-----------|----------|
| simple | standard/high | any | any | direct |
| simple | critical | any | any | fusion |
| moderate/complex | standard/high | any | any | orchestrate |
| moderate/complex | critical | any | any | fusion |
| massive | any | any | any | rlm |
| any | any | broad | review/research | rlm |
| any | any | unknown | research | rlm |
| any | any | broad | moderate/complex | rlm |
| any | any | any | research | research |
| any | any | any | plan | brainstorm |

### Configuration

Config file: `~/.claude/caddy_config.yaml`

```yaml
caddy:
  enabled: true
  auto_invoke_threshold: 0.8     # Confidence threshold for auto-suggestions
  always_suggest: true           # Always show classification (ignores threshold)
  background_monitoring: true    # Enable progress monitoring
  haiku_fallback_threshold: 0.65 # Below this confidence, call Haiku
```

### Logs

Written to `~/.claude/logs/caddy/`:
- `analyses.jsonl` — every prompt classification result

---

## 4. Circuit Breaker

Many PostToolUse hooks are wrapped in `circuit_breaker_wrapper.py` to prevent runaway hook execution from accumulating errors or costs.

### State Machine

```
CLOSED (normal)
    │
    │ N consecutive failures (default: 3)
    ▼
OPEN (hooks disabled for this script)
    │
    │ Recovery period elapsed (default: 60s)
    ▼
HALF_OPEN (one trial execution allowed)
    │
    ├─ success → CLOSED
    └─ failure → OPEN
```

### Wrapper Usage

The wrapper is invoked as:
```bash
circuit_breaker_wrapper.py -- uv run <hook_script.py>
```

It uses `--` to separate its own args from the wrapped script's command. The breaker state is stored per-script in `~/.claude/circuit_breakers/`.

### Checking Status

```bash
ls ~/.claude/circuit_breakers/
cat ~/.claude/circuit_breakers/<script_name>.json
```

Each file contains: `{"state": "closed", "failures": 0, "last_failure": null}`.

---

## 5. Knowledge Pipeline

Three-stage pipeline for persistent cross-session learning.

### Stages

```
SessionStart  →  inject_relevant.py   → INJECT: retrieve + inject past learnings
PostToolUse   →  extract_learnings.py → EXTRACT: pull insights from tool outputs
Stop          →  store_learnings.py   → STORE: persist extracted insights to DB
```

### Database

Location: `~/.claude/data/knowledge-db/knowledge.db`

Schema:
```sql
CREATE TABLE learnings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,          -- ISO 8601
    session_id  TEXT,
    project     TEXT,                   -- inferred from cwd
    category    TEXT,                   -- LEARNED | PATTERN | INVESTIGATION | etc.
    content     TEXT NOT NULL,          -- the learning text
    tags        TEXT,                   -- comma-separated
    source_tool TEXT                    -- which tool triggered extraction
);

CREATE VIRTUAL TABLE learnings_fts USING fts5(
    content,
    tags,
    content='learnings',
    content_rowid='id'
);
```

### inject_relevant.py (SessionStart)

Searches the FTS5 index using terms extracted from the current working directory path and recent git activity. Injects up to 5 relevant learnings as `additionalContext`.

Configurable:
```yaml
# ~/.claude/knowledge_pipeline.yaml
evolve:
  enabled: true
  max_injections: 5
  relevance_threshold: 0.6
  recency_boost: 0.2
  include_categories: [LEARNED, PATTERN, INVESTIGATION]
  lookback_days: 30
```

### extract_learnings.py (PostToolUse)

Fires on Bash/Write/Edit. Analyzes tool outputs for extractable insights (error patterns, successful solutions, new patterns discovered). Stores results in-memory for the current session.

### store_learnings.py (Stop)

At session end, writes all extracted learnings to the SQLite database.

### Manual Queries

Use the `knowledge-db` skill for guided queries, or query directly:
```bash
sqlite3 ~/.claude/data/knowledge-db/knowledge.db \
  "SELECT content FROM learnings_fts WHERE learnings_fts MATCH 'your search terms' LIMIT 10;"
```

---

## 6. Session Lifecycle

What happens from the moment you open Claude Code to when you close it.

```
1. SESSION OPEN
   └─ SessionStart hooks fire (in order):
       a. session_startup.py        — init locks, verify skills, check docs, load prime cache
       b. inject_relevant.py        — inject relevant past learnings
       c. repo_map.py               — inject symbol index if ≥200 source files

2. USER TYPES PROMPT
   └─ UserPromptSubmit hooks fire:
       a. analyze_request.py        — classify prompt, inject Caddy analysis
       b. auto_delegate.py          — inject strategy recommendation

3. CLAUDE CALLS A TOOL
   └─ PreToolUse hooks fire:
       a. session_lock_manager.py   — lock files being accessed (Read/Edit/Write)
       b. unified-damage-control.py — block dangerous commands (Bash/Edit/Write)
       c. auto_review_team.py       — coordination (Bash)

4. TOOL EXECUTES

5. TOOL COMPLETES
   └─ PostToolUse hooks fire:
       a. session_lock_manager.py   — release locks
       b. context-bundle-logger.py  — snapshot session state
       c. auto_cost_warnings.py     — check budget
       d. auto_error_analyzer.py    — analyze failures (Bash only)
       e. auto_refine.py            — trigger refine (Write/Edit)
       f. auto_dependency_audit.py  — check deps (Write/Edit)
       g. auto_context_manager.py   — context health
       h. auto_voice_notifications.py — voice alerts
       i. auto_team_review.py       — team review (Write/Edit)
       j. extract_learnings.py      — extract insights

   → Repeat steps 2–5 for each message in the session

6. CONTEXT FILLS UP
   └─ PreCompact hook fires:
       a. pre_compact_preserve.py   — save task state, file paths, decisions

7. SESSION CLOSES
   └─ Stop hooks fire:
       a. session_lock_manager.py   — cleanup all locks
       b. check_lthread_progress.py — validate RLM state
       c. store_learnings.py        — persist knowledge to DB
```

---

## 7. Model Tiers

Agents are mapped to models in `data/model_tiers.yaml` for cost optimization (50-60% savings).

| Tier | Model | Agents | Use Case |
|------|-------|--------|----------|
| Opus | claude-opus-4-6 | orchestrator, project-architect, critical-analyst | Critical thinking, architectural decisions |
| Sonnet | claude-sonnet-4-5-20250929 | researcher, meta-agent, scout-report-suggest, rlm-root | Heavy analysis, research, implementation |
| Haiku | claude-haiku-4-5-20251001 | docs-scraper | Simple, high-volume tasks |

### Tier Assignment Logic

- **Opus** for agents that make irreversible architectural decisions or need the highest reasoning quality
- **Sonnet** for agents that do substantial work but don't require Opus-level judgment
- **Haiku** for agents with simple, repetitive tasks where cost matters more than depth

To change a tier, edit `data/model_tiers.yaml` and run `bash install.sh`.

---

## 8. Damage Control

The unified-damage-control hook (`global-hooks/damage-control/unified-damage-control.py`) runs on every `Bash`, `Edit`, and `Write` tool call. It checks against patterns defined in `global-hooks/damage-control/patterns.yaml`.

### What Is Blocked

**Hard blocks (exit code 2)**:

| Category | Examples |
|----------|---------|
| Destructive file ops | `rm -rf`, `rm -r`, `rm --force`, `sudo rm` |
| Permission escalation | `chmod 777`, recursive `chown root` |
| Git history rewrites | `git reset --hard`, `git push --force`, `git filter-branch` |
| System destruction | `mkfs.*`, `dd of=/dev/*` |
| Process termination | `kill -9 -1`, `killall -9` |
| Shell obfuscation | `eval `, `bash -c `, `base64 -d \| bash`, `curl \| bash` |
| Cloud destructive ops | AWS/GCP/Firebase/Vercel/Docker/Kubernetes delete commands |
| Database wipes | `TRUNCATE TABLE`, `DROP DATABASE`, `redis-cli FLUSHALL` |
| IaC teardown | `terraform destroy`, `pulumi destroy` |

**Confirmation required (ask: true)**:

| Category | Examples |
|----------|---------|
| Git safety | `git checkout -- .`, `git restore .`, `git stash drop` |
| Branch deletion | `git branch -D`, `git push origin --delete` |
| SQL with ID | `DELETE FROM table WHERE id = X` |

### Protected Paths

**Zero-access paths** (no read, write, or any operation):
- `.env`, `.env.*` — environment files with secrets
- `~/.ssh/`, `~/.gnupg/` — SSH/GPG keys
- `~/.aws/`, `~/.config/gcloud/`, `~/.azure/` — cloud credentials
- `~/.kube/`, `*.tfstate` — Kubernetes and Terraform state
- `*.pem`, `*.key`, `*.p12`, `*.pfx` — TLS certificates/keys
- `*-credentials.json`, `serviceAccountKey.json` — service account keys

**Read-only paths** (can read, cannot write):
- `/etc/`, `/usr/`, `/bin/`, `/sbin/` — system directories
- `~/.bashrc`, `~/.zshrc`, `~/.profile` — shell config
- `package-lock.json`, `yarn.lock`, `uv.lock`, `*.lock` — lockfiles
- `*.min.js`, `*.min.css`, `*.bundle.js` — compiled/minified files
- `dist/`, `build/`, `node_modules/`, `.venv/` — build artifacts

**No-delete paths** (can read/write, cannot delete):
- `~/.claude/`, `CLAUDE.md`, `global-hooks/damage-control/` — framework core
- `LICENSE`, `README.md`, `CONTRIBUTING.md` — project docs
- `.git/`, `.gitignore` — git infrastructure

---

## 9. Configuration

### Files and Their Purposes

| File | Edit This? | Purpose |
|------|-----------|---------|
| `templates/settings.json.template` | ✅ YES | Hook registration, permissions, model, status line |
| `~/.claude/settings.json` | ❌ NO | Generated from template by `bash install.sh` |
| `data/model_tiers.yaml` | ✅ YES | Agent-to-model tier mapping |
| `data/caddy_config.yaml` | ✅ YES | Caddy classifier behavior |
| `~/.claude/knowledge_pipeline.yaml` | ✅ YES | Knowledge pipeline settings |
| `global-hooks/damage-control/patterns.yaml` | ✅ YES | Blocked/confirmed command patterns |

### Workflow: Making Config Changes

1. Edit `templates/settings.json.template` (for hook changes) OR the relevant YAML file
2. Run `bash install.sh` to apply (regenerates `settings.json`, relinks symlinks)
3. Start a new Claude Code session

**Never edit `~/.claude/settings.json` directly** — it is overwritten by `install.sh`.

### Permissions Mode

The framework runs in **Yolo mode** (`"allow": ["*"]`):
- All tool permissions are pre-granted
- No permission prompts for safe operations
- Destructive operations are blocked at the hook level, not the permission level
- Sandbox is disabled

This is intentional: permission prompts interrupt flow. The hook system provides defense-in-depth without interrupting the user.

---

## 10. Troubleshooting

### Hook is firing but doing nothing

1. Check circuit breaker state:
   ```bash
   ls ~/.claude/circuit_breakers/
   cat ~/.claude/circuit_breakers/<hook_name>.json
   ```
2. If state is `"open"`, the hook is disabled. Wait for recovery period or delete the state file.

### Install fails with "hook file not found"

The template references a hook file that doesn't exist. Check:
```bash
grep "__REPO_DIR__" templates/settings.json.template
```
Each path after `__REPO_DIR__/` must exist as a file in the repository.

### Damage control blocking a legitimate command

Edit `global-hooks/damage-control/patterns.yaml`:
- Move the pattern to `ask: true` instead of hard-blocking
- Or add a more specific pattern that won't match your legitimate command
- Run `bash install.sh` to apply (patterns.yaml is read at hook runtime, no reinstall needed)

### Knowledge pipeline not injecting anything

The DB might be empty (first session) or the FTS query might not match. Check:
```bash
sqlite3 ~/.claude/data/knowledge-db/knowledge.db "SELECT count(*) FROM learnings;"
```
If 0, no learnings have been stored yet. Run a few sessions with the framework active.

### Session startup hook errors

Errors from `session_startup.py` appear in Claude Code's hook error display. Common causes:
- Missing symlinks (run `bash install.sh` again)
- `uv` not installed or not in PATH
- Python < 3.10

### RepoMap not appearing for large repos

Check:
1. File count: `find . -name "*.py" -o -name "*.ts" -o -name "*.js" | wc -l`
2. Cache: `cat ~/.claude/REPO_MAP.md | head -5`
3. If cache exists but symbol map is empty, tree-sitter may have failed to install.
   The hook falls back to Python `ast` for `.py` files only.

### Auto-voice notifications speaking at wrong times

Edit `global-hooks/framework/notifications/auto_voice_notifications.py` to adjust the trigger conditions, or disable via the circuit breaker by creating an `open` state file.

---

## Appendix: Directory Structure

```
global-hooks/
  damage-control/           PreToolUse: Bash/Edit/Write protection
    unified-damage-control.py
    patterns.yaml
  observability/            Logging and monitoring
  framework/
    automation/             Auto-delegation hooks
      auto_cost_warnings.py
      auto_dependency_audit.py
      auto_error_analyzer.py
      auto_refine.py
      auto_review_team.py
      auto_team_review.py
      repo_map.py           ← NEW: TreeSitter symbol index
    caddy/                  UserPromptSubmit classifier
      analyze_request.py
      auto_delegate.py
      skill_auditor.py
    context/                Context management
      auto_context_manager.py
      pre_compact_preserve.py
    guardrails/             Circuit breakers
      circuit_breaker.py
      circuit_breaker_wrapper.py
      hook_state_manager.py
    knowledge/              Knowledge pipeline
      extract_learnings.py
      inject_relevant.py
      store_learnings.py
    notifications/          Voice/visual alerts
      auto_voice_notifications.py
    session/                Session management
      session_lock_manager.py
      session_startup.py
    teams/                  Team coordination
    validators/             Validation hooks
      check_lthread_progress.py
  context-bundle-logger.py  PostToolUse: session snapshots

global-agents/              8 agent definitions
global-commands/            14 slash commands
global-skills/              6 skills
global-status-lines/        Status bar customization
apps/observability/         Vue 3 + Bun dashboard (ports 4000/5173)
data/
  knowledge-db/             SQLite FTS5 database
  model_tiers.yaml          Agent-to-model mapping
  caddy_config.yaml         Caddy classifier config
templates/
  settings.json.template    Edit this, not settings.json
```
