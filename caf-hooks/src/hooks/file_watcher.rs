/// FileChanged hook — watches dependency files.
///
/// Python equivalent: global-hooks/framework/automation/file_watcher.py (45 LOC)
///
/// Behavior:
/// - Only process: package.json, pyproject.toml, Cargo.toml, go.mod
/// - Log change to ~/.claude/data/file_changes.jsonl
/// - Inject advisory context
/// - Always exits 0
use chrono::Utc;
use serde::Serialize;
use serde_json::Value;
use std::path::Path;

use crate::io::{read_stdin_value, try_append_jsonl, write_output};
use crate::state::file_changes_path;
use crate::types::HookOutput;

const WATCHED: &[&str] = &["package.json", "pyproject.toml", "Cargo.toml", "go.mod"];

#[derive(Serialize)]
struct FileChangeRecord<'a> {
    timestamp: String,
    session_id: &'a str,
    file: &'a str,
    filename: &'a str,
}

pub fn run() {
    let data: Value = read_stdin_value();

    let session_id = data.get("session_id")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown")
        .to_string();

    let hook_event = data.get("hook_event_name")
        .and_then(|v| v.as_str())
        .unwrap_or("FileChanged")
        .to_string();

    // file_path can come from data["file"]["filePath"] or data["filePath"]
    let file_path = data
        .get("file")
        .and_then(|f| f.get("filePath"))
        .and_then(|v| v.as_str())
        .or_else(|| data.get("filePath").and_then(|v| v.as_str()))
        .or_else(|| data.get("file_path").and_then(|v| v.as_str()))
        .unwrap_or("")
        .to_string();

    let filename = Path::new(&file_path)
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("")
        .to_string();

    // Only process watched files
    if !WATCHED.contains(&filename.as_str()) {
        write_output(&serde_json::json!({}));
        return;
    }

    // Log to JSONL
    let record = FileChangeRecord {
        timestamp: Utc::now().to_rfc3339(),
        session_id: &session_id,
        file: &file_path,
        filename: &filename,
    };
    try_append_jsonl(&file_changes_path(), &record);

    // Inject advisory context
    let msg = format!(
        "Dependency file {} was modified externally. \
        Consider running dependency audit or checking for breaking changes.",
        filename
    );
    let output = HookOutput::inject_context(hook_event, msg);
    write_output(&output);
}
