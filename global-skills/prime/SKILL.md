---
name: prime
description: "Intelligently prime agent with project context. Use when starting a new session or the user says 'prime yourself', 'load context', 'understand this project', or 'get oriented'. Use PROACTIVELY when entering a new codebase."
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

### Step 4: Analyze Hook Configuration (if Claude Code project)

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

### Step 5: Generate Structured Report

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
