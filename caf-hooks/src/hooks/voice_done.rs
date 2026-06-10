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
use std::fs;
use std::process::Command;

use crate::io::read_stdin_value;
use crate::state::orch_done_flag_path;

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

    let _ = session_name;

    // If orchestration just completed, clear the flag so it doesn't fire twice.
    let flag = orch_done_flag_path();
    if flag.exists() {
        let _ = fs::remove_file(&flag);
    }

    // Stop fires every time Claude finishes a turn — this means "I'm done speaking,"
    // not "I need input." Saying "input required" here was wrong: it announced an
    // input prompt on every normal reply. Voice prompts for actual user input come
    // from auto_voice_notifications.py (PreToolUse:AskUserQuestion).
    Some("done".to_string())
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

    // Block until say finishes — the hook itself is async:true so this doesn't
    // block Claude Code. Without waiting, the hook runner may reap the orphaned
    // say child before it produces any audio.
    if let Ok(mut child) = Command::new("/usr/bin/say")
        .arg(&phrase)
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn()
    {
        let _ = child.wait();
    }
}
