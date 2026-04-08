/// Auto Escalate — PostToolUse hook.
///
/// Python equivalent: global-hooks/framework/automation/auto_escalate.py (219 LOC)
///
/// Behavior:
/// - Read JSON state from ~/.claude/auto_escalate_state.json (session-scoped)
/// - Increment counters based on current tool use:
///     tool_use_count always incremented
///     task_count     incremented on TaskCreate
///     error_count    incremented on Bash with non-zero exit_code
///     files_modified list appended on Edit/Write/MultiEdit
/// - If 2+ thresholds exceeded AND not already escalated this session:
///     write escalation message to stderr, mark escalated=true, save state
/// - Always exits 0 (never blocks)
///
/// Thresholds:
///   task_count     >= 4
///   error_count    >= 3
///   files_modified >= 8 unique files
///   tool_use_count >= 25
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::path::PathBuf;

use crate::io::read_stdin_value;

// ── Thresholds ────────────────────────────────────────────────────────────────

const THRESHOLD_TASK_COUNT: u64 = 4;
const THRESHOLD_ERROR_COUNT: u64 = 3;
const THRESHOLD_FILES_MODIFIED: usize = 8;
const THRESHOLD_TOOL_USE_COUNT: u64 = 25;
const MIN_SIGNALS_TO_ESCALATE: usize = 2;

// ── State ─────────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
struct EscalateState {
    session_id: String,
    task_count: u64,
    error_count: u64,
    files_modified: Vec<String>,
    tool_use_count: u64,
    escalated: bool,
    escalation_turn: Option<u64>,
    created_at: String,
}

impl EscalateState {
    fn new(session_id: &str) -> Self {
        let now = chrono::Utc::now().to_rfc3339();
        EscalateState {
            session_id: session_id.to_string(),
            task_count: 0,
            error_count: 0,
            files_modified: Vec::new(),
            tool_use_count: 0,
            escalated: false,
            escalation_turn: None,
            created_at: now,
        }
    }
}

fn state_path() -> PathBuf {
    let mut p = dirs::home_dir().unwrap_or_else(|| PathBuf::from("."));
    p.push(".claude");
    p.push("auto_escalate_state.json");
    p
}

fn load_state(session_id: &str) -> EscalateState {
    let path = state_path();
    if path.exists() {
        if let Ok(contents) = std::fs::read_to_string(&path) {
            if let Ok(state) = serde_json::from_str::<EscalateState>(&contents) {
                if state.session_id == session_id {
                    return state;
                }
            }
        }
    }
    EscalateState::new(session_id)
}

fn save_state(state: &EscalateState) {
    let path = state_path();
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    if let Ok(json) = serde_json::to_string_pretty(state) {
        let _ = std::fs::write(&path, json);
    }
}

// ── Signal counting ───────────────────────────────────────────────────────────

fn update_signals(state: &mut EscalateState, hook_input: &Value) {
    let tool_name = hook_input.get("tool_name").and_then(|v| v.as_str()).unwrap_or("");

    // Parse tool_input — may be a JSON object or a JSON-encoded string
    let tool_input: Value = {
        let raw = hook_input.get("tool_input").cloned().unwrap_or(Value::Null);
        if raw.is_object() {
            raw
        } else if let Some(s) = raw.as_str() {
            serde_json::from_str(s).unwrap_or(Value::Null)
        } else {
            Value::Null
        }
    };

    state.tool_use_count += 1;

    // TaskCreate → multi-task indicator
    if tool_name == "TaskCreate" {
        state.task_count += 1;
    }

    // Bash failure → error indicator
    if tool_name == "Bash" {
        let tool_response = hook_input.get("tool_response").cloned().unwrap_or(Value::Null);
        let resp: Value = if tool_response.is_object() {
            tool_response
        } else if let Some(s) = tool_response.as_str() {
            serde_json::from_str(s).unwrap_or(Value::Null)
        } else {
            Value::Null
        };
        let exit_code = resp.get("exit_code").and_then(|v| v.as_i64()).unwrap_or(0);
        if exit_code != 0 {
            state.error_count += 1;
        }
    }

    // Edit/Write/MultiEdit → file modification indicator
    if matches!(tool_name, "Edit" | "Write" | "MultiEdit") {
        let file_path = tool_input
            .get("file_path")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        if !file_path.is_empty() && !state.files_modified.contains(&file_path.to_string()) {
            state.files_modified.push(file_path.to_string());
        }
    }
}

