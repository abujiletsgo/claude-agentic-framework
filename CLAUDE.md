# Claude Agentic Framework

Consolidated agentic engineering system. One repo, one install, one source of truth.

**Version**: 2.0.0 (February 2026)

## Repo Structure

```
global-hooks/        5 namespaces: mastery/ observability/ damage-control/ framework/ prompt-hooks/
global-agents/       33 agents (13 root + 4 team + 8 guardrails + 8 agbot)
global-commands/     21 commands + bench/
global-skills/       20 skills (meta-skill, video-processor, code-review, dependency-audit,
                     documentation-writer, error-analyzer, git-workflow, knowledge-db,
                     multi-model-tiers, performance-profiler, project-scaffolder,
                     refactoring-assistant, security-scanner, test-generator, tdd-workflow,
                     brainstorm-before-code, feasibility-analysis, task-decomposition,
                     downstream-correction, verification-checklist)
global-output-styles/ 11 styles
global-status-lines/ mastery/(9 versions) + observability/(2)
apps/observability/  Vue 3 dashboard + Bun server
guides/              15 engineering guides
data/                knowledge-db/ + model_tiers.yaml + logs/ + tts_queue/
templates/           settings.json.template (__REPO_DIR__ placeholder) + long-migration.md
docs/                2026_UPGRADE_GUIDE.md + SKILLS_INTEGRITY.md + SECURITY_BEST_PRACTICES.md
install.sh           Symlinks + generates ~/.claude/settings.json
```

## Operational Mode: Full Autonomous (Yolo)

Permissions: `"allow": ["*"]` with deny rules for destructive ops and ask for force-push/hard-reset. Seven-layer security: permissions > command hooks (pattern match) > prompt hooks (LLM semantic review) > skills integrity (SHA-256 verification) > skill auditing (Caddy) > input validation (per-skill) > file permissions (0o600). See Security section below.

## Multi-Model Tiers

Every agent assigned to the right model for cost-quality balance:

```
Opus  (12%):  orchestrator, project-architect, critical-analyst, rlm-root
Sonnet (50%): builder, researcher, meta-agent, project-skill-generator, caddy-assistant, + 12 more
Haiku  (38%): validator, docs-scraper, hello-world, create-worktree-subagent, context-manager, + 8 more
```

Set in agent frontmatter `model:` field. Centralized config: `data/model_tiers.yaml`.

## Knowledge Pipeline

Persistent cross-session memory via SQLite FTS5:
- **Store**: decisions, learnings, patterns, errors, context, preferences
- **Search**: full-text search with BM25 ranking
- **Pipeline**: extract_learnings -> store_learnings -> inject_relevant -> observe_patterns
- **Location**: `global-hooks/framework/knowledge/` (8 modules)
- **CLI**: `global-skills/knowledge-db/`

## Continuous Review

Automated post-commit code review:
- Review engine with pluggable analyzers (complexity, security, style, performance)
- Findings database for tracking issues across commits
- Config: `global-hooks/framework/review/review_config.yaml`

## Agentic Execution Protocol

### 1. Task Decomposition -- Always Use Task Lists
For any non-trivial task (3+ steps), immediately create a TaskList:
- Break work into discrete, parallelizable units
- Mark tasks in_progress before starting, completed when done
- This preserves context across compactions and keeps execution efficient

### 2. Parallel Execution -- Maximize Throughput
- Launch independent subagents simultaneously using multiple Task tool calls in a single message
- Use `run_in_background: true` for long-running agents
- Never serialize work that can run in parallel
- Agent types available: Bash, Explore, Plan, researcher, orchestrator, rlm-root, general-purpose

### 3. Orchestrator Pattern -- Delegate Complex Tasks
For multi-faceted tasks, use the Orchestrator agent (primary coordinator) or /orchestrate command:
- Orchestrator analyzes strategy, plans, delegates to specialized agents (researcher, builder, validator), and synthesizes
- You give high-level goals, Orchestrator handles coordination and strategy selection
- Each subagent gets isolated context (no cross-contamination)

