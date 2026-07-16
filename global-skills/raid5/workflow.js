export const meta = {
  name: 'raid5',
  description: "Tom's RAID 5 protocol: shard output into atomic claims, cross-vendor adversarial verification with rotating seats, no self-grading, redundancy-budgeted.",
  phases: ['Triage', 'Verify', 'Merge'],
};

// ---- vendor normalization (SKILL.md speaks claude/gemini/none; seats speak anthropic/google/null) ----
const FAVOR_ALIASES = {
  anthropic: 'anthropic', claude: 'anthropic',
  openai: 'openai', codex: 'openai', gpt: 'openai',
  google: 'google', gemini: 'google', agy: 'google',
};
function normVendor(v, field) {
  if (v === undefined || v === null || v === 'none' || v === 'null' || v === '') return null;
  const n = FAVOR_ALIASES[String(v).toLowerCase().trim()];
  if (!n) throw new Error(`raid5: unknown ${field} value "${v}" — use anthropic|openai|google (aliases: claude, gemini, codex) or none`);
  return n;
}

// ---- args validation (args may arrive as a JSON string depending on the caller) ----
const A = typeof args === 'string' ? JSON.parse(args) : args;
if (!A || !Array.isArray(A.items) || A.items.length === 0) {
  throw new Error("raid5: A.items is required and must be a non-empty array of {claim, source?, favors?, critical?, contradicted?}");
}
if (A.mode !== 'research' && A.mode !== 'code') {
  throw new Error("raid5: A.mode must be 'research' or 'code'");
}
if (A.mode === 'code') {
  if (!A.writer) throw new Error("raid5(code): A.writer is required — the vendor that wrote the code (anthropic|openai|google); the writer is never its sole reviewer");
  for (const it of A.items) {
    if (!it.source) throw new Error(`raid5(code): every item needs source as a diff/file reference — missing on: "${it.claim}"`);
  }
}
const WRITER = A.mode === 'code' ? normVendor(A.writer, 'writer') : null;

const SEATS = [
  { seat: 'codex', vendor: 'openai' },
  { seat: 'agy', vendor: 'google' },
  { seat: 'claude', vendor: 'anthropic' },
];
const VERDICT_SCHEMA = {
  type: 'object',
  required: ['verdict', 'evidence'],
  properties: {
    verdict: { type: 'string', enum: ['confirmed', 'refuted', 'unverifiable'] },
    evidence: { type: 'string' },
  },
};
const seatLog = [];

// Input-derived offset — varies run to run with different inputs (approximating "rotate across
// sessions" without persisted state) while staying deterministic, which resume requires:
// Math.random/Date.now are unavailable in the Workflow sandbox.
const ROTATION_OFFSET = (A.items.length + (A.items[0].claim || '').length) % SEATS.length;
function pickSeat(index, favors, extraBanned = []) {
  const banned = [favors, WRITER, ...extraBanned].filter(Boolean);
  const eligible = SEATS.filter((s) => !banned.includes(s.vendor));
  if (eligible.length === 0) throw new Error('raid5: favors/writer exclusions removed every verifier seat');
  return eligible[(index + ROTATION_OFFSET) % eligible.length]; // rotate by item index, never a permanent arbiter
}

function seatModel(seat, cheap) {
  if (seat.seat === 'codex') return cheap ? 'gpt-5.6-luna (effort low)' : 'gpt-5.6-sol (effort medium)'; // Luna = vendor cheap tier (verified live); Sol only for contested judgment
  if (seat.seat === 'agy') return cheap ? 'Gemini 3.5 Flash (Low)' : 'Gemini 3.1 Pro (High)';
  return cheap ? 'haiku' : 'opus';
}

