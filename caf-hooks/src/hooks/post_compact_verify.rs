/// PostCompact verification hook.
///
/// Python equivalent: global-hooks/framework/context/post_compact_verify.py (43 LOC)
///
/// Behavior:
/// - Count compressed_context JSON files for the current session
/// - Inject advisory context into Claude's context window
/// - Always exits 0
use serde_json::Value;

use crate::io::{write_output, read_stdin_value};
use crate::state::compressed_context_dir;
use crate::types::HookOutput;

pub fn run() {
    let data: Value = read_stdin_value();
    let session_id = data.get("session_id")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let hook_event = data.get("hook_event_name")
        .and_then(|v| v.as_str())
        .unwrap_or("PostCompact")
        .to_string();

    let n = count_session_summaries(&session_id);

    let msg = if n > 0 {
        format!(
            "Context compaction completed. Pre-computed summaries preserved for {} tasks.",
            n
        )
    } else {
        "Context compacted but no pre-computed summaries found. Key state may need manual recovery."
            .to_string()
    };

    let output = HookOutput::inject_context(hook_event, msg);
    write_output(&output);
}

fn count_session_summaries(session_id: &str) -> usize {
    if session_id.is_empty() {
        return 0;
    }
    let dir = compressed_context_dir();
    if !dir.exists() {
        return 0;
    }
    let mut count = 0;
    if let Ok(entries) = std::fs::read_dir(&dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) != Some("json") {
                continue;
            }
            if let Ok(contents) = std::fs::read_to_string(&path) {
                if let Ok(v) = serde_json::from_str::<Value>(&contents) {
                    if v.get("session_id").and_then(|s| s.as_str()) == Some(session_id) {
                        count += 1;
                    }
                }
            }
        }
    }
    count
}
