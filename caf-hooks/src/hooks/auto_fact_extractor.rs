/// Auto Fact Extractor — PostToolUse hook.
///
/// Python equivalent: global-hooks/framework/facts/auto_fact_extractor.py (258 LOC)
/// Fact storage: global-hooks/framework/facts/fact_manager.py
///
/// Behavior:
/// - Bash (success): match command against CONFIRMED_PATTERNS → append to CONFIRMED section
/// - Bash (failure): match output against GOTCHA_PATTERNS → append to GOTCHAS section
/// - Write tool: match file_path against KEY_PATH_PATTERNS → append to PATHS section
/// - Never blocks (always exit 0)
/// - Deduplicates: reads FACTS.md and checks word-overlap (60% threshold) before appending
use chrono::Utc;
use regex::Regex;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::OnceLock;

use crate::io::{read_stdin_value, write_output};

// ---------------------------------------------------------------------------
// CONFIRMED patterns — match against Bash command on success
// Each: (regex_str, fact_text)
// ---------------------------------------------------------------------------
static CONFIRMED_PATTERNS_STR: &[(&str, &str)] = &[
    (r"\buv run\b", "Python executor is `uv run` (not python3/pip/poetry)"),
    (
        r"\bbash install\.sh\b",
        "`bash install.sh` regenerates config, symlinks, and docs from templates",
    ),
    (r"\bpnpm\b", "JS package manager is `pnpm` (not npm/yarn)"),
    (r"\bbun run\b", "JS runtime/runner is `bun`"),
    (
        r"\bdocker compose\b",
        "Container orchestration: `docker compose` (not docker-compose)",
    ),
    (r"\bmake\b.*build", "Build command is `make build`"),
    (
        r"\bcargo\b.*build",
        "Rust project — build with `cargo build`, run with `cargo run`",
    ),
    (r"\bgo build\b", "Go project — build with `go build`"),
    (r"\bdeno\b", "JS runtime is `deno` (not node/bun)"),
];

// ---------------------------------------------------------------------------
// GOTCHA patterns — match against combined output on Bash failure
// Each: (regex_str, template)
// Template variables (extracted from capture groups):
//   {1} = first capture group, {2} = second capture group
// Special templates are handled in build_gotcha_fact().
// ---------------------------------------------------------------------------
static GOTCHA_PATTERNS_STR: &[(&str, &str)] = &[
    (
        r#"command not found[:\s]+(['"`]?)(\S+)\1"#,
        "CMD_NOT_FOUND",
    ),
    (
        r#"No module named ['"]([^'"]+)['"]"#,
        "NO_MODULE",
    ),
    (
        r#"Cannot find module ['"]([^'"]+)['"]"#,
        "CANNOT_FIND_MODULE",
    ),
    (
        r"(?i)permission denied.*?(/\S+)",
        "PERMISSION_DENIED",
    ),
    (
        r"(?i)address already in use.*?:(\d+)",
        "ADDRESS_IN_USE",
    ),
    (
        r"ENOENT.*?'([^']+)'",
        "ENOENT",
    ),
    (
        r"uv: command not found",
        "uv not installed — install with: curl -LsSf https://astral.sh/uv/install.sh | sh",
    ),
    (
        r"syntax error near unexpected token",
        "Shell syntax error — check for missing quotes or incorrect bash syntax",
    ),
    (
        r"error: could not find `Cargo.toml`",
        "Must be in a Rust crate directory to run cargo commands",
    ),
];

// ---------------------------------------------------------------------------
// KEY_PATH patterns — match against file path on Write tool
// ---------------------------------------------------------------------------
static KEY_PATH_PATTERNS_STR: &[&str] = &[
    r"^\.claude/",
    r"^templates/",
    r"^global-hooks/",
    r"^global-agents/",
    r"^global-skills/",
    r"^global-commands/",
    r"^data/",
    r"^docs/",
    r"^scripts/",
    r"[Cc][Oo][Nn][Ff][Ii][Gg]\.",
    r"settings\.(json|yaml|toml)",
    r"pyproject\.toml$",
    r"Makefile$",
    r"Dockerfile$",
    r"\.env\.",
];

