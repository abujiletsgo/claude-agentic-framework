/// Orchestrator Tool Guard — PreToolUse hook.
///
/// Python equivalent: global-hooks/framework/guardrails/orchestrator_tool_guard.py (137 LOC)
///
/// Behavior:
/// - Check guard.marker exists at ~/.caf/orch_state/guard.marker
/// - Check depth file for current depth (default 0)
/// - Only block at depth == 1 (the orchestrator itself)
/// - If marker exists AND depth == 1 AND tool is Read/Grep/Glob/Edit → exit 2 (block)
/// - If marker exists AND depth == 1 AND tool is Bash AND command starts with
///   research patterns → exit 2 (block)
/// - Otherwise → print {} to stdout and exit 0 (fail-open)
use serde_json::Value;
use std::process;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::io::read_stdin_value;
use crate::state::{orch_depth_path, orch_guard_marker_path};

const STALE_ORCH_STATE_SECS: u64 = 86400;

/// Tools the orchestrator must never call directly (besides Bash research).
const FORBIDDEN_TOOLS: &[&str] = &["Read", "Grep", "Glob", "Edit", "NotebookEdit", "Write"];

/// Bash command prefixes that indicate file research (should be delegated).
const BASH_RESEARCH_PATTERNS: &[&str] = &[
    "cat ", "grep ", "rg ", "find ", "head ", "tail ", "sed ", "awk ",
    "less ", "more ", "wc ", "sort ", "uniq ", "xargs ",
    "ls ", "tree ", "file ", "stat ",
];

const BLOCK_REMINDER: &str = "\
[ORCHESTRATOR GUARD] You are the orchestrator. You MUST NOT use \
file-reading or code-searching tools directly. Spawn a subagent instead:\n\
  - Need to read a file? \u{2192} Agent(name='researcher-N', model='haiku', ...)\n\
  - Need to search code? \u{2192} Agent(name='researcher-N', model='sonnet', ...)\n\
  - Need to edit code? \u{2192} Agent(name='builder-N', model='sonnet', ...)\n\
  - Need to run tests? \u{2192} Agent(name='validator-N', model='haiku', ...)\n\n\
This tool call has been BLOCKED. Delegate this work to a subagent.";

fn get_depth() -> i64 {
    let path = orch_depth_path();
    if !path.exists() {
        return 0;
    }
    match std::fs::read_to_string(&path) {
        Ok(s) => {
            let s = s.trim();
            // Try JSON format first: {"depth": N, "ts": "..."}
            if let Ok(v) = serde_json::from_str::<Value>(s) {
                if let Some(d) = v.get("depth").and_then(|d| d.as_i64()) {
                    return d;
                }
            }
            // Fall back to raw integer (old format)
            s.parse::<i64>().unwrap_or(0)
        }
        Err(_) => 0,
    }
}

/// Read marker file JSON, parse "ts" field, check if age > STALE_ORCH_STATE_SECS.
/// Returns true if marker is stale (should be treated as absent).
fn is_marker_stale() -> bool {
    let path = orch_guard_marker_path();
    let contents = match std::fs::read_to_string(&path) {
        Ok(c) => c,
        Err(_) => return false,
    };
    let v: Value = match serde_json::from_str(contents.trim()) {
        Ok(v) => v,
        Err(_) => return false,
    };
    let ts_str = match v.get("ts").and_then(|t| t.as_str()) {
        Some(s) => s,
        None => return false,
    };
    // Parse RFC3339 timestamp using chrono
    let dt = match chrono::DateTime::parse_from_rfc3339(ts_str) {
        Ok(d) => d,
        Err(_) => return false,
    };
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let marker_secs = dt.timestamp() as u64;
    let age = now.saturating_sub(marker_secs);
    if age > STALE_ORCH_STATE_SECS {
        let age_hours = age / 3600;
        eprintln!("[CAF] Ignoring stale orchestration guard marker (age: {}h)", age_hours);
        return true;
    }
    false
}

fn is_bash_research(command: &str) -> bool {
    let cmd = command.trim().trim_start_matches(|c| c == '\'' || c == '"');
    BASH_RESEARCH_PATTERNS.iter().any(|p| cmd.starts_with(p))
}

pub fn run() {
    // Fail-open wrapper — any internal error → exit 0
    if let Err(_) = run_inner() {
        println!("{{}}");
        process::exit(0);
    }
}

fn run_inner() -> Result<(), Box<dyn std::error::Error>> {
    // Quick exit: no orchestration active
    if !orch_guard_marker_path().exists() {
        println!("{{}}");
        return Ok(());
    }

    // Check if marker is stale — if so, treat as absent
    if is_marker_stale() {
        println!("{{}}");
        return Ok(());
    }

    // Only block at depth 1 (orchestrator itself).
    // Depth 0 = main session (never block), depth 2+ = subagent (allowed).
    let depth = get_depth();
    if depth != 1 {
        println!("{{}}");
        return Ok(());
    }

    let data: Value = read_stdin_value();
    let tool_name = data.get("tool_name").and_then(|v| v.as_str()).unwrap_or("");
    let tool_input = data.get("tool_input").cloned().unwrap_or(Value::Object(Default::default()));

    let should_block = if FORBIDDEN_TOOLS.contains(&tool_name) {
        true
    } else if tool_name == "Bash" {
        let command = tool_input
            .get("command")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        is_bash_research(command)
    } else {
        false
    };

    if should_block {
        eprintln!("{}", BLOCK_REMINDER);
        process::exit(2);
    }

    println!("{{}}");
    Ok(())
}
