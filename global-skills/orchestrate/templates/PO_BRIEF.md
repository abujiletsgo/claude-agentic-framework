# PO Brief — [Project Name]

## What This Project Is
[1-2 sentences describing what the product does and who it's for]

## Active Domain Leads
List which leads are relevant for this project. PO will default to these when routing.

- frontend-lead: [framework — e.g. React 18, Next.js 14]
- backend-lead: [framework — e.g. FastAPI, Express]
- api-lead: [REST/GraphQL, auth approach]
- qa-lead: [test framework — e.g. Vitest, pytest]
- [add/remove as needed]

## Custom Leads
Project-specific leads not in the standard 18. Each entry maps a lead name to its base type and domain.
Format: `<lead-name>: base=<standard-lead-type>, domain="<what it owns>"`
These are loaded automatically from `.claude/agents/*-lead.md` if those files exist.
Leave this section empty or omit it if all your work fits the standard 18.

- [lead-name]: base=[standard-lead-type], domain="[what it owns]"

## What "Good" Looks Like
[Quality bar: e.g. "all user flows tested", "no TypeScript errors", "mobile-first UI"]

## Team Norms
[e.g. "use existing component library", "follow existing file structure", "no new dependencies without approval"]

## Out of Scope
[What should NOT be changed or touched]
