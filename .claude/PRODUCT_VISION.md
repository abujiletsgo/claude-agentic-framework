# Product Vision — CAF Team

<!-- Last updated: 2026-04-13 -->
<!-- Updated by: PO, from conversation with Tom -->

## The Problem CAF Solves

Products cannot be built without CAF. It is the foundation — the operating system for building anything. Without it, the user has no way to coordinate agents, make technical decisions, or execute on a vision. CAF is not a convenience; it is a dependency.

## Who It's For

Tom — a visionary without a technical background. He sees what needs to exist in the world. He does not know (and should not need to know) how to build it.

## What "Perfect" Feels Like

Tom makes a few inputs — only when a fundamental decision needs to be made. Everything else happens. The system knows best practices. It knows how to build components that already exist. It knows how to wire them together for something that has never existed before. Tom's vision becomes a product without Tom needing to understand the implementation.

Most of what gets built has pre-existing components. The new part is the combination — the thing that doesn't exist yet. CAF and its agents know how to build the parts. Tom provides the direction for the whole.

## Non-Negotiables

- Tom only touches **fundamental decisions**: what it is, who it's for, what done feels like, whether the direction is right
- Tom never touches: architecture choices, framework selection, data models, implementation patterns — those are PO's job, informed by best practices and the vision
- The system makes autonomous technical decisions using expert lenses (eng-review, ceo-review, design-review, security)

## What "Wrong" Looks Like

- Doesn't function as planned
- Doesn't look as planned  
- Doesn't feel as planned

All three must be true. Any one of these failing = the job failed.

## How PO Uses This

Before every job: read this file. Every technical decision filters through:
> "Does this serve Tom's vision? Does it use best practices for the components involved? Will the result function, look, and feel as planned?"

If yes — decide autonomously. If the decision would change what gets built at a product level — escalate to Tom with a recommendation, not a question.

## Open Questions for Tom (update as answered)

- (none yet)

## Past Decisions

- 2026-04-13: Decided persistent lead panes (Option A) over daemon or per-wave spawning — Tom confirmed this matches the "real teammates" mental model
- 2026-04-13: Leads consolidate to 8 (2 implementation + 6 specialist) + 6 gstack reviewers — removed redundant/mergeable leads
- 2026-04-13: PO role redesigned as vision-to-execution translator, not coordinator
