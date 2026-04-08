use serde::{Deserialize, Serialize};
use serde_json::Value;

/// All hooks receive one of these event-specific payloads via stdin.
/// Uses untagged deserialization so we can parse any event into a generic Value
/// and then interpret the fields based on hook_event_name.
#[derive(Debug, Deserialize, Clone)]
#[serde(untagged)]
pub enum HookInput {
    PreToolUse {
        session_id: String,
        tool_name: String,
        tool_input: Value,
        cwd: Option<String>,
        hook_event_name: Option<String>,
    },
    PostToolUse {
        session_id: String,
        tool_name: String,
        tool_input: Value,
        tool_response: ToolResponse,
        cwd: Option<String>,
        hook_event_name: Option<String>,
    },
    Stop {
        session_id: String,
        cwd: Option<String>,
        stop_reason: Option<String>,
        stop_hook_active: Option<bool>,
        hook_event_name: Option<String>,
    },
    StopFailure {
        session_id: String,
        error: Option<String>,
        hook_event_name: Option<String>,
    },
    UserPromptSubmit {
        session_id: String,
        prompt: Option<String>,
        hook_event_name: Option<String>,
    },
    SubagentStart {
        session_id: String,
        agent_id: Option<String>,
        agent_type: Option<String>,
        tool_name: Option<String>,
        tool_input: Option<Value>,
        hook_event_name: Option<String>,
    },
    SubagentStop {
        session_id: String,
        agent_id: Option<String>,
        agent_type: Option<String>,
        tool_name: Option<String>,
        tool_input: Option<Value>,
        tool_output: Option<Value>,
        agent_transcript_path: Option<String>,
        hook_event_name: Option<String>,
    },
    TaskCompleted {
        session_id: String,
        task_id: Option<String>,
        task_subject: Option<String>,
        task_description: Option<String>,
        teammate_name: Option<String>,
        status: Option<String>,
        hook_event_name: Option<String>,
    },
    FileChanged {
        session_id: String,
        file_path: Option<String>,
        file: Option<Value>,
        hook_event_name: Option<String>,
    },
    PostCompact {
        session_id: String,
        trigger: Option<String>,
        hook_event_name: Option<String>,
    },
    Generic(Value),
}

/// tool_response can be a dict with output/isError fields, or a raw string
#[derive(Debug, Deserialize, Clone)]
#[serde(untagged)]
pub enum ToolResponse {
    Structured {
        output: Option<String>,
        #[serde(rename = "isError")]
        is_error: Option<bool>,
        stderr: Option<String>,
        stdout: Option<String>,
    },
    Raw(String),
}

impl ToolResponse {
    pub fn output_str(&self) -> &str {
        match self {
            ToolResponse::Structured { output, .. } => output.as_deref().unwrap_or(""),
            ToolResponse::Raw(s) => s.as_str(),
        }
    }

    pub fn is_error(&self) -> bool {
        match self {
            ToolResponse::Structured { is_error, .. } => is_error.unwrap_or(false),
            ToolResponse::Raw(_) => false,
        }
    }
}

/// Output for context injection — matches the hookSpecificOutput JSON shape
#[derive(Debug, Serialize)]
pub struct HookOutput {
    #[serde(rename = "hookSpecificOutput", skip_serializing_if = "Option::is_none")]
    pub hook_specific_output: Option<HookSpecificOutput>,
}

#[derive(Debug, Serialize)]
pub struct HookSpecificOutput {
    #[serde(rename = "hookEventName", skip_serializing_if = "Option::is_none")]
    pub hook_event_name: Option<String>,
    #[serde(rename = "additionalContext", skip_serializing_if = "Option::is_none")]
    pub additional_context: Option<String>,
    #[serde(rename = "permissionDecision", skip_serializing_if = "Option::is_none")]
    pub permission_decision: Option<String>,
    #[serde(rename = "permissionDecisionReason", skip_serializing_if = "Option::is_none")]
    pub permission_decision_reason: Option<String>,
}

impl HookOutput {
    /// Empty output — allow with no context injection
    pub fn empty() -> Self {
        HookOutput { hook_specific_output: None }
    }

    /// Inject additional context into Claude's context window
    pub fn inject_context(event_name: impl Into<String>, context: impl Into<String>) -> Self {
        HookOutput {
            hook_specific_output: Some(HookSpecificOutput {
                hook_event_name: Some(event_name.into()),
                additional_context: Some(context.into()),
                permission_decision: None,
                permission_decision_reason: None,
            }),
        }
    }
}

/// Circuit breaker states matching Python enum CircuitState
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CircuitState {
    Closed,
    Open,
    HalfOpen,
}

impl Default for CircuitState {
    fn default() -> Self {
        CircuitState::Closed
    }
}

/// Per-hook circuit breaker state — mirrors Python HookState dataclass
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HookState {
    pub state: CircuitState,
    pub failure_count: u64,
    pub consecutive_failures: u64,
    pub consecutive_successes: u64,
    pub first_failure: Option<String>,
    pub last_failure: Option<String>,
    pub last_success: Option<String>,
    pub last_error: Option<String>,
    pub disabled_at: Option<String>,
    pub retry_after: Option<String>,
}

impl Default for HookState {
    fn default() -> Self {
        HookState {
            state: CircuitState::Closed,
            failure_count: 0,
            consecutive_failures: 0,
            consecutive_successes: 0,
            first_failure: None,
            last_failure: None,
            last_success: None,
            last_error: None,
            disabled_at: None,
            retry_after: None,
        }
    }
}

/// Global statistics block in hook_state.json
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GlobalStats {
    pub total_executions: u64,
    pub total_failures: u64,
    pub hooks_disabled: u64,
    pub last_updated: String,
}

impl Default for GlobalStats {
    fn default() -> Self {
        GlobalStats {
            total_executions: 0,
            total_failures: 0,
            hooks_disabled: 0,
            last_updated: chrono::Utc::now().to_rfc3339(),
        }
    }
}

/// Full hook_state.json contents
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct HookStateData {
    pub hooks: std::collections::HashMap<String, HookState>,
    pub global_stats: GlobalStats,
}
