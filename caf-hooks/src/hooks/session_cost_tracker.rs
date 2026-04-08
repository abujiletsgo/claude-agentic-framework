/// Session Cost Tracker — SubagentStop hook.
///
/// Python equivalent: global-hooks/framework/monitoring/session_cost_tracker.py
///               and: global-hooks/framework/monitoring/cost_tracker.py
///
/// Behavior:
/// - Reads SubagentStop event from stdin JSON
/// - Extracts agent_transcript_path, session_id, agent_type/id from payload
/// - Parses the transcript JSONL for token usage (assistant + usage entries)
/// - Calculates cost using model tier rates (Haiku/Sonnet/Opus)
/// - Appends a record to ~/.claude/logs/cost_tracking.jsonl
/// - Appends a running-total record to /tmp/caf_session_cost_{session_id}.jsonl
/// - Always exits 0 (never blocks)
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

use chrono::Utc;
use serde_json::Value;

use crate::io::{read_stdin_value, try_append_jsonl, write_output};
use crate::types::HookOutput;

// ── Pricing per 1M tokens (matches cost_tracker.py MODEL_PRICING exactly) ──

struct Pricing {
    input: f64,
    output: f64,
    tier: &'static str,
}

fn resolve_model_tier(model: &str) -> Pricing {
    let lower = model.to_lowercase();

    // Exact / pattern matches — same order as Python TIER_PATTERNS
    if lower.contains("haiku") {
        return Pricing { input: 0.25, output: 1.25, tier: "haiku" };
    }
    if lower.contains("sonnet") {
        return Pricing { input: 3.00, output: 15.00, tier: "sonnet" };
    }
    if lower.contains("opus") {
        return Pricing { input: 15.00, output: 75.00, tier: "opus" };
    }

    // Default to sonnet pricing for unknown models (matches Python)
    Pricing { input: 3.00, output: 15.00, tier: "unknown" }
}

fn calculate_cost(input_tokens: u64, output_tokens: u64, pricing: &Pricing) -> f64 {
    let input_cost = (input_tokens as f64 / 1_000_000.0) * pricing.input;
    let output_cost = (output_tokens as f64 / 1_000_000.0) * pricing.output;
    // Round to 6 decimal places (matches Python round(..., 6))
    (input_cost + output_cost * 1_000_000.0).round() / 1_000_000.0
}

struct TokenUsage {
    input_tokens: u64,
    output_tokens: u64,
    cache_read_tokens: u64,
    cache_write_tokens: u64,
    model: String,
}

/// Parse the transcript JSONL and sum token usage.
/// Matches Python extract_tokens_from_transcript() exactly.
fn extract_tokens_from_transcript(transcript_path: &str) -> TokenUsage {
    let empty = TokenUsage {
        input_tokens: 0,
        output_tokens: 0,
        cache_read_tokens: 0,
        cache_write_tokens: 0,
        model: "unknown".to_string(),
    };

    let path = std::path::Path::new(transcript_path);
    if !path.exists() {
        return empty;
    }

    let file = match File::open(path) {
        Ok(f) => f,
        Err(_) => return empty,
    };

    let mut total_input: u64 = 0;
    let mut total_output: u64 = 0;
    let mut total_cache_read: u64 = 0;
    let mut total_cache_write: u64 = 0;
    let mut model = "unknown".to_string();

    let reader = BufReader::new(file);
    for line in reader.lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => continue,
        };
        let line = line.trim().to_string();
        if line.is_empty() {
            continue;
        }
        let entry: Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(_) => continue,
        };

        match entry.get("type").and_then(|v| v.as_str()) {
            // Claude Code transcript format: assistant messages with usage
            Some("assistant") => {
                let msg = entry.get("message").and_then(|v| v.as_object());
                if let Some(msg) = msg {
                    let usage = msg.get("usage").and_then(|v| v.as_object());
                    if let Some(usage) = usage {
                        total_input += usage.get("input_tokens").and_then(|v| v.as_u64()).unwrap_or(0);
                        total_output += usage.get("output_tokens").and_then(|v| v.as_u64()).unwrap_or(0);
                        total_cache_read += usage.get("cache_read_input_tokens").and_then(|v| v.as_u64()).unwrap_or(0);
                        total_cache_write += usage.get("cache_creation_input_tokens").and_then(|v| v.as_u64()).unwrap_or(0);
                    }
                    if model == "unknown" {
                        if let Some(m) = msg.get("model").and_then(|v| v.as_str()) {
                            if !m.is_empty() {
                                model = m.to_string();
                            }
                        }
                    }
                }
            }
            // Alternative format: direct usage records
            Some("usage") => {
                total_input += entry.get("input_tokens").and_then(|v| v.as_u64()).unwrap_or(0);
                total_output += entry.get("output_tokens").and_then(|v| v.as_u64()).unwrap_or(0);
                total_cache_read += entry.get("cache_read_input_tokens").and_then(|v| v.as_u64()).unwrap_or(0);
                total_cache_write += entry.get("cache_creation_input_tokens").and_then(|v| v.as_u64()).unwrap_or(0);
                if model == "unknown" {
                    if let Some(m) = entry.get("model").and_then(|v| v.as_str()) {
                        if !m.is_empty() {
                            model = m.to_string();
                        }
                    }
                }
            }
            _ => {}
        }
    }

    TokenUsage {
        input_tokens: total_input,
        output_tokens: total_output,
        cache_read_tokens: total_cache_read,
        cache_write_tokens: total_cache_write,
        model,
    }
}