// ---------------------------------------------------------------------------
// SKIP_CMD patterns — skip trivial commands for CONFIRMED extraction
// ---------------------------------------------------------------------------
static SKIP_CMD_PATTERNS_STR: &[&str] = &[
    r"^(ls|ll|cat|echo|pwd|cd|which|type|env|printenv|date|whoami|id)\b",
    r"^git (status|log|diff|show|branch|fetch)\b",
    r"^(grep|rg|find|awk|sed|head|tail|wc)\b",
    r"^(curl|wget)\s+https?://",
    r"^(python3?|node|npm) -[cV]",
];

// ---------------------------------------------------------------------------
// Compiled regex caches
// ---------------------------------------------------------------------------
static CONFIRMED_PATTERNS: OnceLock<Vec<Regex>> = OnceLock::new();
static GOTCHA_PATTERNS: OnceLock<Vec<Regex>> = OnceLock::new();
static KEY_PATH_PATTERNS: OnceLock<Vec<Regex>> = OnceLock::new();
static SKIP_CMD_PATTERNS: OnceLock<Vec<Regex>> = OnceLock::new();

fn confirmed_patterns() -> &'static Vec<Regex> {
    CONFIRMED_PATTERNS.get_or_init(|| {
        CONFIRMED_PATTERNS_STR
            .iter()
            .filter_map(|(p, _)| Regex::new(p).ok())
            .collect()
    })
}

fn gotcha_patterns() -> &'static Vec<Regex> {
    GOTCHA_PATTERNS.get_or_init(|| {
        GOTCHA_PATTERNS_STR
            .iter()
            .filter_map(|(p, _)| Regex::new(p).ok())
            .collect()
    })
}

fn key_path_patterns() -> &'static Vec<Regex> {
    KEY_PATH_PATTERNS.get_or_init(|| {
        KEY_PATH_PATTERNS_STR
            .iter()
            .filter_map(|p| Regex::new(p).ok())
            .collect()
    })
}

fn skip_cmd_patterns() -> &'static Vec<Regex> {
    SKIP_CMD_PATTERNS.get_or_init(|| {
        SKIP_CMD_PATTERNS_STR
            .iter()
            .filter_map(|p| Regex::new(p).ok())
            .collect()
    })
}

// ---------------------------------------------------------------------------
// Fact extraction logic
// ---------------------------------------------------------------------------

fn should_skip_cmd(cmd: &str) -> bool {
    let trimmed = cmd.trim();
    skip_cmd_patterns()
        .iter()
        .any(|p| p.is_match(trimmed))
}

/// Build the GOTCHA fact text from a pattern match.
/// template is the second element in GOTCHA_PATTERNS_STR.
fn build_gotcha_fact(template: &str, caps: &regex::Captures) -> String {
    match template {
        "CMD_NOT_FOUND" => {
            let name = caps.get(2).map(|m| m.as_str()).unwrap_or("unknown");
            format!("`{}` not installed — check PATH or use an alternative", name)
        }
        "NO_MODULE" => {
            let name = caps.get(1).map(|m| m.as_str()).unwrap_or("unknown");
            format!(
                "Python module `{}` missing — install with `uv add {}`",
                name, name
            )
        }
        "CANNOT_FIND_MODULE" => {
            let name = caps.get(1).map(|m| m.as_str()).unwrap_or("unknown");
            format!(
                "Node module `{}` missing — run package install first",
                name
            )
        }
        "PERMISSION_DENIED" => {
            let path = caps.get(1).map(|m| m.as_str()).unwrap_or("unknown");
            format!(
                "Permission denied on `{}` — check chmod or sudo requirements",
                path
            )
        }
        "ADDRESS_IN_USE" => {
            let port = caps.get(1).map(|m| m.as_str()).unwrap_or("unknown");
            format!(
                "Port {} conflict — kill existing process before starting",
                port
            )
        }
        "ENOENT" => {
            let path = caps.get(1).map(|m| m.as_str()).unwrap_or("unknown");
            format!("File not found: `{}` — check path before referencing", path)
        }
        // Static strings — returned as-is
        other => other.to_string(),
    }
}

