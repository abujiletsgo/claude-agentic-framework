# Roles and Responsibilities (R&R)

**Version**: 2.0.0 (February 2026)
**Status**: Comprehensive agent framework hierarchy documentation

This document defines the complete organizational structure, responsibilities, communication protocols, and decision authority for the Claude Agentic Framework.

---

## Table of Contents

1. [Hierarchy Overview](#hierarchy-overview)
2. [Agent Responsibilities Matrix](#agent-responsibilities-matrix)
3. [Communication Protocols](#communication-protocols)
4. [Tool and Skill Coordination](#tool-and-skill-coordination)
5. [Decision Authority](#decision-authority)
6. [Execution Patterns](#execution-patterns)
7. [Model Tier Assignments](#model-tier-assignments)

---

## Hierarchy Overview

### Organizational Structure

```mermaid
graph TD
    User[User] --> Orchestrator[Orchestrator<br/>Primary Coordinator<br/>Opus]

    Orchestrator --> RLM[RLM Root<br/>Recursive Controller<br/>Sonnet]
    Orchestrator --> ProjectArch[Project Architect<br/>System Designer<br/>Opus]
    Orchestrator --> Analyst[Critical Analyst<br/>Risk Analysis<br/>Opus]
    Orchestrator --> Researcher[Researcher<br/>Information Gathering<br/>Sonnet]
    Orchestrator --> MetaAgent[Meta-Agent<br/>Agent Generation<br/>Sonnet]
    Orchestrator --> Scout[Scout-Report-Suggest<br/>Read-Only Analysis<br/>Sonnet]
    Orchestrator --> DocsScraper[Docs Scraper<br/>Documentation<br/>Haiku]

    style User fill:#e1f5ff,stroke:#333
    style Orchestrator fill:#9b59b6,color:#fff
    style RLM fill:#3498db,color:#fff
    style ProjectArch fill:#9b59b6,color:#fff
    style Analyst fill:#9b59b6,color:#fff
    style Researcher fill:#3498db,color:#fff
    style MetaAgent fill:#3498db,color:#fff
    style Scout fill:#3498db,color:#fff
    style DocsScraper fill:#2ecc71,color:#fff
```

### Tier Breakdown

```
TIER 0: User
├── Issues high-level goals
└── Receives synthesized results

TIER 1: Primary Coordinator (Opus)
├── Orchestrator (Strategy Selection + Coordination)
├── Analyzes user intent
├── Selects optimal execution strategy
├── Plans and coordinates agent teams
├── Monitors overall progress
└── Reports completion

TIER 2: Strategic Agents (Opus)
├── Project Architect (Design)
└── Critical Analyst (Risk Analysis)

TIER 3: Execution Agents (Sonnet)
├── RLM Root (Recursive Codebase Exploration)
├── Researcher (Information Gathering)
├── Meta-Agent (Agent Generation)
└── Scout-Report-Suggest (Read-Only Analysis)

TIER 4: Support Agents (Haiku)
└── Docs Scraper (Documentation fetching)
```

---

## Agent Responsibilities Matrix

### Tier 1: Primary Coordinator

#### Orchestrator

**Role**: Primary coordinator with strategy selection and agent team management

| Responsibility | Input | Output | Tools | When to Delegate |
|---|---|---|---|---|
| **Analyze user intent** | Natural language request | Task classification (complexity, type, quality, scope) | Task, Read, Glob, Grep, Bash | Sometimes (to Caddy-Assistant for triage) |
| **Select execution strategy** | Task classification | Strategy selection (direct, team, rlm, fusion, research) | None | Never (core decision) |
| **Plan agent teams** | High-level goal | Agent team plan (roles, models, execution order) | Task, Read | Never (core responsibility) |
| **Match relevant skills** | Task classification | Skill recommendations | None | Sometimes (to Caddy-Assistant for audit) |
| **Spawn specialized agents** | Team plan | Sub-agent tasks | Task | Always (entire purpose) |
| **Coordinate execution** | Agent timeline | Execution management | Task | Never (coordination is core) |
| **Monitor execution progress** | Sub-agent status | Progress report | Task | Always (via sub-agents) |
| **Handle dependencies** | Agent dependencies | Sequential/parallel execution | Task | Never (coordination is core) |
| **Aggregate results** | All agent reports | Synthesized summary | None | Never (synthesis is core) |
| **Manage failures** | Agent failure report | Recovery action | Task | Always (spawn debugger agent) |
| **Report to user** | All sub-agent results | Executive summary | None | Never (core responsibility) |

**Decision Authority**:
- Chooses execution strategy
- Agent team composition
- Execution order (parallel vs sequential)
- Retry/recovery strategies
- Approves/blocks skills (based on Caddy-Assistant audit)
- Decides when to escalate to user
- Final authority on task completion

**Communication**:
- **Receives from**: User
- **Sends to**: RLM Root, Project Architect, Critical Analyst, Researcher, Meta-Agent, Scout-Report-Suggest, Docs Scraper
- **Reports to**: User

---

### Tier 2: Strategic Agents

---

#### RLM Root

**Role**: Recursive language model controller for infinite scale

| Responsibility | Input | Output | Tools | When to Delegate |
|---|---|---|---|---|
| **Search codebase** | Search pattern | File locations | Grep, Glob | Never (uses tools directly) |
| **Peek at files** | File paths | Brief orientation (max 50 lines) | Read | Never (targeted reading) |
| **Delegate analysis** | Code sections | Sub-agent tasks | Task | Always (for deep analysis) |
| **Synthesize findings** | Sub-agent reports | Aggregate analysis | None | Never (synthesis is core) |
| **Iterate exploration** | Current findings | Next search/analysis | Grep, Task | When needed (iterative discovery) |

**Decision Authority**:
- Which code sections to analyze
- When to iterate vs conclude
- Granularity of delegation

**Communication**:
- **Receives from**: Orchestrator, User (via /rlm command)
- **Sends to**: general-purpose sub-agents (for targeted analysis)
- **Reports to**: Orchestrator or User

**Pattern**: Search → Peek → Delegate → Synthesize → Repeat (if needed) → Report

---

#### Project Architect

**Role**: System designer and agent ecosystem creator

| Responsibility | Input | Output | Tools | When to Delegate |
|---|---|---|---|---|
| **Analyze projects** | Project directory | Architecture analysis | Read, Glob, Grep | Sometimes (spawn Researcher for large projects) |
| **Design agent ecosystems** | Project requirements | Custom agent specifications | Task | Never (design is core) |
| **Create automation workflows** | Project patterns | Skills, commands, agents | Write | Sometimes (spawn PSG for implementation) |
| **Design initialization guides** | Project structure | Onboarding documentation | Write | Never (documentation is core) |

**Decision Authority**:
- Agent ecosystem design
- Tool and skill recommendations
- Workflow patterns for project

**Communication**:
- **Receives from**: Caddy
- **Sends to**: Project Skill Generator (for implementation)
- **Reports to**: Caddy

---

#### Critical Analyst

**Role**: Risk analysis and assumption challenger

| Responsibility | Input | Output | Tools | When to Delegate |
|---|---|---|---|---|
| **Question assumptions** | Plan/decision | Challenge questions | None | Never (analysis is core) |
| **Identify risks** | Proposed approach | Risk assessment | Read, Grep | Sometimes (spawn Researcher for context) |
| **Challenge decisions** | Decision rationale | Alternative perspectives | None | Never (critical thinking is core) |
| **Force "why" articulation** | Implementation plan | Rationale validation | None | Never (questioning is core) |

**Decision Authority**:
- None (advisory only)
- All findings are recommendations to Caddy

**Communication**:
- **Receives from**: Caddy
- **Sends to**: Caddy (findings only)
- **Reports to**: Caddy

---

### Tier 3: Execution Agents

#### Researcher

**Role**: Information gathering specialist

| Responsibility | Input | Output | Tools | When to Delegate |
|---|---|---|---|---|
| **Gather information** | Research topic | Research report (2-4k tokens) | Read, Grep, WebSearch, Bash | Never (research is core) |
| **Analyze documentation** | Doc paths | Analysis summary | Read | Never (analysis is core) |
| **Search codebase** | Search pattern | Relevant code sections | Grep, Glob | Never (search is core) |
| **Synthesize findings** | Raw information | Concise report | None | Never (synthesis is core) |

**Decision Authority**:
- Research depth and breadth
- Information relevance
- Summary granularity

**Communication**:
- **Receives from**: Orchestrator, Caddy, RLM Root
- **Sends to**: Builder (via Orchestrator), Orchestrator
- **Reports to**: Orchestrator, Caddy, or RLM Root

**Token budget**: 20-50k tokens (isolated context)

---

#### Meta-Agent

**Role**: Agent file generator

| Responsibility | Input | Output | Tools | When to Delegate |
|---|---|---|---|---|
| **Generate agent files** | Agent specifications | Agent .md files with frontmatter | Write | Never (generation is core) |
| **Define agent roles** | Requirements | Role descriptions | None | Never (definition is core) |
| **Set model tiers** | Agent complexity | Model assignment (opus/sonnet/haiku) | None | Never (tier selection is core) |
| **Configure tools** | Agent purpose | Tool list | None | Never (configuration is core) |

**Decision Authority**:
- Agent file structure
- Model tier assignment
- Tool selection

**Communication**:
- **Receives from**: Orchestrator, Project Architect
- **Sends to**: None
- **Reports to**: Orchestrator or Project Architect

---

### Tier 4: Support Agents

#### Docs Scraper

**Role**: Documentation fetching specialist

| Responsibility | Input | Output | Tools | When to Delegate |
|---|---|---|---|---|
| **Fetch documentation** | URL | Markdown file | WebFetch, Write | Never (fetching is core) |
| **Convert and save** | Raw HTML | Structured .md file | Write | Never (conversion is core) |
| **Bulk scraping** | URL list | Multiple .md files | WebFetch, Write | Never (mechanical task) |

**Decision Authority**:
- Output file structure
- Markdown formatting

**Communication**:
- **Receives from**: Orchestrator, User (direct)
- **Sends to**: None
- **Reports to**: Orchestrator or User

---

## Communication Protocols

### Who Can Message Whom

```mermaid
graph LR
    User --> Orchestrator

    Orchestrator --> RLM
    Orchestrator --> ProjectArch
    Orchestrator --> Analyst
    Orchestrator --> Researcher
    Orchestrator --> MetaAgent
    Orchestrator --> Scout
    Orchestrator --> DocsScraper

    RLM --> SubAgents[general-purpose sub-agents]

    Analyst --> Orchestrator
    RLM --> Orchestrator
    ProjectArch --> Orchestrator
    Researcher --> Orchestrator
    MetaAgent --> Orchestrator
    Scout --> Orchestrator

    Orchestrator --> User
```

### Escalation Paths

```
Level 1: Execution Agent (Researcher, RLM Root, Scout-Report-Suggest)
  ↓ (Task blocked or failure)
Level 2: Strategic Agent (Project Architect, Critical Analyst)
  ↓ (Strategy failure or coordination needed)
Level 3: Primary Coordinator (Orchestrator)
  ↓ (Unresolvable or requires user decision)
Level 4: User
```

### Escalation Triggers

| Trigger | Current Level | Escalate To | Required Information |
|---|---|---|---|
| Task blocked (missing info) | Builder/Researcher | Orchestrator | Blocker description, attempted solutions |
| Agent failure (3+ retries) | Builder/Researcher | Orchestrator | Failure logs, context |
| Coordination failure | Strategic Agent | Orchestrator | Failed coordination plan, agent states |
| Ambiguous requirements | Any | Orchestrator | Ambiguity description, possible interpretations |
| Security critical decision | Any | Orchestrator | Decision context, risk assessment |
| Destructive operation | Any | Orchestrator → User | Operation description, impact assessment |
| Cost/time unusually high | Orchestrator | User | Estimate, rationale |
| Scope creep detected | Builder | Orchestrator | Original scope, discovered scope |

### Handoff Procedures

#### From User to Orchestrator

```yaml
Handoff Package:
  - task_description: "High-level goal in user's words"
  - (Orchestrator performs task classification):
      complexity: "simple|moderate|complex|massive"
      task_type: "implement|fix|refactor|research|test|review|document|deploy|plan"
      quality_need: "standard|high|critical"
      codebase_scope: "focused|moderate|broad|unknown"
  - relevant_context: "Key files, directories, constraints (if provided)"
  - success_criteria: "How to know when done"
  - constraints: "Time, resources, safety requirements"
```

#### From Orchestrator to Builder/Researcher

```yaml
Handoff Package:
  - task_id: "TaskList ID for tracking"
  - task_description: "Specific work to be done"
  - context: "Research reports, security checklists, etc."
  - acceptance_criteria: "Checklist for validation"
  - model: "opus|sonnet|haiku"
  - tools: ["Read", "Write", "Edit", "Bash"]
  - estimated_tokens: "Token budget estimate"
```

#### From Builder to Validator

```yaml
Handoff Package:
  - task_id: "TaskList ID"
  - work_summary: "What was implemented"
  - files_changed: ["file1.ts", "file2.ts"]
  - acceptance_criteria: "Original criteria from task"
  - validation_commands: ["npm test", "npm run lint"]
  - expected_results: "What should pass"
```

### Context Sharing Rules

#### What to Share

| Information Type | Share With | How | When |
|---|---|---|---|
| **Task classification** | Orchestrator | Via Caddy handoff | At delegation |
| **Research findings** | Builder | Via Orchestrator | Before implementation |
| **Security checklists** | Builder | Via Orchestrator | Before implementation |
| **Implementation summary** | Validator | Via Orchestrator | After completion |
| **Validation results** | Orchestrator | Direct report | After validation |
| **Failure context** | Debugger agent | Via Orchestrator | On failure |
| **Executive summary** | User | Via Caddy | At completion |

#### What NOT to Share

| Information Type | Why | Exception |
|---|---|---|
| **Raw agent outputs** | Too verbose, not synthesized | None |
| **Full file contents** | Token waste | Only targeted sections |
| **Debug logs** | Too low-level | Only on escalation |
| **All research material** | Information overload | Only relevant summaries |
| **Sub-agent internal state** | Implementation detail | None |

#### Context Compression

```python
# From Researcher to Builder
Raw Research: 45k tokens
↓
Synthesized Report: 2-4k tokens (only key findings)

# From Builder to Validator
Full Implementation: 30k tokens
↓
Summary + File List: 500 tokens

# From Orchestrator to Caddy
All Agent Reports: 10k tokens
↓
Executive Summary: 2-3k tokens
```

---

## Tool and Skill Coordination

### Tool Assignment by Role

| Tool | Orchestrator | RLM Root | Researcher | Project Architect | Scout-Report-Suggest | Meta-Agent |
|---|---|---|---|---|---|---|
| **Task** | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Read** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Write** | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
| **Edit** | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
| **Glob** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Grep** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Bash** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| **WebSearch** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **TaskCreate** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **TaskUpdate** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **TaskGet** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### Skill Invocation Authority

| Skill Category | Who Can Invoke | Who Recommends |
|---|---|---|
| **Context (prime)** | Orchestrator, Researcher | Orchestrator |
| **Knowledge (knowledge-db)** | Any agent | Orchestrator |
| **Quality (code-review, test-generator)** | Orchestrator, main session | Orchestrator |
| **Security (security-scanner)** | Critical Analyst, Orchestrator | Orchestrator |
| **Analysis (error-analyzer, refactoring-assistant)** | Orchestrator, main session | Orchestrator |
| **Meta (meta-agent)** | Orchestrator, Project Architect | Project Architect |

### Preventing Duplicate Tool Calls

#### Rule 1: Single Source of Truth for Task State

```yaml
Task State Owner: Orchestrator (primary coordinator)

Protocol:
  - Only Orchestrator updates TaskList state
  - Sub-agents report completion to Orchestrator
  - Orchestrator marks tasks completed
```

#### Rule 2: Read Operations Are Safe

```yaml
Read Operations: Read, Glob, Grep, TaskGet, Bash (read-only)

Rule:
  - Multiple agents can read same file simultaneously
  - No coordination needed for read-only operations
```

#### Rule 3: Write Operations Require Ownership

```yaml
Write Operations: Write, Edit, NotebookEdit, TaskUpdate, Bash (write)

Rule:
  - Only ONE agent writes to a file at a time
  - Orchestrator assigns file ownership during planning
  - Validator NEVER writes (enforced via disallowedTools)
```

#### Rule 4: File Ownership During Agent Teams

```yaml
Orchestrator Phase: Planning

For each file to be modified:
  - Assign to ONE Builder agent
  - Document in agent handoff
  - Other agents: read-only access

Example:
  Builder-1: auth/login.ts, auth/session.ts
  Builder-2: db/migrations/*.sql
  Builder-3: tests/auth/*.test.ts
```

### Coordination for File Access

#### Pattern: Sequential Dependency

```yaml
Scenario: Builder-1 must finish before Builder-2 starts

Orchestrator Plan:
  1. Builder-1 (writes auth/login.ts)
  2. Wait for Builder-1 completion
  3. Builder-2 (reads auth/login.ts, writes tests/login.test.ts)

Prevents: Race condition, file conflicts
```

#### Pattern: Parallel Independence

```yaml
Scenario: Builder-1 and Builder-2 work on different files

Orchestrator Plan:
  1. Builder-1 (writes src/feature-a.ts) [PARALLEL]
  2. Builder-2 (writes src/feature-b.ts) [PARALLEL]
  3. Wait for both to complete
  4. Validator (reads both)

Prevents: Blocking, unnecessary serialization
```

#### Pattern: Read-Validate-Write

```yaml
Scenario: Multiple agents need same context, one writes

Orchestrator Plan:
  1. Researcher (reads codebase, produces summary) [SINGLE]
  2. Wait for Researcher
  3. Builder-1 (reads summary, writes code-1) [PARALLEL]
  4. Builder-2 (reads summary, writes code-2) [PARALLEL]
  5. Builder-3 (reads summary, writes code-3) [PARALLEL]

Prevents: Each builder re-reading entire codebase
```

---

## Decision Authority

### Decision Matrix

| Decision Type | Authority | Can Be Overridden By | Requires Approval From |
|---|---|---|---|
| **Execution strategy selection** | Caddy | User | None |
| **Skill security approval** | Caddy | User | None (blocks on critical) |
| **Agent team composition** | Orchestrator | Caddy | None |
| **Agent model tier** | Meta-Agent, PSG | Caddy | None |
| **Implementation approach** | Builder | Orchestrator (scope only) | None |
| **Research depth** | Researcher | Orchestrator (token budget) | None |
| **Pass/fail determination** | Validator | Orchestrator (dispute) | None |
| **Task completion** | Assigned Agent | None | None |
| **Escalation to user** | Caddy | None | None |
| **Destructive operations** | None | User | User (always) |
| **Security-critical changes** | None | Caddy → User | User (destructive) or Caddy (non-destructive) |
| **Cost/time overrun** | None | Caddy → User | User |
| **Scope expansion** | None | Orchestrator → Caddy | Caddy or User |

### Approval Requirements

#### Destructive Operations (User Approval Required)

```yaml
Operations:
  - File deletion (rm, Delete tool)
  - Force push to main/master
  - Hard reset (git reset --hard)
  - Database schema changes
  - Production deployments
  - Credentials/secrets changes

Process:
  1. Agent detects destructive operation
  2. Escalate to Caddy
  3. Caddy presents to User with impact assessment
  4. User approves or denies
  5. Proceed only on explicit approval
```

#### Security-Critical Changes (Caddy Approval Required)

```yaml
Operations:
  - Authentication/authorization code
  - Cryptographic operations
  - API key/secret handling
  - Network security configuration
  - Input validation changes

Process:
  1. Builder implements with security best practices
  2. Critical Analyst reviews (if in team)
  3. Validator runs security tests
  4. Caddy reviews security checklist
  5. Caddy approves or requests changes
```

#### Cost/Time Overrun (User Approval Required)

```yaml
Thresholds:
  - Estimated tokens > 100k
  - Estimated time > 30 minutes
  - Estimated cost > $5

Process:
  1. Orchestrator or Caddy detects overrun
  2. Present revised estimate to User
  3. Explain rationale for increase
  4. User approves or requests alternative approach
```

### Escalation Decision Tree

```mermaid
graph TD
    Start[Agent Encounters Situation] --> Q1{Can agent resolve<br/>with current tools?}
    Q1 -->|Yes| Resolve[Resolve and continue]
    Q1 -->|No| Q2{Is it a blocker?}

    Q2 -->|No| Document[Document as note,<br/>continue]
    Q2 -->|Yes| Q3{Retry possible?}

    Q3 -->|Yes, < 3 retries| Retry[Retry with context]
    Q3 -->|No, or 3+ retries| Q4{Coordination issue?}

    Q4 -->|Yes| EscOrch[Escalate to<br/>Orchestrator]
    Q4 -->|No| Q5{Ambiguous requirements?}

    Q5 -->|Yes| EscCaddy[Escalate to<br/>Caddy]
    Q5 -->|No| Q6{Security/destructive?}

    Q6 -->|Yes| EscUser[Escalate to<br/>User via Caddy]
    Q6 -->|No| EscCaddy

    EscOrch --> Q7{Orchestrator<br/>can resolve?}
    Q7 -->|Yes| OrchFix[Orchestrator fixes<br/>via new agents]
    Q7 -->|No| EscCaddy

    EscCaddy --> Q8{Caddy<br/>can resolve?}
    Q8 -->|Yes| CaddyFix[Caddy changes<br/>strategy]
    Q8 -->|No| EscUser

    EscUser --> UserDecision[User decides]

    Resolve --> End[Continue execution]
    Document --> End
    Retry --> Start
    OrchFix --> End
    CaddyFix --> End
    UserDecision --> End

    style Start fill:#e1f5ff
    style End fill:#d4edda
    style EscUser fill:#f8d7da
    style Retry fill:#fff3cd
```

---

## Execution Patterns

### Pattern 1: Direct Execution

```yaml
Trigger: Simple task, standard quality, focused scope

Flow:
  1. User: "Fix typo in README.md line 42"
  2. Caddy (hook) classifies: simple/fix/standard/focused → direct strategy
  3. Claude session: Read → Edit → Complete
  4. Claude → User: Report

Token efficiency: Highest (no coordination overhead)
```

### Pattern 2: Research → Implement

```yaml
Trigger: Moderate task, needs context before implementation

Flow:
  1. User: "Add user authentication"
  2. Caddy (hook) classifies: moderate/implement/high/moderate → team strategy
  3. Claude → Researcher (parallel): "Explore existing auth code"
  4. Claude → Critical Analyst (parallel): "Identify auth risks"
  5. Claude waits for both
  6. Claude: Implement using sub-agent findings as context
  7. Claude → User: Summary

Participants: Claude session, Researcher, Critical Analyst
Token efficiency: Medium (research in isolation, synthesis)
```

### Pattern 3: RLM for Large Codebases

```yaml
Trigger: Massive task, broad scope, iterative exploration needed

Flow:
  1. User: /rlm "Find all N+1 query problems"
  2. RLM Root: Search codebase (Grep "ORM patterns")
  3. RLM Root: Peek at relevant locations (Read 30-50 lines each)
  4. RLM Root → sub-agents (×3 parallel): Analyze sections
  5. RLM Root waits for all 3
  6. RLM Root: Synthesize findings (prioritized list)
  7. RLM Root: Iterate if needed, then report

Participants: RLM Root, general-purpose sub-agents
Token efficiency: High (RLM never loads full context, uses search+peek+delegate)
```

### Pattern 4: Fusion (Best-of-N) for Critical Quality

```yaml
Trigger: Critical quality, security-sensitive, production-facing

Flow:
  1. User: /fusion "Implement payment processing"
  2. Orchestrator → 3 parallel general-purpose agents with different approaches
  3. Orchestrator: Score all 3 (correctness×3, simplicity×2, robustness×2, performance×1)
  4. Orchestrator: Fuse best solution
  5. Orchestrator → Critical Analyst: Security review
  6. Orchestrator → User: Report with confidence score

Token efficiency: Low (3× work) but quality maximized
Cost justification: Critical tasks worth 3× cost for 95% optimal vs 65% single-agent
```

### Pattern 5: Orchestrated Team

```yaml
Trigger: Complex multi-file task, multiple parallel workstreams

Flow:
  1. User: /orchestrate "Refactor database layer"
  2. Orchestrator plans: 3 independent modules
  3. Orchestrator → general-purpose agents ×3 (parallel): Refactor each module
  4. Orchestrator waits for all 3
  5. Orchestrator → User: Synthesized report

Token efficiency: Very high (maximum parallelization)
Time efficiency: ~3× faster than sequential
```

---

## Model Tier Assignments

### Tier Distribution

```yaml
Opus (3 agents — 37.5%):
  - Reason: Complex reasoning, deep analysis, strategic planning
  - Cost: Highest
  - Agents:
      - orchestrator (team coordination)
      - project-architect (system design)
      - critical-analyst (risk analysis)

Sonnet (4 agents — 50%):
  - Reason: Good balance of speed, quality, cost for implementation
  - Cost: Medium
  - Agents:
      - rlm-root (recursive codebase exploration)
      - researcher (information gathering)
      - meta-agent (agent generation)
      - scout-report-suggest (read-only analysis)

Haiku (1 agent — 12.5%):
  - Reason: Fast, cheap, sufficient for mechanical tasks
  - Cost: Lowest
  - Agents:
      - docs-scraper (doc fetching)
```

### Model Selection Decision Tree

```mermaid
graph TD
    Start[New Agent Needed] --> Q1{Requires deep<br/>reasoning/strategy?}

    Q1 -->|Yes| Q2{Multi-agent<br/>coordination?}
    Q2 -->|Yes| Opus1[Opus<br/>orchestrator]
    Q2 -->|No| Q3{Security/risk<br/>analysis?}
    Q3 -->|Yes| Opus2[Opus<br/>critical-analyst]
    Q3 -->|No| Q4{System design/<br/>architecture?}
    Q4 -->|Yes| Opus3[Opus<br/>project-architect]
    Q4 -->|No| Sonnet1[Sonnet<br/>fallback for complex]

    Q1 -->|No| Q5{Implementation/<br/>synthesis work?}
    Q5 -->|Yes| Sonnet2[Sonnet<br/>rlm-root/researcher/meta-agent]
    Q5 -->|No| Q6{Mechanical/<br/>validation task?}
    Q6 -->|Yes| Haiku1[Haiku<br/>validator/assistant]
    Q6 -->|No| Sonnet3[Sonnet<br/>default]

    Opus1 --> Record[Record in<br/>data/model_tiers.yaml]
    Opus2 --> Record
    Opus3 --> Record
    Sonnet1 --> Record
    Sonnet2 --> Record
    Sonnet3 --> Record
    Haiku1 --> Record

    Record --> Frontmatter[Add to agent<br/>frontmatter:<br/>model: opus/sonnet/haiku]

    style Start fill:#e1f5ff
    style Opus1 fill:#9b59b6,color:#fff
    style Opus2 fill:#9b59b6,color:#fff
    style Opus3 fill:#9b59b6,color:#fff
    style Sonnet1 fill:#3498db,color:#fff
    style Sonnet2 fill:#3498db,color:#fff
    style Sonnet3 fill:#3498db,color:#fff
    style Haiku1 fill:#2ecc71,color:#fff
    style Record fill:#f39c12,color:#fff
    style Frontmatter fill:#d4edda
```

### Cost Optimization Guidelines

| Scenario | Recommended Model | Rationale |
|---|---|---|
| **Simple file operations** | Haiku | Fast, cheap, sufficient |
| **Code implementation** | Sonnet | Quality + speed balance |
| **Multi-file refactoring** | Sonnet | Needs understanding + speed |
| **Security audit** | Opus | Deep reasoning required |
| **Test generation** | Sonnet | Mechanical but needs understanding |
| **Documentation writing** | Sonnet | Clear writing + code understanding |
| **Agent team planning** | Opus | Strategic coordination |
| **Codebase exploration** | Sonnet | Search + synthesis |
| **Validation/verification** | Haiku | Read-only, straightforward checks |
| **Architecture design** | Opus | Trade-off analysis |

---

## Summary

This document provides the complete organizational structure for the Claude Agentic Framework. Key takeaways:

1. **Hierarchy is strict**: User → Orchestrator → Strategic Agents → Execution Agents → Support Agents
2. **Responsibilities are non-overlapping**: Each agent has clear boundaries
3. **Communication follows protocols**: Escalation, handoff, and context sharing are well-defined
4. **Tools are role-specific**: Write operations require ownership, reads are safe
5. **Decision authority is explicit**: Clear approval requirements prevent conflicts
6. **Patterns are reusable**: Direct, Research-Build-Test, RLM, Fusion, Parallel, Sequential
7. **Model tiers optimize cost**: Right model for the right task (50-60% savings)

For implementation details, see:
- [CLAUDE.md](../CLAUDE.md) - Operational protocols
- [README.md](../README.md) - Framework overview
- [2026_UPGRADE_GUIDE.md](2026_UPGRADE_GUIDE.md) - Migration guide
- [SECURITY_BEST_PRACTICES.md](SECURITY_BEST_PRACTICES.md) - Security layer details

---

**Version**: 2.1.0 (February 2026)
**Last Updated**: 2026-02-25
**Maintained by**: Claude Agentic Framework Core Team