### 4. Ralph Loops -- Context-Efficient Iteration
For tasks that may exceed context window or need iterative refinement:
- Use /rlm command or rlm-root agent
- Each iteration gets fresh context, reads progress from filesystem
- State persists via progress files, not context accumulation
- Circuit breaker after N iterations prevents infinite loops

### 5. Validation Protocol -- Verify Everything
After any significant implementation:
- Spawn a **validator subagent** (global-agents/team/validator.md) to independently verify
- Run tests via the Stop hook (framework/validators/run_tests.py auto-runs on stop)
- Check L-thread progress (framework/validators/check_lthread_progress.py)
- For code changes: mastery validators auto-check (ruff, ty, file contains, new file)
- Never mark a task complete without validation passing

### 6. Agent Teams -- Builder + Validator Pattern
For implementation tasks:
- **Builder** (global-agents/team/builder.md, Sonnet): Implements the solution
- **Validator** (global-agents/team/validator.md, Haiku): Reviews and tests independently
- **Project Skill Generator** (global-agents/team/project-skill-generator.md, Sonnet): Creates project-specific skills
- Run both in parallel when possible -- builder implements while validator prepares test cases
- Use /plan_w_team for team-based planning

### 7. Strategic Agents -- Project Intelligence & Critical Thinking

**Project-Architect** (global-agents/project-architect.md, Opus):
- Analyzes projects and creates custom agent ecosystems, skills, and tools
- Use after planning/understanding stage of new or existing projects
- Designs project-specific automation and workflows
- Creates initialization guides and context-loading strategies

**Critical-Analyst** (global-agents/critical-analyst.md, Opus):
- Questions every detail, assumption, plan, and decision
- Use proactively during planning, building, and decision-making
- Challenges ideas to ensure solid foundations
- Forces explicit articulation of "why" and "how"
- Identifies risks and alternative approaches before commitment

### 8. TTS Notifications -- Verbal Feedback
- Notification hook: TTS announces when Claude needs input (--notify flag)
- SubagentStop hook: TTS announces when subagents complete (--notify flag)
- Stop hook: TTS announces task completion (--chat --notify flags)
- Priority: ElevenLabs > OpenAI > pyttsx3 (fallback)

### 9. Skills -- Auto-Discoverable Capabilities
20 skills in global-skills/ with SKILL.md frontmatter. Claude Code discovers and triggers them automatically based on user intent. Key skills:
- `knowledge-db` -- persistent cross-session memory
- `multi-model-tiers` -- configure agent model assignments
- `code-review`, `test-generator`, `tdd-workflow` -- quality lifecycle
- `security-scanner`, `dependency-audit` -- security
- `brainstorm-before-code`, `feasibility-analysis`, `task-decomposition` -- planning
- `meta-skill` -- create new skills from templates
- `video-processor` -- video/audio processing and transcription

### 10. Orchestrator -- Primary Coordinator
- **Orchestrator** (global-agents/orchestrator.md, Opus): Primary coordinator with strategy selection
- Analyzes user intent, classifies complexity/type/quality/scope
- Selects optimal strategy: direct, team coordination, rlm delegation, fusion, research
- Plans agent teams, spawns specialized agents, coordinates execution
- Aggregates results and provides synthesized reports
- Handles all coordination decisions and agent team composition
- You give high-level goals -- Orchestrator handles everything

### 11. Caddy-Assistant -- Support Services
- **Caddy-Assistant** (global-agents/caddy-assistant.md, Sonnet): Support assistant for infrastructure maintenance
- Provides skill auditing and security scanning
- Monitors framework health and detects issues
- Maintains registry of components and validates configurations
- Generates documentation and indexes
- Auditor: `global-hooks/framework/caddy/skill_auditor.py`
- Config: `data/caddy_config.yaml`
- Support role only -- no orchestration or coordination

### 12. Guardrails -- Anti-Loop Protection
- Anti-loop guardrails in `global-hooks/framework/guardrails/`
- 8 guardrail agents in `global-agents/team/guardrails/`
- Documentation: `global-hooks/framework/ANTI_LOOP_GUARDRAILS.md`

## Available Commands (Slash Commands)

