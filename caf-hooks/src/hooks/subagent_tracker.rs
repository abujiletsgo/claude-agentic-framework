/// Subagent Tracker — SubagentStop hook.
///
/// Python equivalent: global-hooks/framework/automation/subagent_tracker.py
///
/// Behavior:
/// - Reads SubagentStop event from stdin JSON
/// - Extracts agent name, tool name, and output from the payload
/// - Checks output for error/anomaly patterns
/// - Appends tracking record to ~/.claude/data/agent_tracking.jsonl
/// - On anomalies: appends to /tmp/caf_watchdog.md and ~/.claude/data/subagent_alerts.jsonl
/// - Always exits 0 (never blocks)
use std::path::PathBuf;

use chrono::Utc;
use regex::Regex;
use serde_json::Value;

use crate::io::{read_stdin_value, try_append_jsonl, write_output};
use crate::types::HookOutput;

/// Output below this character count is considered suspiciously empty
const MINIMUM_MEANINGFUL_OUTPUT: usize = 50;

/// Patterns that signal a failed/errored agent response (match Python exactly)
const ERROR_PATTERNS: &[&str] = &[
    "traceback",
    "exception:",
    "error:",
    "internal error",
    "rate_limit",
    "authentication_failed",
    "tool_call_error",
    "context_length_exceeded",
    "max_tokens",
    "500 ",
    " 500\n",
    "i cannot",
    "i'm unable",
    "i am unable",
];

fn tracking_path() -> PathBuf {
    let home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("/tmp"));
    home.join(".claude").join("data").join("agent_tracking.jsonl")
}

fn alerts_path() -> PathBuf {
    let home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("/tmp"));
    home.join(".claude").join("data").join("subagent_alerts.jsonl")
}

pub fn run() {
    let data: Value = read_stdin_value();

    // Extract fields matching Python logic
    let tool_name = data
        .get("tool_name")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown")
        .to_string();

    let tool_input = data.get("tool_input").cloned().unwrap_or(Value::Null);
    let tool_output = data.get("tool_output").cloned().unwrap_or(Value::Null);

    // Compute output length (matches Python: str→len, dict→json len, else 0)
    let output_text = match &tool_output {
        Value::String(s) => s.clone(),
        Value::Null => String::new(),
        other => serde_json::to_string(other).unwrap_or_default(),
    };
    let output_length = output_text.len();

    // Extract agent name from tool input (matches Python priority order)
    let agent_name = match &tool_input {
        Value::Object(map) => {
            map.get("agent_name")
                .or_else(|| map.get("name"))
                .and_then(|v| v.as_str())
                .map(|s| s.to_string())
                .or_else(|| {
                    map.get("task_description")
                        .and_then(|v| v.as_str())
                        .map(|s| s.chars().take(80).collect())
                })
                .unwrap_or_else(|| "unknown".to_string())
        }
        Value::String(s) => s.chars().take(80).collect(),
        _ => "unknown".to_string(),
    };

    // Input keys for the record
    let input_keys: Vec<String> = match &tool_input {
        Value::Object(map) => map.keys().cloned().collect(),
        _ => Vec::new(),
    };

    // ── Anomaly Detection ──────────────────────────────────────────────────
    let is_empty_output = output_length < MINIMUM_MEANINGFUL_OUTPUT;

    let output_lower = output_text.to_lowercase();
    let has_error_signal = ERROR_PATTERNS.iter().any(|p| output_lower.contains(p));

    // Check if this is a CAF role agent with an expected output file
    let re = Regex::new(r"(builder|validator|debugger)-(\d+)").unwrap();
    let (output_file_missing, expected_file) =
        if let Some(caps) = re.captures(&agent_name.to_lowercase()) {
            let role = caps.get(1).map(|m| m.as_str()).unwrap_or("");
            let iteration = caps.get(2).map(|m| m.as_str()).unwrap_or("");
            let path = format!("/tmp/caf_{}_{}.md", role, iteration);
            let missing = !std::path::Path::new(&path).exists();
            (missing, Some(path))
        } else {
            (false, None)
        };

    let mut anomaly_types: Vec<String> = Vec::new();
    if is_empty_output {
        anomaly_types.push("empty_output".to_string());
    }
    if has_error_signal {
        anomaly_types.push("error_signal".to_string());
    }
    if output_file_missing {
        anomaly_types.push("missing_output_file".to_string());
    }

    // ── Build tracking record ──────────────────────────────────────────────
    let timestamp = Utc::now().to_rfc3339();
    let record = serde_json::json!({
        "timestamp": timestamp,
        "agent_name": agent_name,
        "tool_name": tool_name,
        "output_length": output_length,
        "input_keys": input_keys,
        "anomalies": anomaly_types,
    });

    let _ = try_append_jsonl(&tracking_path(), &record);

    // ── Surface anomalies ──────────────────────────────────────────────────
    if !anomaly_types.is_empty() {
        // Write to watchdog state file
        let watchdog_path = std::path::Path::new("/tmp/caf_watchdog.md");
        let mut error_detail = anomaly_types.join("+");
        if has_error_signal {
            let excerpt: String = output_text
                .chars()
                .take(120)
                .collect::<String>()
                .replace('\n', " ");
            error_detail.push(':');
            error_detail.push_str(&excerpt);
        }
        let watchdog_line = format!(
            "[{}] AGENT:{} STATUS:FAILED TASK:hook_detected ERROR:{}\n",
            timestamp, agent_name, error_detail
        );
        let _ = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(watchdog_path)
            .and_then(|mut f| {
                use std::io::Write;
                f.write_all(watchdog_line.as_bytes())
            });

        // Write to persistent alert log
        let error_excerpt = if has_error_signal {
            Some(output_text.chars().take(200).collect::<String>())
        } else {
            None
        };
        let alert = serde_json::json!({
            "timestamp": timestamp,
            "agent_name": agent_name,
            "anomaly_types": anomaly_types,
            "output_length": output_length,
            "expected_file": expected_file,
            "error_excerpt": error_excerpt,
        });
        let _ = try_append_jsonl(&alerts_path(), &alert);
    }

    write_output(&HookOutput::empty());
}