/// Extract (category, fact_text) pairs from a Bash tool call.
fn extract_from_bash(cmd: &str, output: &str, is_error: bool) -> Vec<(&'static str, String)> {
    let mut facts = Vec::new();

    if should_skip_cmd(cmd) && !is_error {
        return facts;
    }

    if !is_error {
        // Success: check CONFIRMED patterns against the command
        for (i, pat) in confirmed_patterns().iter().enumerate() {
            if pat.is_match(cmd) {
                let fact_text = CONFIRMED_PATTERNS_STR[i].1.to_string();
                facts.push(("CONFIRMED", fact_text));
                break; // one confirmed fact per command
            }
        }
    } else {
        // Failure: check GOTCHA patterns against combined output
        for (i, pat) in gotcha_patterns().iter().enumerate() {
            if let Some(caps) = pat.captures_at(output, 0).or_else(|| {
                // Try case-insensitive via the already-compiled pattern
                pat.captures(output)
            }) {
                let template = GOTCHA_PATTERNS_STR[i].1;
                let fact_text = build_gotcha_fact(template, &caps);
                facts.push(("GOTCHAS", fact_text));
                break; // one gotcha per error
            }
        }
    }

    facts
}

/// Extract PATHS facts from a Write tool call.
fn extract_from_write(file_path: &str, cwd: &str) -> Vec<(&'static str, String)> {
    let mut facts = Vec::new();

    // Compute relative path
    let rel = {
        let fp = Path::new(file_path);
        let cwd_path = Path::new(cwd);
        fp.strip_prefix(cwd_path)
            .map(|r| r.to_string_lossy().into_owned())
            .unwrap_or_else(|_| file_path.to_string())
    };

    for pat in key_path_patterns().iter() {
        if pat.is_match(&rel) {
            facts.push(("PATHS", format!("Key file: `{}`", rel)));
            break;
        }
    }

    facts
}

// ---------------------------------------------------------------------------
// FACTS.md management (ported from fact_manager.py)
// ---------------------------------------------------------------------------

const FACTS_TEMPLATE: &str = "\
# Project Facts
<!-- MANAGED: {project} | updated: {date} | layer: episodic -->
<!-- Injected at session start as authoritative ground truth. -->
<!-- Edit freely — hooks auto-maintain this file. -->

## \u{2713} CONFIRMED (execution-verified \u{2014} trust fully)

## \u{26a0} GOTCHAS (known failure modes \u{2014} read before acting)

## \u{1f4c1} PATHS & ARCHITECTURE (key files, entry points, config)

## \u{2192} PATTERNS (confirmed working sequences)

## \u{2717} STALE (superseded or disproven \u{2014} do not use)
";

struct SectionHeader {
    category: &'static str,
    header: &'static str,
}

static SECTION_HEADERS: &[SectionHeader] = &[
    SectionHeader { category: "CONFIRMED", header: "## \u{2713} CONFIRMED" },
    SectionHeader { category: "GOTCHAS",   header: "## \u{26a0} GOTCHAS" },
    SectionHeader { category: "PATHS",     header: "## \u{1f4c1} PATHS & ARCHITECTURE" },
    SectionHeader { category: "PATTERNS",  header: "## \u{2192} PATTERNS" },
    SectionHeader { category: "STALE",     header: "## \u{2717} STALE" },
];

fn section_header_for(category: &str) -> Option<&'static str> {
    SECTION_HEADERS
        .iter()
        .find(|s| s.category == category)
        .map(|s| s.header)
}

/// Word set for fuzzy dedup (mirrors Python _words())
fn words(text: &str) -> std::collections::HashSet<String> {
    let re = Regex::new(r"[a-zA-Z0-9_-]+").unwrap();
    re.find_iter(&text.to_lowercase())
        .map(|m| m.as_str().to_string())
        .collect()
}

/// Fuzzy duplicate check: word overlap ratio >= 0.60
fn is_duplicate(entry: &str, section_text: &str) -> bool {
    let ew = words(entry);
    if ew.is_empty() {
        return false;
    }
    for line in section_text.lines() {
        let trimmed = line.trim();
        if !trimmed.starts_with("- ") {
            continue;
        }
        let lw = words(trimmed);
        if lw.is_empty() {
            continue;
        }
        let intersection = ew.intersection(&lw).count();
        let max_len = ew.len().max(lw.len());
        let overlap = intersection as f64 / max_len as f64;
        if overlap >= 0.60 {
            return true;
        }
    }
    false
}

fn facts_path(cwd: &str) -> PathBuf {
    Path::new(cwd).join(".claude").join("FACTS.md")
}

fn project_name(cwd: &str) -> String {
    Path::new(cwd)
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("unknown")
        .to_string()
}

