# Plan: CAF v5.0 — Sprint System + Research Intelligence

**Version**: 3.0 (Definitive)
**Status**: Draft
**Scope**: Two integrated subsystems — Sprint Orchestration + Research Intelligence

---

## Executive Summary

Upgrade CAF to v5.0 with two integrated capabilities:

1. **Sprint System** — PM → Lead → Worker hierarchy via tmux, powered by gstack skills
2. **Research Intelligence** — Domain-specific MCP servers, TOON encoding, two-step reasoning

**Combined impact**: True 3-tier agent hierarchy (breaking the flat-agent ceiling), ~60% token reduction on research, persistent sprint memory across sessions, full audit trail.

---

## Part A: Sprint Orchestration System

### The Core Problem

Claude Code's agent hierarchy is **flat**: spawned sub-agents cannot spawn further sub-agents. The orchestrator must micromanage every worker directly — one root agent juggling 10+ builders/validators with no delegation chain.

**tmux solves this.** Each tmux pane is an independent root-level Claude Code session with full `Agent()` access. This enables:

```
PM (Opus, main pane)
├── Planning Lead (Sonnet, tmux pane) ← root session, CAN spawn agents
│   └── researcher (sub-agent)
├── Engineering Lead (Sonnet, tmux pane) ← root session, CAN spawn agents  
│   ├── builder-1 (sub-agent)
│   ├── builder-2 (sub-agent)
│   └── validator (sub-agent)
├── QA Lead (Sonnet, tmux pane) ← root session, CAN spawn agents
│   └── test-runner (sub-agent)
├── Security Lead (Sonnet, tmux pane) ← root session
│   └── scanner (sub-agent)
└── TUI Dashboard (dedicated pane) ← Textual app, no Claude
```

### gstack Integration (Upstream Dependency, Never Forked)

gstack installs at `~/.claude/skills/gstack/`. CAF never modifies gstack files.

**Discovery**: `bin/gstack-bridge` reads gstack's directory structure and CLAUDE.md sections dynamically. If gstack adds new skills, they're auto-discovered. If gstack is missing, sprint degrades to CAF-only skills.

**Usage**: Leads invoke gstack skills directly (`/review`, `/qa`, `/cso`) because they're root sessions with gstack installed. CAF doesn't proxy or wrap gstack commands.

### tmux Session Layout

```
┌────────────────────────────────────────────────────────────────────────────────┐
│  tmux session: sprint-<id>                                                     │
│                                                                                │
│  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────────────────┐ │
│  │ PANE 0: PM         │  │ PANE 1: Plan Lead  │  │ PANE 5: TUI Dashboard   │ │
│  │ (Opus root)        │  │ (Sonnet root)      │  │                          │ │
│  │                    │  │ → /plan-ceo-review  │  │  ╔══ SPRINT ════════╗   │ │
│  │ • decomposes task  │  │ → /plan-eng-review  │  │  ║ Lead Status      ║   │ │
│  │ • writes prompts   │  │ → spawns researcher │  │  ║ PLAN  ▓▓▓▓▓ done║   │ │
│  │ • monitors IPC     │  │ → writes result.md  │  │  ║ BUILD ▓▓░░░ 40% ║   │ │
│  │ • gates waves      │  │                    │  │  ║ QA    ░░░░░ wait ║   │ │
│  ├────────────────────┤  ├────────────────────┤  │  ╠══ Live Log ══════╣   │ │
│  │ PANE 2: Eng Lead   │  │ PANE 3: QA Lead    │  │  ║ [eng] building.. ║   │ │
│  │ (Sonnet root)      │  │ (Sonnet root)      │  │  ║ [qa]  waiting    ║   │ │
│  │ → spawns builders  │  │ → /qa, /browse     │  │  ╠══ Report ════════╣   │ │
│  │ → spawns validators│  │ → spawns testers   │  │  ║ (aggregated)     ║   │ │
│  ├────────────────────┤  ├────────────────────┤  │  ╚═════════════════╝   │ │
│  │ PANE 4: Sec Lead   │  │                    │  │                          │ │
│  │ (Sonnet root)      │  │                    │  │                          │ │
│  │ → /cso             │  │                    │  │                          │ │
│  └────────────────────┘  └────────────────────┘  └──────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────┘
```

### IPC Protocol (Filesystem-Based)

All sprint coordination happens through a shared directory. No sockets, no daemons.

```
/tmp/caf_sprint/<sprint-id>/
├── events.jsonl            ← structured audit trail (append-only JSONL)
├── status.json             ← per-lead health: {role: {status, wave, started}}
├── gate.json               ← wave locks: {unlocked_waves: [0, 1, ...]}
├── pm_plan.md              ← PM's decomposition (plain text, readable)
├── prompts/                ← per-lead prompt files (plain text, readable)
│   ├── planning-lead.md
│   ├── engineering-lead.md
│   └── ...
├── results/                ← per-lead output files (plain text)
│   ├── planning-lead_result.md
│   └── ...
├── logs/                   ← per-lead streaming logs (tailed by TUI)
│   ├── planning-lead.log
│   └── ...
└── report.md               ← live aggregated report
```

**All IPC files are plain text / JSON.** Everything must be human-readable and debuggable.

### Wave Execution Model

```yaml
Wave 0 (Plan):     planning-lead runs all /plan-* reviews in parallel → synthesizes
Wave 1 (Build):    engineering-lead builds features (spawns builders per component)
Wave 2 (Validate): review-lead + qa-lead + security-lead run in parallel
Wave 3 (Ship):     release-lead merges, deploys, documents (sequential, final)
```

PM gates each wave: Wave N+1 doesn't start until all Wave N leads report "done" in status.json.

---

## Part B: Research Intelligence Upgrade

### New MCP Servers

Three MCP servers give agents structured access to research sources, replacing raw web_fetch → parse-HTML flows.

