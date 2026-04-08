# Team Coordination Hooks

Hooks for managing team-based agent workflows with quality gates and coordination enforcement.

## Overview

These hooks enable safe, coordinated multi-agent execution with clear separation of concerns:
- **Lead agent** coordinates and delegates
- **Teammate agents** implement and execute
- **Context-manager** tracks progress and creates summaries
- **Hooks** enforce rules and validate deliverables

## Hooks

### 1. teammate_monitor.py (TeammateIdle Hook)

**Purpose**: Validates teammate work before allowing them to go idle.

**Triggers**: When a teammate agent is about to stop active work.

**Checks**:
- Task completion status
- File changes made
- Deliverables present
- No blockers remaining

**Actions**:
- Exit 0: Allow idle (work complete)
- Exit 1: Warn but allow (minor issues)
- Exit 2: Block idle + send feedback (work incomplete)

**Integration**:
- Notifies context-manager to create summaries
- Logs teammate activity
- Tracks task completion

**Example**:
```json
{
  "message": "Task incomplete",
  "issues": ["No file changes detected"],
  "action": "Please complete the task before going idle"
}
```

### 2. task_validator.py (TaskCompleted Hook)

**Purpose**: Verifies task completion validity before marking as done.

**Triggers**: When `TaskUpdate` changes status to `completed`.

**Checks**:
- File changes actually made
- Tests pass (if applicable)
- Task requirements met
- No obvious errors

**Actions**:
- Exit 0: Allow completion (valid)
- Exit 1: Warn but allow (minor issues)
- Exit 2: Block completion (invalid)

**Integration**:
- Updates context-manager with validation results
- Logs validation events
- Can trigger remediation workflows

**Example**:
```json
{
  "message": "Task validation failed",
  "issues": ["Tests failing: test_auth.py::test_login"],
  "action": "Fix failing tests before completing"
}
```

### 3. delegate_mode_enforcer.py (PreToolUse:Write/Edit Hook)

**Purpose**: Prevents lead agent from implementing when teammates are active.

**Triggers**: Before `Write` or `Edit` tool use.

**Checks**:
- Is current agent a teammate? (Allow)
- Are teammates currently active?
- Is file coordination-only? (Allow)
- Is lead implementing? (Block if teammates active)

**Actions**:
- Exit 0: Allow (safe to write/edit)
- Exit 1: Warn (edge case)
- Exit 2: Block (lead must delegate, not implement)

**Coordination-only files** (allowed for lead):
- `data/team-context/`
- `data/team-sessions/`
- `data/team-communications/`
- `.claude/plans/`
- `.claude/team/`

**Example**:
```json
{
  "message": "Lead cannot implement while teammates active",
  "active_teammates": "builder, validator",
  "action": "Use Task tools to delegate instead",
  "allowed_actions": [
    "Use TaskCreate to create new tasks",
    "Use TaskUpdate to update task status",
    "Write to coordination files"
  ]
}
```

### 4. anti_loop_team.py (PreToolUse:Task Hook)

**Purpose**: Prevents recursive team creation and resource exhaustion.

**Triggers**: Before `Task` tool use for agent delegation.

**Checks**:
- Is teammate trying to spawn sub-teams? (Block)
- Is hierarchy depth exceeded? (Block)
- Is active agent limit reached? (Block)
- Approaching limits? (Warn)

**Limits** (configurable in code):
- `MAX_HIERARCHY_DEPTH`: 2 (Main -> Team -> Stop)
- `MAX_ACTIVE_AGENTS`: 8 (total concurrent)
- `WARN_THRESHOLD`: 6 (warn when approaching)

**Actions**:
- Exit 0: Allow delegation (safe)
- Exit 1: Warn (approaching limits)
- Exit 2: Block (limits exceeded)

**Example**:
```json
{
  "message": "Delegation blocked - safety limit reached",
  "reason": "Teammate agent 'builder' cannot spawn sub-teams",
  "current_state": {
    "hierarchy_depth": 1,
    "active_agents": 3
  }
}
```

## Integration with settings.json

Add to your `settings.json` (or update the template):

```json
{
  "hooks": {
    "TeammateIdle": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run __REPO_DIR__/global-hooks/framework/teams/teammate_monitor.py",
            "timeout": 10,
            "statusMessage": "Validating teammate work..."
          }
        ]
      }
    ],
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run __REPO_DIR__/global-hooks/framework/teams/task_validator.py",
            "timeout": 10,
            "statusMessage": "Validating task completion..."
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "uv run __REPO_DIR__/global-hooks/framework/teams/delegate_mode_enforcer.py",
            "timeout": 5,
            "statusMessage": "Checking delegation mode..."
          }
        ]
      },
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "uv run __REPO_DIR__/global-hooks/framework/teams/delegate_mode_enforcer.py",
            "timeout": 5,
            "statusMessage": "Checking delegation mode..."
          }
        ]
      },
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "uv run __REPO_DIR__/global-hooks/framework/teams/anti_loop_team.py",
            "timeout": 5,
            "statusMessage": "Checking delegation safety..."
          }
        ]
      }
    ]
  }
}
```

## Directory Structure

