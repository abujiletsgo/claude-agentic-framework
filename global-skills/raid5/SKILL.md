---
name: raid5
description: "RAID 5 multi-model verification protocol — shard output into atomic claims, cross-verify with a non-authoring vendor, rotate the verifier seat. Triggers: 'raid 5', 'raid5', 'cross-model verify', 'multi-model review', 'rotate verifier'. Use for high-stakes claims, plans about to be committed to, large refactors, research synthesis. NOT for routine low-stakes facts or mechanical edits — the redundancy budget rule below says most claims should NOT be verified."
user-invocable: true
---

# /raid5 — Cross-Model Verification

Mapping: "disks" = the three vendors (Claude / Codex / Gemini). "Blocks" = atomic, falsifiable claims — not whole topics. "Parity" = a cheap independent verification pass, not a full re-research. "Distributed parity" = the verifier seat rotates so no model becomes the permanent, unchecked arbiter.

## When to Use
- High-stakes factual claims (benchmarks, pricing, capability claims driving decisions)
- Plans you are about to commit to (architecture, spend, migrations)
- Large refactors / security-critical or money/auth/data-integrity code
- Research synthesis before it gets filed as ground truth

## Protocol Rules
1. **Shard first.** Split into atomic falsifiable claims before dispatching. Small claims make bias visible; broad topics let it hide in synthesis. For code: shard into files/functions/PRs — diffs are naturally atomic.
2. **No self-grading.** A claim favorable to Vendor X must be verified by a non-X model. The model that wrote code is never its sole reviewer.
3. **Redundancy budget** (see below) — never uniform triple-redundancy.
4. **Discrepancy handling.** Primary vs verifier disagreement → escalate to the third model as tiebreaker, or report both with the conflict stated. Never silently pick one. Builder-vs-reviewer code disagreements escalate to a third model or Tom.
5. **Rotate the verifier seat** across shards/sessions — a fixed checker just moves the trust bottleneck. (Workflow mechanism: per-item rotation plus a random per-run seat offset; no state persists across sessions.)
6. **Primary-source allowlist** applies to all three legs equally (SEO content-farm rot isn't model-specific).
7. **Execution beats opinion.** Tests passing / code running is harder ground truth than any model's read — check this FIRST before spending a second model's review pass on anything execution could catch.
8. **Cost tiers.** Mechanical checks (quote exists, number matches source) use each vendor's cheap tier (Haiku / Luna / Gemini 3.5 Flash); flagships only for contested judgment.

## Redundancy Budget — what NOT to verify
Always verify: claims self-favorable to their source; claims driving real spend/architecture decisions; anything that already contradicted itself once (permanently "hot" after that); security/auth/money/data-integrity code paths.
Single-source is fine for: neutral, low-stakes, easily-official facts; boilerplate/mechanical code; anything a test already proves.
Full triple-redundancy = RAID 1 = the "search the same thing three times" waste this protocol exists to avoid.

Known limit: this fixes evidentiary bias, not framing bias (which shards get asked). Decorrelate by occasionally having a different model propose the shard list. Composition: routing.md decides WHO BUILDS; RAID 5 decides WHO CHECKS.

## How to Run (workflow — 3+ claims)
Invoke the Workflow tool:
- `scriptPath`: `/Users/tomkwon/.claude/skills/raid5/workflow.js`
- `args`:
  ```json
  {
    "mode": "research" | "code",
    "writer": "anthropic|openai|google — REQUIRED in code mode: the vendor that wrote the code; its seat is excluded so the writer is never its sole reviewer",
    "items": [{ "claim": "...", "source": "optional origin/vendor (required diff/file ref in code mode)", "favors": "anthropic|openai|google|null", "critical": true, "contradicted": true }],
    "context": "one-paragraph background for the verifiers"
  }
  ```
`favors` drives the no-self-grading assignment (canonical values are vendor names `anthropic|openai|google|null`; the aliases `claude`/`gemini`/`codex`/`none` are accepted and normalized). `critical: true` forces verification regardless of budget (enforced in code, not just triage). `contradicted: true` marks a claim that already contradicted itself once — permanently hot, always verified.

## Lightweight Path (1–2 claims, no workflow)
Call the other vendors' CLIs directly:
- Codex: `codex exec -c model_reasoning_effort=medium "Verify: <claim>. Cite a primary source. Answer CONFIRMED/REFUTED/UNCERTAIN + evidence."` (effort flag is mandatory — `codex exec` defaults to reasoning effort NONE)
- Gemini: `agy --print "Verify: <claim> ..." --model "Gemini 3.1 Pro (Low)" --print-timeout 90s` (cheap: `"Gemini 3.5 Flash (Medium)"`)
- Claude-favorable claims → verify with codex or agy, never Claude. Pick the verifier per routing.md; rotate from whoever verified last.
