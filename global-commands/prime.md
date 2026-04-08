---
description: Intelligently prime agent with project-specific context on demand
allowed-tools: Bash, Read, Glob, Grep, Write
---

# Context Priming Protocol v2.0 (Git-Aware Caching)

You are executing the **Elite Context Engineering** priming workflow with intelligent caching. Your goal is to efficiently load project-specific context **on demand** with automatic cache invalidation on git changes.

## Core Principles

- **Cache-First**: Load cached context when available and valid
- **Git-Aware**: Auto-detect changes via commit hash tracking
- **Efficiency First**: Minimize token usage, maximize understanding
- **Adaptive Discovery**: Intelligently find relevant documentation
- **Structured Summary**: Report findings in organized format
- **Smart Persistence**: Save detailed context for future primes

---

## RepoMap Phase (Automatic)

At session start, the `repo_map.py` hook automatically fires before `/prime` is invoked:

- **Threshold**: If the project has **< 200 source files** (`.py`, `.js`, `.ts`, `.tsx`, `.rs`, `.go`, `.java`), the hook exits silently with zero overhead.
- **Threshold met (≥ 200 files)**: Generates a ranked symbol index using tree-sitter parsing (with Python `ast` fallback). Injects it into the session context automatically.
- **Cache**: Stored at `~/.claude/REPO_MAP.md`. Auto-invalidates when the git hash changes. Subsequent sessions load instantly from cache.

Cache format:
```
<!-- GIT_HASH: abc123 -->
<!-- FILES: 347 -->
<!-- GENERATED: 2026-02-17T10:00:00Z -->

## Repository Symbol Map (347 source files)

### src/auth/session.py
- `SessionManager` (class)
- `SessionManager.create(user_id, ttl)` ★★★
- `SessionManager.validate(token)` ★★
...
```

Stars indicate reference frequency across the codebase: ★★★ = referenced 20+ times, ★★ = 10+, ★ = 5+.

When the RepoMap is active, `/prime` can skip the Phase 3 Hook & Agent Discovery scan for large repos since the symbol index already provides structural context.

---

## Phase 0: Cache Detection & Validation

**ALWAYS START HERE** - Check for cached context before doing full analysis.

```bash
# Check if context cache exists
if [ -f .claude/PROJECT_CONTEXT.md ]; then
  echo "✅ Found cached context"

  # Get current git commit hash
  CURRENT_HASH=$(git rev-parse HEAD 2>/dev/null || echo "no-git")

  # Extract cached hash from context file (first line should be: <!-- GIT_HASH: abc123 -->)
  CACHED_HASH=$(head -1 .claude/PROJECT_CONTEXT.md | grep -oE '[a-f0-9]{40}' || echo "no-hash")

  if [ "$CURRENT_HASH" = "$CACHED_HASH" ]; then
    echo "✅ Cache valid (no git changes detected)"
    echo "CACHE_STATUS=VALID"
  else
    echo "⚠️ Cache stale (git changes detected)"
    echo "CACHE_STATUS=STALE"
    echo "Old: $CACHED_HASH"
    echo "New: $CURRENT_HASH"
  fi
else
  echo "📝 No cache found - first prime"
  echo "CACHE_STATUS=NONE"
fi
```

**Decision Tree**:
- `CACHE_STATUS=VALID` → **Load cache internally and give brief confirmation** (instant, minimal output)
- `CACHE_STATUS=STALE` → **Run Phase 1-6** → **MUST run Phase 7 (cache write) before Phase 8** → display full report
- `CACHE_STATUS=NONE` → **Run Phase 1-6** → **MUST run Phase 7 (cache write) before Phase 8** → display full report

> **⚠️ MANDATORY**: Phase 7 (cache write) is NEVER optional after a full analysis. Do not skip it or defer it. Write the cache BEFORE delivering the report in Phase 8.

### If CACHE_STATUS=VALID:

Read `.claude/PROJECT_CONTEXT.md` **internally** (to load context into your understanding) but **do NOT dump it to the user**.

Update the `<!-- GENERATED: ... -->` line in the cache file to the current date (this confirms it was verified without full re-analysis):
```bash
# In the Write tool: overwrite only the second comment line, keep everything else identical
# Replace: <!-- GENERATED: old-date -->
# With:    <!-- GENERATED: current-date -->
```

