/// Voice Done — Stop hook.
///
/// Python equivalent: global-hooks/framework/notifications/voice_done.py (65 LOC)
///
/// Behavior:
/// - Read stop_reason from stdin
/// - Skip on "error" or "cancelled" stop_reason
/// - Run `say <phrase>` via Command::new (non-blocking, macOS only)
/// - Always exits 0
use serde_json::Value;
use std::process::Command;

use crate::io::read_stdin_value;

const DONE_MESSAGES: &[&str] = &["Done.", "Finished.", "Ready.", "Complete."];

pub fn run() {
    let data: Value = read_stdin_value();

    let stop_reason = data.get("stop_reason")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    // Skip on error or cancelled
    if stop_reason == "error" || stop_reason == "cancelled" {
        return;
    }

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

    // Pick a random phrase
    let idx = (std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.subsec_nanos())
        .unwrap_or(0) as usize)
        % DONE_MESSAGES.len();
    let phrase = DONE_MESSAGES[idx];

    // Fire-and-forget: spawn say, don't wait
    let _ = Command::new("say")
        .arg(phrase)
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn();
}
