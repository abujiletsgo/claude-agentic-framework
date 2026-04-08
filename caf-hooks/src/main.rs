/// caf-hooks — Claude Agentic Framework hooks binary.
///
/// Single binary with one subcommand per hook. All hooks read JSON from stdin,
/// write JSON to stdout, and exit 0 (fail-open). Only damage_control and
/// orchestrator_tool_guard ever exit 2.
///
/// Usage:
///   echo $PAYLOAD | caf-hooks <hook-name>
///   echo $PAYLOAD | caf-hooks --cb <hook-name>   # Check circuit breaker first
mod circuit_breaker;
mod hooks;
mod io;
mod state;
mod types;

use clap::{Parser, Subcommand};

use circuit_breaker::{CbDecision, CircuitBreaker};

#[derive(Parser)]
#[command(name = "caf-hooks", version = "0.1.0", about = "CAF hooks binary")]
struct Cli {
    /// Check circuit breaker state before running the hook subcommand.
    /// If the circuit is OPEN, skip execution and exit 0.
    #[arg(long, global = true)]
    cb: bool,

    #[command(subcommand)]
    command: HookCommand,
}

#[derive(Subcommand)]
enum HookCommand {
    // ── SIMPLE hooks (Phase 1 — implemented) ─────────────────────────────────
    /// PostCompact: verify pre-computed summaries were preserved
    PostCompactVerify,
    /// FileChanged: log dependency file changes and inject advisory
    FileWatcher,
    /// Stop: announce completion via macOS `say`
    VoiceDone,
    /// StopFailure: classify API error and inject recovery advice
    StopFailureRecovery,
    /// TaskCompleted: quality gate for test-related tasks
    TaskQualityGate,

    // ── MEDIUM hooks (Phase 3 — not yet implemented) ──────────────────────────
    /// UserPromptSubmit: Korean mode — translate prompt via Haiku API
    KrMode,
    /// UserPromptSubmit: enforce /orchestrate command usage
    EnforceOrchestrate,
    /// UserPromptSubmit: epistemic guardrail — inject OBSERVED/INFERRED reminder
    EpistemicGuard,
    /// PostToolUse (Write|Edit): nudge to run /refine after review
    AutoRefine,
    /// PostToolUse (Bash|Write|Edit): log session context bundle
    ContextBundleLogger,
    /// PostToolUse (Bash): extract error patterns from failed commands
    AutoErrorAnalyzer,
    /// PostToolUse (*): escalation directive on high-complexity sessions
    AutoEscalate,
    /// PostToolUse (Bash|Write): extract facts and write to FACTS.md
    AutoFactExtractor,

    // ── COMPLEX hooks (Phase 4 — not yet implemented) ─────────────────────────
    /// PreToolUse (Bash|Edit|Write): pattern-based security blocker
    DamageControl,
    /// Stop: write session summary to MEMORY.md
    AutoMemoryWriter,
    /// PostToolUse: auto context manager / transcript parser
    AutoContextManager,

    // ── Diagnostic subcommand ─────────────────────────────────────────────────
    /// Run environment health checks (does not read stdin)
    Doctor,

    // ── Other hooks (not yet implemented) ─────────────────────────────────────
    /// SessionStart: orchestrate sub-hooks
    SessionStartup,
    /// SessionEnd/PreToolUse/PostToolUse: multi-session file conflict detection
    SessionLockManager,
    /// PreToolUse (Bash): detect gh pr create and spawn review team
    AutoReviewTeam,
    /// PostToolUse (Write|Edit): detect team mode signals
    AutoTeamReview,
    /// Stop: prune FACTS.md entries >90 days
    ValidateFacts,
    /// Stop: run npm/pip/cargo audit at threshold
    AutoDependencyAudit,
    /// Stop: generate SKILL.md from repeated Grep→Read→Edit sequences
    AutoSkillGenerator,
    /// Stop: check L-Thread progress state
    CheckLthreadProgress,
    /// SubagentStart/SubagentStop: track agent metadata and anomalies
    SubagentTracker,
    /// SubagentStart/SubagentStop: track orchestrator depth
    OrchDepthTracker,
    /// SubagentStart: inject KG triples as context
    SubagentKgInject,
    /// SubagentStop: compute and record session token cost
    SessionCostTracker,
    /// SubagentStop: store agent output in mempalace
    SubagentPalaceStore,
    /// PreToolUse (Read|Grep|Glob|Edit|Bash): block orchestrator from file tools
    OrchestratorToolGuard,
    /// CwdChanged: detect project language/framework
    ProjectFingerprint,
    /// ConfigChange: log config changes and warn on hooks/permissions edits
    AuditConfigChange,
    /// PreCompact: extract and compress context before compaction
    PreCompactPreserve,
    /// UserPromptSubmit: Caddy — classify prompt and suggest strategy
    AnalyzeRequest,
    /// UserPromptSubmit: Caddy — generate execution plan
    AutoDelegate,
}

fn not_implemented(name: &str) {
    eprintln!("caf-hooks: {} not yet implemented", name);
    // Print empty JSON to stdout so Claude doesn't error on missing output
    println!("{{}}");
}

