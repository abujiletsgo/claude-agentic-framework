# Team Templates

Pre-configured multi-agent team structures for common engineering tasks.

## Available Templates

### 1. Review Team (`review_team.yaml`)
**Purpose**: Multi-perspective code review with security, performance, and architecture analysis

**Team Members**:
- `security-reviewer` (Opus) - Security vulnerabilities, input validation, auth
- `performance-reviewer` (Sonnet) - Performance bottlenecks, algorithmic complexity
- `architecture-reviewer` (Opus) - Code structure, maintainability, design patterns

**Usage**:
```bash
uv run scripts/load_team_template.py review_team --files "src/api/**/*.py"
uv run scripts/load_team_template.py review_team --diff HEAD~1
```

**Coordination**: Parallel analysis, then synthesis by architecture-reviewer

---

### 2. Architecture Team (`architecture_team.yaml`)
**Purpose**: Multi-layer system architecture design

**Team Members**:
- `frontend-architect` (Sonnet) - UI/UX, components, state management
- `backend-architect` (Opus) - API design, business logic, scalability
- `data-architect` (Opus) - Database schema, migrations, query optimization
- `infrastructure-architect` (Sonnet) - Deployment, CI/CD, monitoring

**Usage**:
```bash
uv run scripts/load_team_template.py architecture_team --requirements docs/spec.md
uv run scripts/load_team_template.py architecture_team
```

**Coordination**: Iterative consensus with integration reviews

---

### 3. Research Team (`research_team.yaml`)
**Purpose**: Deep technology research and comparison

**Team Members**:
- `primary-researcher` (Sonnet) - Documentation analysis, API exploration
- `comparative-researcher` (Sonnet) - Alternative technologies, trade-off analysis
- `integration-researcher` (Haiku, optional) - Codebase compatibility, tooling

**Usage**:
```bash
uv run scripts/load_team_template.py research_team --topic "React state management (Redux vs Zustand)"
uv run scripts/load_team_template.py research_team --topic "PostgreSQL vs MongoDB"
```

**Coordination**: Independent research, then debate to reach consensus

---

### 4. Debug Team (`debug_team.yaml`)
**Purpose**: Parallel debugging with competing hypotheses

**Team Members**:
- `hypothesis-1-debugger` (Sonnet) - Configuration/environment issues
- `hypothesis-2-debugger` (Sonnet) - Code logic errors
- `hypothesis-3-debugger` (Sonnet) - Data/schema issues
- `hypothesis-4-debugger` (Haiku, optional) - External dependencies
- `hypothesis-5-debugger` (Haiku, optional) - Resource constraints

**Usage**:
```bash
uv run scripts/load_team_template.py debug_team --bug-report .claude/bugs/issue_123.md
```

**Coordination**: Competing hypotheses with early exit on confirmation

---

## Script Usage

### List Templates
```bash
uv run scripts/load_team_template.py --list
```

### Spawn a Team
```bash
# Review team
uv run scripts/load_team_template.py review_team --files "src/**/*.py"
uv run scripts/load_team_template.py review_team --diff HEAD~1

# Architecture team
uv run scripts/load_team_template.py architecture_team --requirements docs/spec.md

# Research team
uv run scripts/load_team_template.py research_team --topic "Your research question"

# Debug team
uv run scripts/load_team_template.py debug_team --bug-report path/to/bug.md
```

---

## Template Structure

Each YAML template includes:

```yaml
name: Team Name
purpose: High-level purpose description
team_type: category (review, architecture, research, debug)

teammates:
  - name: agent-name
    model: opus|sonnet|haiku
    focus_area: Specialization area
    domain:
      files: ["**/*.py"]  # File patterns
      exclude: ["**/tests/**"]
    responsibilities:
      - Specific task 1
      - Specific task 2
    output_format: |
      Markdown template for output

coordination:
  strategy: parallel_then_synthesize|iterative_consensus|competing_hypotheses
  phases:
    - phase: phase_name
      agents: [agent1, agent2]
      execution: parallel|sequential
      timeout: 300

communication:
  shared_context:
    key: value
  handoff_protocol:
    - "Step 1"
    - "Step 2"
  output_location: .claude/teams/

exit_criteria:
  success: [conditions]
  failure: [conditions]
  partial_success: [conditions]
```

---

## Security

The `load_team_template.py` script includes input validation:
- Blocks dangerous shell characters (`;`, `|`, `&`, `$`, `` ` ``)
- Validates template names (alphanumeric + `_` and `-` only)
- Validates path inputs to prevent command injection

---

## Future Justfile Integration

When the framework's prompt hooks are updated, these commands can be added to `justfile`:

```just
# List available team templates
team-list:
    uv run {{project_root}}/scripts/load_team_template.py --list

# Spawn code review team
team-review files:
    uv run {{project_root}}/scripts/load_team_template.py review_team --files {{files}}

# Spawn architecture team
team-architecture requirements:
    uv run {{project_root}}/scripts/load_team_template.py architecture_team --requirements {{requirements}}

# Spawn research team
team-research topic:
    uv run {{project_root}}/scripts/load_team_template.py research_team --topic {{topic}}

# Spawn debug team
team-debug bug_report:
    uv run {{project_root}}/scripts/load_team_template.py debug_team --bug-report {{bug_report}}
```

Currently blocked by prompt hook security validation. The Python script has proper validation but the hook doesn't trust justfile's variable interpolation mechanism.

---

## Extending

To create a new team template:

1. Copy an existing template as a starting point
2. Define your team members with appropriate models
3. Set domain boundaries (file patterns)
4. Define coordination strategy
5. Specify communication patterns
6. Set exit criteria
7. Test with: `uv run scripts/load_team_template.py your_template --args`
