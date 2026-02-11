---
name: prime
version: 0.1.0
description: "This skill should be used when starting a new session or when the user says 'prime yourself', 'load context', 'understand this project', or 'get oriented'. It intelligently primes the agent with project context and should be used proactively when entering a new codebase."
---

# Prime Skill

Execute the elite context engineering priming workflow to load project-specific context on demand.

## When to Use This Skill

This skill should be invoked when:
- User says: "prime", "prime yourself", "get context", "understand this project"
- Starting a new Claude Code session in an unfamiliar codebase
- User switches to a different project directory
- User asks "what does this project do?" or "how is this organized?"
- **PROACTIVELY** when you detect you're in a new codebase and don't understand the structure

## Skill Workflow

### Step 1: Project Structure Discovery

Execute to understand the codebase:

```bash
# Repository overview (limit to avoid token bloat)
git ls-files | head -100

# Project root contents
ls -la

# Detect project type
find . -maxdepth 2 -type f \( -name "package.json" -o -name "pyproject.toml" -o -name "Cargo.toml" -o -name "go.mod" -o -name "pom.xml" -o -name "Makefile" -o -name "justfile" \) 2>/dev/null
```

### Step 2: Critical Documentation (Read These First)

**Priority 1: Always Read**
- `README.md` - Project overview
- `CLAUDE.md` - Claude Code instructions (if exists)

**Priority 2: Claude Code Integration**
- `.claude/skills/*/SKILL.md` - Available skills
- `.claude/agents/*/` - Available sub-agents (list names only)
- `.claude/commands/*.md` - Custom slash commands (list names only)

**Priority 3: AI Documentation**
If `ai_docs/` exists:
- Read `ai_docs/README.md` first
- If no README, read first 3 files in `ai_docs/`

**Priority 4: Architecture**
If exists:
- `ARCHITECTURE.md`
- `docs/architecture.md`
- `docs/README.md`

### Step 3: Technology Stack Detection

Use targeted Grep searches:

```bash
# Detect frameworks (read package.json/pyproject.toml if exists)
grep -r "import.*express" --include="*.js" --include="*.ts" | head -3
grep -r "from fastapi" --include="*.py" | head -3
grep -r "flask" --include="*.py" | head -3

# Detect databases
grep -ri "postgres\|sqlite\|mongodb\|mysql" --include="*.py" --include="*.js" --include="*.ts" | head -5

# Detect testing
grep -ri "jest\|pytest\|vitest\|mocha" package.json pyproject.toml 2>/dev/null
```

### Step 4: Security Audit (Local Skills)

**CRITICAL: Always run security audit before loading local skills**

Scan all project-local skills for security issues using Caddy's auditor:

```bash
# Run security audit on local project skills
cd ~/Documents/claude-agentic-framework && just audit-local-skills
```

This will scan all skills in `.claude/skills/` and report:
- 🚫 **BLOCKED**: Critical security issues detected (eval, os.system, curl|bash, etc.)
- ⚠️ **WARNINGS**: Potential security concerns (rm -rf, API keys, passwords, etc.)
- ℹ️ **INFO**: Minor notes (HTTP requests, code debt markers)
- ✅ **CLEAN**: No security issues detected

**Security Action Rules**:
- **CRITICAL findings**: Block skill loading, report to user immediately, require fixes before use
- **WARNING findings**: Allow loading but surface warnings in report, recommend review
- **INFO findings**: Note in report, no action needed
- **CLEAN skills**: Safe to load and use

**Important Notes**:
- Review findings in .md files manually - they may contain documentation examples, not actual code
- Focus on findings in executable files (.sh, .py, .js, etc.) as highest priority
- When in doubt, read the file at the reported line number to verify if it's actual dangerous code

**If Blocked Skills Detected**:
After priming completes, offer to run detailed review:
```bash
just review-blocked-skills
```

This interactive tool will:
1. Show detailed findings with code context for each blocked skill
2. Display the exact lines triggering security warnings
3. Allow user to whitelist skills they trust (stores in `~/.claude/skills-whitelist.yaml`)
4. Whitelisted skills skip future audits automatically

### Step 5: Analyze Hook Configuration (if Claude Code project)

```bash
# Check for hooks
if [ -f ".claude/settings.json" ]; then
  echo "Claude Code project detected"
  jq '.hooks | keys' .claude/settings.json 2>/dev/null || echo "Cannot parse hooks"
fi

# List custom tooling
ls -1 .claude/hooks/ 2>/dev/null | head -10
ls -1 .claude/agents/ 2>/dev/null
ls -1 .claude/commands/ 2>/dev/null
ls -1 .claude/skills/ 2>/dev/null
```

### Step 6: Team Assessment & Spawning

**Logic**: Analyze project structure from earlier discovery and determine if spawning an agent team would be beneficial.

**Complexity Indicators to Check**:

1. **Multi-layer Architecture**:
   - Frontend + backend directories detected
   - Separate test suites (unit/integration/e2e)
   - Multiple package.json files or workspace configurations
   - Microservices structure

2. **Multiple Technologies**:
   - 3+ different languages in use
   - Multiple frameworks (React + Express + GraphQL)
   - Polyglot repository

3. **Large Codebase**:
   - More than 50 tracked files (`git ls-files | wc -l`)
   - Multiple deeply nested directories (3+ levels)
   - Large test suites

4. **Security Concerns**:
   - Critical or warning findings from Step 4 security audit
   - Authentication/authorization implementation detected
   - API key management patterns found
   - Database connection strings in config

5. **Unfamiliar Stack**:
   - Technologies not commonly used together
   - Custom build systems or tooling
   - Legacy framework versions