fn main() {
    let cli = Cli::parse();

    // Circuit breaker check — derive a stable key from the subcommand name
    if cli.cb {
        let cmd_name = subcommand_name(&cli.command);
        let cb = CircuitBreaker::new();
        match cb.should_execute(cmd_name) {
            CbDecision::Skip => {
                // Circuit open — graceful skip
                let output = serde_json::json!({
                    "result": "continue",
                    "message": format!("Hook {} disabled (circuit open). Skipping.", cmd_name),
                    "success": true
                });
                println!("{}", output);
                std::process::exit(0);
            }
            CbDecision::Execute | CbDecision::ExecuteTest => {
                // Proceed to run the hook
            }
        }
    }

    match cli.command {
        // ── Implemented ──────────────────────────────────────────────────────
        HookCommand::PostCompactVerify => hooks::post_compact_verify::run(),
        HookCommand::FileWatcher => hooks::file_watcher::run(),
        HookCommand::VoiceDone => hooks::voice_done::run(),
        HookCommand::StopFailureRecovery => hooks::stop_failure_recovery::run(),
        HookCommand::TaskQualityGate => hooks::task_quality_gate::run(),

        // ── Diagnostic ───────────────────────────────────────────────────────
        HookCommand::Doctor => hooks::doctor::run(),

        // ── Not yet implemented ───────────────────────────────────────────────
        HookCommand::KrMode => not_implemented("kr-mode"),
        HookCommand::EnforceOrchestrate => hooks::enforce_orchestrate::run(),
        HookCommand::EpistemicGuard => hooks::epistemic_guard::run(),
        HookCommand::AutoRefine => hooks::auto_refine::run(),
        HookCommand::ContextBundleLogger => hooks::context_bundle_logger::run(),
        HookCommand::AutoErrorAnalyzer => hooks::auto_error_analyzer::run(),
        HookCommand::AutoEscalate => hooks::auto_escalate::run(),
        HookCommand::AutoFactExtractor => hooks::auto_fact_extractor::run(),
        HookCommand::DamageControl => hooks::damage_control::run(),
        HookCommand::AutoMemoryWriter => hooks::auto_memory_writer::run(),
        HookCommand::AutoContextManager => not_implemented("auto-context-manager"),
        HookCommand::SessionStartup => not_implemented("session-startup"),
        HookCommand::SessionLockManager => not_implemented("session-lock-manager"),
        HookCommand::AutoReviewTeam => not_implemented("auto-review-team"),
        HookCommand::AutoTeamReview => not_implemented("auto-team-review"),
        HookCommand::ValidateFacts => not_implemented("validate-facts"),
        HookCommand::AutoDependencyAudit => not_implemented("auto-dependency-audit"),
        HookCommand::AutoSkillGenerator => not_implemented("auto-skill-generator"),
        HookCommand::CheckLthreadProgress => not_implemented("check-lthread-progress"),
        HookCommand::SubagentTracker => hooks::subagent_tracker::run(),
        HookCommand::OrchDepthTracker => hooks::orch_depth_tracker::run(),
        HookCommand::SubagentKgInject => not_implemented("subagent-kg-inject"),
        HookCommand::SessionCostTracker => hooks::session_cost_tracker::run(),
        HookCommand::SubagentPalaceStore => not_implemented("subagent-palace-store"),
        HookCommand::OrchestratorToolGuard => hooks::orchestrator_tool_guard::run(),
        HookCommand::ProjectFingerprint => not_implemented("project-fingerprint"),
        HookCommand::AuditConfigChange => hooks::audit_config_change::run(),
        HookCommand::PreCompactPreserve => not_implemented("pre-compact-preserve"),
        HookCommand::AnalyzeRequest => not_implemented("analyze-request"),
        HookCommand::AutoDelegate => not_implemented("auto-delegate"),
    }

    std::process::exit(0);
}

/// Return a stable string key for each subcommand (used as CB hook_cmd key).
fn subcommand_name(cmd: &HookCommand) -> &'static str {
    match cmd {
        HookCommand::Doctor => "doctor",
        HookCommand::PostCompactVerify => "post-compact-verify",
        HookCommand::FileWatcher => "file-watcher",
        HookCommand::VoiceDone => "voice-done",
        HookCommand::StopFailureRecovery => "stop-failure-recovery",
        HookCommand::TaskQualityGate => "task-quality-gate",
        HookCommand::KrMode => "kr-mode",
        HookCommand::EnforceOrchestrate => "enforce-orchestrate",
        HookCommand::EpistemicGuard => "epistemic-guard",
        HookCommand::AutoRefine => "auto-refine",
        HookCommand::ContextBundleLogger => "context-bundle-logger",
        HookCommand::AutoErrorAnalyzer => "auto-error-analyzer",
        HookCommand::AutoEscalate => "auto-escalate",
        HookCommand::AutoFactExtractor => "auto-fact-extractor",
        HookCommand::DamageControl => "damage-control",
        HookCommand::AutoMemoryWriter => "auto-memory-writer",
        HookCommand::AutoContextManager => "auto-context-manager",
        HookCommand::SessionStartup => "session-startup",
        HookCommand::SessionLockManager => "session-lock-manager",
        HookCommand::AutoReviewTeam => "auto-review-team",
        HookCommand::AutoTeamReview => "auto-team-review",
        HookCommand::ValidateFacts => "validate-facts",
        HookCommand::AutoDependencyAudit => "auto-dependency-audit",
        HookCommand::AutoSkillGenerator => "auto-skill-generator",
        HookCommand::CheckLthreadProgress => "check-lthread-progress",
        HookCommand::SubagentTracker => "subagent-tracker",
        HookCommand::OrchDepthTracker => "orch-depth-tracker",
        HookCommand::SubagentKgInject => "subagent-kg-inject",
        HookCommand::SessionCostTracker => "session-cost-tracker",
        HookCommand::SubagentPalaceStore => "subagent-palace-store",
        HookCommand::OrchestratorToolGuard => "orchestrator-tool-guard",
        HookCommand::ProjectFingerprint => "project-fingerprint",
        HookCommand::AuditConfigChange => "audit-config-change",
        HookCommand::PreCompactPreserve => "pre-compact-preserve",
        HookCommand::AnalyzeRequest => "analyze-request",
        HookCommand::AutoDelegate => "auto-delegate",
    }
}
