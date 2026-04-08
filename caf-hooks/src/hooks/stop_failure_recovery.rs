/// Stop Failure Recovery — StopFailure hook.
///
/// Python equivalent: global-hooks/framework/automation/stop_failure_recovery.py (69 LOC)
///
/// Behavior:
/// - Classify error type from hook_event_name + error fields
/// - Log to ~/.claude/data/stop_failures.jsonl
/// - Inject recovery advice as additionalContext
/// - Always exits 0
use chrono::Utc;
use serde::Serialize;
use serde_json::Value;

use crate::io::{read_stdin_value, try_append_jsonl, write_output};
use crate::state::stop_failures_path;
use crate::types::HookOutput;

#[derive(Serialize)]
struct StopFailureRecord<'a> {
    ts: String,
    error_type: &'a str,
    session_id: &'a str,
}

struct Recovery {
    key: &'static str,
    message: &'static str,
}

const RECOVERY_TABLE: &[Recovery] = &[
    Recovery {
        key: "rate_limit",
        message: "[Rate Limit] API rate limit hit. Wait ~60s before retrying. \
            Reduce request frequency or batch operations to avoid throttling.",
    },
    Recovery {
        key: "authentication_failed",
        message: "[Auth Failed] Authentication error. Re-authenticate: \
            run `claude auth` or check your API key / session token.",
    },
    Recovery {
        key: "billing_error",
        message: "[Billing] Billing issue preventing API access. \
            Check plan status and payment method at console.anthropic.com.",
    },
    Recovery {
        key: "server_error",
        message: "[Server Error] Anthropic API returned a server-side error. \
            This is usually transient — retry in a few seconds.",
    },
    Recovery {
        key: "max_output_tokens",
        message: "[Max Output] Response hit the output token limit. \
            Consider breaking the task into smaller pieces or using /rlm for iterative work.",
    },
];

/// Default fallback message (mirrors Python's RECOVERY["server_error"] fallback)
const DEFAULT_MESSAGE: &str = "[Server Error] Anthropic API returned a server-side error. \
    This is usually transient — retry in a few seconds.";

fn classify(data: &Value) -> &'static str {
    let hook_event = data.get("hook_event_name")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    let error = data.get("error")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    let combined = format!("{} {}", hook_event, error).to_lowercase();
    for r in RECOVERY_TABLE {
        if combined.contains(r.key) {
            return r.key;
        }
    }
    "server_error"
}

fn get_message(error_type: &str) -> &'static str {
    for r in RECOVERY_TABLE {
        if r.key == error_type {
            return r.message;
        }
    }
    DEFAULT_MESSAGE
}

pub fn run() {
    let data: Value = read_stdin_value();

    let error_type = classify(&data);
    let session_id = data.get("session_id")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown")
        .to_string();

    // Log to JSONL
    let record = StopFailureRecord {
        ts: Utc::now().to_rfc3339(),
        error_type,
        session_id: &session_id,
    };
    try_append_jsonl(&stop_failures_path(), &record);

    // Output recovery advice
    let msg = get_message(error_type);
    let output = HookOutput::inject_context("StopFailure", msg);
    write_output(&output);
}
