/// Orchestrator Depth Tracker — SubagentStart + SubagentStop hook.
///
/// Python equivalent: global-hooks/framework/guardrails/orch_depth_tracker.py (160 LOC)
///
/// Behavior:
/// - SubagentStart: read int from depth file (default 0), increment, write back.
///   If marker absent and agent is orchestrator → create marker and reset depth to 0 first.
///   If marker absent and agent is NOT orchestrator → skip.
/// - SubagentStop: read int, decrement (min 0), write back.
///   If new depth == 0 and agent is orchestrator → cleanup marker + depth files.
/// - Always exits 0 (never blocks, tracking only).
use serde_json::Value;
use std::fs;

use crate::io::read_stdin_value;
use crate::state::{orch_depth_path, orch_guard_marker_path, orch_state_dir};

fn get_depth() -> i64 {
    let path = orch_depth_path();
    if !path.exists() {
        return 0;
    }
    match fs::read_to_string(&path) {
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

fn set_depth(depth: i64) {
    let val = std::cmp::max(0, depth);
    let ts = chrono::Utc::now().to_rfc3339();
    let json = serde_json::json!({"depth": val, "ts": ts});
    let _ = fs::create_dir_all(orch_state_dir());
    let _ = fs::write(orch_depth_path(), json.to_string());
}

fn cleanup_marker() {
    let _ = fs::remove_file(orch_guard_marker_path());
    let _ = fs::remove_file(orch_depth_path());
}

fn touch_marker() {
    let ts = chrono::Utc::now().to_rfc3339();
    let json = serde_json::json!({"ts": ts});
    let _ = fs::create_dir_all(orch_state_dir());
    let _ = fs::write(orch_guard_marker_path(), json.to_string());
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
        if !orch_guard_marker_path().exists() {
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
        if !orch_guard_marker_path().exists() {
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
