/// Auto Refine After Review — PostToolUse hook.
///
/// Python equivalent: global-hooks/framework/automation/auto_refine.py (113 LOC)
///
/// Behavior:
/// - Detects PostToolUse on Skill(skill="review"/"code-review") or Bash with review script
/// - Counts WARNING/ERROR/CRITICAL findings in the tool_response
/// - If findings >= 1, prints a notice to stderr (does NOT inject context)
/// - Always exits 0
use regex::Regex;
use std::sync::OnceLock;

use crate::io::{read_stdin_value, write_output};

static WARNING_BRACKET: OnceLock<Regex> = OnceLock::new();
static SEVERITY_KEYWORD: OnceLock<Regex> = OnceLock::new();

fn warning_bracket() -> &'static Regex {
    WARNING_BRACKET.get_or_init(|| {
        Regex::new(r"(?i)\[(warning|error|critical|!!+)\]").expect("valid regex")
    })
}

fn severity_keyword() -> &'static Regex {
    SEVERITY_KEYWORD.get_or_init(|| {
        Regex::new(r"(?i)severity[:\s]+(warning|error|critical)").expect("valid regex")
    })
}

fn count_findings(tool_result: &str) -> usize {
    if tool_result.is_empty() {
        return 0;
    }
    let text = tool_result.to_lowercase();
    let warning_count = warning_bracket().find_iter(&text).count();
    let severity_count = severity_keyword().find_iter(&text).count();
    warning_count.max(severity_count)
}

fn is_review_command(tool_name: &str, tool_input: &serde_json::Value) -> bool {
    if tool_name == "Skill" {
        let skill = tool_input
            .get("skill")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        return matches!(skill.to_lowercase().as_str(), "review" | "code-review");
    }

    if tool_name == "Bash" {
        let command = tool_input
            .get("command")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_lowercase();
        if command.contains("review") {
            return command.contains("review.py")
                || command.contains("review_engine")
                || command.contains("/review");
        }
    }

    false
}

pub fn run() {
    let data = read_stdin_value();

    let tool_name = data
        .get("tool_name")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    let tool_input = data
        .get("tool_input")
        .cloned()
        .unwrap_or(serde_json::json!({}));

    // Parse tool_input if it's a JSON string
    let tool_input = if let Some(s) = tool_input.as_str() {
        serde_json::from_str(s).unwrap_or(serde_json::json!({}))
    } else {
        tool_input
    };

    if !is_review_command(tool_name, &tool_input) {
        write_output(&serde_json::json!({}));
        return;
    }

    // Extract tool_response as string
    let tool_response = data.get("tool_response");
    let response_str = match tool_response {
        Some(serde_json::Value::String(s)) => s.clone(),
        Some(serde_json::Value::Object(_)) => {
            tool_response
                .and_then(|v| v.get("output"))
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string()
        }
        Some(other) => other.to_string(),
        None => String::new(),
    };

    let issue_count = count_findings(&response_str);

    if issue_count > 0 {
        eprintln!();
        eprintln!("{}", "=".repeat(60));
        eprintln!("CODE REVIEW COMPLETED");
        eprintln!("{}", "=".repeat(60));
        eprintln!("Found {} issue(s) with severity >= WARNING", issue_count);
        eprintln!();
        eprintln!("  Run /refine to auto-fix these issues");
        eprintln!("{}", "=".repeat(60));
        eprintln!();
    }

    write_output(&serde_json::json!({}));
}