function seatInstructions(seat, cheap) {
  if (seat.seat === 'claude') return 'You are the verifier yourself: check the claim against the source with your own tools (Read/Bash/WebFetch).';
  const cmd = seat.seat === 'codex'
    ? `codex exec -m ${cheap ? 'gpt-5.6-luna' : 'gpt-5.6-sol'} -c model_reasoning_effort=${cheap ? 'low' : 'medium'} "$(cat "$PROMPT_FILE")"`
    : `agy --print "$(cat "$PROMPT_FILE")" --model "${cheap ? 'Gemini 3.5 Flash (Low)' : 'Gemini 3.1 Pro (High)'}" --print-timeout 90s`;
  return [
    "You are only the harness — the external model's judgment is the verdict, not your own opinion.",
    'First WRITE the self-contained refutation prompt (the claim, the source, and the instruction to refute it, all verbatim) to a temp file with the Write tool. NEVER paste the claim text directly into a shell command — quotes/backticks/$() inside a claim would break or inject into the shell. Then via Bash run (with PROMPT_FILE set to that temp file path):',
    `  ${cmd}`,
    seat.seat === 'codex' ? '(codex exec defaults to reasoning effort NONE — the effort flag is mandatory.)' : '',
    "Map the model's answer to the schema. If the command errors or times out, return verdict 'unverifiable' with the error text as evidence.",
  ].filter(Boolean).join('\n');
}

function verifierPrompt(item, seat, cheap) {
  const parts = [
    'RAID 5 verification. Try to REFUTE the claim below; confirm only if a genuine refutation attempt fails against the source. Primary sources outrank secondary ones.',
    `CLAIM: ${item.claim}`,
    `SOURCE: ${item.source || 'none provided — without a checkable primary source, lean unverifiable'}`,
  ];
  if (A.context) parts.push(`CONTEXT: ${A.context}`);
  if (A.mode === 'code') parts.push('RULE (code mode): tests/execution outrank any model opinion — prefer actually running the code/tests referenced by the source over reasoning about it.');
  parts.push(seatInstructions(seat, cheap));
  return parts.join('\n');
}

async function runSeat(item, cheap, extraBanned = []) {
  const seat = pickSeat(item.index, item.favors, extraBanned);
  seatLog.push({ claim: item.claim, seat: seat.seat, model: seatModel(seat, cheap) });
  const base = { index: item.index, claim: item.claim, source: item.source || null, seat: seat.seat, tier: cheap ? 'cheap' : 'flagship' };
  try {
    const res = await agent(verifierPrompt(item, seat, cheap), {
      label: `verify:${item.index}:${seat.seat}`,
      phase: 'Verify',
      schema: VERDICT_SCHEMA,
      // Known residual channel: for codex/agy seats a Haiku harness agent mediates the external
      // model's answer into the schema — prompt forbids it substituting its own opinion, but on
      // CLI failure it is the sole author of the 'unverifiable' evidence.
      model: seat.seat === 'claude' ? (cheap ? 'haiku' : 'opus') : 'haiku',
    });
    return { ...base, verdict: res.verdict, evidence: res.evidence };
  } catch (err) {
    return { ...base, verdict: 'unverifiable', evidence: `verifier seat failed: ${err && err.message}` };
  }
}

