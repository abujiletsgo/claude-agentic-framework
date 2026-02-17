# Caddy Classifier — Integration Guide

## What Caddy Does

Caddy is the request classification system. It runs on every `UserPromptSubmit` event and analyzes the user's prompt to:

1. Classify the task on 4 dimensions (complexity, task type, quality need, codebase scope)
2. Recommend an execution strategy (direct, orchestrate, rlm, fusion, research, brainstorm)
3. Detect relevant skills and suggest them
4. Run a security audit on any detected skills before recommending them

Caddy **never blocks** — it always exits 0. It only injects advisory context into the session.

## Current Architecture

Two scripts, two hooks, both on `UserPromptSubmit`:

```
UserPromptSubmit
    │
    ├─ analyze_request.py  (timeout: 10s)
    │     ─ Keyword classification (instant)
    │     ─ Haiku semantic fallback (when keyword confidence < 0.65)
    │     ─ Skill detection + security audit
    │     ─ Outputs: [Caddy] advisory lines injected into context
    │
    └─ auto_delegate.py    (timeout: 3s)
          ─ Reads classification from analyze_request output
          ─ Injects strategy recommendation
```

### analyze_request.py

The main classifier. All classification logic lives here.

**Input**: `{"prompt": "...", "session_id": "..."}` (stdin)

**Output**:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "[Caddy] Task classified as: complex implement ...\n[Caddy] Recommended strategy: orchestrate ..."
  }
}
```

#### 4 Classification Dimensions

| Dimension | Keyword Signals | Values |
|-----------|-----------------|--------|
| complexity | fix typo, rename → simple; add feature → moderate; authentication, redesign → complex; entire codebase → massive | simple / moderate / complex / massive |
| task_type | build, create → implement; fix, bug → fix; refactor → refactor; how does, explain → research; test, coverage → test; review, audit → review; document → document; deploy → deploy; plan, design → plan | implement / fix / refactor / research / test / review / document / deploy / plan |
| quality | security, auth, payment, critical → critical; important, thorough → high; (default) | standard / high / critical |
| scope | this file → focused; these files, module → moderate; entire codebase → broad; how does, explore → unknown | focused / moderate / broad / unknown |

#### Hybrid Keyword + Haiku Classification

1. Keyword matching runs first (zero latency, no API call)
2. A confidence score is computed:
   - Base: 0.5
   - +0.1 if task_type is not `implement` (clearer signal)
   - +up to 0.2 based on skill match strength
   - -0.2 for very short prompts (< 20 chars)
   - +0.1 for long prompts (> 200 chars)
   - +0.15 for `simple` complexity
   - -0.15 for `critical` quality
3. If confidence < `haiku_fallback_threshold` (default: 0.65), call Haiku
4. Haiku receives a structured system prompt, returns JSON classification
5. Haiku's self-reported confidence replaces the keyword confidence

#### Strategy Routing

```
Auto-RLM triggers (highest priority):
  unknown scope + research task type → rlm
  broad scope + (review | research | audit) → rlm
  massive complexity → rlm
  broad scope + (moderate | complex) → rlm

Standard strategy map:
  simple  + standard/high → direct
  simple  + critical      → fusion
  moderate/complex + standard/high → orchestrate
  moderate/complex + critical      → fusion
  research task (focused scope)    → research
  plan task                        → brainstorm
```

#### Skill Security Audit

When Caddy detects relevant skills, it scans them with `skill_auditor.py`:
- Critical findings → skill is blocked (not recommended)
- Warning findings → skill recommended with warning annotation
- Clean → recommended normally

Skills dirs scanned: `global-skills/` and `~/.claude/skills/`.

### auto_delegate.py

Lightweight hook that reads the classification output and injects a human-readable delegation suggestion. Runs in 3s timeout with no external calls.

## Configuration

Copy `data/caddy_config.yaml` to `~/.claude/caddy_config.yaml`, or it auto-creates defaults:

```yaml
caddy:
  enabled: true
  auto_invoke_threshold: 0.8     # Confidence threshold to show suggestions
  always_suggest: true           # Bypass threshold; always show (recommended: true)
  background_monitoring: true    # Reserved for future use
  haiku_fallback_threshold: 0.65 # Below this, use Haiku for classification
```

## Logs

```bash
cat ~/.claude/logs/caddy/analyses.jsonl | python3 -m json.tool | head -40
```

Each line is a full classification result for one prompt.

## Extending Classification

To add new keywords to any dimension, edit the signal dictionaries at the top of `analyze_request.py`:

- `COMPLEXITY_SIGNALS` — maps complexity level to keyword list
- `TASK_TYPE_SIGNALS` — maps task type to keyword list
- `QUALITY_SIGNALS` — maps quality level to keyword list
- `SCOPE_SIGNALS` — maps scope level to keyword list
- `STRATEGY_MAP` — maps (complexity, quality) → strategy

To add a new skill for detection, add an entry to `SKILL_PATTERNS`:

```python
"my-new-skill": {
    "keywords": ["deploy", "kubernetes", "helm", "k8s"],
    "description": "Kubernetes deployment automation",
},
```

## Testing

Test classify behavior with simulated stdin:

```bash
# Test analyze_request
echo '{"prompt": "Add authentication to the API", "session_id": "test"}' | \
  uv run global-hooks/framework/caddy/analyze_request.py

# Test with a simple task (should classify as direct strategy)
echo '{"prompt": "fix typo in README", "session_id": "test"}' | \
  uv run global-hooks/framework/caddy/analyze_request.py

# Test with a massive task (should classify as rlm strategy)
echo '{"prompt": "refactor the entire codebase", "session_id": "test"}' | \
  uv run global-hooks/framework/caddy/analyze_request.py
```
