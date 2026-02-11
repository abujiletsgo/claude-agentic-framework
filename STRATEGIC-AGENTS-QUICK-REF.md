# Strategic Agents Quick Reference

## 🏗️ project-architect

**One-liner**: Creates custom agent ecosystems, skills, and tools for your projects.

**When**: After planning/understanding stage of new/existing projects

**Example Uses**:
```bash
# Analyze project and create custom agents
cc "Use project-architect to analyze this Next.js project and create development agents"

# Create project-specific skills
cc "Use project-architect to create a VaultMind-specific development workflow"

# Design initialization process
cc "Use project-architect to design the setup process for new developers on this project"
```

**Output**: Custom agents, skills, commands, and initialization guides

**Model**: Opus (thorough analysis and design)

---

## 🔍 critical-analyst

**One-liner**: Questions every detail and forces you to think through decisions.

**When**: Before finalizing plans, during reviews, making technical choices

**Example Uses**:
```bash
# Before implementing
cc "Use critical-analyst to review this architecture plan"

# During development
cc "Use critical-analyst to question this API design decision"

# Before completion
cc "Use critical-analyst to review if we're actually solving the right problem"

# Continuous mode
cc "Keep critical-analyst active to question all decisions during this session"
```

**Output**: Questions, identified risks, alternative approaches, recommendations

**Model**: Sonnet (balanced speed and depth)

---

## 🔄 How They Work Together

### Scenario 1: New Project Setup
```
You → project-architect: "Analyze this codebase"
project-architect → Creates agent designs
You → critical-analyst: "Review these designs"
critical-analyst → Questions assumptions, suggests improvements
You → Refine designs
project-architect → Creates final agents/skills
```

### Scenario 2: Feature Planning
```
You → Plan feature X
You → critical-analyst: "Review this plan"
critical-analyst → Identifies 3 risks, suggests 2 alternatives
You → Adjust plan
You → Build feature
You → critical-analyst: "Review implementation"
critical-analyst → Validates or identifies issues
```

### Scenario 3: Architecture Review
```
You → Design system architecture
You → critical-analyst: "Challenge every assumption in this design"
critical-analyst → 10 critical questions, 5 risks, 3 alternatives
You → Address questions and refine design
You → project-architect: "Create tooling for this architecture"
project-architect → Creates deployment, testing, monitoring agents
```

---

## 💡 Pro Tips

### For project-architect:
1. **Be specific**: "Create an agent for X" works better than "help with project"
2. **Point to examples**: Reference existing files/patterns in the project
3. **Think meta-level**: Ask for agent ecosystems, not individual scripts
4. **After major changes**: Re-run to update tooling

### For critical-analyst:
1. **Use early**: Before building, not after
2. **Be open**: Don't get defensive, embrace the questioning
3. **Request specifics**: "Question the concurrency model" better than "review code"
4. **Continuous mode**: Keep it active during planning phases
5. **Combine with others**: Use before orchestrator, builder, or validator

---

## 🎯 Quick Decision Tree

```
Starting new project?
└─→ Use project-architect

Joining existing project?
└─→ Use project-architect

About to implement a plan?
└─→ Use critical-analyst first

Made a technical decision?
└─→ Ask critical-analyst to validate

Something seems too simple?
└─→ critical-analyst will tell you what you missed

Need project-specific automation?
└─→ Use project-architect

Requirements are vague?
└─→ Use critical-analyst to clarify

Before marking task complete?
└─→ Use critical-analyst + validator

Creating a new agent?
└─→ Use project-architect to design, critical-analyst to review, meta-agent to generate
```

---

## 🚀 One-Command Power Combos

### Combo 1: Complete Project Setup
```bash
cc "Use project-architect to analyze this project and create a development agent ecosystem, then use critical-analyst to review the design and identify any gaps."
```

### Combo 2: Validated Feature Planning
```bash
cc "Create a plan for feature X, then use critical-analyst to challenge every assumption and suggest alternatives, then refine the plan based on feedback."
```

### Combo 3: Meta-Agent Creation
```bash
cc "Use project-architect to design a 'security-auditor' agent for this project, critical-analyst to review the design, and meta-agent to generate the final agent file."
```

### Combo 4: Architecture Deep Dive
```bash
cc "Use critical-analyst to perform a comprehensive review of this architecture, questioning every technical choice, assumption, and risk. Be thorough and ruthless."
```

### Combo 5: Project Onboarding
```bash
cc "Use project-architect to create a complete onboarding workflow including: project structure guide, development setup script, testing guide, and deployment process. Then use critical-analyst to identify what's missing."
```

---

## 📊 Comparison with Other Agents

| Agent | Purpose | When to Use |
|-------|---------|------------|
| **project-architect** | Create project-specific agents/tools | Project init, need custom automation |
| **critical-analyst** | Question and validate decisions | Before building, during reviews |
| **meta-agent** | Generate generic agent files | Need a new agent type |
| **orchestrator** | Coordinate multi-agent workflows | Complex multi-step tasks |
| **researcher** | Deep research and analysis | Need information gathering |
| **builder** | Implement solutions | Actual coding/building work |
| **validator** | Verify implementations | After building, need verification |

---

## 🎓 Learning Path

### Week 1: Get Comfortable
- Day 1-2: Try critical-analyst on existing plans
- Day 3-4: Use project-architect on a small project
- Day 5-7: Combine them on a real task

### Week 2: Build Habits
- Always use critical-analyst before implementing
- Use project-architect on new projects automatically
- Start combining with other agents

### Week 3: Advanced Patterns
- Keep critical-analyst active during sessions
- Create agent ecosystems with project-architect
- Design multi-agent workflows

### Week 4: Mastery
- Proactively invoke before decisions
- Design custom agent collaboration patterns
- Teach patterns to other team members

---

## ⚡ Common Mistakes to Avoid

1. ❌ Using them on trivial tasks (one-line fixes)
2. ❌ Ignoring critical-analyst feedback
3. ❌ Using project-architect without providing project context
4. ❌ Not combining them (they're designed to work together)
5. ❌ Waiting until after building to question decisions
6. ❌ Being too vague ("help with project" vs "create testing automation")
7. ❌ Not updating tooling when project evolves

---

## 📞 Getting Help

If something's unclear:
1. Read the full agent files for comprehensive context
2. Check MIGRATION-CRYPTO-TO-STRATEGIC-AGENTS.md for examples
3. Try on a small project first
4. Use critical-analyst to question how to use the agents (meta!)

## 🔗 Related Files

- Full migration guide: `MIGRATION-CRYPTO-TO-STRATEGIC-AGENTS.md`
- Agent files: `global-agents/project-architect.md`, `global-agents/critical-analyst.md`
- Framework docs: `CLAUDE.md`
- General agent creation: `global-agents/meta-agent.md`
