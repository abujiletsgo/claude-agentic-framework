---
name: facts
description: Manage FACTS.md — the project's living episodic memory layer. Use to add, list, retire, or inspect verified project facts.
scope: framework
---

> **Requires**: Claude Agentic Framework. This skill manages `.claude/FACTS.md` using the framework's fact_manager.py.

# Facts — Episodic Memory Manager

Manages `.claude/FACTS.md` for the current project. This file is the **Layer 2 episodic memory** — injected at every session start as authoritative ground truth to prevent hallucination.

## Sub-commands

### `/facts list`
Display the current FACTS.md for this project.

```
Read .claude/FACTS.md and display its full contents to the user.
If it doesn't exist, say so and offer to run `/facts init`.
```

### `/facts add <CATEGORY> "<fact text>"`
Manually add a fact. Use this when you've verified something that should be remembered.

Categories: `CONFIRMED`, `GOTCHAS`, `PATHS`, `PATTERNS`

Example: `/facts add GOTCHAS "npm install fails silently — always use pnpm"`

```
1. Parse the category and fact text from the user's message
2. Run: uv run {facts_dir}/fact_manager.py add <CATEGORY> "<fact>"
   OR: directly call add() from fact_manager.py
3. Confirm: "Added to FACTS.md under [CATEGORY]"
4. Show the updated entry
```

### `/facts stale "<pattern>"`
Mark a fact as outdated (move to STALE section so it's excluded from injection).

Example: `/facts stale "port 8080"` — moves any entry containing "port 8080" to STALE.

```
1. Find matching entries in FACTS.md (not in STALE already)
2. Move them to the ## ✗ STALE section with today's date
3. Confirm which entries were moved
```

### `/facts init`
Initialize FACTS.md if it doesn't exist, or reinitialize if empty.

```
1. Check if .claude/FACTS.md exists
2. If missing: create it using fact_manager.init()
3. Confirm creation
```

### `/facts summary`
Show fact counts per category and token estimate.

```
1. Read FACTS.md
2. Count entries per section
3. Estimate injection token cost (chars / 4 ≈ tokens)
4. Display table:
   CONFIRMED: N facts
   GOTCHAS:   N facts
   PATHS:     N facts
   PATTERNS:  N facts
   STALE:     N facts (excluded from injection)
   ─────────────────
   Total injected: ~N tokens
```

### `/facts purge-stale`
Remove all STALE entries immediately (don't wait for 90-day auto-prune).

```
1. Read FACTS.md
2. Remove all entries under ## ✗ STALE
3. Confirm count removed
```

---

## Implementation Instructions

When invoked, parse the user's message to determine the sub-command:
- `/facts` alone → show `/facts list`
- `/facts list` → display FACTS.md
- `/facts add <CATEGORY> <text>` → call add()
- `/facts stale <pattern>` → call move_to_stale()
- `/facts init` → call init()
- `/facts summary` → call count_facts() + estimate tokens
- `/facts purge-stale` → remove STALE section entries

The fact_manager library is at `global-hooks/framework/facts/fact_manager.py` relative to the project root.

Discover it at runtime:
```python
import os
# Walk up from __file__ or use the project root (cwd when Claude runs)
project_root = os.getcwd()  # CAF sets cwd to the project root
facts_dir = os.path.join(project_root, "global-hooks", "framework", "facts")
if not os.path.isfile(os.path.join(facts_dir, "fact_manager.py")):
    raise FileNotFoundError(f"fact_manager.py not found at {facts_dir}. Is this a CAF project?")
```

Import it with `sys.path.insert(0, facts_dir)` then `from fact_manager import ...`

---

## Memory Layer Context

FACTS.md sits in **Layer 2 (Episodic)** of the 4-layer memory system:

```
Layer 3 — SEMANTIC (global)  : ~/.claude/memory/MEMORY.md, knowledge DB
Layer 2 — EPISODIC (project) : .claude/FACTS.md  ← this file
Layer 1 — WORKING (session)  : TaskList, compressed summaries
Layer 0 — SENSORY (turn)     : current tool output
```

**When to use each layer:**
- `/facts add CONFIRMED` → truth verified in THIS project, persists across sessions
- knowledge-db skill → patterns that apply across MULTIPLE projects
- MEMORY.md → permanent global rules that apply everywhere always
