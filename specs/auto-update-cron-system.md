# Plan: CAF Auto-Update Cron System — Nightly Self-Evolving Harness

**Status**: Proposed (2026-05-17)
**Task type**: feature
**Complexity**: complex
**Owner**: Tom (CAF maintainer)

---

## Clarifications (2026-05-17)

| Question | Answer |
|---|---|
| Notification channel | Not important right now — HTML report is enough |
| Infrastructure | Local Mac via launchd (no VM, no Docker) |
| Integration | Manual merge only — v1 outputs reports + recommendations, Tom decides |
| Token budget | Claude Code subscription — no caps, no cost enforcement |
| Discovery scope | Claude Code only. Critically: also test existing CAF components to see what can be upgraded, replaced, or removed |

---

## Task Description

Build an **autonomous nightly system** (Mac launchd, no VM/Docker) that:

1. **Inventories** every existing CAF component (skills, agents, hooks, commands, MCPs) — what each one does, its capabilities, its weaknesses. This is the reference layer.
2. **Discovers** new Claude Code repos published since the last run (GitHub Search API + awesome-claude-code RSS feeds).
3. **Evaluates** each candidate against a pre-built, versioned test suite covering all CAF workflows. Critically: when a candidate overlaps with an existing component, runs a head-to-head comparison.
4. **Produces** an HTML report with: what was found, what was tested, metric deltas vs baseline, and a structured recommendation section (Add new / Upgrade existing / Keep existing / Deprecate existing).
5. **Learns over time** — the component inventory and baseline evolve as caf-team itself ships.

**No auto-PR, no auto-merge in v1.** After Tom reviews a few reports and trusts the recommendations, integration automation can be added later.

## Objective

When complete, Tom opens a nightly HTML report and sees: "3 candidates passed eval. One is a drop-in replacement for the `research-docs` skill (-22% tokens, same quality). One is a new MCP server with no existing equivalent. One failed on hooks test. Recommended actions below." Tom can act on any recommendation in under 5 minutes.

The framework becomes **self-aware about its own components** — it knows what it has, knows what's out there, and reports the delta every night.

## Problem Statement

Two compounding problems:

**Ecosystem drift**: The Claude Code ecosystem ships dozens of repos per week. Manual triage is high-latency and biased toward repos Tom happens to notice. Genuinely useful tooling sits unintegrated for weeks.

**Internal stagnation**: Existing CAF components (skills, agents, hooks) were built at a point in time. There is no systematic process to notice when a better alternative exists or when an existing component has become redundant. No component map. No upgrade path.

Together: the framework neither discovers improvements nor knows what it already has clearly enough to recognize them.

## Solution Approach

**Six-stage nightly pipeline**, running natively on Mac via launchd at 02:00 daily:

```
[1] Inventory   →  [2] Discover  →  [3] Triage  →  [4] Eval  →  [5] Compare  →  [6] Report
   (catalog all     (GitHub API      (filter junk,   (run test    (candidate vs    (HTML with
    CAF components   + RSS)          smoke test)     suite)       existing?)       recommendations)
```

**Key design decisions:**

- **Component inventory first**: Before evaluating anything external, the system knows exactly what CAF has and what each component does. This is the ontology everything else is compared against.
- **Head-to-head comparison**: When a candidate overlaps with an existing component, both are run on the same test cases. Report shows the diff clearly — keep / upgrade / replace.
- **Eval stack**: `promptfoo` (headless, CI-friendly) + `deepeval` (`StepEfficiencyMetric`). No cost caps — subscription plan.
- **LLM-as-judge**: Analytic rubric (4 dimensions, 3-point scale, CoT, calibrated against 30 gold examples).
- **Discovery**: GitHub Search API + awesome-claude-code RSS — filtering to Claude-Code-flavored repos only.
- **Shadow mode forever in v1**: Reports are advice. Tom acts. No git operations from the pipeline.
- **Mac launchd**: No VM, no Docker, no Terraform. Runs natively, minimal maintenance.

## Relevant Files (Existing)

Understanding these informs the component inventory scanner and eval fixture design:

