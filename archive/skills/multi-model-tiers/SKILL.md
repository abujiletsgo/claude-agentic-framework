---
name: Multi-Model Tier Configuration
version: 0.1.0
description: "This skill should be used when optimizing model selection, configuring agent tiers, or when the user mentions model tiers, cost optimization, or model selection strategy. It configures and manages multi-model tier assignments for agents and tasks."
---

# Multi-Model Tier Configuration

Assign the right model to the right task for optimal cost/quality balance across all agents and workflows.

## Tier Definitions

### Tier 1: Opus (Deep Reasoning) -- 5 agents
**Model**: `claude-opus-4-6` / `opus`
**Cost**: $15/$75 per 1M tokens (input/output)
**Use for**:
- Orchestration and multi-agent planning
- Architecture and design decisions
- Security-critical analysis
- Complex multi-step reasoning chains
- Recursive context control (RLM)
- Critical thinking and risk analysis
- Autonomous meta-orchestration

**Agents assigned**:
- `orchestrator.md` -- multi-agent coordination and planning
- `project-architect.md` -- architecture design, agent ecosystem creation
- `critical-analyst.md` -- deep critical thinking, risk analysis
- `rlm-root.md` -- recursive context control, delegation
- `caddy.md` -- meta-orchestrator, autonomous goal decomposition

### Tier 2: Sonnet (Balanced) -- 16 agents
**Model**: `claude-sonnet-4-5` / `sonnet`
**Cost**: $3/$15 per 1M tokens (input/output)
**Use for**:
- Standard code generation and implementation
- Research and analysis
- Agent and skill generation
- Code review and refactoring
- Test generation
- Project scaffolding

**Agents assigned**:
- `builder.md` -- code implementation
- `researcher.md` -- research and analysis
- `meta-agent.md` -- agent file generation
- `project-skill-generator.md` -- skill/hook generation
- `scout-report-suggest.md` -- codebase scouting and analysis
- `llm-ai-agents-and-eng-research.md` -- AI/ML research
- `fetch-docs-sonnet45.md` -- doc fetching benchmark (sonnet)
- `agbot/combo-optimizer.md` -- AGBot combo optimization
- `agbot/strategy-advisor.md` -- AGBot strategy recommendations
- `agbot/market-researcher.md` -- AGBot market research
- `agbot/performance-analyzer.md` -- AGBot performance metrics
- `agbot/risk-assessor.md` -- AGBot risk assessment
- `team/guardrails/circuit-breaker-agent.md` -- state machine implementation
- `team/guardrails/cli-tool-agent.md` -- CLI interface
- `team/guardrails/integration-agent.md` -- system integration
- `team/guardrails/state-manager-agent.md` -- state persistence

### Tier 3: Haiku (Fast Tasks) -- 13 agents
**Model**: `claude-haiku-4-5` / `haiku`
**Cost**: $0.25/$1.25 per 1M tokens (input/output)
**Use for**:
- Read-only validation and verification
- Simple file operations and scraping
- Data validation and formatting
- Status reporting and TTS summaries
- Mechanical delegation (worktree creation)
- Documentation from templates

**Agents assigned**:
- `team/validator.md` -- read-only verification
- `create_worktree_subagent.md` -- mechanical slash command delegation
- `scout-report-suggest-fast.md` -- fast codebase scouting
- `docs-scraper.md` -- documentation scraping
- `fetch-docs-haiku45.md` -- doc fetching benchmark (haiku)
- `hello-world-agent.md` -- simple greeting
- `work-completion-summary.md` -- TTS audio summaries
- `agbot/data-ingestion-helper.md` -- AGBot data import
- `agbot/trader-data-validator.md` -- AGBot data quality checks
- `team/guardrails/config-agent.md` -- YAML config (low complexity)
- `team/guardrails/docs-agent.md` -- documentation writing
- `team/guardrails/qa-validator-agent.md` -- QA validation
- `team/guardrails/test-agent.md` -- test execution

## Changes Made (2026-02-11)

Agents downgraded for cost optimization:

| Agent | Before | After | Rationale |
|-------|--------|-------|-----------|
| builder | opus | sonnet | Implementation work, not architecture |
| meta-agent | opus | sonnet | Templated agent generation |
| project-skill-generator | opus | sonnet | Templated skill generation |
| validator | opus | haiku | Read-only checks, fast feedback loops |
| create-worktree-subagent | sonnet | haiku | Mechanical slash command invocation |
| agbot/combo-optimizer | opus | sonnet | Data analysis, not deep reasoning |
| agbot/strategy-advisor | opus | sonnet | Strategy recommendations |
| 8 guardrails agents | (none) | haiku/sonnet | Added frontmatter with model field |

## Decision Matrix

| Task Complexity | Risk Level | Recommended Tier |
|----------------|-----------|-----------------|
| High | High | Opus |
| High | Low | Sonnet |
| Medium | High | Opus |
| Medium | Low | Sonnet |
| Low | Any | Haiku |

## Cost Optimization Rules

1. **Default to Sonnet** unless specific conditions require upgrade/downgrade
2. **Upgrade to Opus** when:
   - Task involves security-critical decisions
   - Multi-step planning or coordination required
   - Architecture or design decisions
   - Debugging complex multi-file issues
   - Critical thinking about assumptions and risks
3. **Downgrade to Haiku** when:
   - Task is mechanical/repetitive
   - Output is intermediate (consumed by another agent)
   - Fast feedback loop needed (validation, checking)
   - Simple transformations or formatting
   - Data validation or schema checks

## Agent Configuration Template

When creating new agents, set the model tier in the frontmatter:

```yaml
---
name: my-agent
description: What this agent does
model: sonnet  # or opus, haiku
---
```

## Configuration File

Centralized tier configuration: `data/model_tiers.yaml`

Contains:
- Tier definitions with pricing
- All agent-to-tier assignments
- Skill default model overrides
- Cost estimation scenarios
- Decision matrix rules

## Tier Distribution

```
Opus:   5 agents (15%) -- orchestrator, project-architect, critical-analyst, rlm-root, caddy
Sonnet: 16 agents (47%) -- builder, researcher, meta-agent, + 13 more
Haiku:  13 agents (38%) -- validator, docs-scraper, hello-world, + 10 more
Total:  34 agents
```

## Estimated Savings

Compared to previous configuration (8 agents on Opus, rest on Sonnet):
- Opus agents reduced from 8 to 4 (50% reduction in Opus usage)
- 13 agents now on Haiku (12x cheaper than Sonnet, 60x cheaper than Opus)
- Validator on Haiku is the biggest single win (runs frequently, was on Opus)

For a heavy session with 50% subagent delegation:
- **Before**: ~$27 (all-Opus) or ~$8 (mixed Opus/Sonnet)
- **After**: ~$4-6 (optimized tiers)
- **Savings**: 50-60% vs previous mixed configuration

## Monitoring Cost

Track model usage via the observability system:
- Hook: `observability/post_tool_use.py` logs model used per agent
- Dashboard: `apps/observability/` shows cost breakdown
- Status line: `status_line_v6.py` shows current session model
- Config: `data/model_tiers.yaml` for centralized management

## Examples

### Example 1: Assigning Tiers to a New Agent Team

When creating agents for a new workflow:
```
Orchestrator: opus (plans, coordinates)
Builder 1: sonnet (implements feature A)
Builder 2: sonnet (implements feature B)
Validator: haiku (fast checks after each builder)
Documenter: haiku (writes final docs from template)
```

### Example 2: Dynamic Tier Escalation

For tasks where complexity varies:
```
Initial analysis: haiku (quick scan)
If complexity > threshold: escalate to sonnet
If security-critical: escalate to opus
```

### Example 3: Overriding in Task Calls

When spawning a subagent that needs a different tier than its default:
```python
Task(
    subagent_type="builder",
    prompt="Implement security-critical auth flow",
    model="opus"  # Override builder's default sonnet
)
```

## Integration with Framework

The model tier is set per-agent in their `.md` frontmatter. The framework respects this when spawning agents via the Task tool. Override with `model` parameter in Task calls when needed.

## Quick Reference

```
opus   = planning, security, architecture, critical analysis
sonnet = coding, research, analysis, agent generation, refactoring
haiku  = validation, data processing, docs, formatting, mechanical ops
```
