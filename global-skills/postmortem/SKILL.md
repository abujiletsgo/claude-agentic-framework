---
name: postmortem
description: "Look back at what actually happened when something broke. Reconstructs a timeline from Claude Code's native transcript plus CAF's failure sinks — the failing tool call, its error, the lead-up, and the failure family. Use when something went wrong and you need evidence instead of a guess: 'why did that fail', 'what broke', 'it worked earlier', 'look back', 'postmortem', 'what happened', a repeated/mysterious failure, or a session that ended badly. ALSO use proactively BEFORE re-attempting anything that already failed once — re-running blind is how loops start."
allowed-tools: Bash, Read, Grep
---

# postmortem

Do not guess at a failure you can read. The evidence already exists: Claude Code
writes a full transcript of every tool call and every error, and CAF writes its
own failure sinks. `bin/postmortem` stitches them into one timeline.

## Run it

```bash
python3 bin/postmortem                      # last failure here, with lead-up
python3 bin/postmortem --last 5             # the 5 most recent
python3 bin/postmortem --since 2h           # everything in the last 2 hours
python3 bin/postmortem --session <id>       # one specific session
python3 bin/postmortem --all                # every session for this project
python3 bin/postmortem --json               # machine-readable
```

(From another repo, use the absolute path: `python3 ~/Documents/caf-team/bin/postmortem`.)

## Read the output in this order

1. **The family histogram.** Repetition is the signal. Twenty of one family is a
   systemic problem; one of twenty is an accident. Fix the family, not the instance.
2. **The failing call** — tool, exact input, verbatim error.
3. **The lead-up** — the calls immediately before it. Most failures are caused by
   the step before, not the step that reported the error.

## Failure families and what they usually mean

| family | first thing to check |
|---|---|
| blocked by damage-control | Did you actually try something destructive, or is this a **false positive**? The scanner matches command *text*, so prose containing `eval`, a commit message quoting a delete command, or a `chmod` on the repo's own `bin/` all trip it. Rephrase; do not fight the guard. |
| permission denied by the classifier | The action looked security-weakening. Re-read what you asked for — the classifier is usually right. Never route around it. |
| command exited non-zero | Read the stderr in the record. Often a `grep` with no match (exit 1) and not a real failure at all. |
| import / dependency missing | A module was deleted or never installed. Check whether something retired it. |
| file or path not found | Something references a file that no longer exists — a classic after a cleanup. |
| rate limit / overload / auth | Transient or credential. Not a code bug; do not "fix" code in response. |
| timeout | The command was too slow, or it hung waiting on input. |

## When to reach for this

- **Before re-running anything that already failed.** Re-attempting blind is how
  loops start; read the error first.
- A failure that repeats, or one whose cause is not obvious from the last message.
- "It worked earlier" — diff the lead-up between the working and failing sessions.
- After an agent or overnight run ends badly: `--since 8h` to see the whole night.

## What it will not tell you

It reports what happened, not why the code is wrong. Once you have the failing
call and its lead-up, go read the code. And note that a *blocked* command is not a
bug — the guard doing its job looks identical to a failure in the log.
