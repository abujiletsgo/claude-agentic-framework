/// Voice Done — Stop hook.
///
/// Python equivalent: global-hooks/framework/notifications/voice_done.py (65 LOC)
///
/// Behavior:
/// - Read stop_reason from stdin
/// - Skip on "error" or "cancelled" stop_reason
/// - Read session name from transcript_path (first line custom-title)
/// - Say "{session_name} done" (e.g. "caf done"), or just "done" if no name
/// - Run `say <phrase>` via Command::new (non-blocking, macOS only)
/// - Always exits 0
use serde_json::Value;
use std::process::Command;

use crate::io::read_stdin_value;

/// Read the session's custom title from the transcript JSONL file.
/// The first line (if present) may be: {"type":"custom-title","customTitle":"caf",...}
fn get_session_name(data: &Value) -> Option<String> {
    let transcript_path = data.get("transcript_path")?.as_str()?;
    let content = std::fs::read_to_string(transcript_path).ok()?;
    let first_line = content.lines().next()?;
    let json: Value = serde_json::from_str(first_line).ok()?;
    if json.get("type").and_then(|v| v.as_str()) == Some("custom-title") {
        json.get("customTitle")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
    } else {
        None
    }
}

/// Build the TTS phrase for a Stop event, prefixed with session name if available.
/// Returns None to skip (error/cancelled).
fn build_phrase(data: &Value) -> Option<String> {
    let stop_reason = data
        .get("stop_reason")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    // Skip on error or cancelled
    if stop_reason == "error" || stop_reason == "cancelled" {
        return None;
    }

    let session_name = get_session_name(data);

    Some(match session_name {
        Some(name) => format!("{} done", name),
        None => "done".to_string(),
    })
}

pub fn run() {
    let data: Value = read_stdin_value();

    // Only run on macOS
    if std::env::consts::OS != "macos" {
        return;
    }

    // Check VOICE_NOTIFICATIONS env var (default: enabled)
    let voice_enabled = std::env::var("VOICE_NOTIFICATIONS")
        .unwrap_or_else(|_| "true".to_string())
        .to_lowercase()
        == "true";
    if !voice_enabled {
        return;
    }

    // Build phrase — None means skip (error/cancelled)
    let phrase = match build_phrase(&data) {
        Some(p) => p,
        None => return,
    };

    // Fire-and-forget: spawn say, don't wait
    let _ = Command::new("say")
        .arg(&phrase)
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn();
}
