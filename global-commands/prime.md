---
description: Intelligently prime agent with project-specific context on demand
allowed-tools: Bash, Read, Glob, Grep
---

# Context Priming Protocol

You are executing the **Elite Context Engineering** priming workflow. Your goal is to efficiently load project-specific context **on demand** rather than permanently.

## Core Principles

- **Efficiency First**: Minimize token usage, maximize understanding
- **Adaptive Discovery**: Intelligently find relevant documentation
- **Structured Summary**: Report findings in organized format
- **Read-Only Mode**: Do NOT modify any files during priming

---

## Phase 1: Project Structure Discovery

Execute these commands to understand the codebase:

```bash
# Get repository overview
git ls-files | head -50

# Identify project type and structure
ls -la

# Check for common project markers
find . -maxdepth 2 -type f \( -name "package.json" -o -name "pyproject.toml" -o -name "Cargo.toml" -o -name "go.mod" -o -name "pom.xml" \) 2>/dev/null
```

---

## Phase 2: Documentation Discovery

Use Glob to find documentation files (prioritize by importance):

### Critical Documentation (Read ALL)
- `README.md` or `README` (project overview)
- `CLAUDE.md` (Claude Code specific instructions)
- `.claude/skills/*/SKILL.md` (available skills)

### Supplementary Documentation (Read if exists)
- `ai_docs/README.md` or `ai_docs/*.md` (AI-specific documentation)
- `docs/architecture.md` or `docs/README.md` (architecture overview)
- `ARCHITECTURE.md` (high-level design)
- `CONTRIBUTING.md` (contribution guidelines)
- `.github/workflows/*.yml` (CI/CD understanding)

### Configuration Files (Scan only, don't read fully)
- `.claude/settings.json` (hook configuration)
- `.claude/agents/*.md` (available sub-agents)
- `.claude/commands/*.md` (custom commands)
- `package.json`, `pyproject.toml`, etc. (dependencies)

---

## Phase 3: Hook & Agent Discovery

If this is a Claude Code project, analyze:

```bash
# List available hooks
ls -la .claude/hooks/ 2>/dev/null || echo "No hooks found"

# List available agents
ls -la .claude/agents/ 2>/dev/null || echo "No agents found"

# List custom commands
ls -la .claude/commands/ 2>/dev/null || echo "No commands found"

# List available skills
ls -la .claude/skills/ 2>/dev/null || echo "No skills found"
```

---

## Phase 4: Technology Stack Detection

Use Grep to identify key technologies:

- Search for import statements to identify frameworks
- Check for database connections (PostgreSQL, SQLite, MongoDB, etc.)
- Identify API frameworks (Express, FastAPI, Flask, etc.)
- Find testing frameworks (Jest, pytest, etc.)

---

## Phase 5: Security Audit (Local Skills)

**CRITICAL: Always run security audit before loading local skills**

Scan all project-local skills for security issues:

```bash
# Run security audit on local project skills
cd ~/Documents/claude-agentic-framework && just audit-local-skills
```

This will scan all skills in `.claude/skills/` and report:
- 🚫 **BLOCKED**: Critical security issues (eval, os.system, curl|bash, etc.)
- ⚠️ **WARNINGS**: Potential concerns (rm -rf, API keys, passwords, etc.)
- ℹ️ **INFO**: Minor notes (HTTP requests, code debt markers)
- ✅ **CLEAN**: No security issues

**Security Action Rules**:
- **CRITICAL findings**: Block skill loading, report to user immediately, require fixes before use
- **WARNING findings**: Allow loading but surface warnings in report, recommend review
- **INFO findings**: Note in report, no action needed
- **CLEAN skills**: Safe to load and use

**Important Notes**:
- Review findings in .md files manually - they may contain documentation examples, not actual code
- Focus on findings in executable files (.sh, .py, .js, etc.) as highest priority
- When in doubt, read the file at the reported line number to verify if it's actual dangerous code

**If Blocked Skills Detected**, offer to run detailed review:
```bash
just review-blocked-skills
```

