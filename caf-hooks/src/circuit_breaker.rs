/// Circuit breaker state machine.
///
/// Mirrors the Python CircuitBreaker + HookStateManager classes.
/// State file: ~/.claude/hook_state.json
/// File locking: fs2::FileExt (Unix flock equivalent)
///
/// Thresholds (defaults):
///   failure_threshold:  3 consecutive failures → OPEN
///   cooldown_seconds:   300s before HALF_OPEN
///   success_threshold:  2 consecutive successes → CLOSED from HALF_OPEN
use std::fs::{self, File};
use std::io::{self, Read, Write};
use std::path::Path;

use chrono::{DateTime, Duration, Utc};
use fs2::FileExt;

use crate::state::hook_state_path;
use crate::types::{CircuitState, HookState, HookStateData};

pub const FAILURE_THRESHOLD: u64 = 3;
pub const COOLDOWN_SECONDS: i64 = 300;
pub const SUCCESS_THRESHOLD: u64 = 2;

/// Decision returned by should_execute()
#[derive(Debug, PartialEq)]
pub enum CbDecision {
    Execute,
    ExecuteTest,
    Skip,
}

pub struct CircuitBreaker {
    state_path: std::path::PathBuf,
}

impl CircuitBreaker {
    pub fn new() -> Self {
        CircuitBreaker {
            state_path: hook_state_path(),
        }
    }

    /// Read state with shared lock.
    fn read_state(&self) -> HookStateData {
        self.ensure_exists();
        match File::open(&self.state_path) {
            Ok(mut f) => {
                if f.lock_shared().is_err() {
                    return HookStateData::default();
                }
                let mut buf = String::new();
                let result = f.read_to_string(&mut buf);
                let _ = f.unlock();
                if result.is_err() {
                    return HookStateData::default();
                }
                serde_json::from_str(&buf).unwrap_or_default()
            }
            Err(_) => HookStateData::default(),
        }
    }

    /// Write state atomically (temp file + rename), with exclusive lock on temp file.
    fn write_state(&self, state: &HookStateData) -> io::Result<()> {
        if let Some(parent) = self.state_path.parent() {
            fs::create_dir_all(parent)?;
        }
        let dir = self.state_path.parent().unwrap_or(Path::new("."));
        let tmp_path = dir.join(format!(".hook_state_{}.tmp", std::process::id()));
        {
            let mut tmp = File::create(&tmp_path)?;
            tmp.lock_exclusive()?;
            let json = serde_json::to_string_pretty(state)
                .map_err(|e| io::Error::new(io::ErrorKind::Other, e))?;
            tmp.write_all(json.as_bytes())?;
            tmp.flush()?;
            let _ = tmp.unlock();
        }
        fs::rename(&tmp_path, &self.state_path)?;
        Ok(())
    }

    fn ensure_exists(&self) {
        if !self.state_path.exists() {
            if let Some(p) = self.state_path.parent() {
                let _ = fs::create_dir_all(p);
            }
            let state = HookStateData::default();
            if let Ok(json) = serde_json::to_string_pretty(&state) {
                let _ = fs::write(&self.state_path, json);
            }
        }
    }

    /// Determine whether a hook should execute.
    pub fn should_execute(&self, hook_cmd: &str) -> CbDecision {
        let state = self.read_state();
        let hook_state = state
            .hooks
            .get(hook_cmd)
            .cloned()
            .unwrap_or_default();

        match hook_state.state {
            CircuitState::Closed => CbDecision::Execute,
            CircuitState::Open => {
                // Check if cooldown elapsed — if so, transition to HALF_OPEN
                if self.is_cooldown_elapsed(&hook_state) {
                    let _ = self.transition_to_half_open(hook_cmd);
                    CbDecision::ExecuteTest
                } else {
                    CbDecision::Skip
                }
            }
            CircuitState::HalfOpen => CbDecision::ExecuteTest,
        }
    }

