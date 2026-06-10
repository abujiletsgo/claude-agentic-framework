# Overnight Audit Notes — 2026-06-11

Branch: `overnight-audit-2026-06-11`. First commit (`9f78ee5e`) is a snapshot of
Tom's pre-existing uncommitted WIP, kept separate from all audit work. To get the
WIP back into a dirty working tree on another branch: `git cherry-pick -n 9f78ee5e`.

Format: one finding per entry. Status: FIXED (commit) / FLAGGED (needs Tom) /
REJECTED (reviewer claim that did not verify) / NOTE.

---

## Fixed

**F1 — pytest could not collect anything (9823b3f2).**
`guardrails/config_loader.py` called `sys.exit(1)` at import time when
pyyaml/pydantic were missing; the test venv had neither. Now raises ImportError;
pyyaml+pydantic added to the dev extra. Baseline after fix: 145 passed / 53 failed.

**F2 — Rust damage-control enforced only a fraction of its patterns (35aa8bce). SECURITY.**
The hand-rolled YAML parser treated a blank line as a top-level header and reset
the section to None — everything after the first blank line in a section was
dropped. Separately, two lookahead regexes ((?!\w) glob guard, tee (?!.*-a))
fail to compile in the regex crate and were silently skipped. Observed before
fix: `cat secrets.env`, `mkfs.ext4`, `shred` all ALLOWED by the Rust binary
while Python blocked them. After fix: Python and Rust agree (battery of 9
commands verified). Regression tests added.

**F3 — epistemic_guard stems never matched (35aa8bce).**
`\b(?:analyz|evaluat|compar...)\b` cannot match "analyze" — `\b` after a stem
needs a non-word char. Fixed in BOTH mirrors (Python + Rust) with `\w*`.
Verified live against the rebuilt release binary.

**F4 — session_cost_tracker.rs cost formula precedence (491d7bb7).**
`(input + output * 1e6).round() / 1e6` — every recorded cost was wrong
(≈ output_cost + input_cost/1e6). Fixed parenthesization; 3 unit tests added.

**F5 — Five Python hook bugs (5229cc01).**
activity_logger globbed summary files by session-id prefix but filenames are
md5 hashes (tasks were never found); auto_dependency_audit counted ALL packages
as vulnerabilities; auto_review_team exited 1 on malformed stdin (only hook
violating fail-open); hook_health_monitor wrote its tmp file twice;
circuit_breaker_wrapper crashed before its fail-open guard could run when CB
deps were missing (verified fix by forcing ImportError); session_startup listed
nonexistent spawn_hud.py.

**F6 — run-explorer: eight bugs (dfd99174).**
Timestamps ×1000 (dates in 2076); CAF_SESSIONS_DIR override ignored; cost card
rendered $NaN (snake_case wire vs camelCase client); run/lead status inversion
(done → IN_PROGRESS instead of PASS); missing-session stub instead of 404;
unused SESSIONS_DIR; getCostProjection ignored its days arg; WS URL double-slash.
Both typechecks clean.

