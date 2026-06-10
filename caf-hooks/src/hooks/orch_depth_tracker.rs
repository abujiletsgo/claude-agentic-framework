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
use std::path::PathBuf;
use std::process::Command;

use crate::io::read_stdin_value;
use crate::state::{orch_depth_path, orch_done_flag_path, orch_guard_marker_path, orch_state_dir};

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

/// Write a start-timing file for the agent being started.
/// Never errors — all results are silently dropped to keep the hook non-blocking.
fn write_agent_start_time(data: &Value) {
    // Resolve agent name: check tool_input.name, tool_input.agent_name, tool_input.subagent_type
    let raw_name = data
        .get("tool_input")
        .and_then(|ti| {
            ti.get("name")
                .or_else(|| ti.get("agent_name"))
                .or_else(|| ti.get("subagent_type"))
        })
        .and_then(|v| v.as_str())
        .unwrap_or("unknown")
        .to_string();

    // Sanitize: replace non-alphanumeric (except '-') with '_', truncate to 64 chars
    let sanitized: String = raw_name
        .chars()
        .map(|c| if c.is_alphanumeric() || c == '-' { c } else { '_' })
        .take(64)
        .collect();

    // Session ID: read from data["session_id"], fallback "unknown", take first 8 chars
    let session_id = data
        .get("session_id")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown")
        .to_string();
    let session_id_8: String = session_id.chars().take(8).collect();

    // Build directory path: ~/.caf/state/agent_starts/
    let dir: PathBuf = match dirs::home_dir() {
        Some(home) => home.join(".caf").join("state").join("agent_starts"),
        None => return,
    };
    let _ = fs::create_dir_all(&dir);

    // File name: <agent_name_sanitized>_<session_id_8>.json
    let filename = format!("{}_{}.json", sanitized, session_id_8);
    let file_path = dir.join(filename);

    // Build JSON content
    let started_at_epoch_ms = chrono::Utc::now().timestamp_millis() as u64;
    let content = serde_json::json!({
        "agent_name": raw_name,
        "session_id": session_id,
        "started_at_epoch_ms": started_at_epoch_ms,
    });

    let _ = fs::write(file_path, content.to_string());
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

        // If orchestrator finished (back to depth 0), clean up and announce immediately.
        // We say "done" here directly rather than relying on the subsequent Stop event
        // because the orchestrator's final response may not trigger a Stop event if
        // agents were still pending when Claude output its last message.
        if new_depth == 0 && is_orchestrator_agent(&data) {
            // Write flag so voice_done skips its own "input required" on the next Stop
            let _ = fs::write(orch_done_flag_path(), "1");
            cleanup_marker();
            // Say "done" immediately — blocking so audio completes before hook exits
            if std::env::consts::OS == "macos" {
                let voice_enabled = std::env::var("VOICE_NOTIFICATIONS")
                    .unwrap_or_else(|_| "true".to_string())
                    .to_lowercase()
                    == "true";
                if voice_enabled {
                    if let Ok(mut child) = Command::new("/usr/bin/say")
                        .arg("done")
                        .stdout(std::process::Stdio::null())
                        .stderr(std::process::Stdio::null())
                        .spawn()
                    {
                        let _ = child.wait();
                    }
                }
            }
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

        write_agent_start_time(&data);
    }
}