This interactive tool shows detailed findings with code context and allows whitelisting trusted skills.

---

## Phase 6: Team Assessment

Analyze project structure and determine if spawning an agent team would be beneficial.

**Complexity Indicators to Check**:

1. **Multi-layer Architecture** (weight: 2.0):
   - Frontend + backend directories detected
   - Separate test suites (unit/integration/e2e)
   - Multiple package.json files or workspace configurations
   - Microservices structure

2. **Multiple Technologies** (weight: 1.5):
   - 3+ different languages in use
   - Multiple frameworks (React + Express + GraphQL)
   - Polyglot repository

3. **Large Codebase** (weight: 1.0):
   - More than 50 tracked files (`git ls-files | wc -l`)
   - Multiple deeply nested directories (3+ levels)
   - Large test suites

4. **Security Concerns** (weight: 2.0):
   - Critical or warning findings from Phase 5 security audit
   - Authentication/authorization implementation detected
   - API key management patterns found
   - Database connection strings in config

5. **Unfamiliar Stack** (weight: 1.5):
   - Technologies not commonly used together
   - Custom build systems or tooling
   - Legacy framework versions

**Team Recommendation Logic**:

Based on detected indicators, suggest appropriate team structure:

- **Review Team**: If security audit found critical issues or warnings
  - Composition: security-scanner + validator + builder (for fixes)
  - Use case: Security-critical codebases, production apps, authentication systems

- **Architecture Team**: If multi-layer structure detected
  - Composition: project-architect + builder + validator
  - Use case: Complex projects needing design before implementation

- **Research Team**: If unfamiliar stack detected
  - Composition: researcher + critical-analyst + builder
  - Use case: New technologies, legacy systems, undocumented codebases

- **Full Development Team**: If multiple indicators present
  - Composition: orchestrator + builder + validator + researcher
  - Use case: Large-scale refactoring, new feature development, complex migrations

**Decision Tree**:
```
Complexity Score = (multi-layer * 2) + (multiple-tech * 1.5) + (large-codebase * 1) + (security-concerns * 2) + (unfamiliar * 1.5)

Score >= 4.0: Recommend Full Development Team
Score >= 3.0: Recommend specific team based on highest-weighted indicator
Score >= 2.0: Mention team option but don't recommend
Score < 2.0: Single-agent sufficient
```

---

## Report Format

After completing all phases, provide a **concise, structured summary**:

### 🎯 Project Overview
- **Name**: [Project name]
- **Type**: [Web app / CLI tool / Library / etc.]
- **Primary Language**: [Language(s)]
- **Tech Stack**: [Key technologies]

### 📚 Documentation Available
- List discovered documentation files
- Note any missing critical docs

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

### 🔧 Claude Code Integration
- Hooks configured: [List hook types]
- Custom agents: [List if any]
- Custom commands: [List available commands]
- Skills: [List available skills]

### 🏗️ Architecture Highlights
- Key directories and their purpose
- Main entry points
- Notable patterns or conventions

### 💡 Key Insights
- 3-5 bullet points about what makes this project unique
- Any potential gotchas or important context

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

### ✅ Ready to Execute
Confirm: "Agent primed. Context loaded. Ready for instructions."

---

## Anti-Patterns (DO NOT DO)

- ❌ Do NOT dump entire file contents
- ❌ Do NOT read every single file
- ❌ Do NOT modify any files during priming
- ❌ Do NOT load context permanently (this is on-demand only)
- ❌ Do NOT include raw JSON/YAML dumps in report

---

## Token Efficiency

Target: **2,000-4,000 tokens** for the entire priming process (including report)

If documentation exceeds this:
1. Read README.md fully
2. Skim other docs (first 50 lines only)
3. Use Grep to find key information instead of reading everything
4. Summarize patterns rather than listing everything

---

## Usage

Run this command at the start of a new session or when switching projects:

```
/prime
```

This gives you targeted context **on demand** without permanently loading it into every conversation.