- `global-skills/` — 30 skills. Scanner reads each `SKILL.md` for purpose + capabilities.
- `global-agents/` — 22 agents. Scanner reads each `.md` for role + model tier.
- `global-hooks/` — 47 hooks across 16 events. Scanner reads each `.py` for hook type + event.
- `global-commands/` — 17 commands. Scanner reads each for invocation pattern + purpose.
- `templates/settings.json.template` — MCP server registrations, hook event bindings, permission rules.
- `data/model_tiers.yaml` — model assignments per agent. Part of inventory.
- `install.sh` — bootstrapper. The eval suite invokes this when testing candidates.
- `caf-hooks/src/` — Rust hook implementations. Inventoried but excluded from auto-update (too high blast radius).
- `CLAUDE.md` — project rules. Eval suite should test compliance with rules (e.g., "uv run", not pip install).
- `.claude/FACTS.md`, `.claude/MEMORY.md` — memory system; inventoried as a sub-system.
- `specs/CURRENT-STATE-PLAN.md` — reference for project state at planning time.

### New Files (Created by This Plan)

```
tools/evolve/
├── README.md
├── pyproject.toml                       # uv-managed: promptfoo, deepeval, pygithub, feedparser, jinja2
│
├── inventory/
│   ├── scanner.py                       # walks caf-team → builds components.json
│   ├── components.json                  # auto-generated: full CAF component catalog
│   ├── COMPONENTS.md                    # human-readable version of the catalog
│   └── schema.json                      # JSON schema for component entries
│
├── runner/
│   ├── __init__.py
│   ├── discover.py                      # GitHub API + RSS → candidates_queue.jsonl
│   ├── triage.py                        # filter by license, language, recency, category
│   ├── evaluate.py                      # per-candidate test suite runner + scorer
│   ├── compare.py                       # head-to-head: candidate vs existing component
│   ├── report.py                        # HTML report generator (Jinja2 + inline Chart.js)
│   └── main.py                          # launchd entrypoint: orchestrates all stages
│
├── evals/
│   ├── promptfooconfig.yaml             # base config: model pin, providers, global assertions
│   ├── suites/
│   │   ├── smoke.yaml                   # 5 fast tests (discovery gate)
│   │   ├── orchestration.yaml           # /orchestrate end-to-end
│   │   ├── research.yaml                # researcher / code-researcher / research-docs
│   │   ├── debugging.yaml               # /debug cycle
│   │   ├── memory.yaml                  # auto-memory write/read, FACTS.md, MEMORY.md
│   │   ├── hooks.yaml                   # hook-fire correctness (deterministic assertions)
│   │   ├── skill_invocation.yaml        # skill routing, /skill-name triggering
│   │   └── multi_agent.yaml             # parallel agent coordination
│   ├── rubrics/
│   │   ├── analytic.md                  # 4-dimension × 3-point CoT rubric with anchored examples
│   │   └── gold_examples.jsonl          # 30 human-annotated calibration examples
│   └── fixtures/                        # input prompts, file tree fixtures per test case
│
├── baseline/
│   ├── baseline.json                    # current caf-team metrics on full suite
│   ├── snapshot_<git-hash>.json         # per-commit snapshots for trend analysis
│   └── REGENERATE.md                    # how to refresh baseline after caf-team changes
│
├── reports/
│   └── YYYY-MM-DD.html                  # one HTML report per nightly run (gitignored)
│
├── state/
│   ├── seen_repos.json                  # de-dup ledger: never re-test known repos
│   ├── last_run.json                    # last run timestamp + caf-team commit at run time
│   └── candidates_queue.jsonl           # pending eval queue (carries over across days)
│
└── infra/
    ├── com.caf.evolve.plist             # launchd plist (daily 02:00, stdout/err to log)
    ├── install-launchd.sh               # copies plist → ~/Library/LaunchAgents/, loads it
    └── secrets.env.example              # ANTHROPIC_API_KEY, GITHUB_TOKEN
```

## Implementation Phases

### Phase 1: Component Inventory System