```
global-hooks/framework/teams/
├── README.md                      # This file
├── teammate_monitor.py            # TeammateIdle hook
├── task_validator.py              # TaskCompleted hook
├── delegate_mode_enforcer.py      # PreToolUse:Write/Edit hook
└── anti_loop_team.py              # PreToolUse:Task hook

~/.claude/data/
├── team-sessions/                 # Active teammate sessions
├── team-notifications/            # Cross-agent notifications
└── team-context/                  # Context-manager summaries

~/.claude/logs/teams/
├── teammate_monitor.jsonl         # Teammate activity log
├── task_validator.jsonl           # Task validation log
├── delegate_mode_enforcer.jsonl   # Delegation enforcement log
└── anti_loop_team.jsonl           # Team safety check log
```

## Workflow Example

### Scenario: Lead delegates to builder and validator

1. **Lead creates tasks**:
   ```
   TaskCreate: "Implement user authentication"
   TaskCreate: "Validate authentication implementation"
   ```

2. **Lead delegates to builder**:
   ```
   Task(agent="builder", task_id="task-1")
   ```
   - `anti_loop_team.py`: Checks team hierarchy (depth=1, OK)
   - `anti_loop_team.py`: Checks active agents (count=1, OK)
   - **Result**: Delegation allowed

3. **Lead tries to implement directly**:
   ```
   Write(file_path="src/auth.ts", content="...")
   ```
   - `delegate_mode_enforcer.py`: Detects active teammate (builder)
   - `delegate_mode_enforcer.py`: Lead is implementing, not coordinating
   - **Result**: BLOCKED - "Use Task tools to delegate instead"

4. **Builder completes task**:
   ```
   TaskUpdate(task_id="task-1", status="completed")
   ```
   - `task_validator.py`: Checks file changes (✓)
   - `task_validator.py`: Runs tests (✓)
   - `task_validator.py`: Validates deliverables (✓)
   - **Result**: Task completion allowed
   - Notifies context-manager to create summary

5. **Builder goes idle**:
   - `teammate_monitor.py`: Checks task status (completed ✓)
   - `teammate_monitor.py`: Notifies context-manager
   - **Result**: Idle allowed
   - Context-manager creates compressed summary for lead

6. **Lead can now implement** (no active teammates):
   ```
   Write(file_path="docs/auth.md", content="...")
   ```
   - `delegate_mode_enforcer.py`: No active teammates
   - **Result**: Write allowed

## Context-Manager Integration

All hooks notify the `context-manager` agent by writing to:
```
~/.claude/data/team-notifications/{event}.json
```

The context-manager reads these notifications and creates summaries in:
```
~/.claude/data/team-context/{task-id}.md
```

This allows the lead agent to understand what happened without loading full context.

## Logging and Observability

All hooks log to `~/.claude/logs/teams/` in JSONL format:

```jsonl
{"timestamp": "2026-02-12T...", "event": "teammate_idle", "teammate": "builder", "task_id": "task-1"}
{"timestamp": "2026-02-12T...", "event": "task_completed_validation", "task_id": "task-1", "validation": {"valid": true}}
{"timestamp": "2026-02-12T...", "event": "delegate_mode_enforcement", "action": "blocked", "agent": "main"}
{"timestamp": "2026-02-12T...", "event": "delegation_safety_check", "action": "allowed", "target": "builder"}
```

Use these logs for:
- Debugging team coordination issues
- Understanding delegation patterns
- Auditing who did what
- Identifying bottlenecks

## Customization

### Adjusting Team Size Limits

Edit `anti_loop_team.py`:
```python
MAX_HIERARCHY_DEPTH = 2  # Main -> Team -> Stop
MAX_ACTIVE_AGENTS = 8    # Total concurrent agents
WARN_THRESHOLD = 6       # Warn when approaching
```

### Adding Custom Validation

Edit `task_validator.py` to add project-specific checks:
```python
def check_custom_validation(task: dict) -> dict:
    # Your custom validation logic
    pass
```

### Defining Coordination-Only Files

Edit `delegate_mode_enforcer.py`:
```python
coordination_patterns = [
    "data/team-context/",
    "your/custom/path/",
]
```

## Troubleshooting

### Hook not triggering

Check that hooks are registered in `settings.json` with correct matchers and paths.

### False positives (blocking valid work)

Check logs to see why hook blocked:
```bash
tail -f ~/.claude/logs/teams/*.jsonl
```

### Teammates not detected as active

Verify session files exist:
```bash
ls ~/.claude/data/team-sessions/
```

### Context-manager not receiving notifications

Check notification files:
```bash
ls ~/.claude/data/team-notifications/
```

## Best Practices

1. **Always use TaskCreate** for teammate work
2. **Let teammates implement**, lead coordinates
3. **Monitor logs** for delegation patterns
4. **Review summaries** from context-manager
5. **Adjust limits** based on your hardware
6. **Test hooks** before production use

## Exit Codes

All hooks follow this convention:
- **0**: Allow (operation is safe)
- **1**: Warn (operation allowed, but issues detected)
- **2**: Block (operation is unsafe, provide feedback)

## Dependencies

- Python 3.11+
- `uv` for script execution
- Claude Code hooks system
- Task tools (TaskCreate, TaskUpdate, TaskGet)
- Agent system (builder, validator, context-manager)

## See Also

- `global-agents/team/context-manager.md` - Context-manager agent
- `global-agents/team/builder.md` - Builder agent
- `global-agents/team/validator.md` - Validator agent
- `global-hooks/framework/ANTI_LOOP_GUARDRAILS.md` - Anti-loop patterns
- `templates/settings.json.template` - Settings configuration
