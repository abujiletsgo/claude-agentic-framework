/// Orchestrator Depth Tracker — SubagentStart + SubagentStop hook.
///
/// Python equivalent: global-hooks/framework/guardrails/orch_depth_tracker.py (160 LOC)
///
/// Behavior:
/// - SubagentStart: read int from /tmp/caf_orch_depth (default 0), increment, write back.
///   If marker absent and agent is orchestrator → create marker and reset depth to 0 first.
///   If marker absent and agent is NOT orchestrator → skip.
/// - SubagentStop: read int, decrement (min 0), write back.
///   If new depth == 0 and agent is orchestrator → cleanup marker + depth files.
/// - Always exits 0 (never blocks, tracking only).
use serde_json::Value;
use std::path::Path;

use crate::io::read_stdin_value;

const MARKER_FILE: &str = "/tmp/caf_orch_guard.marker";
const DEPTH_FILE: &str = "/tmp/caf_orch_depth";

fn get_depth() -> i64 {
    if !Path::new(DEPTH_FILE).exists() {
        return 0;
    }
    match std::fs::read_to_string(DEPTH_FILE) {
        Ok(s) => s.trim().parse::<i64>().unwrap_or(0),
        Err(_) => 0,
    }
}

fn set_depth(depth: i64) {
    let val = std::cmp::max(0, depth);
    let _ = std::fs::write(DEPTH_FILE, val.to_string());
}

fn cleanup_marker() {
    let _ = std::fs::remove_file(MARKER_FILE);
    let _ = std::fs::remove_file(DEPTH_FILE);
}

fn touch_marker() {
    let _ = std::fs::write(MARKER_FILE, "");
}

/// Check if the agent being started/stopped is an orchestrator by inspecting
/// agent_type, agent_id, agent_name, and tool_input fields.
fn is_orchestrator_agent(hook_input: &Value) -> bool {
    // Check agent_type field
    if let Some(s) = hook_input.get("agent_type").and_then(|v| v.as_str()) {
        if s.to_lowercase().contains("orchestrator") {
            return true;
        }
    }
    // Check agent_id and agent_name fields
    for field in &["agent_id", "agent_name"] {
        if let Some(s) = hook_input.get(field).and_then(|v| v.as_str()) {
            if s.to_lowercase().contains("orchestrator") {
                return true;
            }
        }
    }
    // Check tool_input sub-fields: name, agent_name, subagent_type
    if let Some(tool_input) = hook_input.get("tool_input") {
        if tool_input.is_object() {
            for field in &["name", "agent_name", "subagent_type"] {
                if let Some(s) = tool_input.get(field).and_then(|v| v.as_str()) {
                    if s.to_lowercase().contains("orchestrator") {
                        return true;
                    }
                }
            }
        }
    }
    false
}

pub fn run() {
    let data: Value = read_stdin_value();

    if data.is_null() {
        return;
    }

    // Determine SubagentStart vs SubagentStop by presence of stop-only fields.
    // SubagentStop has agent_transcript_path or tool_output.
    let has_transcript = data.get("agent_transcript_path").is_some();
    let has_tool_output = data.get("tool_output").is_some();
    let is_stop = has_transcript || has_tool_output;

    if is_stop {
        // SubagentStop: decrement depth
        if !Path::new(MARKER_FILE).exists() {
            // No orchestration active — nothing to do
            return;
        }

        let depth = get_depth();
        let new_depth = std::cmp::max(0, depth - 1);
        set_depth(new_depth);

        // If orchestrator finished (back to depth 0), clean up
        if new_depth == 0 && is_orchestrator_agent(&data) {
            cleanup_marker();
        }
    } else {
        // SubagentStart: increment depth
        if !Path::new(MARKER_FILE).exists() {
            // Auto-create marker if an orchestrator agent is starting
            if is_orchestrator_agent(&data) {
                touch_marker();
                set_depth(0);
            } else {
                // Not an orchestrator and no orchestration active — skip
                return;
            }
        }

        let depth = get_depth();
        let new_depth = depth + 1;
        set_depth(new_depth);
    }
}