// ── Escalation check ─────────────────────────────────────────────────────────

fn check_escalation(state: &EscalateState) -> (bool, Vec<String>) {
    if state.escalated {
        return (false, Vec::new());
    }

    let mut triggered: Vec<String> = Vec::new();

    if state.task_count >= THRESHOLD_TASK_COUNT {
        triggered.push(format!("{} tasks created", state.task_count));
    }
    if state.error_count >= THRESHOLD_ERROR_COUNT {
        triggered.push(format!("{} errors encountered", state.error_count));
    }
    if state.files_modified.len() >= THRESHOLD_FILES_MODIFIED {
        triggered.push(format!("{} files modified", state.files_modified.len()));
    }
    if state.tool_use_count >= THRESHOLD_TOOL_USE_COUNT {
        triggered.push(format!("{} tool uses", state.tool_use_count));
    }

    let should_escalate = triggered.len() >= MIN_SIGNALS_TO_ESCALATE;
    (should_escalate, triggered)
}

// ── Escalation output ─────────────────────────────────────────────────────────

fn emit_escalation(triggered_signals: &[String]) {
    let signals_str = triggered_signals.join(", ");
    // Pad/truncate to 60 chars to fit in the box (matches Python: signals_str[:60].ljust(60))
    let padded = format!("{:<60}", &signals_str[..signals_str.len().min(60)]);
    let msg = format!(
        "\u{2554}{}\u{2557}\n\
         \u{2551}  \u{1F916} AUTO-ESCALATION: Mid-task complexity threshold exceeded      \u{2551}\n\
         \u{2560}{}\u{2563}\n\
         \u{2551}  Signals detected: {}\u{2551}\n\
         \u{2551}                                                                  \u{2551}\n\
         \u{2551}  MANDATORY: Spawn the orchestrator to coordinate remaining work. \u{2551}\n\
         \u{2551}                                                                  \u{2551}\n\
         \u{2551}  Use the Task tool NOW:                                          \u{2551}\n\
         \u{2551}    Task(                                                         \u{2551}\n\
         \u{2551}      subagent_type=\"orchestrator\",                               \u{2551}\n\
         \u{2551}      description=\"Coordinate remaining work\",                    \u{2551}\n\
         \u{2551}      prompt=\"<summarize what's been done and what remains>\"      \u{2551}\n\
         \u{2551}    )                                                             \u{2551}\n\
         \u{2551}                                                                  \u{2551}\n\
         \u{2551}  The orchestrator will distribute remaining work to specialists  \u{2551}\n\
         \u{2551}  and synthesize results. Do NOT continue direct execution.       \u{2551}\n\
         \u{255A}{}\u{255D}",
        "\u{2550}".repeat(66),
        "\u{2550}".repeat(66),
        padded,
        "\u{2550}".repeat(66),
    );
    eprintln!("{}", msg);
}

// ── Main ──────────────────────────────────────────────────────────────────────

pub fn run() {
    let data: Value = read_stdin_value();

    if data.is_null() {
        println!("{{}}");
        return;
    }

    let session_id = data
        .get("session_id")
        .and_then(|v| v.as_str())
        .or_else(|| std::env::var("CLAUDE_SESSION_ID").ok().as_deref().map(|_| ""))
        .unwrap_or("unknown");

    // Re-fetch via env if not in JSON (mirrors Python fallback)
    let session_id = if session_id.is_empty() {
        std::env::var("CLAUDE_SESSION_ID").unwrap_or_else(|_| "unknown".to_string())
    } else {
        session_id.to_string()
    };

    let mut state = load_state(&session_id);
    update_signals(&mut state, &data);

    let (should_escalate, triggered) = check_escalation(&state);

    if should_escalate {
        state.escalated = true;
        state.escalation_turn = Some(state.tool_use_count);
        emit_escalation(&triggered);
    }

    save_state(&state);
    println!("{{}}");
}