| MCP Server | Sources | Install | Token Impact |
|-----------|---------|---------|--------------|
| **paper-search-mcp** | arXiv, PubMed, Semantic Scholar, Crossref, OpenAlex + 6 more | `uv tool install paper-search-mcp` | ~1K tok vs ~12K tok per paper lookup |
| **sourcegraph-mcp** | Cross-repo code search with regex, language, repo filters | `uv tool install sourcegraph-mcp` | ~2K tok vs ~7K tok per code search |
| **papersflow** | 474M+ papers, citation graph traversal, systematic reviews | Remote MCP (no install) | Unique capability (citation graphs) |

**settings.json.template additions:**
```json
"papers": {
  "command": "uv",
  "args": ["tool", "run", "paper-search-mcp"],
  "env": { "PAPER_SEARCH_MCP_SEMANTIC_SCHOLAR_API_KEY": "${SEMANTIC_SCHOLAR_API_KEY:-}" }
},
"sourcegraph": {
  "command": "sourcegraph-mcp",
  "env": {
    "SOURCEGRAPH_URL": "https://sourcegraph.com",
    "SOURCEGRAPH_TOKEN": "${SRC_ACCESS_TOKEN}"
  }
},
"papersflow": {
  "type": "url",
  "url": "https://doxa.papersflow.ai/mcp",
  "transport": "streamable-http"
}
```

### Domain-Specific Research Agents

| Agent | Tools | When to Use |
|-------|-------|-------------|
| `researcher.md` (updated) | papers, sourcegraph, papersflow, WebSearch, WebFetch | General research — routes to right tool per query type |
| `code-researcher.md` (new) | sourcegraph, WebFetch | "How do other projects implement X" |
| `academic-researcher.md` (new) | papers, papersflow | Papers, citations, literature reviews |

**Tool routing table** (embedded in agent .md files):

| Query Type | Primary Tool | Fallback |
|-----------|-------------|----------|
| Academic papers, citations | mcp__papers | mcp__papersflow |
| Code patterns, implementations | mcp__sourcegraph | WebSearch + "site:github.com" |
| Current events, news | WebSearch → WebFetch | — |
| Library documentation | WebFetch (direct URL) | WebSearch |
| Citation graph / "who cited this" | mcp__papersflow | — |

### TOON Inter-Agent Encoding

**TOON (Token-Oriented Object Notation)** — a lightweight encoding for **uniform lists of flat objects** (search results, file scans). Keys declared once in header, then CSV rows.

```
JSON (2400 tokens for 10 papers):
[{"title":"Paper A","authors":"Smith","year":2025,"doi":"10.1234"},...]

TOON (1400 tokens for 10 papers):
[10,{title,authors,year,doi}]
Paper A,Smith,2025,10.1234
...
```

**~40% savings on tabular inter-agent data.**

**When to use TOON:**
| Data Shape | Format | Why |
|-----------|--------|-----|
| List of search results (uniform fields) | TOON | 40% savings |
| List of code matches (uniform) | TOON | 40% savings |
| Analysis/synthesis prose | Plain text | TOON adds overhead |
| Deeply nested config | JSON | TOON is worse for nesting |
| Mixed-type responses | JSON | TOON requires uniform schema |

**Implementation**: `lib/toon_utils.py` with `encode_results()` / `decode_results()`. Falls back to compact JSON for non-eligible data.

### Two-Step Reasoning/Formatting

For **synthesis tasks** (not simple lookups), split into:
1. **Reasoning** (Sonnet, unconstrained): Think freely about findings
2. **Formatting** (Haiku, strict schema): Convert analysis to structured output

**Why**: Research shows constraining LLM output to JSON during reasoning degrades performance by 10-15% (Tam et al. 2024, "Let Me Speak Freely?").

**Which agents use two-step:**
| Agent | Two-Step? | Reason |
|-------|-----------|--------|
| researcher (synthesis) | YES | Quality on analysis matters |
| critical-analyst | YES | Entire role is reasoning |
| meta-agent | YES | Strategic decisions |
| builder | NO | Code generation, not analysis |
| validator | NO | Binary pass/fail |
| docs-scraper | NO | Simple extraction |

### Research Skill Routing

Four domain-specific research skills the orchestrator dispatches to:

| Skill | Trigger | MCP Tools | Model |
|-------|---------|-----------|-------|
| `research-academic` | papers, studies, citations | papers, papersflow | Sonnet + Haiku (format) |
| `research-code` | implementation, pattern, repo | sourcegraph | Sonnet |
| `research-news` | recent, news, trends | WebSearch, WebFetch | Sonnet |
| `research-docs` | library docs, API reference | WebFetch | Haiku |

**Sprint integration**: The planning-lead can dispatch these research skills when decomposing. Engineering-lead can use code-researcher to find patterns before building.

---

## File Map

### New Files

```
# Sprint System (Part A)
global-skills/sprint/SKILL.md                        ← PM protocol skill
global-agents/sprint-lead.md                          ← lead agent (fallback mode)
bin/tmux-sprint                                       ← tmux session lifecycle
bin/gstack-bridge                                     ← gstack discovery
bin/sprint-event                                      ← JSONL event emitter
data/sprint_config.yaml                               ← roles, waves, IPC, memory config

# TUI Dashboard
dashboard/sprint_tui.py                               ← Textual app entry
dashboard/widgets/lead_panel.py                       ← lead status table
dashboard/widgets/log_viewer.py                       ← live log stream
dashboard/widgets/report_panel.py                     ← aggregated report
dashboard/widgets/wave_progress.py                    ← wave progress bars
dashboard/sprint_tui.css                              ← theme + layout

# Sprint Memory Hooks
global-hooks/hooks_SessionStart/check_gstack.py       ← gstack health check
global-hooks/hooks_SubagentStart/inject_sprint_context.py ← sprint + KG context

# Research Intelligence (Part B)
global-agents/code-researcher.md                      ← sourcegraph-focused agent
global-agents/academic-researcher.md                  ← paper-search-focused agent
global-skills/research-academic/SKILL.md              ← academic research skill
global-skills/research-code/SKILL.md                  ← code pattern research skill
global-skills/research-news/SKILL.md                  ← news/events research skill
global-skills/research-docs/SKILL.md                  ← docs lookup skill
lib/toon_utils.py                                     ← TOON encoder/decoder
```