Before evaluating anything external, the pipeline must know what CAF already has. This is the comparison baseline for the "upgrade existing" and "remove redundant" report sections.

**What the inventory captures per component:**

```json
{
  "name": "research-docs",
  "type": "skill",
  "path": "global-skills/research-docs/",
  "invocation": "/research-docs",
  "purpose": "Fetch and save documentation from URLs as formatted markdown",
  "capabilities": ["WebFetch", "Write", "firecrawl scrape"],
  "model_tier": "haiku",
  "known_weaknesses": [],
  "test_suite_coverage": ["research.yaml#test-02", "research.yaml#test-05"],
  "baseline_tokens_avg": 1840,
  "baseline_quality_avg": 2.7,
  "last_scanned": "2026-05-17"
}
```

**Steps:**

1. **`inventory/scanner.py`**: Walks `global-skills/`, `global-agents/`, `global-hooks/`, `global-commands/`. For each component: parse SKILL.md/agent.md/hook header comments to extract purpose + capabilities. Emit `components.json` + `COMPONENTS.md`.
2. **Run scanner on current caf-team**: Commit initial `components.json` and `COMPONENTS.md`. This is the ground truth.
3. **Link components to test cases**: Each test case in the eval suites should reference the component(s) it covers. After baseline is captured, back-fill `baseline_tokens_avg` and `baseline_quality_avg` into each component entry.
4. **Scanner runs at start of every nightly run** — updates the inventory if caf-team changed since last run (new commit → re-scan + re-baseline).

**Acceptance**: `components.json` exists, all 30+ skills + 22 agents + 47 hooks + 17 commands cataloged, human-readable `COMPONENTS.md` is accurate.

### Phase 2: Eval Suite + Baseline (THE CRITICAL PHASE)

A trustworthy baseline is the foundation. Every metric comparison is meaningless without it.

**Steps:**

1. **Analytic rubric** (`evals/rubrics/analytic.md`): 4 dimensions × 3-point scale with anchored examples per score. Dimensions: (a) task completion, (b) tool-call minimality, (c) context window economy, (d) sub-agent coordination quality. CoT required in judge prompt ("explain your evaluation step by step before scoring"). 
2. **Gold examples** (`evals/rubrics/gold_examples.jsonl`): 30 annotated examples from real caf-team runs, scored manually by Tom. These calibrate the LLM judge — without them, judge drift is invisible.
3. **8 test suites** (`evals/suites/*.yaml`): Each test case has: input prompt, fixture path (file tree), deterministic assertions (hook fired? skill loaded? file at expected path?), and rubric dimensions to LLM-score. Target: ~40 total test cases across all suites.
4. **Model pin**: Use `claude-opus-4-5-20251001` in `promptfooconfig.yaml` — no floating aliases. `temperature=0` for deterministic tests; `N=3` + majority-vote for stochastic.
5. **Run baseline**: Execute full suite against current caf-team HEAD 3×. Record tokens, latency, quality scores per test into `baseline/baseline.json`. Validate variance: <5% token variance, <10% latency variance, ≥0.9 Pearson correlation on quality scores across runs.
6. **Back-fill inventory**: Use baseline results to populate `baseline_tokens_avg` and `baseline_quality_avg` in `components.json`.

**Acceptance**: `baseline.json` committed, variance documented in `REGENERATE.md`, gold examples reviewed by Tom. Re-run confirms stable.

### Phase 3: Discovery + Triage

**Steps:**

1. **`discover.py`**:
   - GitHub Search API: 4 queries per run (`claude code`, `claude hooks`, `mcp server claude`, `claude agent framework`). Filter: `created:>last_run_date`, `stars:>5`, language scoped.
   - RSS feeds: `awesome-claude-code/commits/main.atom`, `awesome-claude-code-toolkit/commits/main.atom` — diff new entries.
   - De-dup against `state/seen_repos.json`. New candidates → `state/candidates_queue.jsonl`.
   - Also watch `modelcontextprotocol/servers` repository for new server entries.

