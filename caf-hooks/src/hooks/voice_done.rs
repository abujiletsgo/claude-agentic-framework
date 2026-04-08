/// Voice Done — Stop and SubagentStop hook.
///
/// Python equivalent: global-hooks/framework/notifications/voice_done.py (65 LOC)
///
/// Behavior:
/// - Read stop_reason / agent_type from stdin
/// - Skip on "error" or "cancelled" stop_reason
/// - Inspect context to pick a contextual phrase
/// - Run `say <phrase>` via Command::new (non-blocking, macOS only)
/// - Always exits 0
use serde_json::Value;
use std::process::Command;

use crate::io::read_stdin_value;

/// Pick a contextual TTS phrase based on the stdin JSON payload.
///
/// Detection priority (checked in order):
/// 1. SubagentStop event  → use agent_type to pick phrase
/// 2. stop_reason == "error" / "cancelled" → return None (skip)
/// 3. AskUserQuestion in last_tool / tool_name → "question"
/// 4. agent_type contains "research"/"researcher" → "research done"
/// 5. agent_type contains "build"/"builder" → "build done"
/// 6. agent_type contains "review"/"validator"/"scout" → "review done"
/// 7. agent_type contains "debug"/"debugger" → "debug done"
/// 8. Default fallback → "done"
fn pick_phrase(data: &Value) -> Option<&'static str> {
    let hook_event = data
        .get("hook_event_name")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    // ── SubagentStop path ────────────────────────────────────────────────────
    if hook_event == "SubagentStop" {
        let agent_type = data
            .get("agent_type")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_lowercase();

        return Some(classify_role(&agent_type));
    }

    // ── Stop path ────────────────────────────────────────────────────────────
    let stop_reason = data
        .get("stop_reason")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    // Skip on error or cancelled
    if stop_reason == "error" || stop_reason == "cancelled" {
        return None;
    }

    // Check tool_name for AskUserQuestion (present if last action was a question)
    let tool_name = data
        .get("tool_name")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_lowercase();

    if tool_name.contains("askuserquestion") || tool_name.contains("ask_user") {
        return Some("question");
    }

    // Check agent_type on Stop events (may be present in some payloads)
    let agent_type = data
        .get("agent_type")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_lowercase();

    if !agent_type.is_empty() {
        return Some(classify_role(&agent_type));
    }

    // Default fallback
    Some("done")
}

/// Map a lowercase agent_type/role string to a TTS phrase.
fn classify_role(role: &str) -> &'static str {
    if role.contains("research") {
        "research done"
    } else if role.contains("build") || role.contains("builder") {
        "build done"
    } else if role.contains("review") || role.contains("validator") || role.contains("scout") {
        "review done"
    } else if role.contains("debug") {
        "debug done"
    } else {
        "done"
    }
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

    // Pick contextual phrase — None means skip (error/cancelled)
    let phrase = match pick_phrase(&data) {
        Some(p) => p,
        None => return,
    };

    // Fire-and-forget: spawn say, don't wait
    let _ = Command::new("say")
        .arg(phrase)
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn();
}