### Modified Files (Phase 5 only)

```
data/caddy_config.yaml                  ← add sprint strategy + research skills
data/model_tiers.yaml                   ← add sprint-lead tier
templates/settings.json.template        ← new hooks + MCP servers + permissions
global-agents/researcher.md             ← update with MCP tool routing + two-step
global-skills/worktree/SKILL.md         ← add /worktree sprint subcommand
global-skills/orchestrate/SKILL.md      ← sprint strategy awareness
scripts/generate_docs.py                ← register new skills + agents
```

---

## Detailed Component Specs

### Component 1: `data/sprint_config.yaml`

```yaml
# CAF Sprint System Configuration
# Single source of truth — everything reads this

sprint:
  # gstack (upstream dependency, never modified)
  gstack:
    path: "~/.claude/skills/gstack"
    auto_update_check_days: 7

  # tmux
  tmux:
    session_prefix: "sprint"
    layout: "tiled"
    dashboard_pane_width_pct: 28

  # IPC filesystem
  ipc:
    base_dir: "/tmp/caf_sprint"
    poll_interval_seconds: 5

  # structured logging
  logging:
    events_format: "jsonl"
    include_token_counts: true
    include_timing: true
    audit_trail: true
    archive_on_teardown: true               # copy events.jsonl to ~/.claude/data/sprint_events/

  # wave definitions
  waves:
    0: { name: "Plan", parallel: true, gate: true, failure_policy: "block" }
    1: { name: "Build", parallel: true, gate: true, failure_policy: "escalate" }
    2: { name: "Validate", parallel: true, gate: true, failure_policy: "escalate" }
    3: { name: "Ship", parallel: false, gate: false, failure_policy: "block" }

  # lead roles
  leads:
    planning-lead:
      wave: 0
      gstack_skills: ["/plan-ceo-review", "/plan-eng-review", "/plan-design-review",
                       "/plan-devex-review", "/autoplan"]
      caf_fallback_agents: ["researcher"]
      description: "Synthesize all planning reviews into unified architecture decision"
      token_budget: 50000

    engineering-lead:
      wave: 1
      gstack_skills: ["/investigate", "/pair-agent", "/careful"]
      caf_fallback_agents: ["builder", "validator", "researcher"]
      description: "Build features with spawned builders, validate with spawned validators"
      token_budget: 100000

    review-lead:
      wave: 2
      gstack_skills: ["/review", "/devex-review", "/codex"]
      caf_fallback_agents: ["critical-analyst"]
      description: "Code review and cross-model comparison"
      token_budget: 60000

    qa-lead:
      wave: 2
      gstack_skills: ["/qa", "/qa-only", "/browse"]
      caf_fallback_agents: ["validator"]
      description: "End-to-end QA, browser testing, regression checks"
      token_budget: 80000

    security-lead:
      wave: 2
      gstack_skills: ["/cso"]
      caf_fallback_agents: ["scout-report-suggest"]
      description: "OWASP/STRIDE security audit"
      token_budget: 40000

    release-lead:
      wave: 3
      gstack_skills: ["/ship", "/land-and-deploy", "/canary", "/document-release", "/retro"]
      caf_fallback_agents: []
      description: "Merge, deploy, document, retrospective"
      token_budget: 30000

  # graceful degradation
  fallback:
    no_tmux: "sequential_agents"    # leads run as Agent() calls (lose hierarchy depth)
    no_gstack: "caf_skills"         # leads use CAF-native skills only
    no_both: "orchestrate"          # equivalent to /orchestrate
```

---

### Component 2: `bin/gstack-bridge` (Bash)

```
Commands:
  gstack-bridge status    → JSON to stdout: {installed, path, git_hash, skill_count, healthy, update_needed}
  gstack-bridge skills    → JSON array: [{name, path}]
  gstack-bridge check     → validates setup (symlinks, CLAUDE.md sections, ~/.gstack/)
  gstack-bridge update    → delegates to gstack's own ./setup

Exit codes: 0=healthy, 1=not_installed, 2=outdated, 3=broken
Caches: /tmp/caf_gstack_status.json (TTL 60s)
All diagnostics → stderr, structured data → stdout
```

---

### Component 3: `bin/sprint-event` (Bash)

Tiny utility to emit structured events to the sprint's `events.jsonl`.

```
Usage:   sprint-event <sprint-id> <type> [<json-payload>]
Output:  {"ts": "ISO8601", "sprint": "<id>", "type": "<type>", ...payload}
Write:   Atomic append to /tmp/caf_sprint/<id>/events.jsonl

Event types:
  sprint_started          sprint_completed
  wave_started            wave_completed
  lead_started            lead_completed         lead_failed
  agent_spawned           gstack_skill_invoked
  gate_unlocked           error
```

---

### Component 4: `bin/tmux-sprint` (Bash)

