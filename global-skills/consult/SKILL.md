---
name: consult
description: "Sequential consultant dialogue. Runs domain consultants one at a time — each builds on the previous consultant's spec. Produces a ready-to-use spec for /orchestrate."
user-invocable: true
---

# /consult [domains]

You are running a consultant session. Route the user through relevant domain consultants **one at a time, sequentially**. Each consultant reads the task and all previous spec sections before asking their questions.

This is NOT orchestration. No builders. No researchers. Pure spec production.

---

## Step 1: Get the task

If the user provided a task description as args, use it directly.

If no args were provided, ask: "What are you building or changing?" — one question, wait for their answer.

---

## Step 2: Detect relevant consultants

Based on the task, determine which consultants to engage:

| Signal in task | Consultant |
|---|---|
| system design, architecture, blast radius, interfaces, refactor, structure | `architecture-consultant` |
| API, database, server, data model, migration, service, endpoint, backend | `backend-consultant` |
| UI, component, page, user flow, styling, UX, React, Vue, frontend | `frontend-consultant` |
| auth, login, permissions, PII, secrets, input validation, compliance, security | `security-consultant` |

If the user specified domains as args (e.g., `/consult frontend backend`), use exactly those.

Before proceeding: tell the user which consultants you're planning to run and in what order. Let them confirm or adjust. Example:

```
I'll run these consultants in order:
1. Architecture Consultant — system structure and interface contracts
2. Backend Consultant — API and data layer

Proceed, or would you like to add/remove any?
```

Wait for confirmation.

---

## Step 3: Run consultants sequentially

**Order when multiple are relevant**: architecture → backend → frontend → security

For each consultant, in order:

### 3a. Announce

Tell the user:

```
---
[1/N] Architecture Consultant — starting now
---
```

### 3b. Spawn the agent

```python
Agent(
    name="architecture-consultant",  # use the actual consultant type
    subagent_type="architecture-consultant",
    model="sonnet",
    prompt="""You are the Architecture Consultant in a /consult session.

TASK:
<task description>

ACCUMULATED SPEC (from consultants who ran before you):
<paste accumulated spec sections, or "None — you are first.">

INSTRUCTIONS:
- Read the codebase as needed before asking questions (informed questions are better)
- Open your FIRST AskUserQuestion with your name bolded: "**[Architecture Consultant]** — ..."
  so the user always knows who they're talking to
- Ask questions one batch at a time — don't dump everything at once
- When you're satisfied with the answers, produce a clean spec section and return it
- Your spec section should be precise enough that a builder can implement it without follow-up questions
"""
)
```

Adjust `name`, `subagent_type`, the bolded name, and ACCUMULATED SPEC for each consultant.

### 3c. Wait and accumulate

- Wait for the agent to complete and return its spec section
- Append the section to the running accumulated spec (use a clear header: `## Architecture` / `## Backend` / etc.)
- Announce to the user: `[Architecture Consultant] done — spec section added.`
- Move to the next consultant

**Never spawn the next consultant until the current one has completed and returned a spec section.**

---

## Step 4: Synthesize and save

After all consultants complete:

Generate a timestamp:
```bash
python3 -c "import time; print(f'consult_{int(time.time())}')"
```

Save the full accumulated spec to `/tmp/claude/consult_<id>.md` with this structure:

```markdown
# Consultation Spec — <id>

**Task**: <original task description>
**Consultants**: <list of consultants run, in order>
**Date**: <today>

---

## Architecture
<architecture consultant spec section>

## Backend
<backend consultant spec section>

## Frontend
<frontend consultant spec section>

## Security
<security consultant spec section>
```

Only include sections for consultants that actually ran.

Then report to the user:

```
## Consultation complete

Consultants: Architecture → Backend (2 of 4)
Spec: /tmp/claude/consult_<id>.md

### Key decisions surfaced
- <decision 1>
- <decision 2>
- <decision 3>

Ready for /orchestrate — you can pass the spec path or reference it directly.
```

---

## Rules

- **Sequential only** — never spawn two consultants at once. This is about depth of understanding, not speed.
- **Accumulated context** — every consultant after the first sees all previous spec sections in their prompt.
- **Identity is visible** — every consultant must open their first question with their name bolded. No anonymous questions.
- **Spec is required output** — a consultant that doesn't produce a spec section has not finished. If an agent returns without one, tell the user and ask if they want to re-run that consultant.
- **No building** — if the user asks to start building mid-session, tell them to run `/orchestrate` with the spec path when the consultation is done.
- **Challenge scope** — if the user's task seems broader or narrower than they realize, surface it early (before consultants run, if obvious; during consultation if discovered).