**F7 — scripts/bin (9021899a).**
orch-shared task-line parser latched found_heading forever (empty Task section
captured the next section's content); audit_local_skill.py imported from a
hardcoded ~/Documents/claude-agentic-framework path; model-tiers.sh always
printed a false FAIL for a skill that doesn't exist in this fork; justfile dead
recipes for the deleted observability server/client + python3→uv run.

**F8 — test suite repaired to green (6f73afac).**
53 failures → 0. Most were test bugs: wrong orch dir (no CAF_ORCH_DIR
injection), fixture headers not matching fact_manager's real section headers,
flat fixture messages vs real transcript shape, stale binary path
(caf-hooks/target/ = April build; workspace builds to target/), entry-point
probing that called the wrong function and swallowed the TypeError,
sample_transcripts.json claiming "3 completed tasks" while containing zero
TaskUpdate blocks. cmux tests now skip as a module (file flagged for deletion,
not deleted). Production fixes that came out of it: caddy STRATEGY_MAP routed
moderate work to the removed "team" strategy (ground truth: moderate→direct);
investigation keywords added to the complex tier.

**F9 — install/config consistency (8359ce6e).**
model_tiers.yaml comment (18→15 Sonnet); caddy_config.yaml stale
brainstorm/tmux_sprint/sprint entries; install.sh dead GSTACK_COUNT (impossible
find pattern) + missing caddy_config.yaml symlink the file's own header
prescribes; uninstall.sh now removes orch-shared/lib/caddy symlinks and no
longer references a backups/ dir that install.sh never creates.

## Flagged for Tom (recommendation included; nothing executed)

**FL1 — Quoted-string false positives in damage-control (the 2 xfail tests).**
`git commit -m "fix: handle rm -rf edge case"` is blocked because bash patterns
match the RAW command. The tests expect quote-stripping, but stripping lets a
quoted command name (`"rm" -rf /`) evade the guard, and the code comment says
raw-checking is deliberate. Recommendation: strip quotes for pattern matching
but ALSO check that the unquoted残 command still contains an executable token —
or accept the false positives as the price of safety. Owner call; both mirrors
must change together (Python + Rust).

**FL2 — dashboard/ directory is dead.**
shared_validator.py crashes on import (deleted cmux_client), notifies via
deleted bin/cmux-sprint, and polls /tmp/caf_orch while orch-shared writes to
~/.caf/orch. sprint_report.py and activity_report.py have the same stale
ORCH_BASE and the same found_heading latch bug. Nothing live references them
(only .claude docs and the removed dashboard-lead agent). Recommendation:
delete dashboard/ (run-explorer is the dashboard). Not deleted per standing
deletion-confirmation rule.

**FL3 — Circuit breaker in caf-hooks is inert.**
`record_success`/`record_failure` are never called from main.rs dispatch, so
Rust-side circuits never open and `total_failures` is always 0. The Python
wrapper path works. Recommendation: either wire record_* into the --cb dispatch
or delete the Rust CB module as dead code. Architectural — not touched.

**FL4 — subagent_tracker false-positive path.**
It expects builder output at /tmp/caf_builder_N.md, but orchestrate writes
~/.caf/orch/<id>/results/builder-<name>.md and agent names are descriptive
(regex `(builder|validator|debugger)-(\d+)` rarely matches). Latent, not firing
today. Recommendation: drop the output_file_missing check or align the path.

**FL5 — tests/test_cmux_integration.py and tests/audit/modules/test_cmux_client.py.**
Both test the removed cmux system; now skipped at module level. Recommendation:
delete both files, plus the lead_memory/cmux_client entries in
tests/audit/run_audit.py MODULES (lead_memory_writer.py no longer exists either).

**FL6 — orchestrator-reference.md sits in global-agents/.**
install.sh symlinks every *.md there as an agent, so a non-agent reference doc
registers as an invocable agent name. Recommendation: move to docs/.

**FL7 — gstack `health` sub-skill silently shadowed.**
global-skills/health/ wins the `health` name; the gstack sub-skill is never
linked, with no warning. Recommendation: warn during install or rename.

**FL8 — stale build artifact caf-hooks/target/.**
Pre-workspace leftover holding an April binary; the workspace builds to
<repo>/target/. It made test_rust_hooks run months-old code (fixed by pointing
the test at the right path). Recommendation: `rm -rf caf-hooks/target`.

**FL9 — remaining "team" path in caddy.**
select_strategy still has a `return "team"` branch for simple+parallel-ops
prompts (analyze_request.py:438) and docstrings still describe the team tier.
Ground truth never expects "team". Recommendation: decide whether "team" should
exist as a strategy at all; if not, route that branch to direct/orchestrate.

## Rejected reviewer claims (verified false)

- voice_done.rs "session name discarded" — that is Tom's deliberate WIP change
  (commented rationale in the diff).
- damage_control.rs starts_with trailing-slash "bypass" — `"/x/.ssh/id_rsa"
  .starts_with("/x/.ssh/")` is true; the suggested change would ADD a false
  positive (`/x/.sshfoo`).
- heredoc regex `\A` "bypass" — the `\n` alternation covers every real case;
  `\A` branch is dead but harmless.
- hook_health_monitor "auto-reset writes dropped" — the empty-state path cannot
  be reached (main exits earlier when state is empty); only a theoretical race.
- doctor "fires on 1st event instead of 10th" — it fires every 10 events with
  phase 0; not a bug.
- CLAUDE.md "46 hooks" off-by-one — structured count of the template is exactly
  46; the 47th "type":"command" is the statusLine.
- wave-0a/0b regex conflation in run-explorer — broadcasters only emit numeric
  wave labels; fixture/comment mentions are not real data.
- auto_memory_writer byte-slice panic on non-ASCII session ids — session ids
  are hex UUIDs; boundary cannot occur.

## Notes / dead ends

- prune_stale (facts) only ages out the STALE section by design; tests that
  expected CONFIRMED facts to expire were corrected to match the system.
- The events.db kept in apps/observability/server/ is live data for
  run-explorer; the justfile db-clean-wal/db-reset recipes were kept.
- cargo build still emits dead-code warnings tied to FL3 (is_open, output_str,
  is_error, record_*) — left in place pending the FL3 decision.

## Test status (end of audit)

- `uv run --extra dev pytest tests/` → 173 passed, 73 skipped, 2 xfailed, 0 failed.
- `cargo test` (caf-hooks) → 6 passed, 0 failed.
- run-explorer: `tsc --noEmit` and `vue-tsc --noEmit` both clean.
- Release binary rebuilt; damage-control battery: 6 destructive commands
  blocked, 3 benign allowed.