```
Commands:
  tmux-sprint create <sprint-id>
    → tmux new-session sprint-<id>
    → mkdir /tmp/caf_sprint/<id>/{logs,prompts,results}
    → auto-split TUI dashboard pane (28% right)
    → sprint-event <id> sprint_initialized

  tmux-sprint launch-lead <sprint-id> <lead-role> <wave>
    → git worktree add ../<repo>-sprint-<id>-<role>
    → tmux split-window in sprint session
    → cd worktree && CAF_SPRINT_ID=<id> CAF_SPRINT_ROLE=<role> \
        claude --prompt "$(cat prompts/<role>.md)" --allowedTools '*' \
        2>&1 | tee logs/<role>.log
    → update status.json: {<role>: {status: "running", wave: N}}

  tmux-sprint poll-wave <sprint-id> <wave>
    → poll status.json every N seconds
    → return 0 when all wave leads "done", 1 if any "failed"

  tmux-sprint gate <sprint-id> <wave>
    → update gate.json: add wave to unlocked list

  tmux-sprint teardown <sprint-id> [--force]
    → kill session, remove worktrees (confirm if unmerged)
    → archive events.jsonl to ~/.claude/data/sprint_events/
    → clean /tmp/caf_sprint/<id>/

  tmux-sprint status <sprint-id>     → pretty-print status
  tmux-sprint list                    → list all sprint-* sessions
  tmux-sprint dashboard <sprint-id>  → re-launch TUI if closed
```

**Atomic writes**: status.json written to .tmp, then `mv` (rename is atomic on macOS/Linux).

---

### Component 5: `/sprint` Skill — PM Protocol

```yaml
---
name: sprint
description: "Project Manager sprint orchestrator. Decomposes work, assigns leads
  to tmux panes (full root sessions that CAN spawn workers), gates phase waves,
  coordinates results across sessions."
user-invocable: true
---
```

**Full PM Protocol:**

#### Pre-flight

```bash
bin/gstack-bridge check   # → GSTACK_AVAILABLE
which tmux                # → TMUX_AVAILABLE
```

Determine mode: full | tmux-only | agents-only | fallback. Log to events.jsonl.

#### Step 1: Decompose Task

Read sprint_config.yaml. Determine which leads are needed. Write decomposition to `/tmp/caf_sprint/<id>/pm_plan.md`.

**Token efficiency**: PM plan ≤1000 tokens. Just the task breakdown, not a novel.

#### Step 3: Write Lead Prompts

For each lead, write `/tmp/caf_sprint/<id>/prompts/<role>.md` (PLAIN TEXT — leads must read it):

```markdown
# You are the <Role> Lead for sprint <id>

## Your Mission
<2-3 sentences: specific task, expected output>

## Context from Prior Sprints
<plain text summary from PM's memory recall — ≤200 tokens>

## gstack Skills Available
<list from sprint_config.yaml>

## You Are a Root Session
You have full Agent() access. Spawn builders, validators, researchers as needed.

## IPC Protocol (REQUIRED)
When done, write results to: /tmp/caf_sprint/<id>/results/<role>_result.md
Mark done: write {"status":"done"} to /tmp/caf_sprint/<id>/<role>.status
```

#### Step 4: Execute Waves

For each wave (0 → 3):
1. Filter leads for this wave
2. `bin/tmux-sprint launch-lead` for each lead (parallel within wave)
3. `bin/tmux-sprint poll-wave` (blocks until all done or timeout)
4. Read results from `results/`
5. Synthesize wave output (3-5 sentence summary)
6. Append to `report.md`
7. `bin/tmux-sprint gate` (unlock next wave)

**On failure**: retry once with additional context, then escalate to user.

#### Step 5: Merge and Store

After all waves:
1. **Merge** worktree branches (or instruct user)
2. **Generate** unified sprint report from all results
3. **Archive** events.jsonl → `~/.claude/data/sprint_events/<id>.jsonl`
5. **Teardown** `bin/tmux-sprint teardown`

#### Fallback Modes

| Mode | Condition | Behavior |
|------|-----------|----------|
| Full | tmux + gstack | PM → Lead panes → Workers. Full hierarchy. |
| tmux-only | tmux, no gstack | Lead panes use CAF skills (researcher, builder, validator) |
| agents-only | no tmux, gstack | Leads run as sequential Agent() calls. Lose hierarchy depth. |
| minimal | no tmux, no gstack | Equivalent to `/orchestrate` |

---

### Component 6: Sprint Hooks

#### `hooks_SessionStart/check_gstack.py`
- Run `bin/gstack-bridge status` with 2s timeout
- Cache at `/tmp/caf_gstack_status.json` (TTL 60s)
- Soft warning if not installed, suggest update if >7 days old
- Target: <500ms. Never blocking.

#### `hooks_SubagentStart/inject_sprint_context.py`
- **Fast path**: if `CAF_SPRINT_ID` not set → return `{}` immediately (<5ms)
- **Sprint path**: inject into `additionalContext` (max 2000 chars total):
  1. Lead's mission from prompt file (already plain text)
  2. Last 5 events from events.jsonl (situational awareness)
  3. Completed lead summaries (first 200 chars each, max 3 leads)

---

### Component 7: TUI Dashboard

**Framework**: Textual ≥0.90.0 (`uv add textual`)
**Launch**: `uv run python dashboard/sprint_tui.py <sprint-id>`
**Auto-launched** by `tmux-sprint create` in rightmost pane (28% width)

**Layout** (3 columns + bottom bar):

