/// Orchestrator Tool Guard — PreToolUse hook.
///
/// Python equivalent: global-hooks/framework/guardrails/orchestrator_tool_guard.py (137 LOC)
///
/// Behavior:
/// - Check /tmp/caf_orch_guard.marker exists
/// - Check /tmp/caf_orch_depth for current depth (default 0)
/// - Only block at depth == 1 (the orchestrator itself)
/// - If marker exists AND depth == 1 AND tool is Read/Grep/Glob/Edit → exit 2 (block)
/// - If marker exists AND depth == 1 AND tool is Bash AND command starts with
///   research patterns → exit 2 (block)
/// - Otherwise → print {} to stdout and exit 0 (fail-open)
use serde_json::Value;
use std::path::Path;
use std::process;

use crate::io::read_stdin_value;

const MARKER_FILE: &str = "/tmp/caf_orch_guard.marker";
const DEPTH_FILE: &str = "/tmp/caf_orch_depth";

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
    if !Path::new(DEPTH_FILE).exists() {
        return 0;
    }
    match std::fs::read_to_string(DEPTH_FILE) {
        Ok(s) => s.trim().parse::<i64>().unwrap_or(0),
        Err(_) => 0,
    }
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
    if !Path::new(MARKER_FILE).exists() {
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