**Team Recommendation Logic**:

Based on detected indicators, suggest appropriate team structure:

- **Review Team**: If security audit found critical issues or warnings
  - **Composition**: security-scanner + validator + builder (for fixes)
  - **Use case**: Security-critical codebases, production apps, authentication systems

- **Architecture Team**: If multi-layer structure detected
  - **Composition**: project-architect + builder + validator
  - **Use case**: Complex projects needing design before implementation

- **Research Team**: If unfamiliar stack detected
  - **Composition**: researcher + critical-analyst + builder
  - **Use case**: New technologies, legacy systems, undocumented codebases

- **Full Development Team**: If multiple indicators present
  - **Composition**: orchestrator + builder + validator + researcher
  - **Use case**: Large-scale refactoring, new feature development, complex migrations

**Implementation Steps**:

1. After completing Step 5, analyze complexity indicators
2. If 2+ indicators detected, formulate team recommendation
3. Include recommendation in priming report (see updated template below)
4. Present rationale and estimated cost multiplier
5. Ask user for approval before spawning
6. If approved:
   - Load appropriate team template from `global-agents/team/` or use orchestrator
   - Spawn team using Task tool or /orchestrate command
   - Track team work via TaskList

**Decision Tree**:
```
Complexity Score = (multi-layer * 2) + (multiple-tech * 1.5) + (large-codebase * 1) + (security-concerns * 2) + (unfamiliar * 1.5)

Score >= 4.0: Recommend Full Development Team
Score >= 3.0: Recommend specific team based on highest-weighted indicator
Score >= 2.0: Mention team option but don't recommend
Score < 2.0: Single-agent sufficient
```

### Step 7: Generate Structured Report

Provide a **concise summary** using this template:

---

## 🎯 Project Priming Report

### Project Identity
- **Name**: [Extract from README or package.json]
- **Type**: [CLI / Web App / Library / Service / Multi-repo]
- **Primary Language**: [Language + version if available]
- **Key Technologies**: [Top 3-5 technologies]

### Documentation Inventory
✅ Found:
- [List discovered docs]

⚠️ Missing:
- [Note any expected but missing docs]

### 🔒 Security Audit (Local Skills)
**Status**: [CLEAN / WARNINGS / CRITICAL]

[If local skills detected, show audit results here:]
- ✅ **skill-name**: CLEAN (no issues)
- ⚠️ **skill-name**: 2 warnings (API key handling, rm -rf)
- 🚫 **skill-name**: BLOCKED (1 critical: eval() call)

[For blocked skills:]
**Blocked Skills** (not loaded due to critical security issues):
- skill-name: [Brief description of critical issue]

**Action Required**: Review and fix critical issues before loading blocked skills.

### Claude Code Integration
- **Hooks Configured**: [List hook event types from settings.json]
- **Custom Agents**: [Count + names if < 5]
- **Commands Available**: [List command names]
- **Skills Available**: [List skill names]

### Architecture Overview
```
[Key directories and their purpose]
project-root/
├── src/          - [Purpose]
├── tests/        - [Purpose]
├── .claude/      - [Claude Code config]
└── docs/         - [Documentation]
```

### Technology Stack
- **Framework**: [e.g., Express.js, FastAPI]
- **Database**: [e.g., PostgreSQL, SQLite]
- **Testing**: [e.g., Jest, pytest]
- **Build Tool**: [e.g., Vite, esbuild]

### Key Insights
[3-5 bullet points about what makes this project unique or important context]

### 🤝 Team Recommendation
**Complexity Score**: [X.X] ([Calculation breakdown])

**Indicators Detected**:
- ✅/❌ Multi-layer architecture
- ✅/❌ Multiple technologies
- ✅/❌ Large codebase (N files)
- ✅/❌ Security concerns
- ✅/❌ Unfamiliar stack

**Recommendation**: [No team needed / Review Team / Architecture Team / Research Team / Full Development Team]

**Rationale**: [Brief explanation based on indicators]

**Suggested Composition**:
- [agent-name] ([model-tier]) - [role]
- [agent-name] ([model-tier]) - [role]
- [agent-name] ([model-tier]) - [role]

**Estimated Cost**: [N×] single session cost

**Approval**: Would you like me to spawn this team? [Yes/No]

[If score < 2.0, replace this section with:]
**Team Assessment**: Single-agent workflow sufficient for this project's complexity.

### ✅ Status
**Agent Primed.** Context loaded efficiently. Ready for instructions.

---

## Token Budget

**Target**: 2,000-4,000 tokens for entire priming process

**Efficiency Guidelines**:
- Read README.md fully (most important)
- Skim other docs (first 30-50 lines only)
- Use Grep for targeted searches instead of reading everything
- Summarize patterns, don't list every file

## Anti-Patterns

❌ **DO NOT**:
- Dump raw file contents
- Read every file in the project
- Modify any files during priming
- Include full JSON/YAML in report
- Spend > 5,000 tokens on priming

✅ **DO**:
- Summarize and synthesize
- Focus on actionable context
- Use structured format
- Keep it scannable

## Example Invocation

User says any of:
- "prime yourself on this project"
- "get context"
- "understand the codebase"
- "what does this project do?"

**You respond by executing this skill workflow and delivering the structured report.**

---

## Success Criteria

After priming, you should be able to:
- Explain the project's purpose in 2-3 sentences
- Navigate the codebase structure
- Identify where to find key functionality
- Know what tools/frameworks are used
- Understand any Claude Code customizations (hooks, agents, commands)

Agent is now **context-aware** and ready to work efficiently.
