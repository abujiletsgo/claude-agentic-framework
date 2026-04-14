/// Damage Control — PreToolUse security hook.
///
/// Python equivalent: global-hooks/damage-control/unified-damage-control.py
///
/// Behavior:
/// - Loads pattern config from patterns.yaml (project-local first, then script-relative)
/// - For Bash tool: checks command against dangerous regex patterns + path access zones
/// - For Edit/Write tools: checks file_path against zero-access and read-only zones
/// - Exit code 2 = BLOCK (writes to stderr explaining why)
/// - Exit code 0 = ALLOW (or fail-open on any internal error)
///
/// Pattern matching is case-insensitive (re.IGNORECASE in Python).
use std::env;
use std::path::{Path, PathBuf};

use regex::Regex;
use serde::Deserialize;
use serde_json::Value;

use crate::io::read_stdin_value;

// ---------------------------------------------------------------------------
// Config types (patterns.yaml structure)
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
struct DamageControlConfig {
    #[serde(default)]
    bash_tool_patterns: Vec<BashPattern>,
    #[serde(default)]
    zero_access_paths: Vec<String>,
    #[serde(default)]
    read_only_paths: Vec<String>,
    #[serde(default)]
    no_delete_paths: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct BashPattern {
    pattern: String,
    reason: String,
    #[serde(default)]
    ask: bool,
}

// ---------------------------------------------------------------------------
// Config loading
// ---------------------------------------------------------------------------

fn get_config_path() -> PathBuf {
    // Check CLAUDE_PROJECT_DIR env var first (project-local override)
    if let Ok(project_dir) = env::var("CLAUDE_PROJECT_DIR") {
        let p = PathBuf::from(&project_dir)
            .join(".claude")
            .join("hooks")
            .join("damage-control")
            .join("patterns.yaml");
        if p.exists() {
            return p;
        }
    }

    // CAF_HOOKS_DIR env var — primary candidate
    if let Ok(dir) = std::env::var("CAF_HOOKS_DIR") {
        let p = PathBuf::from(dir).join("patterns.yaml");
        if p.exists() {
            return p;
        }
    }

    // Script-relative: look in the same dir as this binary, and parent dirs
    // In production, the binary lives alongside the global-hooks dir
    // Try the canonical location relative to CLAUDE_PROJECT_DIR or current dir
    let candidates = [
        // Relative to CWD
        PathBuf::from("global-hooks/damage-control/patterns.yaml"),
        PathBuf::from("damage-control/patterns.yaml"),
        PathBuf::from("patterns.yaml"),
    ];

    for c in &candidates {
        if c.exists() {
            return c.clone();
        }
    }

    // Default (may not exist — load_config handles that gracefully)
    PathBuf::from("patterns.yaml")
}

fn load_config() -> DamageControlConfig {
    let path = get_config_path();
    if !path.exists() {
        eprintln!("[WARN] damage-control: patterns.yaml not found at any candidate path — running with ZERO patterns. Set CAF_HOOKS_DIR env var.");
        return DamageControlConfig::default();
    }
    let text = match std::fs::read_to_string(&path) {
        Ok(t) => t,
        Err(_) => return DamageControlConfig::default(),
    };
    // serde_yaml not available — parse YAML manually using a simple approach.
    // Since we can't add serde_yaml, we implement a targeted YAML parser for
    // the known structure of patterns.yaml.
    parse_patterns_yaml(&text)
}

// ---------------------------------------------------------------------------
// Minimal YAML parser for patterns.yaml
//
// The file has the structure:
//   bashToolPatterns:
//     - pattern: '...'
//       reason: ...
//       ask: true        # optional
//   zeroAccessPaths:
//     - "path"
//   readOnlyPaths:
//     - "path"
//   noDeletePaths:
//     - "path"
//
// We parse this without serde_yaml by scanning line by line.
// ---------------------------------------------------------------------------

fn parse_patterns_yaml(text: &str) -> DamageControlConfig {
    let mut config = DamageControlConfig::default();

    #[derive(PartialEq)]
    enum Section {
        None,
        BashToolPatterns,
        ZeroAccessPaths,
        ReadOnlyPaths,
        NoDeletePaths,
    }

    let mut section = Section::None;
    // current BashPattern being assembled
    let mut cur_pattern: Option<String> = None;
    let mut cur_reason: Option<String> = None;
    let mut cur_ask: bool = false;

    let flush_pattern = |p: &mut Option<String>,
                          r: &mut Option<String>,
                          ask: &mut bool,
                          vec: &mut Vec<BashPattern>| {
        if let (Some(pat), Some(reason)) = (p.take(), r.take()) {
            vec.push(BashPattern {
                pattern: pat,
                reason,
                ask: *ask,
            });
        }
        *ask = false;
    };

    for raw_line in text.lines() {
        // Strip comment-only lines
        let line = raw_line;
        let stripped = line.trim_start();

        // Skip pure comment lines
        if stripped.starts_with('#') {
            continue;
        }

        // Detect top-level section headers (no leading spaces)
        if !line.starts_with(' ') && !line.starts_with('\t') && !line.starts_with('-') {
            // Flush any in-progress bash pattern
            if section == Section::BashToolPatterns {
                flush_pattern(
                    &mut cur_pattern,
                    &mut cur_reason,
                    &mut cur_ask,
                    &mut config.bash_tool_patterns,
                );
            }

            if line.starts_with("bashToolPatterns:") {
                section = Section::BashToolPatterns;
            } else if line.starts_with("zeroAccessPaths:") {
                section = Section::ZeroAccessPaths;
            } else if line.starts_with("readOnlyPaths:") {
                section = Section::ReadOnlyPaths;
            } else if line.starts_with("noDeletePaths:") {
                section = Section::NoDeletePaths;
            } else {
                section = Section::None;
            }
            continue;
        }

        match section {
            Section::BashToolPatterns => {
                // List item start: "  - pattern: '...'"  or "  - pattern: ..."
                if stripped.starts_with("- pattern:") {
                    // Flush previous pattern
                    flush_pattern(
                        &mut cur_pattern,
                        &mut cur_reason,
                        &mut cur_ask,
                        &mut config.bash_tool_patterns,
                    );
                    let val = extract_yaml_value(stripped, "- pattern:");
                    cur_pattern = Some(val);
                } else if stripped.starts_with("pattern:") {
                    flush_pattern(
                        &mut cur_pattern,
                        &mut cur_reason,
                        &mut cur_ask,
                        &mut config.bash_tool_patterns,
                    );
                    let val = extract_yaml_value(stripped, "pattern:");
                    cur_pattern = Some(val);
                } else if stripped.starts_with("reason:") {
                    cur_reason = Some(extract_yaml_value(stripped, "reason:"));
                } else if stripped.starts_with("ask:") {
                    let val = extract_yaml_value(stripped, "ask:");
                    cur_ask = val.trim() == "true";
                }
            }
            Section::ZeroAccessPaths => {
                if let Some(val) = parse_list_item(stripped) {
                    config.zero_access_paths.push(val);
                }
            }
            Section::ReadOnlyPaths => {
                if let Some(val) = parse_list_item(stripped) {
                    config.read_only_paths.push(val);
                }
            }
            Section::NoDeletePaths => {
                if let Some(val) = parse_list_item(stripped) {
                    config.no_delete_paths.push(val);
                }
            }
            Section::None => {}
        }
    }

    // Flush last bash pattern
    if section == Section::BashToolPatterns {
        flush_pattern(
            &mut cur_pattern,
            &mut cur_reason,
            &mut cur_ask,
            &mut config.bash_tool_patterns,
        );
    }

    config
}

/// Extract the value after a YAML key prefix, stripping quotes and inline comments.
fn extract_yaml_value(line: &str, prefix: &str) -> String {
    let rest = line[prefix.len()..].trim();
    strip_yaml_quotes_and_comments(rest)
}

/// Strip leading/trailing single or double quotes from a YAML scalar.
/// Also strips inline # comments that appear after the value.
fn strip_yaml_quotes_and_comments(s: &str) -> String {
    let s = s.trim();
    // Single-quoted: everything between first and last single quote
    if s.starts_with('\'') && s.ends_with('\'') && s.len() >= 2 {
        return s[1..s.len() - 1].to_string();
    }
    // Double-quoted
    if s.starts_with('"') && s.ends_with('"') && s.len() >= 2 {
        return s[1..s.len() - 1].to_string();
    }
    // Unquoted: strip inline comment (# preceded by whitespace)
    // But be careful not to strip # inside patterns
    // Simple approach: if there's a " #" sequence, strip from there
    if let Some(idx) = s.find(" #") {
        return s[..idx].trim().to_string();
    }
    s.to_string()
}

/// Parse a YAML list item "  - value" or "  - \"value\"", return the value.
fn parse_list_item(stripped: &str) -> Option<String> {
    if stripped.starts_with("- ") {
        let val = stripped[2..].trim();
        Some(strip_yaml_quotes_and_comments(val))
    } else if stripped == "-" {
        None
    } else {
        None
    }
}

// ---------------------------------------------------------------------------
// Path matching (mirrors Python match_path)
// ---------------------------------------------------------------------------

fn is_glob_pattern(pattern: &str) -> bool {
    pattern.contains('*') || pattern.contains('?') || pattern.contains('[')
}

fn expand_home(path: &str) -> String {
    if path.starts_with("~/") {
        if let Some(home) = dirs::home_dir() {
            return format!("{}/{}", home.display(), &path[2..]);
        }
    } else if path == "~" {
        if let Some(home) = dirs::home_dir() {
            return home.display().to_string();
        }
    }
    path.to_string()
}

fn normalize_path(p: &str) -> String {
    let expanded = expand_home(p);
    // Resolve symlinks / canonicalize if possible, otherwise just normalize
    match std::fs::canonicalize(&expanded) {
        Ok(canon) => canon.display().to_string(),
        Err(_) => {
            // Manual normpath equivalent
            PathBuf::from(expanded).display().to_string()
        }
    }
}

fn match_path(file_path: &str, pattern: &str) -> bool {
    let expanded_pattern = normalize_path(pattern);
    let normalized = PathBuf::from(file_path)
        .display()
        .to_string();
    let expanded_normalized = normalize_path(&normalized);

    if is_glob_pattern(pattern) {
        let basename = Path::new(&expanded_normalized)
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("")
            .to_lowercase();
        let pattern_lower = pattern.to_lowercase();
        let expanded_lower = expanded_pattern.to_lowercase();

        // Match basename against expanded_lower glob
        if glob_match(&basename, &expanded_lower) {
            return true;
        }
        // Match basename against original pattern (lowercase)
        if glob_match(&basename, &pattern_lower) {
            return true;
        }
        // Match full path against expanded_lower glob
        if glob_match(&expanded_normalized.to_lowercase(), &expanded_lower) {
            return true;
        }
        return false;
    } else {
        // Exact path prefix match
        let ep = expanded_pattern.trim_end_matches('/');
        if expanded_normalized.starts_with(&expanded_pattern)
            || expanded_normalized == ep
        {
            return true;
        }
        false
    }
}

/// Simple glob matcher supporting * (matches non-separator chars) and ? (matches one non-separator char).
/// Mirrors the Python fnmatch behavior used for path matching.
fn glob_match(text: &str, pattern: &str) -> bool {
    glob_match_inner(text.as_bytes(), pattern.as_bytes())
}

fn glob_match_inner(text: &[u8], pattern: &[u8]) -> bool {
    match (text, pattern) {
        (_, &[]) => text.is_empty(),
        (_, &[b'*', ref rest @ ..]) => {
            // * matches any sequence of non-separator chars
            // Try matching zero characters, then one at a time
            if glob_match_inner(text, rest) {
                return true;
            }
            for i in 1..=text.len() {
                if text[i - 1] == b'/' {
                    break; // * doesn't cross directory separators in fnmatch
                }
                if glob_match_inner(&text[i..], rest) {
                    return true;
                }
            }
            false
        }
        (&[], _) => false,
        (&[tc, ref tr @ ..], &[b'?', ref pr @ ..]) => {
            if tc == b'/' {
                false
            } else {
                glob_match_inner(tr, pr)
            }
        }
        (&[tc, ref tr @ ..], &[pc, ref pr @ ..]) => {
            if tc == pc {
                glob_match_inner(tr, pr)
            } else {
                false
            }
        }
    }
}

// ---------------------------------------------------------------------------
// File path check for Edit/Write tools
// ---------------------------------------------------------------------------

enum FileCheckResult {
    Allow,
    Block(String),
}

fn check_file_path(file_path: &str, config: &DamageControlConfig) -> FileCheckResult {
    for zero_path in &config.zero_access_paths {
        if match_path(file_path, zero_path) {
            return FileCheckResult::Block(format!(
                "zero-access path {} (no operations allowed)",
                zero_path
            ));
        }
    }
    for readonly in &config.read_only_paths {
        if match_path(file_path, readonly) {
            return FileCheckResult::Block(format!("read-only path {}", readonly));
        }
    }
    FileCheckResult::Allow
}

// ---------------------------------------------------------------------------
// Strip quoted content (mirrors Python strip_quoted_content)
// ---------------------------------------------------------------------------

fn strip_quoted_content(command: &str) -> String {
    // Remove heredoc bodies (<<'EOF'...EOF or <<EOF...EOF)
    let heredoc_re = Regex::new(r"(?s)<<'?\w+'?\n.*?(?:\n|\A)\w+\n?").unwrap();
    let result = heredoc_re.replace_all(command, " ").into_owned();

    // Remove $(...) subshell content (up to 500 chars)
    let subshell_re = Regex::new(r"\$\([^)]{0,500}\)").unwrap();
    let result = subshell_re.replace_all(&result, " ").into_owned();

    // Remove backtick subshell
    let backtick_re = Regex::new(r"`[^`]{0,500}`").unwrap();
    let result = backtick_re.replace_all(&result, " ").into_owned();

    // Remove double-quoted strings
    let dq_re = Regex::new(r#""[^"\\]*(?:\\.[^"\\]*)*""#).unwrap();
    let result = dq_re.replace_all(&result, " ").into_owned();

    // Remove single-quoted strings
    let sq_re = Regex::new(r"'[^']*'").unwrap();
    sq_re.replace_all(&result, " ").into_owned()
}

// ---------------------------------------------------------------------------
// Operation patterns for path-based command checking
// (mirrors Python READ_ONLY_BLOCKED / NO_DELETE_BLOCKED)
// ---------------------------------------------------------------------------

#[derive(Clone)]
struct OpPattern {
    template: &'static str,
    operation: &'static str,
}

const WRITE_PATTERNS: &[OpPattern] = &[
    OpPattern { template: r">\s*{path}", operation: "write" },
    OpPattern { template: r"\btee\s+(?!.*-a).*{path}", operation: "write" },
];

const APPEND_PATTERNS: &[OpPattern] = &[
    OpPattern { template: r">>\s*{path}", operation: "append" },
    OpPattern { template: r"\btee\s+-a\s+.*{path}", operation: "append" },
    OpPattern { template: r"\btee\s+.*-a.*{path}", operation: "append" },
];

const EDIT_PATTERNS: &[OpPattern] = &[
    OpPattern { template: r"\bsed\s+-i.*{path}", operation: "edit" },
    OpPattern { template: r"\bperl\s+-[^\s]*i.*{path}", operation: "edit" },
    OpPattern { template: r"\bawk\s+-i\s+inplace.*{path}", operation: "edit" },
];

const MOVE_COPY_PATTERNS: &[OpPattern] = &[
    OpPattern { template: r"\bmv\s+.*\s+{path}", operation: "move" },
    OpPattern { template: r"\bcp\s+.*\s+{path}", operation: "copy" },
];

const DELETE_PATTERNS: &[OpPattern] = &[
    OpPattern { template: r"\brm\s+.*{path}", operation: "delete" },
    OpPattern { template: r"\bunlink\s+.*{path}", operation: "delete" },
    OpPattern { template: r"\brmdir\s+.*{path}", operation: "delete" },
    OpPattern { template: r"\bshred\s+.*{path}", operation: "delete" },
];

const PERMISSION_PATTERNS: &[OpPattern] = &[
    OpPattern { template: r"\bchmod\s+.*{path}", operation: "chmod" },
    OpPattern { template: r"\bchown\s+.*{path}", operation: "chown" },
    OpPattern { template: r"\bchgrp\s+.*{path}", operation: "chgrp" },
];

const TRUNCATE_PATTERNS: &[OpPattern] = &[
    OpPattern { template: r"\btruncate\s+.*{path}", operation: "truncate" },
    OpPattern { template: r":\s*>\s*{path}", operation: "truncate" },
];

fn read_only_blocked() -> Vec<OpPattern> {
    let mut v = Vec::new();
    v.extend_from_slice(WRITE_PATTERNS);
    v.extend_from_slice(APPEND_PATTERNS);
    v.extend_from_slice(EDIT_PATTERNS);
    v.extend_from_slice(MOVE_COPY_PATTERNS);
    v.extend_from_slice(DELETE_PATTERNS);
    v.extend_from_slice(PERMISSION_PATTERNS);
    v.extend_from_slice(TRUNCATE_PATTERNS);
    v
}

/// Convert a glob path pattern to a regex fragment (mirrors Python glob_to_regex).
fn glob_to_regex(glob_pattern: &str) -> String {
    let mut result = String::new();
    for ch in glob_pattern.chars() {
        match ch {
            '*' => result.push_str(r"[^\s/]*"),
            '?' => result.push_str(r"[^\s/]"),
            '\\' | '.' | '^' | '$' | '+' | '{' | '}' | '[' | ']' | '|' | '(' | ')' => {
                result.push('\\');
                result.push(ch);
            }
            _ => result.push(ch),
        }
    }
    result
}

fn check_path_patterns(
    command: &str,
    path: &str,
    patterns: &[OpPattern],
    path_type: &str,
) -> Option<String> {
    if is_glob_pattern(path) {
        let glob_regex = glob_to_regex(path);
        for op in patterns {
            // Replace {path} placeholder with the glob regex
            let cmd_prefix = op.template.replace("{path}", "");
            let full_re = format!("{}{}", cmd_prefix.trim_end(), glob_regex);
            if let Ok(re) = Regex::new(&format!("(?i){}", full_re)) {
                if re.is_match(command) {
                    return Some(format!(
                        "Blocked: {} operation on {} {}",
                        op.operation, path_type, path
                    ));
                }
            }
        }
    } else {
        let expanded = expand_home(path);
        let escaped_expanded = regex::escape(&expanded);
        let escaped_original = regex::escape(path);
        for op in patterns {
            let pat_exp = op.template.replace("{path}", &escaped_expanded);
            let pat_orig = op.template.replace("{path}", &escaped_original);
            let matched = Regex::new(&pat_exp).map(|r| r.is_match(command)).unwrap_or(false)
                || Regex::new(&pat_orig).map(|r| r.is_match(command)).unwrap_or(false);
            if matched {
                return Some(format!(
                    "Blocked: {} operation on {} {}",
                    op.operation, path_type, path
                ));
            }
        }
    }
    None
}

// ---------------------------------------------------------------------------
// Bash command check
// ---------------------------------------------------------------------------

enum BashCheckResult {
    Allow,
    Block(String),
    Ask(String),
}

fn check_bash_command(command: &str, config: &DamageControlConfig) -> BashCheckResult {
    // 1. Check explicit bash tool patterns
    for item in &config.bash_tool_patterns {
        if let Ok(re) = Regex::new(&format!("(?i){}", item.pattern)) {
            if re.is_match(command) {
                if item.ask {
                    return BashCheckResult::Ask(item.reason.clone());
                } else {
                    return BashCheckResult::Block(format!("Blocked: {}", item.reason));
                }
            }
        }
    }

    // 2. Zero-access path checks
    // For glob patterns, use unquoted command to avoid false positives in quoted strings.
    // For exact paths, check the full command (specific enough).
    let unquoted_command = strip_quoted_content(command);

    for zero_path in &config.zero_access_paths {
        if is_glob_pattern(zero_path) {
            // Match against unquoted tokens only, with word-boundary check
            let glob_re_str = format!("{}(?!\\w)", glob_to_regex(zero_path));
            if let Ok(re) = Regex::new(&format!("(?i){}", glob_re_str)) {
                if re.is_match(&unquoted_command) {
                    return BashCheckResult::Block(format!(
                        "Blocked: zero-access pattern {} (no operations allowed)",
                        zero_path
                    ));
                }
            }
        } else {
            let expanded = expand_home(zero_path);
            let escaped_expanded = regex::escape(&expanded);
            let escaped_original = regex::escape(zero_path);
            let matched =
                Regex::new(&escaped_expanded).map(|r| r.is_match(command)).unwrap_or(false)
                    || Regex::new(&escaped_original).map(|r| r.is_match(command)).unwrap_or(false);
            if matched {
                return BashCheckResult::Block(format!(
                    "Blocked: zero-access path {} (no operations allowed)",
                    zero_path
                ));
            }
        }
    }

    // 3. Read-only path checks
    let ro_patterns = read_only_blocked();
    for readonly in &config.read_only_paths {
        if let Some(reason) = check_path_patterns(command, readonly, &ro_patterns, "read-only path")
        {
            return BashCheckResult::Block(reason);
        }
    }

    // 4. No-delete path checks
    for no_delete in &config.no_delete_paths {
        if let Some(reason) =
            check_path_patterns(command, no_delete, DELETE_PATTERNS, "no-delete path")
        {
            return BashCheckResult::Block(reason);
        }
    }

    BashCheckResult::Allow
}

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------

pub fn run() {
    let data: Value = read_stdin_value();

    let tool_name = data
        .get("tool_name")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let tool_input = data
        .get("tool_input")
        .cloned()
        .unwrap_or(Value::Object(Default::default()));

    let config = load_config();

    if tool_name == "Bash" {
        let command = tool_input
            .get("command")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        if command.is_empty() {
            println!("{{}}");
            return;
        }

        match check_bash_command(command, &config) {
            BashCheckResult::Block(reason) => {
                eprintln!("SECURITY: {}", reason);
                let truncated = if command.len() > 100 {
                    format!("{}...", &command[..100])
                } else {
                    command.to_string()
                };
                eprintln!("Command: {}", truncated);
                std::process::exit(2);
            }
            BashCheckResult::Ask(reason) => {
                let output = serde_json::json!({
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "ask",
                        "permissionDecisionReason": reason
                    }
                });
                println!("{}", output);
                // exit 0 (allow path continues after this function returns)
            }
            BashCheckResult::Allow => {
                println!("{{}}");
            }
        }
    } else if tool_name == "Edit" || tool_name == "Write" {
        let file_path = tool_input
            .get("file_path")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        if file_path.is_empty() {
            println!("{{}}");
            return;
        }
        match check_file_path(file_path, &config) {
            FileCheckResult::Block(reason) => {
                eprintln!(
                    "SECURITY: Blocked {} to {}: {}",
                    tool_name.to_lowercase(),
                    reason,
                    file_path
                );
                std::process::exit(2);
            }
            FileCheckResult::Allow => {
                println!("{{}}");
            }
        }
    } else {
        // Unknown tool — fail-open
        println!("{{}}");
    }
}