2. **`triage.py`**:
   - Filter: license (MIT/Apache/BSD only), last commit <90 days, README exists, language (Python/TypeScript/Rust/Bash).
   - Auto-categorize: skill / agent / hook / mcp / harness / eval-framework. Drop "other" (log reason).
   - **Overlap detection**: For each candidate, do a quick semantic match against `components.json` (name + purpose embedding or keyword match). Tag with `overlaps_existing: ["research-docs", "docs-scraper"]` if applicable. These get priority in eval — they're the "upgrade existing" candidates.
   - Smoke gate (fast): install candidate's README instructions in a clean caf-team checkout; run 5-test smoke suite. Reject if smoke fails.

3. **`main.py` discovery entrypoint**: Appends new candidates to queue. Queue carries across nights — if queue grows (viral week), it drains FIFO over successive nights.

**Acceptance**: `discover.py --dry-run` against real GitHub emits >0 candidates with overlap tags.

### Phase 4: Evaluation + Head-to-Head Comparison

This phase is what separates "interesting repo" from "actually better". Two tracks run for every candidate that passes triage:

**Track A — New Addition** (no existing overlap):
- Run full 8-suite test. Score vs baseline. Accept if ≥95% quality and adds new capability not currently in CAF.

**Track B — Upgrade Candidate** (overlaps existing component):
- Run full 8-suite test for candidate.
- Re-run the same test cases for the existing component it overlaps.
- Direct metric comparison: token delta, latency delta, quality delta per dimension.
- Output: `upgrade_recommendation.json` with: which existing component, what metric change, which test cases show improvement vs regression.

**`evaluate.py`**:
- Candidate integration by type: skill → symlink into `~/.claude/skills/`; hook → add to settings.json and fire one test trigger; MCP → register in settings.json; agent → add .md to global-agents/ and re-run install.sh.
- Run promptfoo in headless mode: `npx promptfoo eval -c evals/promptfooconfig.yaml --no-cache -o result.json`.
- Run deepeval `StepEfficiencyMetric` on traces.
- Run LLM-as-judge rubric on outputs.
- Write `result.json` per candidate.

**`compare.py`**:
- Takes `result.json` (candidate) + existing component's baseline metrics.
- Computes delta per dimension.
- Renders comparison table for the report section.

**Acceptance**: End-to-end eval on one synthetic candidate completes, produces valid `result.json`, compare.py produces delta table.

### Phase 5: HTML Report

The report is the primary product. It must be readable in 5 minutes, actionable in under 5 more.

**Report structure:**

```
1. Nightly Summary (top)
   ├── Run date, caf-team commit at run time, N repos scanned, N passed triage, N passed eval
   └── "What changed since last night" (component inventory diff, if any)

2. Component Map (the "what we have" section)
   └── Table: component name | type | purpose | baseline tokens | status
       Status options: HEALTHY | CANDIDATE UPGRADE AVAILABLE | REDUNDANT (may remove)

3. Recommended Actions (the "what to do" section — ordered by impact)
   ├── ADD: [repo name] — new capability, no existing equivalent
   │   └── What it does, test results, how to install (copy-paste commands)
   ├── UPGRADE: [repo] replaces [existing component] 
   │   └── Metric table (before/after), how to swap in (commands), blast radius
   └── NO ACTION: [repos that passed triage but didn't beat existing or add value]

4. Full Eval Results (detail section)
   └── Per candidate: test case results, quality scores per dimension, failure reasons

5. Discovery Log
   └── All repos found this night, triage outcome for each (accept/reject reason)

6. Historical Trend
   └── 30-day token usage trend, quality trend (Chart.js inline)
```

**`report.py`**: Jinja2 template → self-contained HTML (no external assets). Saved to `reports/YYYY-MM-DD.html`. Previous night's report linked in the new one for easy comparison.

**Acceptance**: Report generated from synthetic data renders correctly in browser. All sections populate. Historical trend chart visible.

### Phase 6: Mac launchd Wiring

**Steps:**

