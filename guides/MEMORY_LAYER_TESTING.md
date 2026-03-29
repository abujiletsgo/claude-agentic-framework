# Memory Layer Testing: Question-Driven Validation

> How to verify your memory files (CLAUDE.md, ARCHITECTURE.md, FACTS.md, MEMORY.md, PROJECT_CONTEXT.md) actually work. If a fresh agent can't answer a question from memory files alone, that's a gap.

---

## 1. The Question-Driven Design Principle

Memory layers exist to answer questions FAST. Not to document everything. Not to be comprehensive. To let a fresh agent — with zero prior context — get the right answer on the first try.

The test is simple: write questions a real developer would ask, spawn a fresh agent with only the memory files, and see if it can answer them. Every PARTIAL or FAILED answer reveals a gap in your memory layer.

**Why this works**: You don't know what's missing until you ask for it. Developers don't read docs top-to-bottom — they arrive with a question and need an answer. Memory layers that aren't tested against real questions accumulate dead weight and miss critical information.

**The failure mode**: Memory files that describe what code does (which the agent can read itself) instead of what the agent can't figure out alone — rationale, gotchas, cross-system invariants, workflow sequences.

---

## 2. Five Categories of Questions to Test

### Category 1: Mistake Prevention
Questions about traps, footguns, and "don't do this" knowledge.

```
"Can I write to the database?"
"Is it safe to use git add -A in this repo?"
"Can I modify the BacktestConfig type?"
```

**What good answers look like**: Immediate, definitive warnings with consequences stated.

**What memory files need**: Explicit "CRITICAL" / "NEVER" / "GOTCHAS" sections. Agents won't infer danger from neutral descriptions. If modifying X breaks Y, say so directly.

### Category 2: Task Routing
Questions about how to accomplish specific tasks.

```
"I want to run a backtest, what's the command?"
"How do I add a new strategy?"
"How do I regenerate the dashboard?"
```

**What good answers look like**: Copy-paste commands, exact file paths, step sequence.

**What memory files need**: A "Common Workflows" or "Build & Run Commands" section with actual commands — not descriptions of commands. Include `cd` prefixes, flags, and expected output.

### Category 3: Decision Context
Questions about WHY things are the way they are.

```
"Why is the trader cap set to 3%?"
"Why does the project use both Python and Rust?"
"Why is equal weighting not used?"
```

**What good answers look like**: The rationale WITH the evidence. Not "3% was chosen" but "3% because 80% of top walk-forward configs use it."

**What memory files need**: Inline rationale next to configuration values. A "Key Findings" section with numbered results. Decision context decays fastest — if you don't write it down during the session that produced the finding, it's gone.

### Category 4: Data Freshness
Questions about whether information is current and when things last ran.

```
"When was the last full backtest run?"
"Is the Supabase data a snapshot or live?"
"Are the results/ files current?"
```

**What good answers look like**: Dated answers — "Last run 2026-03-25" not "recently."

**What memory files need**: Timestamps on facts ([YYYY-MM-DD] format). FACTS.md entries must be dated. STALE section for superseded information. Without timestamps, every fact is potentially wrong.

### Category 5: Common Workflows
Questions about multi-step processes and sequencing.

```
"How do I go from data load to dashboard?"
"What's the full pipeline sequence?"
"After I change types.rs, what else needs updating?"
```

**What good answers look like**: Ordered steps with dependencies called out. "After X, do Y because Z depends on it."

**What memory files need**: ARCHITECTURE.md blast-radius table ("if X changes, update Y"). Pipeline scripts numbered or sequenced. Cross-system invariants documented as explicit sync requirements.

---

## 3. The Testing Process

### Step 1: Write 15 Questions (3 Per Category)

Write questions that a real developer would actually ask on day one. Not trick questions — real ones. Bias toward questions where getting it wrong has consequences (data loss, broken builds, wrong results).

Good question criteria:
- Answer requires information NOT in the source code
- Getting it wrong would waste >30 minutes or produce incorrect results
- A senior developer on the project would know the answer immediately

### Step 2: Spawn a Fresh Agent

