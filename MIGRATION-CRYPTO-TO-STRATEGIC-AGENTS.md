# Migration: Crypto Agents → Strategic Agents

**Date**: 2026-02-10
**Status**: Complete (manual cleanup needed)

## Summary

Removed all cryptocurrency-focused agents and replaced them with two powerful, versatile strategic agents that work across all projects.

## What Was Removed

### Agents
- 7 crypto agent prompt files from `global-commands/agent_prompts/`
- crypto-backup-20260210 directory (still exists in global-agents, can be deleted)
- Broken symlink: `~/.claude/agents/crypto`

### Commands
- `/crypto_research` - Crypto market analysis with multiple agents
- `/crypto_research_haiku` - Lightweight crypto research
- `/cook` - Parallel execution of 7 tasks (included crypto agents)
- `/cook_research_only` - Parallel crypto coin analysis

### Broken Symlinks (Manual Cleanup Required)
Your security hooks prevent deletion of these. Please remove manually:
```bash
rm ~/.claude/agents/crypto
rm ~/.claude/commands/cook_research_only.md
rm ~/.claude/commands/crypto_research.md
rm ~/.claude/commands/cook.md
rm ~/.claude/commands/crypto_research_haiku.md
```

## What Was Added

### 1. Project-Architect Agent
**Location**: `global-agents/project-architect.md`
**Symlink**: `~/.claude/agents/project-architect.md` ✓

**Purpose**: Expert at analyzing projects and creating custom agent ecosystems, skills, tools, and automation workflows tailored to specific projects.

**When to Use**:
- After completing planning or understanding phase of a new project
- When initializing work on an existing project
- When you need project-specific automation
- After major architectural decisions

**Capabilities**:
- Deep project analysis (tech stack, patterns, requirements)
- Design custom agent ecosystems for the project
- Create project-specific skills and commands
- Build initialization workflows
- Generate context-loading strategies
- Design testing and deployment automation

**Example Invocations**:
```bash
# For a new React project
cc "I just created a new Next.js app. Use project-architect to set up an agent ecosystem for it."

# For VaultMind project
cc "Use project-architect to analyze the VaultMind plugin and create specialized agents for Obsidian plugin development."

# For any project initialization
cc "Use project-architect to analyze this codebase and create automation workflows."
```

### 2. Critical-Analyst Agent
**Location**: `global-agents/critical-analyst.md`
**Symlink**: `~/.claude/agents/critical-analyst.md` ✓

**Purpose**: Questions every detail, assumption, plan, and decision throughout the project lifecycle. Acts as a critical thinking specialist that challenges ideas and forces explicit reasoning.

**When to Use**:
- Before finalizing any plan or architectural decision
- During PR reviews or significant code changes
- When making technical choices between alternatives
- Before marking non-trivial tasks complete
- When requirements are vague or assumptions unstated
- When someone says "this should be simple"

**Capabilities**:
- Challenge unstated assumptions
- Probe rationale (ask "why" and "how")
- Identify risks before they materialize
- Verify alignment between goals and implementation
- Demand clarity and explicit reasoning
- Present alternative approaches with tradeoffs

**Example Invocations**:
```bash
# Before implementing a feature
cc "Use critical-analyst to review this plan before we start building: [plan details]"

# During architecture review
cc "Use critical-analyst to evaluate this API design decision and identify potential issues."

# Before finalizing
cc "Use critical-analyst to review the VaultMind agent architecture and question any assumptions."

# Continuous questioning during build
cc "As we build this feature, I want critical-analyst to question each decision we make."
```

## Updated Documentation

### CLAUDE.md Changes
1. Updated agent count: `17 agents (15 root + 2 team)` (was 28)
2. Updated command count: `25 commands + bench/` (was 29 + agent_prompts/)
3. Removed crypto-related commands from Available Commands section
4. Added new section **"7. Strategic Agents"** documenting both new agents

### Framework Structure
```
global-agents/
├── project-architect.md     ← NEW: Project-specific agent creator
├── critical-analyst.md      ← NEW: Critical thinking specialist
├── meta-agent.md           (Generic agent creator)
├── orchestrator.md
├── researcher.md
├── rlm-root.md
├── docs-scraper.md
├── llm-ai-agents-and-eng-research.md
├── fetch-docs-haiku45.md
├── fetch-docs-sonnet45.md
├── hello-world-agent.md
├── work-completion-summary.md
├── scout-report-suggest.md
├── scout-report-suggest-fast.md
├── create_worktree_subagent.md
├── agbot/
├── team/
│   ├── builder.md
│   └── validator.md
└── crypto-backup-20260210/  ← Can be deleted
```

## How These Agents Work Together

### Project Initialization Workflow
```
1. User starts new project or approaches existing one
2. Invoke project-architect to analyze and design agent ecosystem
3. project-architect creates custom agents, skills, and tools
4. Invoke critical-analyst to review the architecture
5. critical-analyst questions assumptions and identifies gaps
6. Refine based on critical-analyst feedback
7. Begin development with custom project agents
```

### During Development Workflow
```
1. Plan a feature
2. Invoke critical-analyst to review plan
3. critical-analyst identifies risks and alternatives
4. Refine plan based on feedback
5. Build the feature (possibly with builder agent)
6. Invoke critical-analyst to review implementation
7. Validate with validator agent
8. Mark complete
```