1. **`infra/com.caf.evolve.plist`**:
   ```xml
   StartCalendarInterval: {Hour: 2, Minute: 0}
   ProgramArguments: ["/Users/tomkwon/.local/bin/uv", "run", 
                      "python", ".../tools/evolve/runner/main.py"]
   StandardOutPath: ~/Library/Logs/caf-evolve/run.log
   StandardErrorPath: ~/Library/Logs/caf-evolve/error.log
   EnvironmentVariables: {ANTHROPIC_API_KEY: ..., GITHUB_TOKEN: ...}
   ```
   - `RunAtLoad: false` — cron-only, not on login.
   - `StartInterval` is NOT used (use `StartCalendarInterval` for daily at 2am).

2. **`infra/install-launchd.sh`**:
   - Copies plist to `~/Library/LaunchAgents/com.caf.evolve.plist`.
   - `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.caf.evolve.plist`.
   - Creates log directory `~/Library/Logs/caf-evolve/`.
   - Prints: "Evolve will run nightly at 02:00. View logs: tail -f ~/Library/Logs/caf-evolve/run.log".

3. **`main.py`** guards: If already ran today (checks `state/last_run.json`), exit 0 immediately. Idempotent.

4. **Secrets**: `ANTHROPIC_API_KEY` and `GITHUB_TOKEN` loaded from a `.env` file that the plist sources. `.env` path in `infra/secrets.env.example`. Never committed.

**Acceptance**: `launchctl list | grep caf.evolve` shows the job. `launchctl start com.caf.evolve` triggers a dry-run run immediately. Log appears.

## Team Orchestration

- I operate as team lead. I do NOT write code directly. I coordinate via Task tools.
- **Phase 1 (inventory) and Phase 2 (eval suite + baseline)** run FIRST — all later phases depend on them.
- Phases 3–6 have sub-tasks that can parallelize once Phase 2 is done.
- Critical analyst and security consultant run in parallel with Phase 1 planning.

### Team Members

- **Builder**
  - Name: `inventory-architect`
  - Role: Build `inventory/scanner.py` + initial `components.json` + `COMPONENTS.md`. Owns the component catalog — the ontology the whole system depends on.
  - Agent Type: `builder`
  - Resume: true

- **Builder**
  - Name: `eval-suite-architect`
  - Role: Design the analytic rubric, gold examples (hand-curated, needs Tom review), and all 8 test suite YAMLs. Most critical deliverable.
  - Agent Type: `builder`
  - Resume: true

- **Builder**
  - Name: `baseline-runner`
  - Role: Run full suite against current caf-team, validate variance, commit baseline.json, back-fill inventory metrics.
  - Agent Type: `builder`
  - Resume: true

- **Builder**
  - Name: `discovery-engineer`
  - Role: Build `discover.py` + `triage.py` including overlap detection against components.json.
  - Agent Type: `builder`
  - Resume: true

- **Builder**
  - Name: `evaluator-engineer`
  - Role: Build `evaluate.py` + `compare.py` — candidate integration, promptfoo + deepeval runners, head-to-head comparison, LLM judge.
  - Agent Type: `builder`
  - Resume: true

- **Builder**
  - Name: `reporter-engineer`
  - Role: HTML report (Jinja2 + inline Chart.js, all 6 sections) + `main.py` pipeline wiring.
  - Agent Type: `builder`
  - Resume: true

- **Builder**
  - Name: `launchd-engineer`
  - Role: Mac launchd plist, install script, secrets handling, log rotation.
  - Agent Type: `builder`
  - Resume: true

- **Critical Analyst**
  - Name: `plan-skeptic`
  - Role: Review plan before building. Surface risks in component overlap detection (false positives), judge reliability, report section ordering (is Tom seeing what matters first?), feedback loop when recommendations are ignored.
  - Agent Type: `critical-analyst`
  - Resume: false

- **Validator**
  - Name: `end-to-end-validator`
  - Role: Full pipeline smoke: synthetic good candidate (new skill), synthetic upgrade candidate (replaces existing component), synthetic bad candidate (regression). Confirm all route to correct report section.
  - Agent Type: `validator`
  - Resume: false