    fn is_cooldown_elapsed(&self, hook_state: &HookState) -> bool {
        if let Some(ref disabled_at) = hook_state.disabled_at {
            if let Ok(dt) = disabled_at.parse::<DateTime<Utc>>() {
                let elapsed = Utc::now() - dt;
                return elapsed >= Duration::seconds(COOLDOWN_SECONDS);
            }
        }
        false
    }

    /// Record a successful hook execution. May close circuit from HALF_OPEN.
    pub fn record_success(&self, hook_cmd: &str) {
        let mut state = self.read_state();
        let hook_state = state
            .hooks
            .entry(hook_cmd.to_string())
            .or_insert_with(HookState::default);

        hook_state.consecutive_successes += 1;
        hook_state.consecutive_failures = 0;
        hook_state.last_success = Some(Utc::now().to_rfc3339());

        if hook_state.state == CircuitState::HalfOpen
            && hook_state.consecutive_successes >= SUCCESS_THRESHOLD
        {
            hook_state.state = CircuitState::Closed;
            hook_state.failure_count = 0;
            hook_state.first_failure = None;
            hook_state.disabled_at = None;
            hook_state.retry_after = None;
            hook_state.last_error = None;
        }

        update_global_stats(&mut state);
        let _ = self.write_state(&state);
    }

    /// Record a failed hook execution. May open the circuit.
    pub fn record_failure(&self, hook_cmd: &str, error: &str) {
        let mut state = self.read_state();
        let hook_state = state
            .hooks
            .entry(hook_cmd.to_string())
            .or_insert_with(HookState::default);

        hook_state.consecutive_failures += 1;
        hook_state.consecutive_successes = 0;
        hook_state.failure_count += 1;
        hook_state.last_failure = Some(Utc::now().to_rfc3339());
        hook_state.last_error = Some(error.to_string());

        if hook_state.first_failure.is_none() {
            hook_state.first_failure = hook_state.last_failure.clone();
        }

        let retry_after = (Utc::now() + Duration::seconds(COOLDOWN_SECONDS)).to_rfc3339();

        // Any failure in HALF_OPEN immediately reopens
        if hook_state.state == CircuitState::HalfOpen {
            hook_state.state = CircuitState::Open;
            hook_state.disabled_at = Some(Utc::now().to_rfc3339());
            hook_state.retry_after = Some(retry_after);
        } else if hook_state.consecutive_failures >= FAILURE_THRESHOLD
            && hook_state.state != CircuitState::Open
        {
            hook_state.state = CircuitState::Open;
            hook_state.disabled_at = Some(Utc::now().to_rfc3339());
            hook_state.retry_after = Some(retry_after);
        }

        update_global_stats(&mut state);
        let _ = self.write_state(&state);
    }

    fn transition_to_half_open(&self, hook_cmd: &str) -> bool {
        let mut state = self.read_state();
        if let Some(hook_state) = state.hooks.get_mut(hook_cmd) {
            if hook_state.state == CircuitState::Open {
                hook_state.state = CircuitState::HalfOpen;
                hook_state.consecutive_successes = 0;
                hook_state.consecutive_failures = 0;
                update_global_stats(&mut state);
                let _ = self.write_state(&state);
                return true;
            }
        }
        false
    }

    /// Check if the circuit is open (skip execution).
    pub fn is_open(&self, hook_cmd: &str) -> bool {
        matches!(self.should_execute(hook_cmd), CbDecision::Skip)
    }
}

fn update_global_stats(state: &mut HookStateData) {
    let disabled = state
        .hooks
        .values()
        .filter(|h| h.state == CircuitState::Open)
        .count() as u64;
    state.global_stats.hooks_disabled = disabled;
    state.global_stats.last_updated = Utc::now().to_rfc3339();
    state.global_stats.total_executions += 1;
}

impl Default for CircuitBreaker {
    fn default() -> Self {
        Self::new()
    }
}
