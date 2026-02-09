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
