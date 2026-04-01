#!/usr/bin/env python3
"""
Epistemic Guard - UserPromptSubmit Hook
========================================

Detects when the user is asking for analysis, interpretation, or evaluation
of data/results, and injects a reminder to separate observations from
inferences and speculation.

This prevents Claude from constructing confident-sounding narratives that
go beyond what the data actually shows, without flagging the leap.

Trigger: UserPromptSubmit
Exit: Always 0 (never blocks)
Output: additionalContext with epistemic discipline reminder
"""

import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# Prompts that involve interpretation, analysis, or evaluation of data/results
ANALYSIS_PATTERNS = [
    # Data analysis
    r"\b(?:analyz|analyse|interpret|evaluat|assess)\b",
    r"\b(?:what does .* (?:mean|show|tell|indicate|suggest|imply))",
    r"\b(?:why (?:is|are|did|does|do|was|were))\b",
    r"\b(?:explain|understand|make sense of)\b.*\b(?:data|results?|numbers?|output|findings?|pattern)\b",
    # Performance/metrics
    r"\b(?:performance|accuracy|results?|metrics?|statistics?|returns?|p&l|pnl|sharpe|drawdown)\b",
    r"\b(?:backtest|forward test|live results?|track record)\b",
    r"\b(?:alpha|beta|signal|edge|predictive|forecast)\b",
    # Causation/correlation
    r"\b(?:caus|correlat|driv|contribut|factor|reason|because)\b.*\b(?:why|how|what)\b",
    r"\b(?:what (?:caused|drove|explains?))\b",
    # Comparison/ranking
    r"\b(?:better|worse|best|worst|outperform|underperform|compar)\b",
    r"\b(?:which (?:is|are|was|were) (?:better|best|more))\b",
    # Narrative construction
    r"\b(?:story|narrative|thesis|theory|hypothesis|conclusion)\b",
    r"\b(?:what(?:'s| is) (?:going on|happening)|what do you (?:think|make of))\b",
    # Quantitative claims
    r"\b\d+(?:\.\d+)?%\b",  # Percentage in prompt suggests data discussion
    r"\b(?:significant|meaningful|negligible|marginal)\b",
]

# Prompts that are clearly NOT analysis (skip injection to save context)
SKIP_PATTERNS = [
    r"^/",                          # Slash commands
    r"^\s*(?:yes|no|ok|sure|go|y|n|continue|proceed|do it|lgtm|done|next)\s*$",
    r"^\s*(?:fix|create|write|edit|delete|add|remove|install|run|build|deploy)\b",
]

# Compiled for performance
_analysis_res = [re.compile(p, re.IGNORECASE) for p in ANALYSIS_PATTERNS]
_skip_res = [re.compile(p, re.IGNORECASE) for p in SKIP_PATTERNS]


def is_analysis_request(prompt: str) -> bool:
    """Return True if the prompt involves analysis/interpretation of data."""
    stripped = prompt.strip()

    # Short prompts or skip patterns
    if len(stripped) < 20:
        return False
    for pat in _skip_res:
        if pat.search(stripped):
            return False

    # Check for analysis patterns - need at least 2 matches for confidence
    matches = sum(1 for pat in _analysis_res if pat.search(stripped))
    return matches >= 2


# ---------------------------------------------------------------------------
# Reminder messages
# ---------------------------------------------------------------------------

EPISTEMIC_REMINDER = """\
[Epistemic Guard] This prompt involves data analysis or interpretation.
MANDATORY: Structure your response to separate:
  - OBSERVED: What the data/evidence directly shows (cite sources)
  - INFERRED: Your conclusions drawn from observations (flag as inference, state reasoning)
  - UNCERTAIN: What the data does NOT clearly show (gaps, alternative explanations)
Do NOT construct confident narratives without flagging which parts are inference vs. observation.
If reversing a prior position, acknowledge the reversal explicitly."""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        # CAF_MODE check
        _framework_dir = Path(__file__).parent.parent
        if str(_framework_dir) not in sys.path:
            sys.path.insert(0, str(_framework_dir))
        try:
            from caf_mode import should_run
            if not should_run("epistemic_guard"):
                sys.exit(0)
        except ImportError:
            pass

        input_data = json.load(sys.stdin)
        prompt = input_data.get("prompt", "")

        if not prompt or not prompt.strip():
            sys.exit(0)

        if is_analysis_request(prompt):
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": EPISTEMIC_REMINDER,
                }
            }
            print(json.dumps(output))

        sys.exit(0)

    except Exception:
        # Never block
        sys.exit(0)


if __name__ == "__main__":
    main()
