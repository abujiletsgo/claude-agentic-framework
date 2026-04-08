pub mod file_watcher;
pub mod post_compact_verify;
pub mod stop_failure_recovery;
pub mod task_quality_gate;
pub mod voice_done;

// Phase 3 — medium hooks
pub mod auto_error_analyzer;
pub mod auto_refine;
pub mod context_bundle_logger;
pub mod enforce_orchestrate;
pub mod epistemic_guard;

// Phase 4 — complex hooks
pub mod auto_memory_writer;
pub mod damage_control;

// Wave 1 — high-frequency latency-sensitive hooks
pub mod auto_escalate;
pub mod auto_fact_extractor;
pub mod orch_depth_tracker;
pub mod orchestrator_tool_guard;

// Wave 1 — monitoring hooks (items 1.5–1.7)
pub mod audit_config_change;
pub mod session_cost_tracker;
pub mod subagent_tracker;

// Diagnostic subcommand
pub mod doctor;