fn cost_log_path() -> PathBuf {
    let home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("/tmp"));
    home.join(".claude").join("logs").join("cost_tracking.jsonl")
}

pub fn run() {
    let data: Value = read_stdin_value();

    let session_id = data
        .get("session_id")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown")
        .to_string();

    let agent_id = data
        .get("agent_id")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown")
        .to_string();

    let agent_type = data
        .get("agent_type")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown")
        .to_string();

    let transcript_path = data
        .get("agent_transcript_path")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    // Derive agent name from type or id (matches Python)
    let agent_name = if !agent_type.is_empty() && agent_type != "unknown" {
        agent_type.clone()
    } else {
        let short_id: String = agent_id.chars().take(7).collect();
        format!("agent-{}", short_id)
    };

    // Extract token usage from transcript
    let usage = extract_tokens_from_transcript(&transcript_path);

    // Skip if no token data (matches Python)
    if usage.input_tokens == 0 && usage.output_tokens == 0 && usage.cache_read_tokens == 0 {
        write_output(&HookOutput::empty());
        return;
    }

    let pricing = resolve_model_tier(&usage.model);
    let cost = calculate_cost(usage.input_tokens, usage.output_tokens, &pricing);

    let timestamp = Utc::now().to_rfc3339();
    let epoch_ms = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0);

    // Cache hit rate: what % of input came from cache (matches Python metadata)
    let total_input_with_cache = usage.input_tokens + usage.cache_read_tokens;
    let cache_hit_rate = if total_input_with_cache > 0 {
        (usage.cache_read_tokens as f64 / total_input_with_cache as f64 * 1_000.0).round()
            / 1_000.0
    } else {
        0.0
    };

    // ── Append to persistent cost log (~/.claude/logs/cost_tracking.jsonl) ──
    let cost_entry = serde_json::json!({
        "timestamp": format!("{}Z", timestamp),
        "epoch_ms": epoch_ms,
        "session_id": session_id,
        "model": usage.model,
        "tier": pricing.tier,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cost_usd": cost,
        "agent_name": agent_name,
        "event_type": "SubagentStop",
        "tool_name": "",
        "metadata": {
            "agent_id": agent_id,
            "cache_read_tokens": usage.cache_read_tokens,
            "cache_write_tokens": usage.cache_write_tokens,
            "cache_hit_rate": cache_hit_rate,
        }
    });
    let _ = try_append_jsonl(&cost_log_path(), &cost_entry);

    // ── Update running session total (/tmp/caf_session_cost_{session_id}.jsonl) ──
    let session_file = PathBuf::from(format!("/tmp/caf_session_cost_{}.jsonl", session_id));
    let session_record = serde_json::json!({
        "timestamp": timestamp,
        "agent": agent_name,
        "model": usage.model,
        "tier": pricing.tier,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cost_usd": cost,
    });
    let _ = try_append_jsonl(&session_file, &session_record);

    write_output(&HookOutput::empty());
}
