---
name: ui-flow-audit
description: "Meticulous navigation & interaction FLOW audit for any interface (web, mobile/PWA, desktop, TUI). Models the app as a state graph, traces real journeys, scores every transition against a flow-integrity checklist, interrogates each flow for speed/clarity/fitness against known reference patterns, sweeps every prose-bearing surface for text-readability defects (walls of text, collapsed newlines, run-on facts, list/table-shaped prose), then prescribes the concrete UI remedy (back-link, sheet, breadcrumb, undo-toast, return-to-origin, line-per-fact rendering, key-value rows, or a better-fitting pattern entirely) for each issue — ranked and ready to hand to design + build. Triggers: 'flow audit', 'ui flow audit', 'audit the flows', 'navigation review', 'the flow feels off', 'users get lost/stranded', 'text formatting audit', 'unreadable wall of text'."
when_to_use: "Use when a flow feels wrong, after adding a new entry point/route/screen, before shipping a redesign, when a screen is reachable from several places, or when mobile vs desktop navigation diverges. NOT for visual polish (use design-review), code correctness (code-review), or feature pass/fail (qa-cycle) — this audits how the user MOVES between states and whether they can always tell where they are and get back. Composes with those skills."
user-invocable: true
argument-hint: "[--area <name>] [--journey <task>] [--report-only]"
---

# ui-flow-audit: model the graph → trace journeys → score → prescribe remedies

You audit **flow**, not looks and not logic: how a user moves between states, and whether the app preserves their context, closes every loop, and never strands, dead-ends, or disorients them. Your output is a **ranked issue list where every issue names the concrete UI affordance that fixes it** (the button, link, sheet, breadcrumb, toast) and where it lives — so it hands directly to the frontend-design and implementation skills. Finding the problem is half the job; prescribing the remedy is the other half.

This is app-type-agnostic. "Screen" below means route / view / window / panel / modal / sheet / TUI page; "action" means anything that changes what the user sees or where they are.

## Cardinal sins this audit hunts (the whole point)

1. **Losing the user's place** — an action drops them somewhere other than where they were working, with no way back to it.
2. **Hardcoded returns** — a screen reachable from N entry points whose "close/back/done" is wired to ONE fixed destination, ignoring where the user actually came from. (The single most common flow defect.)
3. **Dead-ends** — a state with no forward action and no clean way out; you finish a task and are left staring at the finished thing.
4. **Context/mode switches with no escape** — you enter a mode (editor, wizard, overlay, different tab) and can't back out to the prior context, or the OS/hardware back does the wrong thing.
5. **Orphan / unreachable states** — a screen or empty/error state you can land in but can't leave, or that nothing routes to.
6. **Irreversible-without-safety** — a destructive or consequential action with no confirm and no undo, or (equally bad) a confirm dialog on a high-frequency action so it gets muscle-memoried away.
7. **Inconsistent affordance** — the same action looks/behaves differently across screens, so the user can't build a model.
8. **Lost progress/position** — reload, navigate away, or resume loses form input, scroll position, focus, filters, or selection.
9. **Responsive/cross-device divergence** — a flow that works on one form factor strands the user on another (e.g., closing a full-screen mobile detail lands on a different tab than it opened from).
10. **Wall-of-text rendering** — content with real structure (fields, rows, discrete facts, enumerations) flattened into one run-on paragraph. Reading IS a flow: a screen the user cannot scan is a screen they get lost in. (Phase 4T hunts these.)

## Method

Run these phases in order. Skip nothing; a shallow pass misses exactly the transitions that break. Respect `--area` (scope to one section), `--journey` (trace one named task deeply), `--report-only` (audit only, never propose file edits).

### Phase 0 — Enumerate the nodes (the surface)
List **every** screen, view, route, window, modal, dialog, sheet, drawer, popover, inline-expand, panel, and overlay. For each, also list its **transient states**: default, empty, loading, error, partial/skeleton, success/confirmation, disabled/locked, and any role/permission variants. A flow bug hides in the empty and error states more often than the happy one. Drive this from the code (route table, component tree, state machine) AND, when a live build exists, from the running app.