Also check the architecture map status (one bash line, no file reads):
```bash
[ -f .claude/ARCHITECTURE.md ] && echo "ARCH=EXISTS" || echo "ARCH=MISSING"
```

Then extract key summary info and present this brief confirmation:

```
🚀 **Cached Context Loaded** (instant - no git changes)

✅ [Project Name] v[version if available]
✅ [N] agents, [N] commands, [N] skills
✅ [Primary tech stack in 3-5 words]
🗺️  Architecture map: [EXISTS → ready | MISSING → run /arch-map to generate]

Ready for instructions.
```

**Total output: ~50-100 tokens maximum**

**Then STOP** - Do not re-run Phase 1-6 (cache is valid). Do not show the full report.

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
- **`.claude/ARCHITECTURE.md`** ← **read this first if it exists** — contains the full dependency map, "if X changes update Y" table, and critical paths. Use it to populate the Architecture Highlights section of the report instead of doing manual exploration.
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

**If CACHE_STATUS=STALE**: Only re-scan skills that changed since last prime:
```bash
# Get list of changed files since cached commit
git diff --name-only $CACHED_HASH HEAD | grep '.claude/skills/'
```

**If CACHE_STATUS=NONE**: Scan all project-local skills for security issues:

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

- **Architecture Team**: If multi-layer structure detected
  - Composition: project-architect + builder + validator

- **Research Team**: If unfamiliar stack detected
  - Composition: researcher + critical-analyst + builder

- **Full Development Team**: If multiple indicators present
  - Composition: orchestrator + builder + validator + researcher

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

[If local skills detected, show audit results]

**Blocked Skills** (if any):
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
- **If `.claude/ARCHITECTURE.md` exists**: pull the top 3-5 rows from the "If X changes, update Y" table here, and list the critical workflow paths. This section should be populated from the arch map, not re-discovered manually.
- **Architecture map status**: 🗺️ [FRESH | STALE — run /arch-map | Generated just now | Not yet created — run /arch-map]

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

**Approval**: Would you like me to spawn this team? [Yes/No]

[If score < 2.0:]
**Team Assessment**: Single-agent workflow sufficient for this project's complexity.

### ✅ Ready to Execute
Confirm: "Agent primed. Context loaded. Ready for instructions."

---

## Phase 6.5: Architecture Map — Check & Suggest

**Run after Phase 6 team assessment, before writing the cache.**

```bash
# Check arch map existence and staleness (threshold: 10+ commits behind = stale)
ARCH_HASH=$(head -3 .claude/ARCHITECTURE.md 2>/dev/null | grep -oE '[a-f0-9]{40}' || echo "")
CURRENT_HASH=$(git rev-parse HEAD 2>/dev/null || echo "")

if [ ! -f .claude/ARCHITECTURE.md ]; then
  echo "ARCH=MISSING"
elif [ -n "$ARCH_HASH" ] && [ -n "$CURRENT_HASH" ] && [ "$ARCH_HASH" != "$CURRENT_HASH" ]; then
  COMMITS_BEHIND=$(git rev-list --count "${ARCH_HASH}..HEAD" 2>/dev/null || echo "0")
  [ "$COMMITS_BEHIND" -ge 10 ] && echo "ARCH=STALE ($COMMITS_BEHIND commits)" || echo "ARCH=FRESH"
else
  echo "ARCH=FRESH"
fi
```

**Decision tree — based on ARCH status AND Phase 6 complexity score:**

- **`ARCH=FRESH`**: Read it internally (do NOT dump to user). Pull top 3-5 rows from the "If X changes" table and the critical paths into the Architecture Highlights section of the prime report. Note: "🗺️ Architecture map up to date."

- **`ARCH=STALE`**: Note in the report: "🗺️ Architecture map is ~N commits behind — run `/arch-map` to regenerate." Do NOT regenerate automatically.

- **`ARCH=MISSING` + complexity score < 2.0**: Project is simple — say nothing. Skip the suggestion entirely. Not worth the overhead.

- **`ARCH=MISSING` + complexity score 2.0–3.5**: Mention it once at the end of the report: "🗺️ This project is growing in complexity — consider running `/arch-map` to generate a dependency map and blast-radius table."