The agent gets access to ONLY:
- `.claude/CLAUDE.md`
- `.claude/ARCHITECTURE.md`
- `.claude/FACTS.md`
- `.claude/MEMORY.md` (and linked topic files)
- `.claude/PROJECT_CONTEXT.md`

No source code. No git history. No running commands. Just the memory files.

This simulates the worst case: an agent that has to rely entirely on what you wrote down.

### Step 3: Rate Each Answer

| Rating | Criteria |
|--------|----------|
| **ANSWERED** | Correct, complete, immediately actionable. No guessing. |
| **PARTIAL** | Partially correct or missing key details. Agent would need to search further. |
| **FAILED** | Wrong, missing, or would lead to a mistake. |

Be strict. PARTIAL means the agent has to do extra work — that's a real cost measured in tokens and time.

### Step 4: Fix Gaps

For each PARTIAL or FAILED:
1. Identify which memory file should contain the answer
2. Add the missing information in the smallest possible edit
3. Don't restructure the whole file — surgical fixes only

Common fixes by failure type:
- **Missing warning** -> Add to FACTS.md GOTCHAS or CLAUDE.md CRITICAL section
- **Missing command** -> Add to CLAUDE.md Build & Run Commands
- **Missing rationale** -> Add inline next to the value in CLAUDE.md
- **Missing timestamp** -> Add [YYYY-MM-DD] to FACTS.md entry
- **Missing dependency** -> Add to ARCHITECTURE.md blast-radius table

### Step 5: Re-Test

Run the same 15 questions again after fixes. Verify score improved. If a fix introduced ambiguity or contradiction with existing content, that counts as a regression.

**Target: 13/15+ ANSWERED.**

---

## 4. What Each Layer Should Contain

### CLAUDE.md (Project Instructions)

The primary file every agent reads first. Optimized for fast orientation.

**MUST have:**
- Project overview with core thesis (1-2 sentences, not a paragraph)
- Build & run commands (copy-paste ready, with `cd` prefixes)
- Architecture summary with CRITICAL warnings for gotchas
- Critical invariants (what breaks if you get it wrong)
- Strategy/config values WITH rationale ("3% trader cap — 80% of top configs use it")
- Common workflows section
- Key findings (numbered, with actual metrics)
- "When to Read What" table pointing to other docs
- "Where to Find What" table for results/data directories

**MUST NOT have:**
- Verbose file-by-file descriptions (agents can read the code)
- Stale information (nothing is worse than confident wrong answers)
- Duplicate content from ARCHITECTURE.md
- Aspirational content ("we plan to..." — only document what IS)

### ARCHITECTURE.md (Dependency Map)

The blast-radius document. Its most valuable section is "if X changes, update Y."

**MUST have:**
- Blast-radius table: `| Changed File | Must Also Update | Why |`
- Dead code identification (saves hours of confused exploration)
- Directory structure with key files marked
- Data flow diagram (text-based ASCII, not Mermaid — renders everywhere)
- Key constants that must match across systems (with file paths for both)

