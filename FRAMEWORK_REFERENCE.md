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

## 10. Context Compaction

Claude Code automatically compacts the conversation context when it approaches the context window limit. Without intervention, compaction causes the agent to "forget" what tasks are in progress, which files were modified, and what decisions were made. The `pre_compact_preserve.py` hook prevents this.

### How It Works

The `PreCompact` hook fires before any compaction (auto or manual). The hook reads the live session transcript (JSONL file), extracts critical state, then injects that state as `additionalContext` so the compaction summary includes it.

```
Context approaches limit
       │
       ▼
PreCompact hook fires
  └─ pre_compact_preserve.py reads transcript JSONL
       ├─ Scans TaskCreate/TaskUpdate calls → finds in-progress tasks
       ├─ Scans Write/Edit calls → finds modified files this session
       ├─ Scans Bash calls → finds test commands run
       └─ Extracts key decisions from assistant messages
       │
       ▼
Injects preservation block into compaction prompt:
  "PRESERVE ACROSS COMPACTION:
   Active tasks: [task 1, task 2, ...]
   Modified files: [src/auth.py, tests/test_auth.py, ...]
   Last test command: pytest tests/ -v
   Key decisions: ..."
       │
       ▼
Claude Code compacts, but the summary retains the extracted state
       │
       ▼
Work continues with no lost context
```

### What Gets Preserved

| Item | Source | Example |
|------|--------|---------|
| Active tasks | TaskCreate/TaskUpdate tool calls | "Implement OAuth2 login [in_progress]" |
| Modified files | Write/Edit tool calls | `src/auth.py`, `templates/login.html` |
| Test commands | Bash tool calls matching `pytest/jest/npm test` | `pytest tests/test_auth.py -v` |
| Key decisions | Assistant messages with decision language | "Decided to use JWT over sessions because..." |

### Without This Hook

Without `pre_compact_preserve.py`, after compaction Claude would:
- Ask "what are we working on?" (lost task list)
- Re-read files it already read (wasted tokens)
- Forget which tests were passing/failing
- Make decisions inconsistent with earlier choices

### Configuration

The hook is non-configurable — it runs automatically on every `PreCompact` event and always exits 0 (never blocks compaction).

---

## 11. Multi-Agent Teams

The framework includes a full team coordination system for orchestrating multiple Claude agents in parallel. The `teams/` directory provides four hooks that enforce clean separation of concerns between the lead agent and its teammates.

### Team Architecture

```
Lead Agent (coordinates)
    │
    ├─ Task(agent="builder")   → Builder (implements)
    ├─ Task(agent="validator") → Validator (verifies)
    └─ Task(agent="researcher")→ Researcher (analyzes)

Rules enforced by hooks:
  - Lead agent cannot Write/Edit when teammates are active
  - Teammates cannot spawn their own sub-teams
  - Tasks must pass validation before marking completed
  - Teammates must validate deliverables before going idle
```

### Team Hooks (in `global-hooks/framework/teams/`)

These four hooks are **available but not registered in `settings.json.template` by default** — they're opt-in for projects that use the team system. Add them to your template to enable.

#### anti_loop_team.py (PreToolUse: Task)

Prevents recursive team creation and resource exhaustion.

- Blocks teammates from spawning sub-teams (only lead can delegate)
- Enforces hierarchy depth limit: `MAX_HIERARCHY_DEPTH = 2` (Main → Team → Stop)
- Enforces concurrent agent limit: `MAX_ACTIVE_AGENTS = 8`
- Warns at `WARN_THRESHOLD = 6` active agents

#### delegate_mode_enforcer.py (PreToolUse: Write/Edit)

Forces the lead agent into coordination-only mode while teammates are active.

- Checks if any teammate sessions are active
- If yes: blocks Write/Edit on implementation files
- If yes: allows Write/Edit on coordination-only paths: `data/team-context/`, `.claude/plans/`
- Lead must use Task tool to delegate instead of implementing directly

This prevents context conflicts where both the lead and a teammate modify the same file simultaneously.

#### task_validator.py (TaskCompleted)

Runs when a task is marked `completed` via `TaskUpdate`. Verifies the task is actually done.

Checks:
- File changes were actually made (not just a status update)
- Tests pass (if applicable)
- Task requirements in the description are met
- No obvious errors remain

Exits 2 (blocks completion) if validation fails, feeding reason back to Claude.

#### teammate_monitor.py (TeammateIdle)

Runs when a teammate is about to go idle. Validates work is complete before allowing it.

Checks:
- Task status is completed (not still in_progress)
- Deliverables are present
- No blockers remain

Also triggers context-manager to create a compressed summary of the teammate's work, so the lead can load it efficiently.

### Registering Team Hooks

To opt in, add to `templates/settings.json.template`:

```json
"TeammateIdle": [{"hooks": [{"type": "command", "command": "uv run __REPO_DIR__/global-hooks/framework/teams/teammate_monitor.py", "timeout": 10}]}],
"TaskCompleted": [{"hooks": [{"type": "command", "command": "uv run __REPO_DIR__/global-hooks/framework/teams/task_validator.py", "timeout": 10}]}],
```

And add to `PreToolUse`:
```json
{"matcher": "Write|Edit", "hooks": [{"type": "command", "command": "uv run __REPO_DIR__/global-hooks/framework/teams/delegate_mode_enforcer.py", "timeout": 5}]},
{"matcher": "Task", "hooks": [{"type": "command", "command": "uv run __REPO_DIR__/global-hooks/framework/teams/anti_loop_team.py", "timeout": 5}]}
```

### Auto Team Review (auto_team_review.py)

This PostToolUse hook (Write/Edit, already registered) detects when team work completes and automatically runs a quality stack:
- code-review skill (Sonnet)
- security-scanner skill (Opus)
- test-generator skill (Sonnet)

Logic: simple tasks (no team) → skip auto-review (save tokens). Complex tasks (TeamCreate detected in session) → run full review stack after completion (~$2-4 per team).

### Auto Review Team (auto_review_team.py)

This PreToolUse hook (Bash, already registered) detects PR creation commands (`gh pr create`, `git push` with pr/ branch) and offers to spawn a parallel review team:
- Security reviewer (Opus) — vulnerabilities, auth issues
- Performance reviewer (Sonnet) — bottlenecks, complexity
- Architecture reviewer (Opus) — design patterns, maintainability

Always exits 0 (never blocks the PR command, just offers the team).

### Team Logs

All team hooks write JSONL to `~/.claude/logs/teams/`:
```bash
tail -f ~/.claude/logs/teams/anti_loop_team.jsonl
tail -f ~/.claude/logs/teams/task_validator.jsonl
```

---

## 12. Context Bundle / Session Restore

The context bundle system creates a "save game" of what the agent has read and done, so a new session can be restored to the same knowledge state with zero token waste.

### How Bundles Work

`context-bundle-logger.py` runs on every PostToolUse event (Bash/Write/Edit). It logs:
- Every file Read, Edit, Write, NotebookEdit this session
- The content read/written and timestamps
- Tool successes/failures

Bundles are stored at `~/.claude/bundles/{session_id}.json`.

### Restoring a Bundle

Use the `/loadbundle` command at the start of a new session:

```
/loadbundle
```

This reads the most recent bundle file and injects all the file content Claude previously read back into context — without re-reading each file. Instead of 10 Read tool calls (10 × context cost), it's one bundle load.

**Token savings**: For a session that read 20 files totaling 3000 lines, restoring from bundle costs ~200 tokens vs ~6000 tokens to re-read.

### Bundle Location

```bash
ls ~/.claude/bundles/
cat ~/.claude/bundles/<session_id>.json | python3 -m json.tool | head -50
```

---

## 13. Auto-Hooks Ecosystem

The PostToolUse hooks form an automation layer that fires background intelligence after every tool call. Here's what each actually does:

### auto_error_analyzer.py (PostToolUse: Bash)

Fires after every Bash tool call. If the exit code is non-zero:
1. Reads the error output
2. Identifies the error category (syntax, import, permission, network, etc.)
3. Injects a brief diagnosis and suggested fix as `additionalContext`

This means Claude sees "PermissionError: [Errno 13]" AND the diagnosis "File permission issue — check file ownership with `ls -la`" in the same turn.

### auto_refine.py (PostToolUse: Write/Edit)

Fires after every Write or Edit. Checks if the written content has obvious issues (syntax errors detectable without running code, incomplete implementations, TODO markers). If issues are found, injects a suggestion to run `/refine`.

### auto_dependency_audit.py (PostToolUse: Write/Edit)

Fires when `package.json`, `pyproject.toml`, `requirements.txt`, or similar dependency files are written/edited. Checks for:
- Known vulnerable package versions
- Outdated major versions
- Missing security-relevant packages

Timeout is 15s because it may call external APIs.

### auto_cost_warnings.py (PostToolUse: *)

Fires after every tool call. Reads the session cost from the environment/session state. If cumulative cost exceeds the configured threshold, injects a warning: "Session cost is $X.XX — consider compacting context."

### auto_context_manager.py (PostToolUse: Bash/Write/Edit)

Monitors context health (token usage as a percentage of the window). When usage exceeds a threshold:
- Suggests specific files that can be dropped from context
- Suggests running `/prime` to reload only what's needed
- May trigger pre-compact preservation proactively

### auto_voice_notifications.py (PostToolUse: Bash/Write/Edit)