### Phase 1 — Map the edges (the transition matrix)
For **each node**, enumerate every way **IN** and every way **OUT**.
- IN: every entry point — direct navigation, links from other screens, deep links / shared URLs, notifications, redirects, back/forward, search results, "open recent." List them ALL; the defect lives in the entries you forget.
- OUT: every exit — primary/secondary buttons, close (×), back, breadcrumb, cancel, submit/confirm, swipe/gesture, auto-advance, timeout/session-expiry, error-retry, and "what happens after the action succeeds."
Build a node × (entries, exits) table. **Flag any node with multiple entries but a single hardcoded exit** — that is almost always cardinal sin #2, and one node like this usually explains several reported symptoms.

### Phase 2 — Trace the real journeys (not just single screens)
Walk end-to-end tasks a real user performs, hop by hop. For each journey, and for `--journey` in depth, cover:
- the primary happy path,
- **cancel / abandon mid-flow** (does it return cleanly, is progress kept or discarded, is that the right choice?),
- **reload / refresh mid-state** (deep link integrity: does the URL/state rehydrate, or dump you at the root?),
- **interrupt & resume** (leave to a related entity and come back),
- **deep-link / notification entry** (you arrive at a mid-flow screen with no history — does close/back still work?),
- **back-button / hardware-back / swipe-back at every step**,
- **cross-surface hop**: list → detail → related entity → back. This is where most stranding lives.
At **every hop** ask the three questions: *After this action, where am I? Is it where I expected? Can I get back to where I was?* Record every "no."

### Phase 3 — Score against the flow-integrity checklist
Walk this checklist against the map from Phases 1–2. It is generic and exhaustive; apply every item that the app can exhibit.

- **Return-to-origin**: does close/back/done return to the actual entry point, or a hardcoded one? Test the same screen from each of its entries.
- **Loop closure**: every task the user starts can be finished or cleanly cancelled — no path that just... ends.
- **No dead-ends**: every state has at least one obvious forward or exit action, including after success.
- **Post-action landing**: after submit/confirm/delete/send, the user lands somewhere sensible (usually back at the list/queue they acted from), not stranded on the now-changed item.
- **Back-button integrity**: browser/OS back never destroys a real entry, never no-ops, never skips past where the user expects; forward works too.
- **Context preservation**: filters, sort, selection, scroll position, expanded/collapsed state, and unsaved input survive a round-trip and a back.
- **Location legibility**: the user can always tell where they are (title, breadcrumb, active-nav, highlighted item) — no "where am I?" screens.
- **Mode escape**: any modal/wizard/editor/overlay has an obvious, always-available way out (Esc, ×, Cancel, scrim-click) that does the expected thing; scrim-click loss is intentional or blocked.
- **Modal vs navigation correctness**: transient/contextual work uses a modal/sheet/popover (preserves the backdrop context); a destination uses navigation. Flag full-page navigations that should have been overlays (they nuke context) and overlays that should have been pages (deep-link/shareability lost).
- **Destructive safety**: irreversible/consequential actions have confirm OR undo — and high-frequency actions prefer optimistic + undo-toast over a confirm dialog (confirms get muscle-memoried away).
- **Consistent affordance**: the same action is the same control, label, and position everywhere; the same gesture means the same thing.
- **Focus & scroll restoration**: returning to a list restores scroll and focus to the item you left from; opening a screen moves focus to it (a11y + orientation).
- **Empty/error/loading exits**: every empty, error, and loading state has a way forward or out (retry, back, primary CTA) — never a terminal blank.
- **Deep-link integrity**: any linkable state loads standalone with a valid back/close, and unlinkable-but-important states are reachable.
- **Responsive/cross-device parity**: the flow holds across form factors; specifically, an overlay/full-screen on small screens returns to the same place it opened from, and tab bars / nav stacks don't silently switch the user's context.
- **Notification/alert routing**: a tapped notification lands on the right screen with a working way back, and (for sensitive apps) the notification itself doesn't leak content it shouldn't.
- **Progress & interruption**: multi-step flows show progress, allow back between steps without data loss, and can be resumed.
- **Idempotent re-entry**: re-triggering an action (double-submit, re-open) doesn't duplicate or corrupt; the flow guards it.

### Phase 4 — Interrogate: is this the right pattern, not just a correctly-wired one
Phase 3 catches flows that are wired wrong. This phase catches flows that are wired correctly but are still the wrong pattern for the job, the gap between "works" and "good." For every flow Phase 2 traced, ask three questions:

- **Speed**: count the actual steps, clicks, taps, and waits a real user takes end to end. Is this the minimum a well-designed flow needs, or is there a shorter path (inline edit instead of a full page, bulk action instead of one-at-a-time, a default that skips a step entirely)?
- **Understanding**: at each step, does the user know what just happened and what to do next by looking, or do they have to infer state, guess, or check a different screen to confirm the action worked?
- **Fitness for purpose**: is this the right INTERACTION SHAPE for the job, not merely a technically working one? A full-page navigation for a two-field edit, a wizard for a task that is really one form, a flat list where a calendar or timeline would show the data's real shape, a modal for something the user needs to reference while doing other work, these are fitness problems even when every transition inside them is flawless.

When a flow scores poorly on any axis and you are not confident what "good" looks like here, do a **quick prior-art pass**: name 1-3 concrete reference patterns from specific known products that solve this exact interaction, not a vague "best practices." For common, well-covered interaction patterns (deep-link anchoring, undo toasts, inline-expand vs navigate, calendar/schedule views, empty states, command palettes, bulk selection, optimistic actions) draw directly on established reference apps (Gmail, Linear, Superhuman, Google Calendar, Notion, Things, Superhuman) without needing to search, these are well-documented conventions worth knowing by heart. Reach for WebSearch/WebFetch only for genuinely uncertain or unusual cases where no well-known pattern comes to mind. State plainly whether a cited pattern is recalled knowledge or the result of an active search.

Do not research for its own sake. Skip this phase entirely for a flow that already scores clean on all three axes, or where the fix is a mechanical wiring issue Phase 3 already named precisely (hardcoded return, missing undo) and no pattern-level question is actually open. Judgment over exhaustiveness: the point is to catch the flows where "correctly built" and "actually good" have quietly diverged, not to second-guess every screen.

Findings from this phase feed into Phase 5 exactly like flow-integrity findings, same severity scale, same concrete-affordance requirement, but tagged `[pattern]` in the issue list (flow-integrity findings are tagged `[flow]`) so the remedy consumer can see which findings are "this is wired wrong" and which are "this works but there is a fundamentally better way to do it."

### Phase 4T — Text readability sweep (every prose-bearing surface)
Walls of text are a flow defect: a screen the user cannot scan disorients exactly like a screen with no location indicator. Sweep every surface that renders more than one sentence of data-driven text and score it against this checklist. Do not reduce content to fix these — restructure it.

- **Collapsed structure**: text whose SOURCE carries line breaks or field boundaries rendered through a whitespace-collapsing element (a `<p>`/`<div>` eating `\n`). Check the data before blaming the copy — the classic bug is one missing `white-space: pre-wrap`, or a generator that flattens lines before storage.
- **Run-on facts**: one paragraph carrying several discrete facts (context + finding + count + action). Each fact earns its own line; emphasis goes only on the severity-bearing line.
- **List-shaped prose**: enumerations jammed into a sentence ("A, B, and C are overdue") where a bulleted or numbered list would scan.
- **Key-value prose**: label/value pairs flattened into sentences ("Patient: X DOB: Y Sex: Z") instead of aligned key-value rows.
- **Table-shaped prose**: rows-and-columns data (lab panels, schedules, line items) dumped as a text stream instead of a table or aligned mono block.
- **Metadata run-ons**: provenance, sources, timestamps, or disclaimers appended inline to the sentence they qualify ("…consider ECG. · UpToDate workflow") instead of a caption line below it.
- **Missing hierarchy**: heading, body, and caption all at the same size/weight so nothing anchors the eye; or dense legal/disclaimer text styled like body copy.
- **Verbatim documents**: raw source material (OCR text, logs, transcripts, quoted originals) styled like UI copy instead of AS a document (mono, boxed, pre-wrap, scrollable).

Trace each finding to its ROOT before prescribing: (a) CSS collapsing structure the data already has → one-line style fix; (b) renderer flattening structured data → restructure the component; (c) generator/pipeline destroying structure before storage → fix at the source so every consumer benefits, with a display-only formatter as the fallback when the stored artifact must stay verbatim. Remedy vocabulary: **pre-wrap document block**; **line-per-fact rendering** (structured text joins facts with `\n`, renderer gives each line a row); **bulleted/numbered list**; **key-value rows**; **real table**; **caption line** for provenance; **severity emphasis** on at most one line. Findings are tagged `[text]` and feed Phase 5 with the same severity scale (an unreadable safety-critical surface is P0). Acceptance shape: "no rendered element flattens structure its data source carries; every enumerable series renders as a list or table; provenance reads as a caption, not a tail."

