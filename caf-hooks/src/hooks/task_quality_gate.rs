/// Task Quality Gate — TaskCompleted hook.
///
/// Python equivalent: global-hooks/framework/automation/task_quality_gate.py (75 LOC)
///
/// Behavior:
/// - Log task completion to ~/.claude/data/task_completions.jsonl
/// - Check task_description for test keywords
/// - If keywords found, inject quality gate reminder
/// - Always exits 0
use chrono::Utc;
use serde::Serialize;
use serde_json::Value;

use crate::io::{read_stdin_value, try_append_jsonl, write_output};
use crate::state::task_completions_path;
use crate::types::HookOutput;

const TEST_KEYWORDS: &[&str] = &["test", "verify", "validate", "check"];

#[derive(Serialize)]
struct TaskCompletionRecord<'a> {
    timestamp: String,
    task_id: &'a str,
    task_subject: &'a str,
    teammate_name: &'a str,
}

pub fn run() {
    let data: Value = read_stdin_value();

    if data.is_null() || data == Value::Object(Default::default()) {
        write_output(&serde_json::json!({}));
        return;
    }

    let task_id = data.get("task_id")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown")
        .to_string();
    let task_subject = data.get("task_subject")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let task_desc = data.get("task_description")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let teammate = data.get("teammate_name")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    // Log to JSONL
    let record = TaskCompletionRecord {
        timestamp: Utc::now().to_rfc3339(),
        task_id: &task_id,
        task_subject: &task_subject,
        teammate_name: &teammate,
    };
    try_append_jsonl(&task_completions_path(), &record);

    // Check for test requirements in description
    let desc_lower = task_desc.to_lowercase();
    let has_test_req = TEST_KEYWORDS.iter().any(|kw| desc_lower.contains(kw));

    if has_test_req {
        let msg = format!(
            "[Quality Gate] Task '{}' mentions testing requirements. \
            Please confirm that all relevant tests pass before considering this done.",
            task_subject
        );
        let output = HookOutput::inject_context("TaskCompleted", msg);
        write_output(&output);
    } else {
        write_output(&serde_json::json!({}));
    }
}
