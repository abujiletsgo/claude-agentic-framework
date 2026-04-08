/// Context Bundle Logger — PostToolUse hook.
///
/// Python equivalent: global-hooks/framework/context-bundle-logger.py (157 LOC)
///
/// Behavior:
/// - Only process Read, Edit, Write, NotebookEdit tool uses
/// - Load/create session bundle at ~/.claude/bundles/<session_id>.json
/// - Log the operation (tool, file, action, summary counts)
/// - Save updated bundle
/// - Always exits 0
use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

use crate::io::{read_stdin_value, write_output};
use crate::state::claude_dir;

const LOGGED_TOOLS: &[&str] = &["Read", "Edit", "Write", "NotebookEdit"];

fn bundle_path(session_id: &str) -> PathBuf {
    let dir = claude_dir().join("bundles");
    let _ = fs::create_dir_all(&dir);
    dir.join(format!("{}.json", session_id))
}

#[derive(Debug, Serialize, Deserialize)]
struct BundleSummary {
    read_count: u64,
    edit_count: u64,
    write_count: u64,
    total_operations: u64,
}

impl Default for BundleSummary {
    fn default() -> Self {
        BundleSummary {
            read_count: 0,
            edit_count: 0,
            write_count: 0,
            total_operations: 0,
        }
    }
}

#[derive(Debug, Serialize, Deserialize)]
struct Bundle {
    session_id: Option<String>,
    created_at: String,
    last_updated: Option<String>,
    operations: Vec<serde_json::Value>,
    files_read: Vec<String>,
    files_modified: Vec<String>,
    summary: BundleSummary,
}

impl Bundle {
    fn new() -> Self {
        Bundle {
            session_id: None,
            created_at: Utc::now().to_rfc3339(),
            last_updated: None,
            operations: Vec::new(),
            files_read: Vec::new(),
            files_modified: Vec::new(),
            summary: BundleSummary::default(),
        }
    }
}

fn load_bundle(path: &PathBuf) -> Bundle {
    if path.exists() {
        if let Ok(content) = fs::read_to_string(path) {
            if let Ok(bundle) = serde_json::from_str::<Bundle>(&content) {
                return bundle;
            }
        }
    }
    Bundle::new()
}

fn save_bundle(path: &PathBuf, bundle: &mut Bundle) {
    bundle.last_updated = Some(Utc::now().to_rfc3339());
    if let Ok(json) = serde_json::to_string_pretty(bundle) {
        let _ = fs::write(path, json);
    }
}

fn extract_file_path(tool_input: &serde_json::Value) -> Option<String> {
    if let Some(obj) = tool_input.as_object() {
        // file_path, notebook_path, path — in that priority order
        for key in &["file_path", "notebook_path", "path"] {
            if let Some(v) = obj.get(*key).and_then(|v| v.as_str()) {
                if !v.is_empty() {
                    return Some(v.to_string());
                }
            }
        }
    }
    None
}

fn log_operation(
    bundle: &mut Bundle,
    tool_name: &str,
    tool_input: &serde_json::Value,
    timestamp: &str,
) {
    let file_path = match extract_file_path(tool_input) {
        Some(p) => p,
        None => return, // Skip if no file path
    };

    let mut operation: HashMap<String, serde_json::Value> = HashMap::new();
    operation.insert("timestamp".into(), serde_json::Value::String(timestamp.to_string()));
    operation.insert("tool".into(), serde_json::Value::String(tool_name.to_string()));
    operation.insert("file".into(), serde_json::Value::String(file_path.clone()));

    match tool_name {
        "Read" => {
            operation.insert("action".into(), serde_json::Value::String("read".into()));
            if !bundle.files_read.contains(&file_path) {
                bundle.files_read.push(file_path.clone());
            }
            bundle.summary.read_count += 1;
        }
        "Edit" => {
            operation.insert("action".into(), serde_json::Value::String("edit".into()));
            // Store truncated old_string / new_string (max 100 chars each)
            let old_str = tool_input
                .get("old_string")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            let new_str = tool_input
                .get("new_string")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            operation.insert(
                "old_string".into(),
                serde_json::Value::String(old_str.chars().take(100).collect()),
            );
            operation.insert(
                "new_string".into(),
                serde_json::Value::String(new_str.chars().take(100).collect()),
            );
            if !bundle.files_modified.contains(&file_path) {
                bundle.files_modified.push(file_path.clone());
            }
            bundle.summary.edit_count += 1;
        }
        "Write" => {
            operation.insert("action".into(), serde_json::Value::String("write".into()));
            // Don't store content — just track that file was written
            if !bundle.files_modified.contains(&file_path) {
                bundle.files_modified.push(file_path.clone());
            }
            bundle.summary.write_count += 1;
        }
        "NotebookEdit" => {
            operation.insert("action".into(), serde_json::Value::String("notebook_edit".into()));
            let cell_id = tool_input
                .get("cell_id")
                .cloned()
                .unwrap_or(serde_json::Value::Null);
            operation.insert("cell_id".into(), cell_id);
            if !bundle.files_modified.contains(&file_path) {
                bundle.files_modified.push(file_path.clone());
            }
            bundle.summary.edit_count += 1;
        }
        _ => return,
    }

    bundle
        .operations
        .push(serde_json::to_value(operation).unwrap_or(serde_json::Value::Null));
    bundle.summary.total_operations += 1;
}

pub fn run() {
    let data = read_stdin_value();

    let session_id = data
        .get("session_id")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown")
        .to_string();

    let tool_name = data
        .get("tool_name")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    // Only log the relevant tools
    if !LOGGED_TOOLS.contains(&tool_name) {
        write_output(&serde_json::json!({}));
        return;
    }

    let tool_input = data
        .get("tool_input")
        .cloned()
        .unwrap_or(serde_json::json!({}));
    // Parse if it's a JSON string
    let tool_input = if let Some(s) = tool_input.as_str() {
        serde_json::from_str(s).unwrap_or(serde_json::json!({}))
    } else {
        tool_input
    };

    let timestamp = data
        .get("timestamp")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .unwrap_or_else(|| Utc::now().to_rfc3339());

    let path = bundle_path(&session_id);
    let mut bundle = load_bundle(&path);

    if bundle.session_id.is_none() {
        bundle.session_id = Some(session_id.clone());
    }

    log_operation(&mut bundle, tool_name, &tool_input, &timestamp);

    save_bundle(&path, &mut bundle);

    write_output(&serde_json::json!({}));
}