## Step by Step Tasks

### 1. Pre-flight critique
- **Task ID**: `pre-critique`
- **Depends On**: none
- **Assigned To**: `plan-skeptic`
- **Agent Type**: `critical-analyst`
- **Parallel**: false
- Read this plan. Surface ≥5 concrete risks ranked by severity. Particular focus: (a) overlap detection accuracy — will keyword matching produce false positives? (b) gold example collection — is asking Tom to annotate 30 examples a blocker? (c) what happens when the scanner mis-categorizes a component? (d) report information density — will Tom actually open it nightly if it's noisy?
- Save to `specs/auto-update-cron-system-CRITIQUE.md`.

### 2. Build component inventory scanner
- **Task ID**: `inventory-scanner`
- **Depends On**: `pre-critique`
- **Assigned To**: `inventory-architect`
- **Agent Type**: `builder`
- **Parallel**: false
- Build `tools/evolve/inventory/scanner.py`. Walk `global-skills/`, `global-agents/`, `global-hooks/`, `global-commands/`, `templates/settings.json.template`. Extract per-component: name, type, path, invocation, purpose (from first non-blank SKILL.md paragraph or agent .md purpose section), capabilities (from markdown lists), model tier (from `data/model_tiers.yaml`).
- Emit `inventory/components.json` (machine-readable) + `inventory/COMPONENTS.md` (human-readable table).
- Define `inventory/schema.json` for validation.
- Run scanner against current caf-team. Commit output.

### 3. Design analytic rubric + collect gold examples
- **Task ID**: `rubric-design`
- **Depends On**: `pre-critique`
- **Assigned To**: `eval-suite-architect`
- **Agent Type**: `builder`
- **Parallel**: true
- Write `evals/rubrics/analytic.md`: 4 dimensions × 3-point scale (Excellent=3 / Acceptable=2 / Poor=1) with anchored examples per score per dimension. Include the full LLM judge CoT prompt template.
- Curate `evals/rubrics/gold_examples.jsonl`: 30 examples from real caf-team runs, pre-scored. Format: `{input, output, scores: {task_completion, tool_minimality, context_economy, coordination_quality}, explanation}`. Output a `GOLD_REVIEW_NEEDED.md` listing the 30 inputs so Tom can validate.

### 4. Build 8 test suites
- **Task ID**: `eval-suites`
- **Depends On**: `rubric-design`, `inventory-scanner`
- **Assigned To**: `eval-suite-architect` (resumed)
- **Agent Type**: `builder`
- **Parallel**: false
- Write all 8 YAML suites under `evals/suites/`. Each test: input prompt, fixture path, `components_covered` list (from components.json names), deterministic assertions, rubric dimensions.
- Smoke suite: exactly 5 tests, one per major workflow area.
- Full suite: ~40 tests total. Each test links to ≥1 component in components.json.
- Write `fixtures/` inputs and file-tree stubs.

### 5. Run baseline + back-fill inventory
- **Task ID**: `baseline-capture`
- **Depends On**: `eval-suites`
- **Assigned To**: `baseline-runner`
- **Agent Type**: `builder`
- **Parallel**: false
- Run full suite 3× against current caf-team HEAD. Compute variance. Commit `baseline/baseline.json` + `baseline/snapshot_<hash>.json`.
- Back-fill `baseline_tokens_avg` + `baseline_quality_avg` into `components.json` per covered test.
- Update `baseline/REGENERATE.md` with the commands to re-run.

### 6. Build discovery + triage with overlap detection
- **Task ID**: `discovery`
- **Depends On**: `inventory-scanner`
- **Assigned To**: `discovery-engineer`
- **Agent Type**: `builder`
- **Parallel**: true
- Build `runner/discover.py`: GitHub Search API (4 queries), RSS feeds (3 feeds), de-dup vs `state/seen_repos.json`. Emit to `candidates_queue.jsonl`.
- Build `runner/triage.py`: license/language/recency filters, category classifier, **overlap detection** against `components.json` (keyword match on name + purpose, emit `overlaps_existing` list). Smoke gate.
- Unit tests with frozen GitHub response fixtures.

