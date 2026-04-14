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

    let session_id = data
        .get("session_id")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown");

    let event_name = data
        .get("hook_event_name")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    let cwd = data
        .get("cwd")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    let record = match event_name {
        "SessionStart" => json!({
            "ts": now_ts(),
            "ms": epoch_ms(),
            "type": "SessionStart",
            "cwd": cwd,
        }),
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