Fires on macOS via the `say` command (no-op on other platforms). Speaks an alert when:
- A long-running operation completes (> configured threshold)
- An error requires attention
- A session milestone is reached

Tuned to avoid false positives — only speaks for genuinely noteworthy events.

---

## 14. Commands Reference

All 13 slash commands available after installation:

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/prime` | Load project context with git-aware caching | Start of every session; instant on repeat calls |
| `/orchestrate "goal"` | Multi-agent coordination via orchestrator agent (Opus) | Complex tasks with 5+ steps or multiple concerns |
| `/research "topic"` | Delegate heavy research to sub-agent | Exploring unknown codebases, documentation lookup |
| `/rlm` | Recursive Language Model controller | Infinite-scale codebase analysis without context rot |
| `/fusion` | Best-of-N parallel agents, synthesized | Critical code where correctness matters most |
| `/plan "feature"` | Engineering implementation planning | Before starting a new feature or refactor |
| `/review` | Code review via code-review skill | After writing code; pre-PR quality check |
| `/refine` | Auto-fix review findings | After `/review` identifies issues |
| `/test` | Run or generate tests | TDD workflow; adding coverage to existing code |
| `/commit` | Smart commit with conventional message | After completing a unit of work |
| `/debug` | Diagnose and fix errors | When stuck on a failing test or error |
| `/costs` | API usage and cost tracking | Budget monitoring |
| `/loadbundle` | Restore agent intelligence from bundle | New session continuing previous work |

### Command Implementation

Each command is a Markdown file in `global-commands/` (symlinked to `~/.claude/commands/`). The file contains a system prompt that Claude follows when the command is invoked. Commands are not scripts — they're instructions.

To add a custom command:
1. Create `global-commands/my-command.md`
2. Run `bash install.sh` to symlink it

---

## 15. Skills Reference

Six skills available after installation (symlinked to `~/.claude/skills/`):

| Skill | Invocation | Model | Purpose |
|-------|-----------|-------|---------|
| `code-review` | `/review` or `use code-review` | Sonnet | Bugs, security, performance, style |
| `error-analyzer` | `/debug` or `use error-analyzer` | Sonnet | Root cause analysis for errors/exceptions |
| `knowledge-db` | `use knowledge-db` | Haiku | Query/store persistent SQLite knowledge |
| `refactoring-assistant` | `use refactoring-assistant` | Sonnet | Safe refactoring with incremental changes |
| `security-scanner` | `use security-scanner` | Opus | Vulnerability detection, OWASP top 10 |
| `test-generator` | `/test` or `use test-generator` | Sonnet | Comprehensive test suite generation |

Skills are Markdown files with a system prompt. The Caddy classifier automatically suggests relevant skills based on the user's prompt.

### Skills Integrity Verification

At session start, `session_startup.py` verifies the SHA-256 hash of each skill file against a lock file. If a skill has been tampered with, it's flagged before being loaded. The lock file is generated by `scripts/generate_skills_lock.py`.

---

## 16. Observability Dashboard

A Vue 3 + Bun app provides real-time visibility into hook execution, agent activity, and cost tracking.

### Running the Dashboard

```bash
cd apps/observability
bun install
bun run dev
```

- **Frontend**: http://localhost:5173 (Vue 3, Vite)
- **Backend**: http://localhost:4000 (Bun HTTP server)

### What It Shows

- **Hook Activity**: Live feed of every hook execution, its exit code, and any output
- **Cost Tracking**: Per-session and cumulative API costs
- **Agent Activity**: Which sub-agents have been spawned and their completion status
- **Error Log**: Aggregated errors from all hook executions
- **Context Health**: Token usage over time within a session

### Data Source

The observability backend reads from the same JSONL logs that the hooks write:
- `~/.claude/logs/caddy/analyses.jsonl`
- `~/.claude/logs/teams/*.jsonl`
- `~/.claude/bundles/`

---

## 17. Status Line

The framework includes a custom status line (`global-status-lines/mastery/v9/`) that replaces Claude Code's default status bar.

### What It Shows

```
[main ✓] 3 agents | $0.42 | 47% ctx | 14:32
```

- **Git branch + status**: current branch, dirty/clean indicator
- **Active agents**: count of sub-agents spawned this session
- **Session cost**: cumulative API cost
- **Context usage**: percentage of context window used
- **Time**: current time

### Configuration

The status line is registered in `templates/settings.json.template`:
```json
"statusLine": {
  "type": "command",
  "command": "uv run __REPO_DIR__/global-status-lines/mastery/status_line_custom.py",
  "padding": 0
}
```

It runs as a command and outputs a single line. Keep it fast (< 100ms) — it fires frequently.

---

## 18. Troubleshooting

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
      repo_map.py           TreeSitter symbol index (≥200 files)
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