### 7. Build evaluator + head-to-head comparison
- **Task ID**: `evaluator`
- **Depends On**: `baseline-capture`, `discovery`
- **Assigned To**: `evaluator-engineer`
- **Agent Type**: `builder`
- **Parallel**: false
- Build `runner/evaluate.py`: per-candidate integration by type, promptfoo headless invocation, deepeval step-efficiency metric, LLM judge scoring using `evals/rubrics/analytic.md` template.
- Build `runner/compare.py`: loads candidate `result.json` + existing component's baseline slice from `components.json`. Computes per-dimension delta. Emits `upgrade_recommendation.json` if candidate wins on ≥3 of 4 dimensions.

### 8. Build HTML report + pipeline wiring
- **Task ID**: `reporter`
- **Depends On**: `evaluator`
- **Assigned To**: `reporter-engineer`
- **Agent Type**: `builder`
- **Parallel**: true (with task 9)
- Build `runner/report.py`: Jinja2 template → self-contained HTML with all 6 sections. Inline Chart.js for trend charts. Each "Recommended Action" section includes: copy-paste install commands, blast radius note, before/after metric table.
- Build `runner/main.py`: orchestrates all stages in order, writes `state/last_run.json` on success, idempotent guard on re-run.

### 9. Build Mac launchd setup
- **Task ID**: `launchd`
- **Depends On**: `pre-critique`
- **Assigned To**: `launchd-engineer`
- **Agent Type**: `builder`
- **Parallel**: true (with task 8)
- Write `infra/com.caf.evolve.plist` (daily 02:00, StandardOut/ErrPath, uv entrypoint, env source).
- Write `infra/install-launchd.sh` (install + load, create log dir, print confirmation).
- Write `infra/secrets.env.example`.
- Test manually: `launchctl start com.caf.evolve` triggers a run and log appears.

### 10. End-to-end validation
- **Task ID**: `validate-all`
- **Depends On**: `reporter`, `launchd`
- **Assigned To**: `end-to-end-validator`
- **Agent Type**: `validator`
- **Parallel**: false
- Run full pipeline against 3 synthetic candidates:
  - **Good-new**: A trivial skill with no existing overlap → should appear in "ADD" section.
  - **Good-upgrade**: A mock skill with same `overlaps_existing` tag as `research-docs`, with 20% fewer tokens → should appear in "UPGRADE" section.
  - **Bad**: A skill that regresses quality by 30% → should appear in failure log, not in recommended actions.
- Confirm HTML report renders with correct sections. Confirm launchd runs on schedule (force-trigger and observe log).
- Confirm `state/seen_repos.json` updated so duplicate run is a no-op.

## Acceptance Criteria

- `tools/evolve/` fully structured with all subdirectories and files above.
- `inventory/components.json` catalogs all CAF components. `COMPONENTS.md` is human-readable.
- `baseline/baseline.json` committed, variance bands documented, gold examples written (Tom to validate).
- Full test suite: 8 YAMLs, ~40 tests, each linked to ≥1 component.
- `launchctl list | grep caf.evolve` shows the job loaded. `launchctl start com.caf.evolve` produces a log entry.
- End-to-end pipeline run (manual trigger) completes without error on all 3 synthetic candidates.
- HTML report for synthetic run renders correctly, includes all 6 sections, upgrade comparison table visible.
- 3 consecutive nightly runs complete without manual intervention.
- `state/seen_repos.json` prevents re-evaluation of already-tested repos.
- Report contains "how to install" copy-paste instructions for each recommendation.

## Validation Commands

