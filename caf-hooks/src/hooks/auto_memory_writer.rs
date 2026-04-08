/// Auto Memory Writer — Stop hook.
///
/// Python equivalent: global-hooks/framework/memory/auto_memory_writer.py
///
/// Behavior:
/// - Reads session_id and cwd from stdin JSON
/// - Runs `git diff --stat HEAD~1 HEAD --` (falls back to staged/unstaged diffs)
/// - Runs `git log -1 --format=%s (%h) by %an` for last commit
/// - Reads compressed_context JSON files for task summaries
/// - Builds a dated session entry (skips if nothing changed)
/// - Upserts entry into .claude/MEMORY.md (dedup on commit hash)
/// - Prunes oldest entries if >30 entries
/// - Atomically writes MEMORY.md
/// - Always exits 0 (never blocks)
use std::path::{Path, PathBuf};
use std::process::Command;

use chrono::Utc;
use serde_json::Value;

use crate::io::{atomic_write, read_stdin_value, write_output};
use crate::state::compressed_context_dir;
use crate::types::HookOutput;

const MAX_MEMORY_ENTRIES: usize = 30;

// ---------------------------------------------------------------------------
// Path helpers
// ---------------------------------------------------------------------------

fn memory_path(cwd: &str) -> PathBuf {
    PathBuf::from(cwd).join(".claude").join("MEMORY.md")
}

// ---------------------------------------------------------------------------
// Git subprocess helpers
// ---------------------------------------------------------------------------

fn run_git(args: &[&str], cwd: &str) -> String {
    let output = Command::new("git")
        .args(args)
        .current_dir(cwd)
        .output();
    match output {
        Ok(o) if o.status.success() => {
            String::from_utf8_lossy(&o.stdout).trim().to_string()
        }
        _ => String::new(),
    }
}

fn get_git_changes(cwd: &str) -> Vec<String> {
    // Try committed changes first
    let stat = run_git(&["diff", "--stat", "HEAD~1", "HEAD", "--"], cwd);
    let stat = if stat.is_empty() {
        // No commit yet — try staged/unstaged changes
        let s = run_git(&["diff", "--stat"], cwd);
        if s.is_empty() {
            run_git(&["diff", "--stat", "--cached"], cwd)
        } else {
            s
        }
    } else {
        stat
    };

    if stat.is_empty() {
        return Vec::new();
    }
    stat.lines()
        .filter(|l| !l.trim().is_empty())
        .map(|l| l.to_string())
        .collect()
}

fn get_commit_hash(cwd: &str) -> String {
    run_git(&["log", "-1", "--format=%h"], cwd)
}

fn get_last_commit(cwd: &str) -> String {
    run_git(&["log", "-1", "--format=%s (%h) by %an"], cwd)
}

fn get_git_author(cwd: &str) -> String {
    let name = run_git(&["config", "user.name"], cwd);
    if !name.is_empty() {
        return name;
    }
    let email = run_git(&["config", "user.email"], cwd);
    if email.is_empty() {
        return String::new();
    }
    email.split('@').next().unwrap_or("").to_string()
}

// ---------------------------------------------------------------------------
// Compressed context summaries
// ---------------------------------------------------------------------------

fn get_compressed_summaries(session_id: &str) -> Vec<String> {
    let mut summaries = Vec::new();
    let dir = compressed_context_dir();
    if !dir.exists() {
        return summaries;
    }

    let prefix = &session_id[..session_id.len().min(8)];
    let pattern = format!("{}*.json", prefix);

    let glob_pattern = dir.join(&pattern);
    let glob_str = glob_pattern.to_string_lossy();

    let mut paths: Vec<PathBuf> = glob::glob(&glob_str)
        .map(|paths| paths.flatten().collect())
        .unwrap_or_default();
    paths.sort();

    for path in paths {
        if let Ok(text) = std::fs::read_to_string(&path) {
            if let Ok(data) = serde_json::from_str::<Value>(&text) {
                let subj = data.get("subject").and_then(|v| v.as_str()).unwrap_or("");
                let outcome = data.get("outcome").and_then(|v| v.as_str()).unwrap_or("");
                if !subj.is_empty() {
                    let line = if outcome.is_empty() {
                        format!("- Task: {}", subj)
                    } else {
                        format!("- Task: {} → {}", subj, outcome)
                    };
                    summaries.push(line);
                }
            }
        }
        if summaries.len() >= 5 {
            break;
        }
    }
    summaries
}

// ---------------------------------------------------------------------------
// Entry builder
// ---------------------------------------------------------------------------

