/// Enforce Orchestrate — UserPromptSubmit hook.
///
/// Python equivalent: global-hooks/framework/guardrails/enforce_orchestrate.py (132 LOC)
///
/// Behavior:
/// - Detect if user prompt contains /orchestrate or orchestration intent
/// - If so, inject a blocking enforcement reminder into additionalContext
/// - Always exits 0
use regex::Regex;
use std::sync::OnceLock;

use crate::io::{read_stdin_value, write_output};
use crate::types::HookOutput;

const ORCHESTRATE_ENFORCEMENT_SHORT: &str = "\
[ORCHESTRATE] Call Skill(skill=\"orchestrate\") FIRST — do NOT read/write/run before the skill loads.
Spawn parallel Agent() calls; never do the work yourself.";

const ORCHESTRATE_ENFORCEMENT: &str = "\
[ORCHESTRATE ENFORCEMENT — BLOCKING REQUIREMENT]
The user has requested /orchestrate. You MUST:

1. IMMEDIATELY call: Skill(skill=\"orchestrate\", args=\"<user's full message>\")
2. Do NOT read files, do NOT write code, do NOT research — the Skill tool FIRST
3. Do NOT treat /orchestrate as decorative text — it is a COMMAND
4. The skill will load the orchestrator protocol — YOU are the orchestrator
5. You coordinate by spawning parallel Agent() calls — never do work yourself

SEQUENCE: Skill(\"orchestrate\") → protocol loads → YOU spawn parallel agents (researchers, builders, validators)
VIOLATION: Any Read/Edit/Bash call instead of spawning agents = failure";

static SLASH_ORCHESTRATE: OnceLock<Regex> = OnceLock::new();
static ORCHESTRATE_INTENT: OnceLock<Regex> = OnceLock::new();

fn slash_orchestrate() -> &'static Regex {
    SLASH_ORCHESTRATE.get_or_init(|| {
        Regex::new(r"(?i)(?:^|\s)/orchestrate\b").expect("valid regex")
    })
}

fn orchestrate_intent() -> &'static Regex {
    ORCHESTRATE_INTENT.get_or_init(|| {
        Regex::new(r"(?i)\b(?:orchestrate\b|run orchestrat\w*|use orchestrat\w*|spawn orchestrat\w*|parallel agents?\b|multi.?agent\b|spawn.*team\b)").expect("valid regex")
    })
}

/// Returns true if /tmp/caf_caddy_result.json exists and contains strategy == "orchestrate".
fn caddy_already_says_orchestrate() -> bool {
    let path = "/tmp/caf_caddy_result.json";
    if let Ok(contents) = std::fs::read_to_string(path) {
        if let Ok(v) = serde_json::from_str::<serde_json::Value>(&contents) {
            return v.get("strategy").and_then(|s| s.as_str()) == Some("orchestrate");
        }
    }
    false
}

fn needs_orchestrate_enforcement(prompt: &str) -> bool {
    let stripped = prompt.trim();
    if stripped.is_empty() {
        return false;
    }
    if slash_orchestrate().is_match(stripped) {
        return true;
    }
    if orchestrate_intent().is_match(stripped) {
        return true;
    }
    false
}

pub fn run() {
    let data = read_stdin_value();

    let prompt = data
        .get("prompt")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    if needs_orchestrate_enforcement(prompt) {
        let message = if caddy_already_says_orchestrate() {
            ORCHESTRATE_ENFORCEMENT_SHORT
        } else {
            ORCHESTRATE_ENFORCEMENT
        };
        let output = HookOutput::inject_context("UserPromptSubmit", message);
        write_output(&output);
    } else {
        write_output(&serde_json::json!({}));
    }
}
