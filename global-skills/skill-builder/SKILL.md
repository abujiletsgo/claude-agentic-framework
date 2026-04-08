---
name: Skill Builder
version: 1.0.0
description: "Interactive skill creation assistant. Helps users design, generate, and install new Claude Code skills with proper structure, security, and testing."
user-invocable: true
---

# Skill Builder

Create new Claude Code skills interactively. Guides you through the design process, generates a properly formatted SKILL.md, installs it, and validates it works.

## When to Use

- User says: `/skill-builder`, "create a skill", "make a new skill", "automate this workflow"
- When a repeated workflow should be codified as a reusable skill
- When converting a manual process into a skill

## Workflow

### Step 1: Gather Requirements

Ask the user:

1. **What workflow do you want to automate?** Get a clear description of the task.
2. **When should this skill trigger?** Manual invocation (`/skill-name`) or automatic conditions.
3. **What tools does it need?** (Bash, Read, Edit, Write, Grep, Glob, WebFetch, etc.)
4. **What inputs does it need?** Arguments, file paths, configuration.
5. **What does success look like?** Expected outputs and side effects.

If the user gives a one-line description, infer reasonable defaults and confirm.

### Step 2: Analyze Project Context

Before generating, examine the project to understand conventions:

```bash
# Detect language and framework
ls package.json pyproject.toml Cargo.toml go.mod Makefile 2>/dev/null

# Check existing skills for style reference
ls .claude/skills/ 2>/dev/null
ls ~/.claude/skills/ 2>/dev/null

# Check project structure
find . -maxdepth 2 -type f -name "*.md" | head -10
```

Use this context to tailor the generated skill to the project's conventions.

### Step 3: Generate the SKILL.md

Use the template below. The generated skill MUST follow these rules:

**Required structure:**
- YAML frontmatter with name, description, user-invocable
- Clear "When to Use" section
- Step-by-step "Workflow" section
- At least one concrete "Example"

**Security rules (MANDATORY):**
- NEVER include `eval()`, `exec()`, or dynamic code execution
- NEVER include shell injection vectors (unquoted variables in bash)
- NEVER include hardcoded secrets, API keys, or credentials
- NEVER include `rm -rf /` or other destructive unbounded commands
- NEVER include `curl | bash` or piped execution from remote sources
- All file paths must be explicit, not constructed from user input without validation
- All Bash commands must be specific, not dynamically generated

**Quality rules:**
- Each step should be independently verifiable
- Include error handling guidance ("if X fails, do Y")
- Keep the skill focused -- one skill = one workflow
- Prefer idempotent operations (safe to run twice)

### Step 4: Write the Skill File

Place the generated SKILL.md at the correct location:

- **Project-level skill**: `.claude/skills/<skill-name>/SKILL.md`
- **Global skill**: `~/.claude/skills/<skill-name>/SKILL.md`

Ask the user which scope they prefer. Default to project-level.

```bash
# Create the skill directory and file
mkdir -p .claude/skills/<skill-name>
# Write SKILL.md content via the Write tool
```

### Step 5: Validate the Skill

After writing, perform these checks:

1. **Frontmatter valid**: YAML parses correctly, required fields present
2. **No security violations**: Scan for dangerous patterns listed above
3. **Workflow completeness**: At least 2 steps defined
4. **Examples present**: At least 1 example scenario
5. **Dry run**: Walk through the skill mentally with a sample input and confirm each step makes sense

Report validation results to the user.

## SKILL.md Template

Use this template as the starting point for generated skills:

```markdown
---
name: <skill-name>
description: "<one-line description of what the skill does>"
user-invocable: true
---

# <Skill Display Name>

<2-3 sentence description of the skill's purpose and value.>

## When to Use

- <Trigger condition 1>
- <Trigger condition 2>
- <Trigger condition 3>

## Workflow

### Step 1: <First Action>

<Description of what to do and why.>

### Step 2: <Second Action>

<Description of what to do and why.>

### Step 3: <Verification>

<How to verify the skill completed correctly.>

## Examples

### Example 1: <Scenario Name>

User: "<example invocation>"

1. <What the skill does first>
2. <What it does next>
3. <Expected outcome>
```

## Good vs Bad Skills

### Good Skill Characteristics

- **Focused**: Does one thing well ("Generate API client from OpenAPI spec")
- **Deterministic**: Same input produces same output
- **Safe**: No destructive operations without confirmation
- **Contextual**: Reads project state before acting
- **Verifiable**: Each step has a clear success/failure signal

### Bad Skill Characteristics

- **Too broad**: "Fix all code issues" -- no clear scope
- **Fragile**: Assumes specific file paths that may not exist
- **Destructive**: Deletes or overwrites without checking first
- **Magic**: Does things without explaining what or why
- **Stateful**: Depends on hidden state from previous runs

### Examples of Good Skills

**Good**: "Convert CSV data files to typed TypeScript interfaces"
- Clear input (CSV files), clear output (TS interfaces)
- Examines existing project types for naming conventions
- Generates one file per CSV, places in expected directory

**Good**: "Run database migration with rollback plan"
- Reads migration file, generates rollback SQL first
- Applies migration in transaction
- Verifies schema matches expected state

### Examples of Bad Skills

**Bad**: "Make the code better"
- No measurable outcome, no clear scope

**Bad**: "Deploy to production"
- Too dangerous for automation, needs human oversight
- Environment-specific, breaks across projects

## Advanced: Hook-Based Skills

If the user wants a skill that triggers automatically (not via slash command),
guide them to create a hook instead:

1. Write a Python script following the hook conventions in `global-hooks/`
2. Register it in `settings.json` under the appropriate event (PreToolUse, PostToolUse, Stop, etc.)
3. Use `uv run` as the command prefix
4. Always exit 0 to avoid blocking the workflow

Refer them to `/update-config` skill for registering the hook.

## Notes

- Generated skills are placed in `.claude/skills/` by default (project scope)
- Users can move to `~/.claude/skills/` for global availability
- Skills should be version-controlled with the project
- Review auto-generated skills in `~/.claude/skills/auto-generated/` for inspiration