| Panel | Widget | Data Source | Refresh |
|-------|--------|-------------|---------|
| Left (30%) | LeadPanel (DataTable) | status.json | 2s |
| Center (42%) | LogViewer (RichLog) | logs/*.log | 0.5s |
| Right (28%) | ReportPanel (Markdown) | report.md + results/*.md | 5s |
| Bottom (fixed) | WaveProgress (ProgressBar × N) | gate.json + status.json | 2s |

**LeadPanel columns**: Role | Wave | Status (✓/⟳/✗/◌) | Agents | Elapsed | Tokens
**LogViewer**: Tails all log files, color-coded per lead role, filter bar
**WaveProgress**: `[Plan ████████ 100%] [Build ████░░ 67%] [Validate ░░░ 0%]`

**Key bindings**: `q` quit, `r` refresh, `f` filter log, `tab` cycle focus

---

### Component 8: Research Agents

#### `global-agents/researcher.md` (update existing)

Add MCP tool routing table and two-step synthesis protocol. Core changes:
- Primary tools: `mcp__papers__*`, `mcp__sourcegraph__*`, `mcp__papersflow__*`
- Rule: Never `WebFetch` an academic paper URL when `mcp__papers` can return structured metadata (10x savings)
- Rule: Never `WebSearch` for code patterns when `mcp__sourcegraph` searches actual implementations
- Two-step: for synthesis tasks, reason freely first, format second

#### `global-agents/code-researcher.md` (new)

Sonnet agent focused on `mcp__sourcegraph__*`. Knows Sourcegraph query syntax (`lang:`, `repo:`, `file:`, `type:symbol`). Returns structured code pattern comparisons.

#### `global-agents/academic-researcher.md` (new)

Sonnet agent focused on `mcp__papers__*` and `mcp__papersflow__*`. Handles paper search, citation verification, literature reviews. Two-step for synthesis.

---

### Component 9: TOON Utils

`lib/toon_utils.py`:
- `is_toon_eligible(data)` — check if data is uniform flat array
- `encode_results(data)` — encode as TOON (header + CSV), fallback to compact JSON
- `decode_results(toon_str)` — decode TOON back to list of dicts

Used by research agents when returning uniform search results to orchestrator. Not used for IPC within sprints.

---

### Component 10: Research Skills

Four skills in `global-skills/`:
- `research-academic/SKILL.md` — papers + papersflow, Sonnet + Haiku format, target <15K tokens
- `research-code/SKILL.md` — sourcegraph, Sonnet, target <10K tokens
- `research-news/SKILL.md` — WebSearch + WebFetch, Sonnet, target <20K tokens
- `research-docs/SKILL.md` — WebFetch direct, Haiku, target <5K tokens

Each skill defines: trigger keywords, tool priority, output schema, token budget.

Dispatch table added to orchestrator's instructions.

---

## Structured Logging & Auditability

### Event Schema

Every sprint produces `events.jsonl`. Each line:
```json
{"ts": "2026-04-08T03:15:00Z", "sprint": "<id>", "type": "<type>", ...payload}
```

### Sprint Completion Event (full audit summary)

```json
{
  "type": "sprint_completed",
  "sprint": "sprint-1712541300",
  "task": "build REST API with auth",
  "duration_seconds": 847,
  "mode": "full",
  "waves_completed": 4,
  "leads": {
    "planning-lead": {"status": "done", "tokens_input": 12400, "tokens_output": 8200, "duration_s": 180, "agents_spawned": 1},
    "engineering-lead": {"status": "done", "tokens_input": 67200, "tokens_output": 31000, "duration_s": 420, "agents_spawned": 3},
    "qa-lead": {"status": "done", "tokens_input": 31000, "tokens_output": 14500, "duration_s": 300, "agents_spawned": 2}
  },
  "total_tokens": {"input": 110600, "output": 53700},
}
```

### Queryable Audit Trail

```bash
# What decisions were made?
jq 'select(.type=="kg_triple_written")' events.jsonl

# Token cost per lead
jq 'select(.type=="lead_completed") | {lead: .lead_role, tokens: .tokens_input}' events.jsonl

# Wave timeline
jq 'select(.type | startswith("wave_"))' events.jsonl
```

### Archive Lifecycle

1. During sprint: events.jsonl grows in `/tmp/caf_sprint/<id>/`
2. On teardown: archived to `~/.claude/data/sprint_events/<id>.jsonl`
3. Archived JSONL available for historical queries

---

## Implementation Phases & Tasks

### Phase 1: Foundation (all parallel, no dependencies)

| # | Task | Assigned To | Files |
|---|------|-------------|-------|
| 1 | Create sprint_config.yaml | foundation-builder | `data/sprint_config.yaml` |
| 2 | Create gstack-bridge | foundation-builder | `bin/gstack-bridge` |
| 3 | Create sprint-event | foundation-builder | `bin/sprint-event` |

### Phase 2: tmux Infrastructure (depends on Phase 1)

| # | Task | Assigned To | Files |
|---|------|-------------|-------|
| 4 | Create tmux-sprint | foundation-builder | `bin/tmux-sprint` |

### Phase 3: Sprint Skill + Agent + Hooks (depends on Phase 1)

| # | Task | Assigned To | Parallel? | Files |
|---|------|-------------|-----------|-------|
| 5 | Create /sprint skill | skill-builder | no (depends on 1-4) | `global-skills/sprint/SKILL.md` |
| 6 | Create sprint-lead agent | skill-builder | yes | `global-agents/sprint-lead.md` |
| 7 | Create SessionStart hook | hooks-builder | yes | `global-hooks/hooks_SessionStart/check_gstack.py` |
| 8 | Create SubagentStart hook | hooks-builder | yes | `global-hooks/hooks_SubagentStart/inject_sprint_context.py` |

### Phase 4: TUI Dashboard (depends on Phase 1 config only)

| # | Task | Assigned To | Parallel? | Files |
|---|------|-------------|-----------|-------|
| 10 | Build TUI app + widgets | tui-builder | yes (parallel to Phase 3) | `dashboard/sprint_tui.py`, `dashboard/widgets/*.py`, `dashboard/sprint_tui.css` |
| 11 | Integrate TUI with tmux-sprint | tui-builder | no (depends on 4, 10) | update `bin/tmux-sprint` |

### Phase 5: Research Intelligence (fully parallel to Phases 2-4)

| # | Task | Assigned To | Parallel? | Files |
|---|------|-------------|-----------|-------|
| 12 | Create TOON utils | research-builder | yes | `lib/toon_utils.py` |
| 13 | Create research agents | research-builder | yes | `global-agents/code-researcher.md`, `global-agents/academic-researcher.md` |
| 14 | Create research skills | research-builder | yes | `global-skills/research-*/SKILL.md` |
| 15 | Update existing researcher.md | research-builder | yes | `global-agents/researcher.md` |

### Phase 6: CAF Integration (depends on all above)

| # | Task | Assigned To | Parallel? | Files |
|---|------|-------------|-----------|-------|
| 16 | Update caddy_config + model_tiers | integration-builder | yes | `data/caddy_config.yaml`, `data/model_tiers.yaml` |
| 18 | Update settings.json.template | integration-builder | no (depends on 7-9) | `templates/settings.json.template` |
| 19 | Update worktree skill + orchestrator | integration-builder | yes | existing SKILL.md files |
| 20 | Update generate_docs.py + install | integration-builder | no (last) | `scripts/generate_docs.py` |

### Phase 7: Validation

| # | Task | Assigned To | Files |
|---|------|-------------|-------|
| 21 | Validate everything | validator | all |

---

## Team Members

| Name | Role | Agent Type |
|------|------|-----------|
| foundation-builder | Shell scripts, config YAML | builder |
| skill-builder | /sprint SKILL.md, sprint-lead agent | builder |
| hooks-builder | All 3 hook scripts | builder |
| tui-builder | Textual dashboard + tmux integration | builder |
| research-builder | TOON, research agents, research skills | builder |
| integration-builder | All existing file modifications | builder |
| validator | Final validation | validator |

---

## Step by Step Tasks (Detailed)

### 1. Create sprint_config.yaml
- **Task ID**: create-sprint-config
- **Depends On**: none
- **Assigned To**: foundation-builder
- **Agent Type**: builder
- **Parallel**: true
- Write `data/sprint_config.yaml` per Component 1 spec above
- Validate: `python3 -c "import yaml; yaml.safe_load(open('data/sprint_config.yaml'))"`

### 2. Create gstack-bridge
- **Task ID**: create-gstack-bridge
- **Depends On**: none
- **Assigned To**: foundation-builder
- **Agent Type**: builder
- **Parallel**: true
- Write `bin/gstack-bridge` per Component 2 spec, chmod +x
- Cache at /tmp/caf_gstack_status.json, TTL 60s
- Validate: `shellcheck bin/gstack-bridge`

### 3. Create sprint-event
- **Task ID**: create-sprint-event
- **Depends On**: none
- **Assigned To**: foundation-builder
- **Agent Type**: builder
- **Parallel**: true
- Write `bin/sprint-event` per Component 3 spec, chmod +x
- Atomic append, creates events.jsonl and IPC dir if missing
- Validate: `shellcheck bin/sprint-event`

### 4. Create tmux-sprint
- **Task ID**: create-tmux-sprint
- **Depends On**: create-sprint-config, create-sprint-event
- **Assigned To**: foundation-builder
- **Agent Type**: builder
- **Parallel**: false
- Write `bin/tmux-sprint` per Component 4 spec, chmod +x
- All subcommands: create, launch-lead, poll-wave, gate, teardown, status, list, dashboard
- Auto-launches TUI pane on create
- Validate: `shellcheck bin/tmux-sprint`

### 5. Create /sprint skill
- **Task ID**: create-sprint-skill
- **Depends On**: create-sprint-config, create-gstack-bridge, create-tmux-sprint
- **Assigned To**: skill-builder
- **Agent Type**: builder
- **Parallel**: false
- Write `global-skills/sprint/SKILL.md` per Component 5 spec
- Full PM protocol: pre-flight → memory recall → decompose → write prompts → execute waves → merge → store
- Plain text prompts ONLY
- Validate: SKILL.md frontmatter YAML parses

### 6. Create sprint-lead agent
- **Task ID**: create-sprint-lead
- **Depends On**: none
- **Assigned To**: skill-builder
- **Agent Type**: builder
- **Parallel**: true
- Write `global-agents/sprint-lead.md` — model: sonnet, has Agent tool
- Note: only used in fallback mode (no tmux); tmux panes use direct `claude` invocation
- Validate: frontmatter parses, model=sonnet

### 7. Create SessionStart gstack hook
- **Task ID**: create-session-hook
- **Depends On**: create-gstack-bridge
- **Assigned To**: hooks-builder
- **Agent Type**: builder
- **Parallel**: true
- Write `global-hooks/hooks_SessionStart/check_gstack.py` per Component 6 spec
- 60s cache, <500ms, soft warning only
- Validate: `uv run python -m py_compile` + `echo '{}' | uv run python <file>` doesn't crash

### 8. Create SubagentStart sprint hook
- **Task ID**: create-subagent-start-hook
- **Depends On**: create-sprint-config
- **Assigned To**: hooks-builder
- **Agent Type**: builder
- **Parallel**: true
- Write `global-hooks/hooks_SubagentStart/inject_sprint_context.py` per Component 6 spec
- Fast path: <5ms when CAF_SPRINT_ID not set
- Sprint path: inject ≤2000 chars (prompt + events + results)
- Validate: `uv run python -m py_compile` + returns `{}` when no sprint env

### 10. Build TUI dashboard
- **Task ID**: build-tui
- **Depends On**: create-sprint-config
- **Assigned To**: tui-builder
- **Agent Type**: builder
- **Parallel**: true (parallel to Phase 3)
- `uv add textual`
- Write `dashboard/sprint_tui.py` — 3-column + bottom bar Textual app
- Write `dashboard/widgets/lead_panel.py` — DataTable: Role, Wave, Status, Agents, Elapsed
- Write `dashboard/widgets/log_viewer.py` — RichLog tailing logs/*.log, color per role, filter
- Write `dashboard/widgets/report_panel.py` — Markdown renderer of report.md
- Write `dashboard/widgets/wave_progress.py` — ProgressBar per wave
- Write `dashboard/sprint_tui.css` — dark theme, role colors
- Validate: `uv run python -m py_compile dashboard/sprint_tui.py dashboard/widgets/*.py`

### 11. Integrate TUI with tmux-sprint
- **Task ID**: integrate-tui
- **Depends On**: build-tui, create-tmux-sprint
- **Assigned To**: tui-builder
- **Agent Type**: builder
- **Parallel**: false
- Update `bin/tmux-sprint create` to auto-split TUI pane (28%)
- Update `bin/tmux-sprint launch-lead` to tee output to logs/
- Add `tmux-sprint dashboard` subcommand
- Validate: `shellcheck bin/tmux-sprint`

### 12. Create TOON utils
- **Task ID**: create-toon-utils
- **Depends On**: none
- **Assigned To**: research-builder
- **Agent Type**: builder
- **Parallel**: true
- Write `lib/toon_utils.py` per Component 9 spec
- `is_toon_eligible()`, `encode_results()`, `decode_results()`, `_parse_csv_line()`
- Falls back to compact JSON for non-eligible data
- Validate: `uv run python -m py_compile lib/toon_utils.py`

### 13. Create research agents
- **Task ID**: create-research-agents
- **Depends On**: none
- **Assigned To**: research-builder
- **Agent Type**: builder
- **Parallel**: true
- Write `global-agents/code-researcher.md` — sourcegraph-focused, Sonnet
- Write `global-agents/academic-researcher.md` — paper-search-focused, Sonnet, two-step
- Include full tool routing tables and output format specs
- Validate: frontmatter parses

### 14. Create research skills
- **Task ID**: create-research-skills
- **Depends On**: none
- **Assigned To**: research-builder
- **Agent Type**: builder
- **Parallel**: true
- Write `global-skills/research-academic/SKILL.md` — trigger, tools, schema, token budget
- Write `global-skills/research-code/SKILL.md`
- Write `global-skills/research-news/SKILL.md`
- Write `global-skills/research-docs/SKILL.md`
- Validate: frontmatter parses

### 15. Update existing researcher agent
- **Task ID**: update-researcher
- **Depends On**: none
- **Assigned To**: research-builder
- **Agent Type**: builder
- **Parallel**: true
- Add MCP tool routing table to `global-agents/researcher.md`
- Add two-step synthesis protocol
- Add TOON encoding instructions for returning results
- Validate: frontmatter parses

### 16. Update caddy + model tiers
- **Task ID**: update-caddy
- **Depends On**: create-sprint-config
- **Assigned To**: integration-builder
- **Agent Type**: builder
- **Parallel**: true
- `data/caddy_config.yaml`: add sprint strategy, research skills, sprint-lead defaults
- `data/model_tiers.yaml`: add sprint-lead under sonnet
- Validate: YAML parses

### 18. Update settings template
- **Task ID**: update-settings
- **Depends On**: create-session-hook, create-subagent-start-hook, create-subagent-stop-hook
- **Assigned To**: integration-builder
- **Agent Type**: builder
- **Parallel**: false
- Add 3 new hooks to their event arrays
- Add 3 MCP servers (papers, sourcegraph, papersflow)
- Add MCP permissions
- Validate: `python3 -m json.tool templates/settings.json.template > /dev/null`

### 19. Update worktree + orchestrator
- **Task ID**: update-integrations
- **Depends On**: create-sprint-skill
- **Assigned To**: integration-builder
- **Agent Type**: builder
- **Parallel**: true
- `global-skills/worktree/SKILL.md`: add `/worktree sprint <id>` subcommand
- `global-skills/orchestrate/SKILL.md`: add 5-line sprint strategy note + research dispatch table
- Validate: frontmatter parses

### 20. Update generate_docs + install
- **Task ID**: update-docs-install
- **Depends On**: all above
- **Assigned To**: integration-builder
- **Agent Type**: builder
- **Parallel**: false
- Register sprint skill, sprint-lead agent, research agents, research skills in `scripts/generate_docs.py`
- Run `bash install.sh`
- Validate: install exits 0

### 21. Validate all
- **Task ID**: validate-all
- **Depends On**: all above
- **Assigned To**: validator
- **Agent Type**: validator
- **Parallel**: false
- Full validation per commands below

---

## Acceptance Criteria

### Sprint System
- [ ] `bin/gstack-bridge status` exits 0/1/2/3 in <2s
- [ ] `bin/sprint-event test sprint_started '{}'` writes valid JSONL
- [ ] `bin/tmux-sprint create s1` creates session + IPC dir + TUI pane
- [ ] `bin/tmux-sprint launch-lead s1 eng-lead 1` creates pane + worktree + tees to log
- [ ] Lead pane has full Agent() access (root session, not sub-agent)
- [ ] Lead pane inherits all CAF hooks (damage-control, memory, facts)
- [ ] Wave gating enforced (Wave 1 waits for Wave 0)
- [ ] `/sprint "build X"` produces full PM → Lead → Worker hierarchy

### Memory
- [ ] SubagentStart hook injects ≤2000 chars sprint context
- [ ] events.jsonl archived to `~/.claude/data/sprint_events/` on teardown

### TUI Dashboard
- [ ] Dashboard auto-launches in rightmost pane (28% width)
- [ ] LeadPanel shows live status with 2s refresh
- [ ] LogViewer streams all lead logs with color coding
- [ ] ReportPanel renders report.md as leads complete
- [ ] WaveProgress shows % per wave

### Research Intelligence
- [ ] paper-search-mcp returns structured results for academic queries
- [ ] sourcegraph-mcp returns code patterns with language/repo filters
- [ ] TOON encoding produces ~40% fewer tokens than JSON for 10+ uniform results
- [ ] Two-step synthesis: researcher reasons freely, then formats
- [ ] Research skills route correctly (academic/code/news/docs)

### Degradation & Resilience
- [ ] Without tmux: leads run as sequential Agent() calls
- [ ] Without gstack: leads use CAF-native skills
- [ ] gstack `git pull && ./setup` doesn't break integration
- [ ] `bash install.sh` succeeds with all new files

---

## Validation Commands

```bash
# Phase 1: Foundation
python3 -c "import yaml; yaml.safe_load(open('data/sprint_config.yaml'))"
shellcheck bin/gstack-bridge bin/sprint-event bin/tmux-sprint

# Phase 3: Hooks
uv run python -m py_compile global-hooks/hooks_SessionStart/check_gstack.py
uv run python -m py_compile global-hooks/hooks_SubagentStart/inject_sprint_context.py
echo '{}' | CAF_SPRINT_ID= uv run python global-hooks/hooks_SubagentStart/inject_sprint_context.py
# ^ must output {} or empty (no sprint active)

# Phase 4: TUI
uv run python -c "import textual; print(textual.__version__)"
uv run python -m py_compile dashboard/sprint_tui.py
for f in dashboard/widgets/*.py; do uv run python -m py_compile "$f"; done

# Phase 5: Research
uv run python -m py_compile lib/toon_utils.py
uv run python -c "from lib.toon_utils import encode_results, decode_results; print('OK')"

# Phase 6: Integration
python3 -c "import yaml; yaml.safe_load(open('data/caddy_config.yaml'))"
python3 -c "import yaml; yaml.safe_load(open('data/model_tiers.yaml'))"
python3 -m json.tool templates/settings.json.template > /dev/null
grep -q 'sprint' data/caddy_config.yaml
grep -q 'sprint-lead' data/model_tiers.yaml
grep -q 'check_gstack' templates/settings.json.template
grep -q 'paper-search-mcp\|papers' templates/settings.json.template
bash install.sh

# Lifecycle smoke test
bin/sprint-event smoke sprint_initialized '{}'
python3 -c "import json; print([json.loads(l)['type'] for l in open('/tmp/caf_sprint/smoke/events.jsonl')])"
rm -rf /tmp/caf_sprint/smoke
```

---

## Notes

### The tmux Insight
`claude --prompt "..."` in a tmux pane is NOT a sub-agent. It's a fresh root Claude Code process with full Agent() access, full hooks, full skills. The PM doesn't "spawn" leads — it *launches independent processes* that coordinate via filesystem IPC.

### Token Efficiency Summary
| Mechanism | Savings | Where |
|-----------|---------|-------|
| MCP servers vs web scraping | ~86% per research lookup | Phase 5 research agents |
| TOON vs JSON (tabular data) | ~40% on search results | Research agent → orchestrator |
| KG inject budget cap | 375 tokens max | SubagentStart hook |
| Sprint context cap | 2000 chars max | SubagentStart hook |
| Lead prompt brevity | ~500 tokens per prompt | PM writes concise prompts |

### Scalability
- **4-6 concurrent leads** sweet spot on Max plan (rate limits)
- **Multiple concurrent sprints** supported (different IDs, separate sessions)
- **Worktree naming** includes sprint ID + role (no collisions)
- **events.jsonl** typically <1MB per sprint (no rotation needed)

### Project Adaptability (Critical Design Constraint)

CAF is a **global framework** installed once, used across any project. The sprint system MUST NOT hardcode project-specific paths, test commands, language tooling, or conventions.

**Layer 1: sprint_config.yaml lives in CAF global (default roles/waves)**
All users get the same default lead roles, wave definitions, and gstack skill mappings. These are universal — planning/build/validate/ship is the same workflow everywhere.

**Layer 2: Project overrides via `.claude/sprint.yaml` (optional)**
Any project can drop a `.claude/sprint.yaml` in its root to override defaults:
```yaml
# .claude/sprint.yaml — project-level sprint overrides
sprint:
  leads:
    engineering-lead:
      # This project uses Go, not Python
      token_budget: 80000
      extra_context: "Use `go test ./...` not `pytest`. Build with `go build`."
    qa-lead:
      # This project has Playwright tests
      extra_context: "Run `npx playwright test` for E2E. CI is GitHub Actions."
  waves:
    # This project doesn't need security review
    2: { leads: ["review-lead", "qa-lead"] }  # no security-lead
```
PM reads project override, merges with global defaults. Missing keys fall back to global.

**Layer 3: `/project-adapter` integration**
CAF already has a `project-adapter` skill that generates `/tmp/caf_project_context.md` with project-specific test commands, conventions, and paths. Sprint leads should read this file if it exists. Add to lead prompt template:
```markdown
## Project Context
If /tmp/caf_project_context.md exists, read it first. It contains this project's:
- Test commands (don't guess — use what's specified)
- Build commands
- Naming conventions
- Directory structure
```

**Layer 4: gstack is optional, not assumed**
Every lead has `caf_fallback_agents` defined. If gstack isn't installed:
- planning-lead → uses researcher agents instead of /plan-ceo-review
- qa-lead → uses validator agents instead of /qa
- security-lead → uses security-scanner skill instead of /cso
- review-lead → uses code-review skill instead of /review

No user is required to install gstack. Sprint degrades gracefully at every level.

**Layer 5: tmux is optional, not assumed**
Without tmux, leads run as sequential Agent() calls. Users on Windows (no tmux) or CI (no terminal) still get the sprint decomposition and wave gating — just without the hierarchy depth and parallel panes.

**What this means for installation**:
```bash
# Minimum viable install (any Claude Code user):
cd ~/.claude/skills && git clone <caf-repo>
# Sprint works with: agents-only mode, no gstack

# Full install (power user):
# + Install gstack
git clone https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && ./setup
# + Install tmux: brew install tmux
# Sprint works with: full mode (PM → Lead → Worker hierarchy)
```

**No step is required. Every step adds capability.**
