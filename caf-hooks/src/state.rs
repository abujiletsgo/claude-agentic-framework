use std::path::PathBuf;

/// Resolve the ~/.claude/ directory.
pub fn claude_dir() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_else(|| PathBuf::from("/tmp"))
        .join(".claude")
}

/// Resolve ~/.claude/data/
pub fn claude_data_dir() -> PathBuf {
    claude_dir().join("data")
}

/// Path to the circuit breaker state file: ~/.claude/hook_state.json
pub fn hook_state_path() -> PathBuf {
    claude_dir().join("hook_state.json")
}

/// Path to stop failures log: ~/.claude/data/stop_failures.jsonl
pub fn stop_failures_path() -> PathBuf {
    claude_data_dir().join("stop_failures.jsonl")
}

/// Path to file changes log: ~/.claude/data/file_changes.jsonl
pub fn file_changes_path() -> PathBuf {
    claude_data_dir().join("file_changes.jsonl")
}

/// Path to task completions log: ~/.claude/data/task_completions.jsonl
pub fn task_completions_path() -> PathBuf {
    claude_data_dir().join("task_completions.jsonl")
}

/// Path to compressed context directory: ~/.claude/data/compressed_context/
pub fn compressed_context_dir() -> PathBuf {
    claude_data_dir().join("compressed_context")
}
