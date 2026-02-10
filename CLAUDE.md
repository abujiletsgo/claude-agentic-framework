# Claude Agentic Framework

Consolidated agentic engineering system. One repo, one install, one source of truth.

## Repo Structure

```
global-hooks/        4 namespaces: mastery/ observability/ damage-control/ framework/
global-agents/       28 agents (13 root + 13 crypto + 2 team)
global-commands/     29 commands + agent_prompts/ + bench/
global-skills/       5 skills (prime, meta-skill, video-processor, worktree-manager, create-worktree)
global-output-styles/ 11 styles
global-status-lines/ mastery/(9 versions) + observability/(2)
apps/observability/  Vue 3 dashboard + Bun server
guides/              15 engineering guides
templates/           settings.json.template (__REPO_DIR__ placeholder)
install.sh           Symlinks + generates ~/.claude/settings.json
```

## Operational Mode: Full Autonomous (Yolo)

Permissions: `"allow": ["*"]` with deny rules for destructive ops and ask for force-push/hard-reset. Damage-control hooks + LLM prompt reviewers provide safety net on Bash/Edit/Write.

## Agentic Execution Protocol

### 1. Task Decomposition — Always Use Task Lists
For any non-trivial task (3+ steps), immediately create a TaskList:
- Break work into discrete, parallelizable units
- Mark tasks in_progress before starting, completed when done
- This preserves context across compactions and keeps execution efficient

### 2. Parallel Execution — Maximize Throughput
- Launch independent subagents simultaneously using multiple Task tool calls in a single message
- Use `run_in_background: true` for long-running agents
- Never serialize work that can run in parallel
- Agent types available: Bash, Explore, Plan, researcher, orchestrator, rlm-root, general-purpose

### 3. Orchestrator Pattern — Delegate Complex Tasks
For multi-faceted tasks, use the orchestrator agent or /orchestrate command:
- Orchestrator plans, delegates to specialized agents (researcher, builder, validator), and synthesizes
- You give high-level goals, orchestrator handles coordination
- Each subagent gets isolated context (no cross-contamination)

### 4. Ralph Loops — Context-Efficient Iteration
For tasks that may exceed context window or need iterative refinement:
- Use /rlm command or rlm-root agent
- Each iteration gets fresh context, reads progress from filesystem
- State persists via progress files, not context accumulation
- Circuit breaker after N iterations prevents infinite loops

### 5. Validation Protocol — Verify Everything
After any significant implementation:
- Spawn a **validator subagent** (global-agents/team/validator.md) to independently verify
- Run tests via the Stop hook (framework/validators/run_tests.py auto-runs on stop)
- Check L-thread progress (framework/validators/check_lthread_progress.py)
- For code changes: mastery validators auto-check (ruff, ty, file contains, new file)
- Never mark a task complete without validation passing

### 6. Agent Teams — Builder + Validator Pattern
For implementation tasks:
- **Builder** (global-agents/team/builder.md): Implements the solution
- **Validator** (global-agents/team/validator.md): Reviews and tests independently
- Run both in parallel when possible — builder implements while validator prepares test cases
- Use /plan_w_team for team-based planning

### 7. TTS Notifications — Verbal Feedback
- Notification hook: TTS announces when Claude needs input (--notify flag)
- SubagentStop hook: TTS announces when subagents complete (--notify flag)
- Stop hook: TTS announces task completion (--chat --notify flags)
- Priority: ElevenLabs > OpenAI > pyttsx3 (fallback)

## Available Commands (Slash Commands)
- `/orchestrate` — Multi-agent orchestration
- `/rlm` — Ralph loop (stateless resampling)
- `/fusion` — Best-of-N fusion execution
- `/plan_w_team` — Plan with builder + validator team
- `/prime` — Load project context
- `/research` — Delegate deep research
- `/analyze` — Deep code analysis
- `/search` — Codebase search delegation
- `/loadbundle` — Restore session from bundle
- `/cook` — Structured task execution
- `/quick-plan` — Fast planning
- `/build` — Build/compile project
- `/crypto_research` — Crypto market analysis

## Observability
All hooks emit events to the observability dashboard (apps/observability/):
- Server: `just server` (port 4000)
- Client: `just client` (port 5173)
- Events tracked: tool use, subagent lifecycle, sessions, errors, permissions

## Key Rules
- Focus on clarity and simplicity when writing documentation
- Always quote file paths with spaces in shell commands
- Use `uv run` for all Python hook/script execution
- Hooks use `Path(__file__).parent` for imports — they work from any location
- settings.json is generated from template — edit the template, not settings.json directly