fn init_facts(path: &Path, project: &str) -> String {
    let today = Utc::now().format("%Y-%m-%d").to_string();
    let content = FACTS_TEMPLATE
        .replace("{project}", project)
        .replace("{date}", &today);
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let _ = fs::write(path, &content);
    content
}

/// Append a fact to FACTS.md — mirrors Python fact_manager.add().
/// Returns true if added, false if duplicate or error.
fn add_fact(path: &Path, category: &str, entry: &str, project: &str) -> bool {
    // Read or init
    let content = if path.exists() {
        fs::read_to_string(path).unwrap_or_default()
    } else {
        String::new()
    };

    let content = if content.is_empty() {
        init_facts(path, project)
    } else {
        content
    };

    let header = match section_header_for(category) {
        Some(h) => h,
        None => return false,
    };

    let h_idx = match content.find(header) {
        Some(idx) => idx,
        None => return false,
    };

    let after_h = &content[h_idx + header.len()..];

    // Find section end = next "## " header or EOF
    let section_end = after_h
        .find("\n## ")
        .map(|i| h_idx + header.len() + i)
        .unwrap_or(content.len());

    let section = &content[h_idx..section_end];

    if is_duplicate(entry, section) {
        return false;
    }

    let today = Utc::now().format("%Y-%m-%d").to_string();
    let new_entry = format!("- {} [{}]", entry, today);

    // Build new content
    let section_trimmed = section.trim_end();
    let new_section = format!("{}\n{}\n", section_trimmed, new_entry);

    let new_content = format!(
        "{}{}{}",
        &content[..h_idx],
        new_section,
        &content[section_end..]
    );

    // Update the MANAGED header timestamp
    let managed_re = Regex::new(r"<!-- MANAGED: [^|]+ \| updated: [0-9-]+ \|").unwrap();
    let new_content = managed_re
        .replace(
            &new_content,
            format!("<!-- MANAGED: {} | updated: {} |", project, today).as_str(),
        )
        .into_owned();

    // Write atomically via temp file
    let parent = path.parent().unwrap_or(Path::new("."));
    let tmp_path = parent.join(format!(
        ".tmp_FACTS_{}.md",
        std::process::id()
    ));
    if let Ok(mut f) = OpenOptions::new().write(true).create(true).truncate(true).open(&tmp_path) {
        let _ = f.write_all(new_content.as_bytes());
        let _ = f.flush();
        let _ = fs::rename(&tmp_path, path);
    }

    true
}

// ---------------------------------------------------------------------------
// Hook entry point
// ---------------------------------------------------------------------------

pub fn run() {
    let data = read_stdin_value();

    let tool_name = data
        .get("tool_name")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    let cwd = data
        .get("cwd")
        .and_then(|v| v.as_str())
        .unwrap_or(".")
        .to_string();

    let tool_input = {
        let raw = data.get("tool_input").cloned().unwrap_or(serde_json::json!({}));
        if let Some(s) = raw.as_str() {
            serde_json::from_str(s).unwrap_or(serde_json::json!({}))
        } else {
            raw
        }
    };

    let mut facts: Vec<(&'static str, String)> = Vec::new();

    match tool_name {
        "Bash" => {
            let cmd = tool_input
                .get("command")
                .and_then(|v| v.as_str())
                .unwrap_or("");

            let tool_response = data.get("tool_response");
            let (output, is_error) = match tool_response {
                Some(serde_json::Value::Object(map)) => {
                    let out = map
                        .get("output")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    let err = map
                        .get("isError")
                        .and_then(|v| v.as_bool())
                        .unwrap_or(false);
                    (out.to_string(), err)
                }
                Some(serde_json::Value::String(s)) => (s.clone(), false),
                _ => (String::new(), false),
            };

            facts = extract_from_bash(cmd, &output, is_error);
        }
        "Write" => {
            let file_path = tool_input
                .get("file_path")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            if !file_path.is_empty() {
                facts = extract_from_write(file_path, &cwd);
            }
        }
        _ => {}
    }

    if !facts.is_empty() {
        let path = facts_path(&cwd);
        let project = project_name(&cwd);
        for (category, entry) in &facts {
            let _ = add_fact(&path, category, entry, &project);
        }
    }

    write_output(&serde_json::json!({}));
}