### Example: VaultMind Development
```bash
# 1. Initial architecture review
cc "Use critical-analyst to review the 9-agent VaultMind architecture. Question every assumption about concurrency, error handling, and state management."

# 2. Before adding a new feature
cc "I want to add a new agent to VaultMind that handles X. Use critical-analyst to question whether this is the right approach and what alternatives exist."

# 3. Creating project-specific tooling
cc "Use project-architect to create a custom skill for VaultMind that builds the plugin, validates it, and hot-reloads it in Obsidian."
```

## Agent Collaboration Matrix

| Agent | Works Best With | Purpose of Collaboration |
|-------|----------------|-------------------------|
| **project-architect** | critical-analyst | Validate agent ecosystem design |
| **project-architect** | meta-agent | Generate the actual agent files |
| **project-architect** | researcher | Study similar project architectures |
| **critical-analyst** | orchestrator | Challenge orchestration plans |
| **critical-analyst** | builder | Review implementation decisions |
| **critical-analyst** | validator | Question test coverage |
| **critical-analyst** | project-architect | Validate agent designs |

## Benefits Over Crypto Agents

### Before (Crypto Agents)
- ❌ Highly specialized to one domain (cryptocurrency)
- ❌ Limited applicability to other projects
- ❌ No project-specific customization
- ❌ No critical thinking or assumption challenging
- ❌ Agents existed but no "agent about agents"

### After (Strategic Agents)
- ✅ Universal applicability across all projects
- ✅ Creates custom agents for any domain
- ✅ Project-specific automation and workflows
- ✅ Built-in critical thinking and risk identification
- ✅ Meta-level intelligence about agent design
- ✅ Questions and validates all decisions
- ✅ Scalable to any tech stack or project type

## Advanced Usage Patterns

### Pattern 1: Continuous Critical Analysis
Keep critical-analyst active throughout development:
```bash
cc "For this entire session, I want critical-analyst to proactively question any plan or decision I make. Challenge me on every assumption."
```

### Pattern 2: Project Setup Automation
Create a complete project setup in one command:
```bash
cc "Use project-architect to:
1. Analyze this Next.js codebase
2. Create agents for: component generation, API testing, deployment
3. Create skills for: dev server with hot reload, production build, test suite
4. Create a /prime-nextjs skill that loads all project context
Then use critical-analyst to review the design."
```

### Pattern 3: Architecture Review Before Build
Always validate before implementing:
```bash
# 1. Create the plan
cc "Plan how to implement feature X"

# 2. Get critical analysis
cc "Use critical-analyst to review this plan. Question:
- Why this approach?
- What could go wrong?
- What alternatives exist?
- What assumptions are we making?"

# 3. Refine and build
[Iterate based on feedback]
```

### Pattern 4: Meta-Agent Creation
When you need a new agent type:
```bash
# 1. Design with project-architect
cc "Use project-architect to design a 'security-auditor' agent for this project"

# 2. Review with critical-analyst
cc "Use critical-analyst to review this agent design"

# 3. Generate with meta-agent
cc "Use meta-agent to create the security-auditor agent based on this design"
```

## Migration Checklist

- [x] Remove crypto agent prompt files
- [x] Remove crypto command files (cook, crypto_research*)
- [x] Create project-architect agent
- [x] Create critical-analyst agent
- [x] Create symlinks to ~/.claude/agents/
- [x] Update CLAUDE.md documentation
- [ ] **Manual**: Remove broken symlinks in ~/.claude/
- [ ] **Optional**: Delete crypto-backup-20260210 directory
- [ ] **Optional**: Update any custom scripts that referenced crypto agents

## Next Steps

1. **Clean up broken symlinks** (manual step due to security hooks)
2. **Test the new agents**:
   ```bash
   # Test project-architect
   cc "Use project-architect to analyze the claude-agentic-framework itself"

   # Test critical-analyst
   cc "Use critical-analyst to review the decision to replace crypto agents with strategic agents"
   ```
3. **Try them on VaultMind**:
   ```bash
   cc "Use project-architect to create VaultMind-specific development agents"
   cc "Use critical-analyst to review the VaultMind security audit findings"
   ```
4. **Integrate into workflow**:
   - Use project-architect whenever starting or joining a project
   - Use critical-analyst before finalizing any significant decision
   - Let critical-analyst run in background during planning phases

## Questions & Troubleshooting

**Q: Why remove crypto agents?**
A: They were domain-specific and only useful for cryptocurrency research. The new strategic agents are universal and can create crypto-specific agents if needed via project-architect.

**Q: Can I recreate crypto agents if needed?**
A: Yes! Use project-architect: "Create a crypto market analysis agent for [specific use case]"

**Q: When should I NOT use these agents?**
A: For simple, single-file changes or trivial tasks. These are for architectural, planning, and complex decision-making.

**Q: Do they work with existing agents?**
A: Yes! They're designed to enhance your existing agent ecosystem, not replace it.

**Q: Performance impact?**
A: project-architect uses Opus (thorough), critical-analyst uses Sonnet (balanced). Both are optimized for their specific tasks.
