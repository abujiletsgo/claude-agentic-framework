/// Audit Config Change — ConfigChange hook.
///
/// Python equivalent: global-hooks/framework/security/audit_config_change.py
///
/// Behavior:
/// - Reads ConfigChange event from stdin JSON
/// - Extracts change details from the payload (and nested tool_input)
/// - Builds an audit record with timestamp, event, change_keys, and details
/// - Appends audit record to ~/.claude/data/logs/config_audit.jsonl
/// - If sensitive keys (hooks, permissions, allow, deny) are touched, writes
///   a warning message to stderr
/// - Always outputs {} and exits 0 (never blocks)
use std::collections::HashSet;
use std::path::PathBuf;

use chrono::Utc;
use serde_json::Value;

use crate::io::{read_stdin_value, try_append_jsonl, write_output};
use crate::types::HookOutput;

/// Sensitive config keys — matches Python SENSITIVE_KEYS exactly
const SENSITIVE_KEYS: &[&str] = &["hooks", "permissions", "allow", "deny"];

fn audit_log_path() -> PathBuf {
    let home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("/tmp"));
    home.join(".claude")
        .join("data")
        .join("logs")
        .join("config_audit.jsonl")
}

/// Collect all top-level keys plus nested keys from a JSON object.
/// Matches Python check_sensitive_fields() traversal.
fn collect_keys(obj: &Value) -> HashSet<String> {
    let mut keys = HashSet::new();
    if let Value::Object(map) = obj {
        for (k, v) in map.iter() {
            keys.insert(k.clone());
            // Also check nested structures (one level deep — matches Python)
            if let Value::Object(nested) = v {
                for nk in nested.keys() {
                    keys.insert(nk.clone());
                }
            }
        }
    }
    keys
}

/// Return sorted list of sensitive keys found in this object.
fn find_sensitive_hits(obj: &Value) -> Vec<String> {
    let all_keys = collect_keys(obj);
    let sensitive: HashSet<&str> = SENSITIVE_KEYS.iter().copied().collect();
    let mut hits: Vec<String> = all_keys
        .iter()
        .filter(|k| sensitive.contains(k.as_str()))
        .cloned()
        .collect();
    hits.sort();
    hits
}

pub fn run() {
    let data: Value = read_stdin_value();

    // Extract change_data and tool_input (matches Python main() exactly)
    let change_data = match &data {
        Value::Object(_) => data.clone(),
        _ => Value::Object(Default::default()),
    };

    let tool_input = change_data
        .get("tool_input")
        .cloned()
        .unwrap_or_else(|| change_data.clone());

    // Build change_keys list (top-level keys of change_data)
    let change_keys: Vec<String> = match &change_data {
        Value::Object(map) => map.keys().cloned().collect(),
        _ => Vec::new(),
    };

    let timestamp = Utc::now().to_rfc3339();

    // Build audit record (matches Python record dict exactly)
    let record = serde_json::json!({
        "timestamp": timestamp,
        "event": "config_change",
        "change_keys": change_keys,
        "details": change_data,
    });

    let _ = try_append_jsonl(&audit_log_path(), &record);

    // Check for sensitive field modifications and warn (matches Python)
    let mut all_warnings: Vec<String> = Vec::new();

    let hits = find_sensitive_hits(&change_data);
    if !hits.is_empty() {
        all_warnings.push(format!(
            "[SECURITY AUDIT] Config change modifies sensitive sections: {}",
            hits.join(", ")
        ));
    }

    // Also check tool_input separately (matches Python: warnings.extend(check_sensitive_fields(tool_input)))
    let tool_hits = find_sensitive_hits(&tool_input);
    if !tool_hits.is_empty() {
        all_warnings.push(format!(
            "[SECURITY AUDIT] Config change modifies sensitive sections: {}",
            tool_hits.join(", ")
        ));
    }

    for warning in &all_warnings {
        eprintln!("{}", warning);
    }

    write_output(&HookOutput::empty());
}
