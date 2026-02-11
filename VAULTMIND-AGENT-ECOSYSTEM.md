# VaultMind Agent Ecosystem

**Created**: 2026-02-11
**Status**: ✅ Complete and Active

## Project Analysis Summary

**VaultMind** is a sophisticated Obsidian plugin with:
- **9 AI agents** working in coordination
- **Gemini integration** for YouTube video analysis
- **Telegram bot** for URL intake
- **Dual LLM providers** (Claude/Anthropic + Gemini + Local Ollama)
- **585KB bundle**, 23 source files, 17 commands
- **All 9 phases complete**, production-ready

**Tech Stack**: TypeScript, Obsidian API, Anthropic SDK, Gemini REST API, esbuild
**Complexity Level**: High - requires understanding of multi-agent coordination, security patterns, and API integration

## Custom Agents Created

### 1. vaultmind-agent-debugger 🔧
**Location**: `~/.claude/agents/vaultmind-agent-debugger.md`
**Purpose**: Debug and optimize VaultMind's 9-agent system
**Model**: Sonnet
**Color**: Orange

**Use When**:
- Agents behaving unexpectedly
- Performance issues
- Coordination problems between agents
- Dashboard not updating
- Confidence routing issues
- Gemini fallback not working

**Example**:
```bash
cc "Use vaultmind-agent-debugger to investigate why Agent 1 isn't processing notes"
cc "vaultmind-agent-debugger: Dashboard stats aren't updating after Agent 8 runs"
```

**Capabilities**:
- Understands all 9 agents and their coordination
- Knows Obsidian API patterns
- Identifies common issues (rate limiting, path validation, event listeners)
- Provides specific fixes with file/line references
- Creates test plans for verification

---

### 2. vaultmind-deployer 🚀
**Location**: `~/.claude/agents/vaultmind-deployer.md`
**Purpose**: Build, validate, and deploy VaultMind to Obsidian
**Model**: Haiku (fast for simple tasks)
**Color**: Green

**Use When**:
- After code changes
- Need to rebuild and reload plugin
- Validating build output
- Deploying to Obsidian

**Example**:
```bash
cc "Use vaultmind-deployer to build and deploy the plugin"
cc "Deploy VaultMind after these changes"
```

**Capabilities**:
- Runs `npm run build` with proper paths
- Validates bundle size (~585KB expected)
- Checks TypeScript errors
- Provides reload instructions (3 methods)
- Verifies plugin files (main.js, manifest.json, styles.css)

---

## Custom Skills Created

### 1. /vaultmind-init 📚
**Command**: `/vaultmind-init`
**Purpose**: Load complete VaultMind context to start working

**What It Does**:
- Reads project CLAUDE.md files (plugin + system + vault)
- Loads dashboard status (_dashboard.md)
- Reads recent changelog
- Shows tag ontology structure
- Lists source file structure
- Provides current build status

**Use When**:
- Starting a new Claude Code session
- Need to understand current project state
- Before making changes
- After being away from project

**Example**:
```bash
cc /vaultmind-init
```

**Output**:
```markdown
# VaultMind Context Loaded

**Status**: ✅ All 9 phases complete, 585KB bundle
**Active Issues**: 3 uncertain categorizations
**Recent Activity**: Agent 1 processed 5 notes
**Agent Status**: All Idle
**Ready to**: Debug, add features, process notes
```

---

### 2. /vaultmind-deploy 🚀
**Command**: `/vaultmind-deploy`
**Purpose**: Complete build and deployment workflow

**What It Does**:
- Runs `npm run build`
- Validates build output
- Checks bundle size
- Provides reload instructions
- Shows verification checklist

**Use When**:
- After editing source code
- Need to test changes in Obsidian
- Rebuilding plugin

**Example**:
```bash
cc /vaultmind-deploy
```

**Output**:
```markdown
# 🚀 VaultMind Deployment

**Build Status**: ✅ Success
**Bundle**: 587 KB
**TypeScript**: 0 errors

## 🔄 Reload Obsidian

[3 reload methods provided]

## ✅ Checklist
- [ ] Console shows no errors
- [ ] 17 commands available
- [ ] Settings accessible
```

---

### 3. /vaultmind-test ✅
**Command**: `/vaultmind-test`
**Purpose**: Run comprehensive test checklist

**What It Does**:
- Provides structured test checklist for all 17 commands
- Includes diagnostic bash commands
- Tests each of the 9 agents
- Verifies Gemini integration
- Tests Telegram bot
- Checks dashboard rendering
- Validates settings persistence

**Use When**:
- After deployment
- Verifying functionality
- Troubleshooting issues
- Before marking work complete

**Example**:
```bash
cc /vaultmind-test
```

**Output**:
```markdown
# VaultMind Test Report

| # | Test | Status | Notes |
|---|------|--------|-------|
| 1 | Plugin Load | ✅ Pass | No errors |
| 2 | Settings | ✅ Pass | All keys present |
| 3 | Note Processing | ✅ Pass | 5 notes processed |
...

**Overall**: 9/10 passed
```

