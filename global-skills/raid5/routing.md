# Model Routing Table (corrected, verified live 2026-07-17)

Stack: Claude subscription (Claude Code, direct) + ChatGPT subscription (Codex CLI 0.144.5, default gpt-5.6-sol) + Antigravity FREE tier (agy CLI 1.1.3).
Source: `/Users/tomkwon/My Drive/Obsidian/08 - Learning/multi-model-ai-harness-master-structure-2026-07-16.md`

## Hard constraints
- **NEVER route Claude via agy** — it serves stale Claude 4.6 and bills a separate Anthropic API key. Claude always direct via Claude Code (Fable 5 / Opus 4.8 / Sonnet 5 / Haiku 4.5).
- **agy free tier serves exactly:** "Gemini 3.5 Flash (Low|Medium|High)", "Gemini 3.1 Pro (Low|High)", "GPT-OSS 120B (Medium)" — names passed verbatim to `--model`. NO Deep Think, NO Deep Research (Gemini-app/Ultra features; any route citing them is unexecutable). gemini CLI is dead for this tier (IneligibleTierError since 2026-06-18).
- **`codex exec` defaults to reasoning effort NONE** — always pass effort explicitly (e.g. `-c model_reasoning_effort=medium`). Sol also mis-self-reports as "GPT-5 Codex".

## Routing

| Task | Primary | Fallback | Note |
|---|---|---|---|
| Orchestrator / conductor | Opus 4.8 (Fable 5 for hardest decomposition) | Fable 5, architecture calls only (cost) | Harness lives in Claude Code (subagents, hooks, MCP, shell to other CLIs). Near-Fable judgment at 2x lower cost. Stays put regardless of quota. |
| Hard coding / deep refactors | Fable 5 | Sol second independent impl for mission-critical | SWE-bench Pro lead 80.0% (80.3% is Mythos 5). All SWE-bench Pro numbers vendor-reported; Scale AI's independent board runs 15–30 pts lower, excludes these models. |
| Long-horizon / multi-hour agent coding | Sol via Codex CLI (effort flag explicit) | Fable 5 | Sol is the Terminal-Bench leader (verified live 2026-07-17) and built for long-horizon/compaction. METR's benchmark-gaming flag stands as a caution: verify outputs, don't lean on margins. |
| Everyday building / default driver | Sonnet 5 | Terra for cheap parallel first pass/review | 63.2% SWE-bench Pro (vendor-reported), near-Opus at Sonnet cost. |
| Scoped implementation / first-pass review | GPT-5.6 Terra | Haiku 4.5 | ~2x cheaper than Sol, competitive — second pair of hands. |
| Scientific / math / PhD-level reasoning | Gemini 3.1 Pro (High) via agy | Fable 5 (strong adversarial check) | Deep Think pick unexecutable on free agy; Deep Think numbers (HLE 41%, GPQA 93.8%, ARC-AGI-2 45.1%) belong to Deep Think only. |
| Huge-context ingestion | Gemini 3.1 Pro via agy | Fable 5 (1M ctx) | "2M vs 1M" edge corrected twice: standard Gemini tier is 1M (2M = enterprise/Vertex), matching Fable; 2M route UNVERIFIED on free agy. Cheaper for ingestion, worse once coding. |
| Complex planning / architecture / API / schema | Fable 5 + Sol (independent second plan) | Gemini 3.1 Pro (High) third opinion on high-stakes | Panel/critic pattern — differently-trained brain catches Claude blind spots. |
| Routing / classification / extraction / high-volume | Haiku 4.5 | Luna or Gemini 3.5 Flash via agy | Cheap ($1/$5 per M). 3.5 Flash is Google's free-tier default and per Google beats 3.1 Pro on coding/agentic. |
| Debugging — unfamiliar/large codebase | Fable 5 | — | Context-bottlenecked → understanding → Fable. |
| Debugging — flaky CI/env, iterate-until-green | Sol via Codex CLI | Fable 5 | Execution-loop-bottlenecked. Effort flag explicit. |
| Refactoring — large multi-file, one sitting | Fable 5 | — | Context-bottlenecked. |
| Refactoring — multi-day migration, build/test cycles | Sol (compaction stays coherent for hours) | Fable 5 | Sol's long-horizon/compaction lead consistent with its Terminal-Bench leadership (verified live 2026-07-17). |
| New feature (greenfield) | Sonnet 5 | Opus/Fable if architecture-heavy | Daily driver. |
| Frontend / UI / CSS | Claude (Sonnet → Opus/Fable) | Gemini for Grid/Flexbox; GPT for CSS-in-JS | WebDev Arena corrected: no outright Claude lead — #1 sol-xhigh 1631 vs #2 fable-5 1630 (tied); Opus #4. |
| Code review / PR review | Opus/Fable | codex review cross-check, high-stakes PRs | Caught IDOR, stale-closure, webhook-signature bugs others missed. RAID 5: writer never sole reviewer. |
| Security / vulnerability review | Claude + second-lab cross-check | — | Best LLM reviewers still miss ~40% of real vulns on adversarial CVE benchmarks — pair with static analysis, never single-model gate. |
| Test writing / TDD scaffolding | Sonnet 5 / Terra | — | Mechanical — no Tier-S budget here. |
| Docs, changelogs, commits, PR descriptions | Haiku 4.5 / Luna / Gemini 3.5 Flash via agy | — | Pure cost play. |
| Multimodal — screenshots, mockups, general | whichever model is active | — | MMMU-Pro saturated (80%+ all frontier); leaderboard stale since Sept 2025 — no independent ground truth. |
| Multimodal — video/audio | Gemini | — | Clear leader. |
| Multimodal — charts, code-with-vision | GPT | — | Clear leader. |
| Multimodal — long-document OCR | Claude | — | Clear leader. |
| DevOps / infra-as-code, CI/CD | bottleneck rule | — | Pipeline reruns → Sol; sprawling infra-repo comprehension → Fable. |
| Meta: designing the subagents/harness | Opus/Fable | — | Conductor job — stays put regardless of quota. |

## Quota-fallback tier chains (swap WITHIN a row only, never across tiers)
- **Tier S** (hardest): Fable 5 ↔ Sol (max reasoning, effort flag explicit) ↔ Gemini 3.1 Pro (High) [Deep Think leg unexecutable on free agy]
- **Tier A** (daily): Sonnet 5 ↔ Terra ↔ Gemini 3.1 Pro
- **Tier C** (cheap): Haiku 4.5 ↔ Luna ↔ Gemini 3.5 Flash (Google's default)

Opus↔Codex swap matters because Claude Max's weekly cap is a SHARED all-models pool (plus a Sonnet-only sub-limit) — diverting Opus calls to Sol protects the whole account's budget including Sonnet.

**Mechanism: reactive circuit breaker, not predictive tracking.** No vendor exposes a stable usage API for consumer plans and ceilings move (Claude doubled 5-hr caps 2026-05-06; OpenAI lifted its window 2026-07-12; Google went opaque). Catch 429/quota at runtime → fail over to next in chain → log. Codex `/status` is parseable mid-session as a cheap proactive nudge layered on top, not a replacement.

**Continuity rule:** swap at task/session boundaries only — Claude Code context/hooks/MCP state doesn't transfer; mid-loop swaps cost more in lost continuity than saved quota.

**Free byproduct:** log every fallback event — weeks of data show which vendor's headroom is actually starving, the real renewal signal.
