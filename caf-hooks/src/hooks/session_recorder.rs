/// Session Recorder — SessionStart / UserPromptSubmit / Stop hook.
///
/// Writes session events to ~/.caf/sessions/<session_id>.jsonl so the
/// run-explorer dashboard can list and replay every Claude session.
///
/// Format: one JSON object per line, newest events appended.
/// Reader: apps/run-explorer/server/src/services/sessionParser.ts
///
/// Always exits 0 — never blocks Claude.
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

use chrono::Utc;
use serde_json::{json, Value};

use crate::io::{read_stdin_value, try_append_jsonl, write_output};
use crate::types::HookOutput;

fn read_current_orch_id() -> Option<String> {
    let path = dirs::home_dir()?.join(".caf").join("current_orch_id");
    let text = std::fs::read_to_string(&path).ok()?;
    let val: serde_json::Value = serde_json::from_str(&text).ok()?;
    let orch_id = val.get("orch_id")?.as_str()?.to_string();
    // If started_at is missing or unparseable, skip the stale check and treat as fresh
    if let Some(started_at_str) = val.get("started_at").and_then(|v| v.as_str()) {
        if let Ok(started_at) = chrono::DateTime::parse_from_rfc3339(started_at_str) {
            let age_secs = Utc::now().signed_duration_since(started_at).num_seconds();
            // Treat as stale if older than 4 hours (14400 seconds)
            if age_secs > 14400 {
                return None;
            }
        }
    }
    Some(orch_id)
}

fn sessions_dir() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_else(|| PathBuf::from("/tmp"))
        .join(".caf")
        .join("sessions")
}

fn session_file(session_id: &str) -> PathBuf {
    sessions_dir().join(format!("{}.jsonl", session_id))
}

fn now_ts() -> String {
    Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true)
}

fn epoch_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

pub fn run() {
    let data: Value = read_stdin_value();

    let session_id_owned = data
        .get("session_id")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .unwrap_or_else(|| format!("unknown-{}", chrono::Utc::now().timestamp_millis()));
    let session_id = session_id_owned.as_str();

    let event_name = data
        .get("hook_event_name")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    let cwd = data
        .get("cwd")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    let record = match event_name {
        "SessionStart" => {
            let mut rec = json!({
                "ts": now_ts(),
                "ms": epoch_ms(),
                "type": "SessionStart",
                "cwd": cwd,
            });
            if let Some(orch_id) = read_current_orch_id() {
                rec["orch_run_id"] = json!(orch_id);
            }
            rec
        }
        "UserPromptSubmit" => {
            let prompt = data
                .get("prompt")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            // Truncate to 500 chars — enough for display, not wasteful
            let prompt_preview: String = prompt.chars().take(500).collect();
            json!({
                "ts": now_ts(),
                "ms": epoch_ms(),
                "type": "UserPromptSubmit",
                "cwd": cwd,
                "prompt": prompt_preview,
            })
        }
        "Stop" => json!({
            "ts": now_ts(),
            "ms": epoch_ms(),
            "type": "Stop",
            "cwd": cwd,
        }),
        _ => {
            // Unknown event — skip silently
            write_output(&HookOutput::empty());
            return;
        }
    };

    let path = session_file(session_id);
    try_append_jsonl(&path, &record);

    write_output(&HookOutput::empty());
}