---

## Typical Development Workflows

### Workflow 1: Start Work on VaultMind
```bash
# 1. Load context
cc /vaultmind-init

# 2. Check current state
# (Output shows dashboard, recent changes, agent status)

# 3. Start working
cc "Use vaultmind-agent-debugger to investigate [issue]"
```

### Workflow 2: Fix a Bug
```bash
# 1. Debug the issue
cc "Use vaultmind-agent-debugger to find why Agent 2 Gemini fallback isn't working"

# 2. Get fix recommendation
# (Agent provides specific file/line changes)

# 3. Implement fix
cc "Implement this fix: [details]"

# 4. Deploy
cc /vaultmind-deploy

# 5. Test
cc /vaultmind-test
```

### Workflow 3: Add New Feature
```bash
# 1. Load context
cc /vaultmind-init

# 2. Plan the feature
cc "I want to add [feature]. Use critical-analyst to review this plan."

# 3. Implement
cc "Use builder to implement [feature] for VaultMind"

# 4. Deploy
cc /vaultmind-deploy

# 5. Test
cc /vaultmind-test
```

### Workflow 4: Debug Agent Coordination
```bash
# 1. Identify the issue
cc "Agent 8 dashboard isn't updating after Agent 1 runs"

# 2. Debug
cc "Use vaultmind-agent-debugger to investigate Agent 8 coordination"

# 3. Fix
# (Implement suggested fix)

# 4. Deploy and verify
cc /vaultmind-deploy
cc /vaultmind-test
```

### Workflow 5: Optimize Performance
```bash
# 1. Identify bottleneck
cc "Use vaultmind-agent-debugger to analyze why note processing is slow"

# 2. Get optimization suggestions
# (Agent suggests rate limiting adjustments, batching, etc.)

# 3. Implement
cc "Implement these optimizations: [details]"

# 4. Deploy and benchmark
cc /vaultmind-deploy
cc "Test note processing speed with 100 notes"
```

---

## Agent Collaboration Matrix

| Primary Agent | Works With | Purpose |
|--------------|------------|---------|
| **vaultmind-agent-debugger** | critical-analyst | Validate fix before implementing |
| **vaultmind-agent-debugger** | builder | Debug identifies issue, builder fixes it |
| **vaultmind-deployer** | validator | Deploy then validate functionality |
| **vaultmind-init skill** | - | Always run first in new sessions |
| **vaultmind-deploy skill** | vaultmind-test skill | Deploy then test |

---

## VaultMind Architecture Quick Reference

### The 9 Agents
1. **Note Processor** - Classify, tag, summarize → Areas frontmatter
2. **Content Scraper** - Gemini-first for URLs/YouTube
3. **Ontology Manager** - Tag health, proposals
4. **Semantic Clusterer** - Cross-area clustering
5. **Periodic Recaps** - Daily/weekly/monthly summaries
6. **Fact Checker** - Verify claims
7. **Resource Synthesizer** - Entity pages in 9807/
8. **Control Panel** - Update dashboard
9. **Versioning** - Change tracking

### Key Paths
```bash
# Plugin source
/Users/tomkwon/Library/CloudStorage/GoogleDrive-tomjihoonkwon@gmail.com/My Drive/Obsidian/.obsidian/plugins/vaultmind/

# Vault root
/Users/tomkwon/Library/CloudStorage/GoogleDrive-tomjihoonkwon@gmail.com/My Drive/Obsidian/

# Dashboard
{vault}/95 - Control Panel/_dashboard.md

# Notes (inbox and processed)
{vault}/98 - Database/9801 - Notes/

# System files
{vault}/98 - Database/9806 - VaultMind/
```

### Build Commands
```bash
# Build (always quote - spaces in path)
cd "{vault}/.obsidian/plugins/vaultmind" && npm run build

# Watch mode
cd "{vault}/.obsidian/plugins/vaultmind" && npm run dev

# Check bundle
ls -lh "{vault}/.obsidian/plugins/vaultmind/main.js"
```

### Key Patterns

**API Keys** (localStorage only):
- `vaultmind-api-key` (Claude)
- `vaultmind-gemini-api-key` (Gemini)
- `vaultmind-telegram-token` (Telegram)

**File Operations**:
- `Vault.process()` for atomic edits
- `FileManager.processFrontMatter()` for frontmatter
- `FileManager.renameFile()` for moves

**Confidence Routing** (notes never move):
- >= 80%: processed
- 50-80%: flagged
- < 50%: flagged

**Gemini Fallback**:
- Primary: Gemini for Agent 2 (YouTube, articles)
- Fallback: Claude/local LLM if Gemini fails

---

## Common Issues & Solutions

### Issue: Agent not processing
**Solution**: Use vaultmind-agent-debugger
```bash
cc "vaultmind-agent-debugger: Agent 1 isn't processing notes"
```