**MUST NOT have:**
- Duplicate of CLAUDE.md content
- Full API documentation (that's in the code itself)
- Implementation details that change frequently

### FACTS.md (Episodic Ground Truth)

The timestamped record of what's actually true right now.

**MUST have:**
- **CONFIRMED** section — execution-verified facts with dates
- **GOTCHAS** section — failure modes and their consequences
- **PATHS** section — key file locations (saves repeated searches)
- **STALE** section — superseded information (prevents agents from acting on old data)
- Every entry timestamped `[YYYY-MM-DD]`

**Format example** (from a real project):
```markdown
## CONFIRMED
- Rust System B (backtester.rs) is the only active engine — System A is dead code [2026-03-29]
- Portfolio walk-forward: 4/5 OOS windows positive, Sharpe 1.53-1.87 [2026-03-29]

## GOTCHAS
- Two BacktestConfig types: models.BacktestConfig (Rust) vs engine.BacktestConfig (Python) [2026-03-29]
- Supabase loader lacks bet_range — events have bet_range="" [2026-03-29]

## STALE
- Old results paths (BACKTEST_*.json at results/ root) — moved to results/backtests/ [2026-03-29]
```

### MEMORY.md (Cross-Session Context)

The index that persists across conversations. Links to topic files for details.

**MUST have:**
- One-line index entries (<150 characters each)
- Links to separate topic `.md` files for details
- Organized semantically (by topic), not chronologically
- Each linked topic file has frontmatter: name, description, type

**Format example:**
```markdown
- [Combo Redefinition](project_combo_redefinition.md) — combo = seriesSlug-marketType
- [Supabase Data Source](reference_supabase.md) — live auto-updating DB, 441K+ rows
```

**MUST NOT have:**
- Long explanations inline (those go in topic files)
- Chronological ordering (hard to scan)
- Entries without links (orphaned context)

### PROJECT_CONTEXT.md (Session Cache)

The fast-load snapshot written by `/prime` and loaded at session start.

**MUST have:**
- Git-hash version for auto-invalidation (stale detection)
- Full prime report content (not a summary of a summary)
- 50-100 lines (enough context without bloat)

**Auto-invalidation rule**: If the git hash in PROJECT_CONTEXT.md doesn't match the current repo hash, re-prime. This prevents stale context from persisting across significant code changes.

---

## 5. Scoring Rubric

| Score | Rating | Action |
|-------|--------|--------|
| 14-15/15 | Excellent | Ready for production. Minor polish only. |
| 12-13/15 | Good | Fix the 2-3 gaps. Usually missing rationale or timestamps. |
| 10-11/15 | Needs work | Missing entire question categories. Likely no GOTCHAS or no workflow docs. |
| <10/15 | Rewrite | Memory files are descriptive rather than actionable. Start over with questions first. |

**Typical progression**: First test scores 8-10. After one round of fixes, scores 12-14. Second round of fixes reaches 14-15. Rarely needs a third round.

---

## 6. Example Test Session

Based on actual testing of the agbot_strategy project (copy-trading strategy framework, Python + Rust, Supabase data source).

### The 15 Questions

**Mistake Prevention:**
1. "Can I write data to Supabase?"
2. "I need to modify BacktestConfig — is there only one?"
3. "Can I use `include_bet_range=True` in a strategy?"

**Task Routing:**
4. "How do I run a single backtest for testing?"
5. "How do I run the full grid search?"
6. "How do I install the Python package for development?"

**Decision Context:**
7. "Why is the trader cap set to 3%?"
8. "Why does the project use PnL-weighting instead of equal weighting?"
9. "Why is the rebalance period 5 days?"

**Data Freshness:**
10. "When was the last full backtest run?"
11. "Is the Supabase database a static snapshot or live?"
12. "Are the results/ JSON files current?"

**Common Workflows:**
13. "After changing a type in core/src/types.rs, what else must I update?"
14. "What's the full pipeline from data to report?"
15. "How do I add a new strategy to the framework?"

### Round 1 Results (Before Fixes)

| # | Question | Rating | Gap Identified |
|---|----------|--------|----------------|
| 1 | Write to Supabase? | ANSWERED | CLAUDE.md has explicit "STRICTLY READ-ONLY" warning |
| 2 | How many BacktestConfigs? | FAILED | Only CLAUDE.md mentions Rust types; Python engine.BacktestConfig not documented |
| 3 | include_bet_range safe? | PARTIAL | CLAUDE.md says "always False" but doesn't explain the forward-looking bias consequence |
| 4 | Run single backtest? | ANSWERED | Command in CLAUDE.md: `python scripts/test_single_strategy.py` |
| 5 | Run grid search? | ANSWERED | Command in CLAUDE.md: `python scripts/rust_full_analysis.py` |
| 6 | Install for dev? | ANSWERED | `pip install -e ".[dev]"` in CLAUDE.md |
| 7 | Why 3% trader cap? | PARTIAL | Value listed in CLAUDE.md config section but rationale was buried in Key Findings |
| 8 | Why PnL-weighting? | PARTIAL | Key Findings mentions equal weight loses money, but no direct comparison metrics |
| 9 | Why 5-day rebalance? | ANSWERED | "Only perfectly stable parameter" documented in Key Findings |
| 10 | Last backtest run? | ANSWERED | FACTS.md: "~2026-03-25" with timestamp |
| 11 | Supabase live or snapshot? | ANSWERED | Both FACTS.md and CLAUDE.md confirm live auto-updating |
| 12 | Results files current? | PARTIAL | FACTS.md has last run date but no inventory of which result files map to which runs |
| 13 | After changing types.rs? | FAILED | No blast-radius table existed yet |
| 14 | Full pipeline sequence? | PARTIAL | CLAUDE.md mentions "numbered 01-12" but doesn't list the sequence |
| 15 | Add a new strategy? | FAILED | No workflow documented for extending the framework |

**Round 1 Score: 7 ANSWERED / 5 PARTIAL / 3 FAILED = 7/15**

### Fixes Applied

| Gap | Fix | File |
|-----|-----|------|
| Two BacktestConfigs | Added to FACTS.md GOTCHAS: "Two BacktestConfig types: models.BacktestConfig (Rust) vs engine.BacktestConfig (Python)" | FACTS.md |
| bet_range consequence | Added to CLAUDE.md invariants: "`include_bet_range` is always `False` — setting True introduces forward-looking bias" | CLAUDE.md |
| Trader cap rationale | Moved rationale inline with config value: "Trader cap: 3% max per trader (80% of top walk-forward configs use this)" | CLAUDE.md |
| PnL-weight comparison | Added metric to Key Findings: "Equal weight Sharpe 1.43 vs PnL-weight Sharpe 1.53-1.87" | CLAUDE.md |
| Results file inventory | Added "Where to Find What" table mapping result types to directories | CLAUDE.md |
| Blast-radius table | Created ARCHITECTURE.md with "if X changes, update Y" table: types.rs -> models.py, stats.rs -> combo.py | ARCHITECTURE.md |
| Pipeline sequence | Listed all 12 steps with script names in CLAUDE.md | CLAUDE.md |
| New strategy workflow | Added "Adding a Strategy" to Common Workflows: create subclass, register, add to pipeline | CLAUDE.md |

### Round 2 Results (After Fixes)

| # | Question | Rating | Notes |
|---|----------|--------|-------|
| 1 | Write to Supabase? | ANSWERED | |
| 2 | How many BacktestConfigs? | ANSWERED | GOTCHAS entry now catches this |
| 3 | include_bet_range safe? | ANSWERED | Consequence documented inline |
| 4 | Run single backtest? | ANSWERED | |
| 5 | Run grid search? | ANSWERED | |
| 6 | Install for dev? | ANSWERED | |
| 7 | Why 3% trader cap? | ANSWERED | Rationale now inline with value |
| 8 | Why PnL-weighting? | ANSWERED | Comparative metrics added |
| 9 | Why 5-day rebalance? | ANSWERED | |
| 10 | Last backtest run? | ANSWERED | |
| 11 | Supabase live or snapshot? | ANSWERED | |
| 12 | Results files current? | ANSWERED | "Where to Find What" table added |
| 13 | After changing types.rs? | ANSWERED | Blast-radius table in ARCHITECTURE.md |
| 14 | Full pipeline sequence? | ANSWERED | 12 steps listed |
| 15 | Add a new strategy? | PARTIAL | Workflow added but missing example of strategy registration |

**Round 2 Score: 14 ANSWERED / 1 PARTIAL / 0 FAILED = 14/15**

Target of 13/15 achieved. The remaining PARTIAL is a minor gap — the strategy addition workflow could include a code snippet, but the agent can figure it out from the existing strategy files.

---

## 7. Quick Reference: Running This Test

```
1. Write 15 questions (3 per category)               ~15 min
2. Spawn fresh agent, feed only memory files          ~5 min
3. Rate answers                                       ~20 min
4. Fix gaps (surgical edits, not restructures)        ~30 min
5. Re-test                                            ~20 min
                                                Total: ~90 min
```

Schedule this after any major project milestone, refactor, or when onboarding a new contributor. The questions themselves are the most valuable artifact — keep them versioned alongside the memory files.
