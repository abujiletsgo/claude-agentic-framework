/// Auto Error Analyzer — PostToolUse hook.
///
/// Python equivalent: global-hooks/framework/automation/auto_error_analyzer.py (183 LOC)
///
/// Behavior:
/// - Only processes Bash tool use
/// - Checks if command matches test command patterns (pytest, cargo test, etc.)
/// - If the command failed (non-zero exit code or stderr with error keywords), prints
///   a structured error analysis notice to stderr
/// - Always exits 0
use regex::Regex;
use std::sync::OnceLock;

use crate::io::{read_stdin_value, write_output};

// Test command patterns
static TEST_PATTERNS_STR: &[&str] = &[
    r"(?i)\bpytest\b",
    r"(?i)\bpy\.test\b",
    r"(?i)\bnpm\s+test\b",
    r"(?i)\bnpm\s+run\s+test\b",
    r"(?i)\byarn\s+test\b",
    r"(?i)\bgo\s+test\b",
    r"(?i)\bcargo\s+test\b",
    r"(?i)\bjest\b",
    r"(?i)\bmake\s+test\b",
    r"(?i)\buv\s+run\s+pytest\b",
    r"(?i)\bbun\s+test\b",
];

static TEST_PATTERNS: OnceLock<Vec<Regex>> = OnceLock::new();

fn test_patterns() -> &'static Vec<Regex> {
    TEST_PATTERNS.get_or_init(|| {
        TEST_PATTERNS_STR
            .iter()
            .filter_map(|p| Regex::new(p).ok())
            .collect()
    })
}

fn is_test_command(command: &str) -> bool {
    if command.is_empty() {
        return false;
    }
    let lower = command.to_lowercase();
    test_patterns().iter().any(|pat| pat.is_match(&lower))
}

const MAX_INJECTION_CHARS: usize = 1500;

const ERROR_KEYWORDS: &[&str] = &[
    "error", "exception", "traceback", "failed", "assert", "expected", "got", "stack trace",
];

fn extract_error_context(stderr: &str, stdout: &str, exit_code: i64) -> String {
    let mut output = String::new();

    if !stderr.is_empty() {
        output.push_str("=== STDERR ===\n");
        output.push_str(stderr);
        output.push_str("\n\n");
    }
    if !stdout.is_empty() {
        output.push_str("=== STDOUT ===\n");
        output.push_str(stdout);
        output.push_str("\n\n");
    }
    output.push_str(&format!("Exit Code: {}\n", exit_code));

    if output.len() <= 5000 {
        return output;
    }

    // Try to extract lines with error indicators
    let lines: Vec<&str> = output.lines().collect();
    let mut error_lines: Vec<String> = Vec::new();
    let n = lines.len();

    for (i, line) in lines.iter().enumerate() {
        let line_lower = line.to_lowercase();
        if ERROR_KEYWORDS.iter().any(|kw| line_lower.contains(kw)) {
            let start = if i >= 5 { i - 5 } else { 0 };
            let end = (i + 6).min(n);
            for j in start..end {
                error_lines.push(lines[j].to_string());
            }
        }
    }

    if !error_lines.is_empty() {
        let limited: Vec<String> = error_lines.into_iter().take(200).collect();
        limited.join("\n")
    } else {
        output.chars().take(5000).collect()
    }
}

pub fn run() {
    let data = read_stdin_value();

    // Only process Bash tool
    let tool_name = data
        .get("tool_name")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    if tool_name != "Bash" {
        write_output(&serde_json::json!({}));
        return;
    }

    // Get command
    let tool_input = data
        .get("tool_input")
        .cloned()
        .unwrap_or(serde_json::json!({}));
    let tool_input = if let Some(s) = tool_input.as_str() {
        serde_json::from_str(s).unwrap_or(serde_json::json!({}))
    } else {
        tool_input
    };

    let command = tool_input
        .get("command")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    if !is_test_command(command) {
        write_output(&serde_json::json!({}));
        return;
    }

    // Parse tool_response
    let tool_response = data.get("tool_response");

    // Build a unified object with stdout, stderr, exit_code
    let response_obj: serde_json::Value = match tool_response {
        Some(serde_json::Value::Object(map)) => serde_json::Value::Object(map.clone()),
        Some(serde_json::Value::String(s)) => {
            // Try JSON parse, otherwise treat as stdout
            serde_json::from_str(s).unwrap_or_else(|_| {
                serde_json::json!({"stdout": s})
            })
        }
        _ => serde_json::json!({}),
    };

    let stdout = response_obj
        .get("stdout")
        .or_else(|| response_obj.get("output"))
        .and_then(|v| v.as_str())
        .unwrap_or("");
    let stderr = response_obj
        .get("stderr")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    // Determine exit code
    let exit_code: Option<i64> = response_obj
        .get("exit_code")
        .and_then(|v| v.as_i64());

    let failed = match exit_code {
        Some(0) => false,
        Some(_) => true,
        None => {
            // No exit code: check if stderr contains error keywords
            if stderr.is_empty() {
                // Can't determine — skip
                write_output(&serde_json::json!({}));
                return;
            }
            let stderr_lower = stderr.to_lowercase();
            ERROR_KEYWORDS.iter().any(|kw| stderr_lower.contains(kw))
        }
    };

    if !failed {
        write_output(&serde_json::json!({}));
        return;
    }

    let effective_exit_code = exit_code.unwrap_or(1);
    let raw_context = extract_error_context(stderr, stdout, effective_exit_code);
    let error_context = if raw_context.len() > MAX_INJECTION_CHARS {
        format!("{}... [truncated]", &raw_context[..MAX_INJECTION_CHARS])
    } else {
        raw_context
    };

    eprintln!();
    eprintln!("{}", "=".repeat(60));
    eprintln!("AUTO ERROR ANALYSIS");
    eprintln!("{}", "=".repeat(60));
    eprintln!("Command: {}", command);
    eprintln!();
    eprintln!("Error context ({} chars):", error_context.len());
    eprintln!("{}", "-".repeat(60));
    eprintln!("{}", error_context);
    eprintln!("{}", "-".repeat(60));
    eprintln!();
    eprintln!("  Run /error-analyzer for detailed analysis");
    eprintln!("{}", "=".repeat(60));
    eprintln!();

    write_output(&serde_json::json!({}));
}