```bash
# Inventory
uv run python tools/evolve/inventory/scanner.py --check
cat tools/evolve/inventory/components.json | python -m json.tool | head -100

# Baseline stability (run twice, compare)
uv run python tools/evolve/runner/main.py --mode baseline --runs 3
diff tools/evolve/baseline/snapshot_*.json  # should be within variance bands

# Discovery dry-run (no actual queue writes)
uv run python tools/evolve/runner/discover.py --since 2026-05-01 --dry-run

# Triage on sample (includes overlap detection)
uv run python tools/evolve/runner/triage.py \
  --input tools/evolve/evals/fixtures/candidates_sample.jsonl

# Full pipeline on synthetic candidates
uv run python tools/evolve/runner/main.py \
  --candidates-from tools/evolve/evals/fixtures/synthetic_set.jsonl

# Report renders
open tools/evolve/reports/$(date +%Y-%m-%d).html

# launchd
cat ~/Library/LaunchAgents/com.caf.evolve.plist
launchctl list | grep caf.evolve
launchctl start com.caf.evolve
tail -f ~/Library/Logs/caf-evolve/run.log
```

## Notes

### Component Inventory Design Decisions

**What "overlap" means**: A candidate overlaps an existing component if: (a) the repo README or description mentions the same primary action (fetch docs, search papers, orchestrate agents, etc.) AND (b) the component type matches (skill→skill, agent→agent, hook→hook). A new MCP server does NOT overlap a skill that calls that server's domain — they compose, not compete.

**Overlap detection v1**: Keyword matching (TF-IDF against component `purpose` strings) is good enough for v1. Do not over-engineer into embeddings — the candidate set is small and human review of the component map happens weekly.

**What "upgrade" means in the report**: The candidate is recommended as an upgrade only if it wins on ≥3 of 4 rubric dimensions vs the existing component. Winning only on tokens while losing quality is NOT an upgrade.

**Component "REDUNDANT" flag**: If two existing components have near-identical `capabilities` lists and one has consistently lower scores, flag the weaker one as `REDUNDANT` in the report. This is a separate job from evaluating new candidates — the scanner can do this statically by comparing components.json entries.

### Eval Suite Coverage Targets

| Suite | CAF Components Covered | Test Count |
|---|---|---|
| smoke.yaml | 1 per major area | 5 |
| orchestration.yaml | orchestrate, orchestrator, po, consultants | 6 |
| research.yaml | researcher, code-researcher, research-docs, research-news, academic-researcher | 7 |
| debugging.yaml | debugger, error-analyzer, debug skill | 4 |
| memory.yaml | auto-memory hooks, FACTS.md writer, MEMORY.md writer | 4 |
| hooks.yaml | damage-control, session hooks, cost hooks | 5 |
| skill_invocation.yaml | 6 core skills by invocation name | 6 |
| multi_agent.yaml | parallel agent coordination, watchdog, validator | 5 |
| **Total** | | **~42** |

### Gold Examples Collection

Tom needs to review `evals/rubrics/GOLD_REVIEW_NEEDED.md` after Phase 2 Task 3 completes. 30 examples, scoring takes ~10-15 minutes. This is the only manual step in the whole pipeline. The eval quality degrades without calibration — do not skip.

### launchd vs cron

`launchctl` on macOS is preferred over crontab because: (a) it handles sleep/wake correctly — if Mac is asleep at 02:00, launchd runs it when it wakes; (b) logs go to dedicated files, not the system cron mail spool; (c) it survives logout without requiring `cron`.

### Feedback Loop

When Tom ignores a recommendation for multiple nights, the system should eventually lower its confidence score for that candidate type. v1 doesn't track this. Flag as a v2 enhancement: record Tom's merge/ignore decision in `state/last_run.json` and adjust the acceptance threshold for that component category over time.

### Dependencies

```bash
# tools/evolve/
uv add promptfoo deepeval pygithub feedparser jinja2 gitpython python-dotenv
# promptfoo CLI (for headless eval)
npm install -g promptfoo
```

### Out of Scope (v1)

- Notifications (Telegram, email) — HTML file on disk is enough.
- Auto-PR or any git operations — manual merge only.
- Multi-ecosystem discovery (LangChain, AutoGen) — Claude Code only.
- Modifying Rust `caf-hooks` binary — always manual, always flagged as high-blast-radius.
- Modifying `templates/settings.json.template` schema — additions to existing arrays OK, schema changes manual only.
- Feedback loop / auto-tune of thresholds.