### Phase 5 — Rank and prescribe the remedy (do not stop at "it's broken")
For every issue found, assign severity and **name the concrete UI affordance that fixes it and where it lives**. This is the half that makes the audit actionable and lets it work with the design skills.
- **Severity**: **P0** = strands the user / loses work / dead-end / data loss. **P1** = friction, missing back affordance, avoidable extra step. **P2** = polish, consistency, legibility.
- **Remedy vocabulary** (pick the right affordance, name its placement, describe its states): return-to-origin close (navigate-back with a sensible fallback, or carry an explicit origin token); a labeled **"← Back to <origin>"** link/header; a **breadcrumb**; convert a page-navigation into a **bottom sheet / side drawer / dialog / inline-expand** to preserve context (or the reverse for shareable destinations); **post-action redirect** to the originating list; **optimistic action + undo toast** instead of a confirm dialog (or add a confirm where none exists); **scroll/focus restoration** on return; **active-location indicator** / title / progress header; **guarded re-entry** (disable-on-pending). For each, give: the flow, the defect, the prescribed affordance, its placement, the states/edge-cases it must handle, and a one-line acceptance criterion.
- **Collapse to systemic fixes**: group issues that share one root (e.g., "all of these are the same hardcoded-return; one origin-aware close fixes 1–6") so the team fixes causes, not symptoms.

### Phase 6 — Handoff
Emit a **remedy spec** the design/build skills can execute directly, and state which remedies are one systemic change vs per-screen. Offer to render the audit as a **visual flow map** (nodes + edges, problem edges highlighted) when that's clearer than a table.

## Output format

Produce, in this order:
1. **Root patterns** — the 2–5 recurring causes (this is the insight; symptoms roll up to these).
2. **Node × entry/exit table** (or per-node list) — the map, with multi-entry/single-exit nodes flagged.
3. **Ranked issues** — numbered, P0→P2, each tagged `[flow]`, `[pattern]`, or `[text]`: `flow → defect → prescribed affordance + placement → acceptance criterion`. Numbered so the user can pick ("fix 1,3,5").
4. **Systemic-fix summary** — the one or few architectural changes that clear most of the list.
5. Offer the visual flow-map artifact and, if not `--report-only`, offer to route the remedy spec to the design/build skills.

## Composes with (this skill finds & prescribes; these design & build)

- **design-consultation / design-review** — take the prescribed affordances and design their look, placement, motion, and states. Run this audit BEFORE a redesign to fix flow, AFTER to catch flow regressions the visual pass introduced. Phase 4's prior-art pass is a lightweight, inline lookup to settle a specific pattern question; design-consultation is where a full multi-option design system gets built when a `[pattern]` finding warrants more than picking a known shape.
- **orchestrate / builder** — implement the remedy spec.
- **qa-cycle** — regression-test the new flows once built (feed it the acceptance criteria from Phase 5).
- **arch-map** — resolve the code-level nav wiring (route table, history, state) behind a flow.
- **verify** — confirm the flow fixes match the spec by driving the affected flow end-to-end.

## Adapting the checklist by app type

- **Web / SPA**: routes, browser history & back/forward, deep links & shareable URLs, modals-vs-routes, scroll restoration, tab/window duplication.
- **Mobile / native / PWA**: tab bars, navigation stacks, gesture/edge swipe-back, hardware back button, bottom sheets, full-screen covers returning to the tab they opened from, safe-area and offline states.
- **Desktop**: windows & window focus, menu bars, modal vs modeless dialogs, keyboard navigation & shortcuts, multi-window state.
- **CLI / TUI**: command/subcommand chains, interactive prompts, Esc/Ctrl-C cancel, backing out of nested menus, exit codes as "landing," and re-run/resume behavior.

## Guardrails

- Audit flow only. Bugs → code-review; visuals → design-review; feature correctness → qa-cycle. Note them in passing but don't scope-creep. Phase 4's pattern interrogation stays at the interaction-shape level (which control, which flow, how many steps) — it does not extend into color, spacing, or type, that is still design-review's job.
- Prefer one systemic remedy over N patches when issues share a root — say so explicitly.
- Every issue MUST carry a prescribed affordance; "this is confusing" without a named fix is an incomplete finding.
- Under `--report-only`, never edit files — deliver the audit and remedy spec only.