// ---- Phase 1: Triage ----
phase('Triage');
log(`Triage: ${A.items.length} claims, mode=${A.mode}${A.writer ? `, writer=${A.writer}` : ''}`);
const TRIAGE_SCHEMA = {
  type: 'object',
  required: ['tags'],
  properties: {
    tags: {
      type: 'array',
      items: {
        type: 'object',
        required: ['index', 'mechanical', 'needsVerify'],
        properties: {
          index: { type: 'integer' },
          mechanical: { type: 'boolean' },
          needsVerify: { type: 'boolean' },
          favors: { type: ['string', 'null'], enum: ['anthropic', 'openai', 'google', null] },
        },
      },
    },
  },
};
const triage = await agent(
  [
    "Apply Tom's RAID 5 redundancy budget. For each item return {index, mechanical, needsVerify, favors}.",
    'mechanical = checkable by literal lookup (quote exists, number matches source); anything needing judgment is not mechanical.',
    'needsVerify = true ONLY if the claim is self-favorable (favors is set or clearly flatters its producing vendor), OR critical === true, OR contradicted === true. Everything else is NOT verified — single-source is fine; never uniform re-verification.',
    "favors: copy the item's favors field if present; else infer (anthropic|openai|google) only when the claim clearly flatters one vendor; else null.",
    `ITEMS: ${JSON.stringify(A.items.map((it, i) => ({ index: i, ...it })))}`,
  ].join('\n'),
  { label: 'triage', phase: 'Triage', schema: TRIAGE_SCHEMA, model: 'haiku' }
);
const tagByIndex = {};
for (const t of (triage && triage.tags) || []) tagByIndex[t.index] = t;
const tagged = A.items.map((it, i) => {
  const t = tagByIndex[i] || { mechanical: false, needsVerify: true, favors: null };
  const callerFavors = normVendor(it.favors, 'favors'); // explicit caller input outranks triage output in a bias control
  const favors = callerFavors !== null ? callerFavors : normVendor(t.favors, 'favors (triage)');
  return {
    ...it,
    index: i,
    mechanical: !!t.mechanical,
    // critical/contradicted force verification in code — a triage mistake can never downgrade them
    needsVerify: !!t.needsVerify || !!it.critical || !!it.contradicted,
    favors,
  };
});

// ---- Phase 2: Verify ----
phase('Verify');
const full = tagged.filter((t) => t.needsVerify);
const budgetSkipped = tagged.filter((t) => !t.needsVerify);
log(`Verify: ${full.length} budgeted for verification (flagship if contested, cheap if mechanical); ${budgetSkipped.length} skipped by redundancy budget (single-source ok)`);
const fullResults = (await pipeline(full, (item) => runSeat(item, item.mechanical))).filter(Boolean);

// ---- Phase 3: Merge ----
phase('Merge');
const verified = [];
const refuted = [];
const contested = [];
const skipped = [];
for (const r of fullResults) {
  if (r.verdict === 'confirmed') { verified.push(r); continue; }
  if (r.verdict !== 'refuted') { skipped.push({ ...r, note: 'unverifiable' }); continue; }
  // Rule 4: never silently accept a lone refutation — escalate to a different-vendor tiebreaker.
  const item = full.find((it) => it.index === r.index);
  const firstVendor = (SEATS.find((s) => s.seat === r.seat) || {}).vendor;
  let tie = null;
  try {
    tie = await runSeat(item, false, [firstVendor]);
  } catch (err) {
    tie = null; // exclusions left no eligible third seat
  }
  if (!tie) refuted.push({ ...r, note: 'refuted; no eligible third seat for tiebreak' });
  else if (tie.verdict === 'refuted') refuted.push({ ...r, note: `refuted; tiebreaker ${tie.seat} concurs`, tiebreak: tie });
  else if (tie.verdict === 'confirmed') contested.push({ ...r, note: `conflict: ${r.seat} refuted vs ${tie.seat} confirmed — both reported, not silently resolved`, tiebreak: tie });
  else refuted.push({ ...r, note: `refuted; tiebreaker ${tie.seat} unverifiable`, tiebreak: tie });
}
for (const it of budgetSkipped) {
  skipped.push({ index: it.index, claim: it.claim, source: it.source || null, verdict: 'not-verified', note: 'redundancy budget: single-source, not verified' });
}
log(`Merge: ${verified.length} verified, ${refuted.length} refuted, ${contested.length} contested, ${skipped.length} skipped — seatLog has ${seatLog.length} entries`);
// Top-level return: the Workflow loader wraps this body in an async function, so `return`
// (not `export default`) is how results reach the caller. node --check rejects it — that's
// expected; this file is loaded by the Workflow tool, never by node.
return { verified, refuted, contested, skipped, seatLog };
