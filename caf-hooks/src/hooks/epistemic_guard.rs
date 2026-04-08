/// Epistemic Guard — UserPromptSubmit hook.
///
/// Python equivalent: global-hooks/framework/guardrails/epistemic_guard.py (138 LOC)
///
/// Behavior:
/// - Detect if the user prompt involves data analysis or interpretation
/// - Requires at least 2 matching analysis patterns (same as Python)
/// - Skip patterns (slash commands, simple one-word responses) bypass the check
/// - If triggered, inject epistemic discipline reminder
/// - Always exits 0
use regex::Regex;
use std::sync::OnceLock;

use crate::io::{read_stdin_value, write_output};
use crate::types::HookOutput;

const EPISTEMIC_REMINDER: &str = "\
[Epistemic Guard] This prompt involves data analysis or interpretation.
MANDATORY: Structure your response to separate:
  - OBSERVED: What the data/evidence directly shows (cite sources)
  - INFERRED: Your conclusions drawn from observations (flag as inference, state reasoning)
  - UNCERTAIN: What the data does NOT clearly show (gaps, alternative explanations)
Do NOT construct confident narratives without flagging which parts are inference vs. observation.
If reversing a prior position, acknowledge the reversal explicitly.";

// Analysis patterns — mirrors Python ANALYSIS_PATTERNS list
static ANALYSIS_PATTERNS_STR: &[&str] = &[
    r"(?i)\b(?:analyz|analyse|interpret|evaluat|assess)\b",
    r"(?i)\b(?:what does .* (?:mean|show|tell|indicate|suggest|imply))",
    r"(?i)\b(?:why (?:is|are|did|does|do|was|were))\b",
    r"(?i)\b(?:explain|understand|make sense of)\b.*\b(?:data|results?|numbers?|output|findings?|pattern)\b",
    r"(?i)\b(?:performance|accuracy|results?|metrics?|statistics?|returns?|p&l|pnl|sharpe|drawdown)\b",
    r"(?i)\b(?:backtest|forward test|live results?|track record)\b",
    r"(?i)\b(?:alpha|beta|signal|edge|predictive|forecast)\b",
    r"(?i)\b(?:caus|correlat|driv|contribut|factor|reason|because)\b.*\b(?:why|how|what)\b",
    r"(?i)\b(?:what (?:caused|drove|explains?))\b",
    r"(?i)\b(?:better|worse|best|worst|outperform|underperform|compar)\b",
    r"(?i)\b(?:which (?:is|are|was|were) (?:better|best|more))\b",
    r"(?i)\b(?:story|narrative|thesis|theory|hypothesis|conclusion)\b",
    r"(?i)\b(?:what(?:'s| is) (?:going on|happening)|what do you (?:think|make of))\b",
    r"(?i)\b\d+(?:\.\d+)?%\b",
    r"(?i)\b(?:significant|meaningful|negligible|marginal)\b",
];

// Action verbs that indicate simple imperative prompts — if prompt starts with one of these
// AND is under 80 chars, skip epistemic injection entirely.
static ACTION_VERBS: &[&str] = &[
    "fix", "add", "create", "update", "delete", "remove", "rename", "move", "install",
    "upgrade", "run", "execute", "build", "test", "deploy", "push", "pull", "merge",
    "revert", "undo",
];

// Skip patterns — mirrors Python SKIP_PATTERNS list
static SKIP_PATTERNS_STR: &[&str] = &[
    r"^/",
    r"(?i)^\s*(?:yes|no|ok|sure|go|y|n|continue|proceed|do it|lgtm|done|next)\s*$",
    r"(?i)^\s*(?:fix|create|write|edit|delete|add|remove|install|run|build|deploy)\b",
];

static ANALYSIS_PATTERNS: OnceLock<Vec<Regex>> = OnceLock::new();
static SKIP_PATTERNS: OnceLock<Vec<Regex>> = OnceLock::new();

fn analysis_patterns() -> &'static Vec<Regex> {
    ANALYSIS_PATTERNS.get_or_init(|| {
        ANALYSIS_PATTERNS_STR
            .iter()
            .filter_map(|p| Regex::new(p).ok())
            .collect()
    })
}

fn skip_patterns() -> &'static Vec<Regex> {
    SKIP_PATTERNS.get_or_init(|| {
        SKIP_PATTERNS_STR
            .iter()
            .filter_map(|p| Regex::new(p).ok())
            .collect()
    })
}

fn is_analysis_request(prompt: &str) -> bool {
    let stripped = prompt.trim();

    if stripped.len() < 20 {
        return false;
    }

    // Action-verb short-prompt skip: if prompt starts with an action verb and is under 80 chars
    if stripped.len() < 80 {
        let lower = stripped.to_lowercase();
        for verb in ACTION_VERBS {
            if lower.starts_with(verb)
                && lower[verb.len()..]
                    .chars()
                    .next()
                    .map(|c| !c.is_alphabetic())
                    .unwrap_or(true)
            {
                return false;
            }
        }
    }

    // Check skip patterns first
    for pat in skip_patterns() {
        if pat.is_match(stripped) {
            return false;
        }
    }

    // Need at least 2 analysis pattern matches
    let matches = analysis_patterns()
        .iter()
        .filter(|pat| pat.is_match(stripped))
        .count();

    matches >= 2
}

pub fn run() {
    let data = read_stdin_value();

    let prompt = data
        .get("prompt")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    if prompt.trim().is_empty() {
        write_output(&serde_json::json!({}));
        return;
    }

    if is_analysis_request(prompt) {
        let output = HookOutput::inject_context("UserPromptSubmit", EPISTEMIC_REMINDER);
        write_output(&output);
    } else {
        write_output(&serde_json::json!({}));
    }
}