fn build_entry(cwd: &str, session_id: &str) -> Option<String> {
    let today = Utc::now().format("%Y-%m-%d").to_string();
    let time_str = Utc::now().format("%H:%M UTC").to_string();
    let project = Path::new(cwd)
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("unknown")
        .to_string();

    let git_changes = get_git_changes(cwd);
    let last_commit = get_last_commit(cwd);
    let task_summaries = get_compressed_summaries(session_id);
    let author = get_git_author(cwd);

    // Only write if something happened
    if git_changes.is_empty() && task_summaries.is_empty() {
        return None;
    }

    let _ = project; // used in header below for context

    let mut lines: Vec<String> = Vec::new();

    let mut header = format!("## {} ({})", today, time_str);
    if !author.is_empty() {
        header.push_str(&format!(" · @{}", author));
    }
    lines.push(header);

    if !last_commit.is_empty() {
        lines.push(format!("**Commit:** {}", last_commit));
    }

    if !git_changes.is_empty() {
        lines.push("**Changed:**".to_string());
        let display_count = git_changes.len().min(10);
        for line in &git_changes[..display_count] {
            if line.contains('|') || line.contains("changed") {
                lines.push(format!("  {}", line.trim()));
            }
        }
        if git_changes.len() > 10 {
            lines.push(format!("  ... and {} more files", git_changes.len() - 10));
        }
    }

    if !task_summaries.is_empty() {
        lines.push("**Tasks completed:**".to_string());
        lines.extend(task_summaries);
    }

    lines.push(String::new()); // trailing newline

    Some(lines.join("\n"))
}

// ---------------------------------------------------------------------------
// Prune old entries (keep most recent MAX_MEMORY_ENTRIES)
// ---------------------------------------------------------------------------

fn prune_old_entries(content: &str, max_entries: usize) -> String {
    // Split on "## YYYY-MM-DD" date headers
    let re = regex::Regex::new(r"(## \d{4}-\d{2}-\d{2})").unwrap();
    let parts: Vec<&str> = re.split(content).collect();
    let headers: Vec<&str> = re.find_iter(content).map(|m| m.as_str()).collect();

    if headers.is_empty() {
        return content.to_string();
    }

    let file_header = parts[0];
    let mut sessions: Vec<String> = Vec::new();
    for (i, header) in headers.iter().enumerate() {
        let body = if i + 1 < parts.len() {
            parts[i + 1]
        } else {
            ""
        };
        sessions.push(format!("{}{}", header, body));
    }

    if sessions.len() <= max_entries {
        return content.to_string();
    }

    // Keep most recent
    let kept = &sessions[sessions.len() - max_entries..];
    format!("{}{}", file_header, kept.join(""))
}

// ---------------------------------------------------------------------------
// Upsert entry (dedup on commit hash)
// ---------------------------------------------------------------------------

fn upsert_entry(content: &str, entry: &str, commit_hash: &str) -> String {
    if commit_hash.is_empty() {
        // No commit hash to dedup on — just append
        return format!("{}\n\n{}", content.trim_end(), entry);
    }

    let re = regex::Regex::new(r"(## \d{4}-\d{2}-\d{2})").unwrap();
    let parts: Vec<&str> = re.split(content).collect();
    let headers: Vec<&str> = re.find_iter(content).map(|m| m.as_str()).collect();

    if headers.is_empty() {
        return format!("{}\n\n{}", content.trim_end(), entry);
    }

    let file_header = parts[0];
    let mut sessions: Vec<String> = Vec::new();
    for (i, header) in headers.iter().enumerate() {
        let body = if i + 1 < parts.len() {
            parts[i + 1]
        } else {
            ""
        };
        sessions.push(format!("{}{}", header, body));
    }

    // Find existing entry with this commit hash and replace it
    let mut replaced = false;
    for block in sessions.iter_mut() {
        if block.contains(commit_hash) {
            *block = format!("{}\n", entry);
            replaced = true;
            break;
        }
    }

    if replaced {
        let body = sessions.join("");
        format!("{}\n\n{}", file_header.trim_end(), body.trim_end())
            + "\n"
    } else {
        format!("{}\n\n{}", content.trim_end(), entry)
    }
}

// ---------------------------------------------------------------------------
// Ensure MEMORY.md exists
// ---------------------------------------------------------------------------

fn ensure_memory_file(path: &Path, project: &str) -> String {
    if path.exists() {
        return std::fs::read_to_string(path).unwrap_or_default();
    }
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let header = format!(
        "# Project Memory — {}\n\
         <!-- Mid-term project memory: one entry per session. Auto-maintained. -->\n\
         <!-- Layer 2 (episodic): what changed, was fixed, was decided across sessions. -->\n\n",
        project
    );
    let _ = std::fs::write(path, &header);
    header
}

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------

pub fn run() {
    let data: Value = read_stdin_value();

    let cwd = data
        .get("cwd")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .unwrap_or_else(|| {
            std::env::current_dir()
                .map(|p| p.display().to_string())
                .unwrap_or_else(|_| ".".to_string())
        });

    let session_id = data
        .get("session_id")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown")
        .to_string();

    let project = Path::new(&cwd)
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("unknown")
        .to_string();

    let path = memory_path(&cwd);

    let entry = match build_entry(&cwd, &session_id) {
        Some(e) => e,
        None => {
            // Nothing happened — skip write
            write_output(&HookOutput::empty());
            return;
        }
    };

    let content = ensure_memory_file(&path, &project);
    let commit_hash = get_commit_hash(&cwd);
    let content = upsert_entry(&content, &entry, &commit_hash);
    let content = prune_old_entries(&content, MAX_MEMORY_ENTRIES);

    let _ = atomic_write(&path, &content);

    write_output(&HookOutput::empty());
}