- **`ARCH=MISSING` + complexity score > 3.5**: Proactively recommend it in the Architecture Highlights section: "🗺️ **Recommended:** Run `/arch-map` — this project has multiple layers and interconnected scripts where a dependency map would save significant time." Do NOT auto-generate (user opts in by running the command).

---

## Phase 7: Save Context Cache ← DO THIS BEFORE PHASE 8

**BLOCKING REQUIREMENT**: Do NOT proceed to Phase 8 until this file is written. The cache write is the most important step — it is what makes future sessions instant and what `auto_prime.py` loads at session start.

After completing Phase 6 analysis, save the full report to `.claude/PROJECT_CONTEXT.md`:

```bash
# Get current git commit hash
GIT_HASH=$(git rev-parse HEAD 2>/dev/null || echo "no-git-$(date +%s)")

# Create .claude directory if it doesn't exist
mkdir -p .claude
```

Then use the **Write tool** to create/overwrite `.claude/PROJECT_CONTEXT.md` with this format:

**CRITICAL**: Use Write, NOT Edit. Write completely overwrites the file, ensuring the cache stays fresh and doesn't accumulate old data.

```markdown
<!-- GIT_HASH: [insert actual git hash here] -->
<!-- GENERATED: [insert current date/time] -->
<!-- PRIME_VERSION: 2.0 -->

# Project Context Cache

[Insert the ENTIRE report from Phase 6 here, including all sections:
- 🎯 Project Overview
- 📚 Documentation Available
- 🔒 Security Audit
- 🔧 Claude Code Integration
- 🏗️ Architecture Highlights
- 💡 Key Insights
- 🤝 Team Recommendation
]

---

## Change Detection

This cache will be invalidated automatically when:
- Git commit hash changes (pull, commit, checkout)
- .claude/PROJECT_CONTEXT.md is deleted
- /prime is run with --force flag

To force re-analysis: `rm .claude/PROJECT_CONTEXT.md && /prime`
```

**Important Notes**:
- **Always use Write tool** - completely overwrites the file (no appending, no old data accumulation)
- Save the FULL detailed report, not a summary
- Include all sections with complete information
- Each update replaces the entire cache - keeps context fresh and up-to-date
- File should be 1000-2000 lines for comprehensive context

**After writing, verify**:
```bash
# Confirm file exists and is non-empty
wc -l .claude/PROJECT_CONTEXT.md
```

Only proceed to Phase 8 once the file is confirmed written.

---

## Phase 8: Report Delivery

Present the final report to the user:

**If this was a full analysis (CACHE_STATUS=NONE or STALE)**:
```
✅ **Analysis Complete & Cached**

[Show the full report]

💾 Context saved to .claude/PROJECT_CONTEXT.md
🔄 Next /prime will load instantly (unless git changes detected)

Ready for instructions.
```

**If this was a cache load (CACHE_STATUS=VALID)**:
```
🚀 **Cached Context Loaded** (instant - no git changes)

✅ [Project Name] v[version]
✅ [N] agents, [N] commands, [N] skills
✅ [Primary tech stack]

Ready for instructions.
```

**Token efficiency**: ~50-100 tokens total (vs 3,500+ if dumping full cache)

---

## Anti-Patterns (DO NOT DO)

- ❌ Do NOT dump entire file contents
- ❌ Do NOT read every single file
- ❌ Do NOT modify any files during priming
- ❌ Do NOT load context permanently (this is on-demand only)
- ❌ Do NOT include raw JSON/YAML dumps in report
- ❌ **Do NOT dump cached report when CACHE_STATUS=VALID** (this wastes 3,500+ tokens)

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

**Behavior**:
- **First time**: Full analysis (~4,000 tokens) → saves cache → shows full report
- **Subsequent times**: Instant load (~50-100 tokens) → brief confirmation only
- **After git pull/commit**: Auto-detects changes → re-analyzes → shows full report → updates cache

**Token savings**: 97-98% reduction on cached loads (4,000 → 50 tokens)

**Force re-analysis**:
```bash
rm .claude/PROJECT_CONTEXT.md && /prime
```

**Cache location**: `.claude/PROJECT_CONTEXT.md` (git-ignored, project-specific)

This gives you targeted context **on demand** without permanently loading it into every conversation, with intelligent caching to avoid redundant analysis.