### Issue: Build fails
**Solution**: Check TypeScript errors
```bash
cd "{vault}/.obsidian/plugins/vaultmind" && npm run build
```

### Issue: Dashboard not updating
**Solution**: Debug Agent 8
```bash
cc "vaultmind-agent-debugger: Dashboard stats not updating"
```

### Issue: Gemini not working
**Solution**: Check API key and fallback
```bash
# Verify key in Obsidian console:
# localStorage.getItem('vaultmind-gemini-api-key')
```

### Issue: Bundle size wrong
**Solution**: Redeploy
```bash
cc /vaultmind-deploy
```

---

## Integration with Global Agents

VaultMind agents work seamlessly with global strategic agents:

### Use project-architect
```bash
cc "Use project-architect to create additional VaultMind automation"
```

### Use critical-analyst
```bash
cc "Use critical-analyst to review this VaultMind feature plan"
```

### Use orchestrator
```bash
cc "Use orchestrator to coordinate: debug with vaultmind-agent-debugger, fix with builder, validate with validator"
```

### Use builder
```bash
cc "Use builder to implement this VaultMind feature"
```

### Use validator
```bash
cc "Use validator to verify VaultMind deployment"
```

---

## Benefits of This Ecosystem

### Before (No VaultMind Agents)
- ❌ Generic debugging for complex multi-agent system
- ❌ Manual build and deployment steps
- ❌ No structured testing approach
- ❌ No context loading for sessions
- ❌ Hard to understand 9-agent coordination

### After (VaultMind Agent Ecosystem)
- ✅ Specialized debugging for VaultMind architecture
- ✅ One-command deployment (`/vaultmind-deploy`)
- ✅ Comprehensive test checklist (`/vaultmind-test`)
- ✅ Instant context loading (`/vaultmind-init`)
- ✅ Deep understanding of agent coordination
- ✅ Project-specific patterns and best practices
- ✅ Fast iteration cycle (debug → fix → deploy → test)

---

## Next Steps

1. **Restart Claude Code** to load the new agents and skills
2. **Test the ecosystem**:
   ```bash
   cc /vaultmind-init
   cc /vaultmind-deploy
   cc /vaultmind-test
   ```
3. **Try debugging**:
   ```bash
   cc "Use vaultmind-agent-debugger to review the current state of all 9 agents"
   ```
4. **Integrate into workflow**:
   - Always run `/vaultmind-init` when starting work
   - Use `/vaultmind-deploy` after code changes
   - Run `/vaultmind-test` before finishing

---

## Files Created

**Agents**:
- `~/.claude/agents/vaultmind-agent-debugger.md`
- `~/.claude/agents/vaultmind-deployer.md`

**Skills**:
- `~/.claude/skills/vaultmind-init/skill.md`
- `~/.claude/skills/vaultmind-deploy/skill.md`
- `~/.claude/skills/vaultmind-test/skill.md`

**Documentation**:
- This file: `VAULTMIND-AGENT-ECOSYSTEM.md`

---

## Questions?

**Q: Why specialized VaultMind agents instead of generic ones?**
A: VaultMind is complex (9 agents, multi-provider, security-first). Generic agents don't understand the coordination, patterns, and architecture. Specialized agents are dramatically more effective.

**Q: Do these agents work outside VaultMind?**
A: No - they're VaultMind-specific. Use project-architect to create agents for other projects.

**Q: Can I modify these agents?**
A: Yes! They're markdown files. Edit them to match your workflow.

**Q: How do I update them?**
A: Edit the files directly, or use meta-agent to regenerate them with new requirements.

**Q: Performance impact?**
A: Minimal. vaultmind-agent-debugger uses Sonnet (balanced), vaultmind-deployer uses Haiku (fast). Skills are just structured prompts.

---

## Demonstration: Complete Development Cycle

```bash
# Day 1: Start work
cc /vaultmind-init
# [Context loaded, shows current state]

# Day 1: Notice an issue
cc "Agent 2 YouTube scraping seems to skip timestamps sometimes"

# Day 1: Debug
cc "Use vaultmind-agent-debugger to investigate Agent 2 timestamp extraction"
# [Agent identifies regex issue in content-scraper.ts:245]

# Day 1: Review fix with critical thinking
cc "Use critical-analyst to review this fix: [proposed change]"
# [Critical-analyst validates or suggests improvements]

# Day 1: Implement
cc "Implement the fix in content-scraper.ts:245"

# Day 1: Deploy
cc /vaultmind-deploy
# [Build complete, reload instructions provided]
# User reloads Obsidian

# Day 1: Test
cc /vaultmind-test
# [Runs full test suite, reports results]

# Day 1: Verify specific fix
cc "Test YouTube scraping with this URL: [url]"
# [Confirms timestamps now working]

# Done! Issue resolved in one session.
```

This is the power of project-specific agent ecosystems.