### Core
- `/prime` -- Load project context (includes security audit and team assessment)
- `/research` -- Delegate deep research, analysis, and search
- `/loadbundle` -- Restore session from bundle

### Orchestration
- `/orchestrate` -- Multi-agent orchestration
- `/rlm` -- Ralph loop (stateless resampling)
- `/fusion` -- Best-of-N fusion execution

### Planning
- `/plan` -- Structured planning with optional team coordination

### Development
- `/build` -- Build/compile project
- `/refine` -- Iteratively refine output
- `/question` -- Ask focused question to sub-agent
- `/sentient` -- Advanced reasoning mode

### Worktrees
- `/create-worktree` -- Create git worktree
- `/list-worktrees` -- List git worktrees
- `/remove-worktree` -- Remove git worktree

### Utility
- `/start` -- Initialize session
- `/git_status` -- Quick git status
- `/all_tools` -- List available tools
- `/convert_paths_absolute` -- Convert paths to absolute
- `/load_ai_docs` -- Load AI documentation
- `/update_status_line` -- Update status line display

## Observability
All hooks emit events to the observability dashboard (apps/observability/):
- Server: `just server` (port 4000)
- Client: `just client` (port 5173)
- Events tracked: tool use, subagent lifecycle, sessions, errors, permissions, model tiers

## Security

Defense-in-depth security across 7 layers: permissions > command hooks > prompt hooks > skills integrity > skill auditing > input validation > file permissions.

### Skills Integrity Verification
- SHA-256 hashes of all skill files stored in `~/.claude/skills.lock`
- Verification hook runs on `SessionStart` -- reports modified, deleted, new, missing, or unlocked files
- Generator: `scripts/generate_skills_lock.py`
- Verifier: `global-hooks/framework/security/verify_skills.py`
- Documentation: `docs/SKILLS_INTEGRITY.md`

### Automatic Skill Auditing
- Caddy-Assistant audits skills before recommendations (code injection, dangerous commands, sensitive file access, insecure permissions)
- Auditor: `global-hooks/framework/caddy/skill_auditor.py`
- CLI: `scripts/audit_skill.py`
- Config: `data/caddy_config.yaml` under `skill_audit`
- Critical findings block skill recommendations; warnings are shown to user
- All audit results reviewed by Orchestrator before final recommendation

### Input Validation
- worktree-manager-skill: character allowlist validation via `scripts/validate_name.sh`, path containment checks
- video-processor: output path restricted to CWD, system directory write-blocking, input file validation
- knowledge-db: import path restricted to `~/.claude/` and CWD, path traversal blocked

### File Permissions
- Knowledge database and logs: `0o600` (owner read/write only)
- Enforced on every open operation, not just creation

### Security Commands
```bash
just skills-lock          # Generate SHA-256 lock file
just skills-verify        # Verify skill integrity
just audit-skill <name>   # Audit one skill
just audit-all-skills     # Audit all global skills
just audit-local-skills   # Audit local project skills (.claude/skills/)
```

### Prime Integration
When `/prime` runs, it automatically scans all local project skills in `.claude/skills/` for security issues:
- Detects critical patterns (eval, os.system, curl|bash)
- Blocks skills with critical issues
- Warns about potential concerns (rm -rf, API keys, passwords)
- Reports findings in the priming report
- Note: .md files may trigger false positives from documentation examples

### Security Documentation
- Full guide: `docs/SECURITY_BEST_PRACTICES.md`
- Skills integrity: `docs/SKILLS_INTEGRITY.md`
- Skill auditing: `global-agents/team/caddy-assistant.md` (Skill Security Audit section)

## Key Rules
- Focus on clarity and simplicity when writing documentation
- Always quote file paths with spaces in shell commands
- Use `uv run` for all Python hook/script execution
- Hooks use `Path(__file__).parent` for imports -- they work from any location
- settings.json is generated from template -- edit the template, not settings.json directly
- Agent model tiers set in frontmatter `model:` field -- centralized in data/model_tiers.yaml
- Knowledge database at data/knowledge-db/ -- use knowledge-db skill for CLI access
- Review config at global-hooks/framework/review/review_config.yaml
