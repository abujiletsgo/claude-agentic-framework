/// CAF Doctor — environment health check subcommand.
///
/// Does NOT read stdin. Runs self-contained checks and prints results to stdout.
/// Exit code: 0 if all PASS or only WARNs, 1 if any FAIL.
use std::path::{Path, PathBuf};
use std::process::Command;

enum Status {
    Pass(String),
    Warn(String),
    Fail(String),
}

struct CheckResult {
    name: String,
    status: Status,
}

impl CheckResult {
    fn pass(name: &str, detail: impl Into<String>) -> Self {
        CheckResult { name: name.to_string(), status: Status::Pass(detail.into()) }
    }
    fn warn(name: &str, detail: impl Into<String>) -> Self {
        CheckResult { name: name.to_string(), status: Status::Warn(detail.into()) }
    }
    fn fail(name: &str, detail: impl Into<String>) -> Self {
        CheckResult { name: name.to_string(), status: Status::Fail(detail.into()) }
    }
}

pub fn run() {
    println!("CAF Doctor — Environment Health Check");
    println!("======================================");
    println!();

    let mut results: Vec<CheckResult> = Vec::new();

    // ── Core prerequisites ────────────────────────────────────────────────
    results.push(check_uv());
    results.push(check_python());
    results.push(check_python_version());
    results.push(check_git());
    results.push(check_claude_cli());
    results.push(check_cargo());
    results.push(check_officecli());
    results.push(check_rust_binary());

    // ── Configuration ────────────────────────────────────────────────────
    results.push(check_settings_json_exists());
    results.push(check_settings_json_path_has_uv());
    results.push(check_hook_scripts());
    results.push(check_symlinks());

    // ── Directories & files ──────────────────────────────────────────────
    results.push(check_required_dirs());
    results.push(check_circuit_breaker_dir());
    results.push(check_tmp_claude_dir());
    results.push(check_memory_files());

    // ── Framework & integrations ─────────────────────────────────────────
    results.push(check_framework_integrity());
    results.push(check_mempalace());
    results.push(check_aaak_compression());

    // ── Runtime smoke tests ──────────────────────────────────────────────
    results.push(check_python_deps());
    results.push(check_anthropic_sdk());
    results.push(check_hook_smoke_test());

    // Print results
    let mut passes = 0usize;
    let mut warns = 0usize;
    let mut fails = 0usize;

    for r in &results {
        match &r.status {
            Status::Pass(detail) => {
                println!("[PASS] {}", r.name);
                println!("  {}", detail);
                passes += 1;
            }
            Status::Warn(detail) => {
                println!("[WARN] {}", r.name);
                println!("  {}", detail);
                warns += 1;
            }
            Status::Fail(detail) => {
                println!("[FAIL] {}", r.name);
                println!("  {}", detail);
                fails += 1;
            }
        }
        println!();
    }

    // Summary
    println!("Summary: {} passed, {} warnings, {} failures", passes, warns, fails);

    // Quick fixes for failures
    if fails > 0 {
        println!();
        println!("Quick fixes:");
        for r in &results {
            if let Status::Fail(detail) = &r.status {
                match r.name.as_str() {
                    "uv binary" => {
                        println!("  uv not found: curl -LsSf https://astral.sh/uv/install.sh | sh");
                        println!("    then add ~/.local/bin to PATH in your shell profile");
                    }
                    "settings.json exists" => {
                        println!("  settings.json missing: bash install.sh");
                    }
                    "Hook scripts referenced in settings.json exist" => {
                        println!("  Hook scripts missing: bash install.sh");
                        println!("  Detail: {}", detail);
                    }
                    "Framework repo integrity" => {
                        println!("  Framework directories missing: verify git repo is intact");
                    }
                    "Claude Code CLI" => {
                        println!("  Claude Code not found: npm install -g @anthropic-ai/claude-code");
                    }
                    "Hook smoke test" => {
                        println!("  Hook runtime broken. Try: uv cache clean && bash install.sh");
                    }
                    "Symlinks (commands/skills/agents)" => {
                        println!("  Symlinks missing or broken: bash install.sh");
                    }
                    _ => {
                        println!("  {}: {}", r.name, detail);
                    }
                }
            }
        }
    }

    if fails > 0 {
        std::process::exit(1);
    }
    // Only WARNs or all PASSes — exit 0 (handled by main's exit(0) after run())
}

// ── Individual checks ────────────────────────────────────────────────────────

fn check_uv() -> CheckResult {
    println!("[CHECK] uv binary");
    // Try running uv --version from PATH
    match Command::new("uv").arg("--version").output() {
        Ok(out) if out.status.success() => {
            let version = String::from_utf8_lossy(&out.stdout).trim().to_string();
            return CheckResult::pass("uv binary", version);
        }
        _ => {}
    }

    // Not in PATH — check common locations
    let common = [
        dirs::home_dir().map(|h| h.join(".local/bin/uv")),
        dirs::home_dir().map(|h| h.join(".cargo/bin/uv")),
        Some(PathBuf::from("/usr/local/bin/uv")),
    ];

    for loc_opt in &common {
        if let Some(loc) = loc_opt {
            if loc.exists() {
                return CheckResult::fail(
                    "uv binary",
                    format!("not in PATH, found at {} — add to PATH", loc.display()),
                );
            }
        }
    }

    CheckResult::fail("uv binary", "not in PATH and not found at common locations")
}

fn check_python() -> CheckResult {
    println!("[CHECK] Python");
    match Command::new("python3").arg("--version").output() {
        Ok(out) if out.status.success() => {
            let version = String::from_utf8_lossy(&out.stdout).trim().to_string();
            CheckResult::pass("Python", version)
        }
        Ok(out) => {
            let stderr = String::from_utf8_lossy(&out.stderr).trim().to_string();
            CheckResult::fail("Python", format!("python3 --version failed: {}", stderr))
        }
        Err(e) => CheckResult::fail("Python", format!("python3 not found: {}", e)),
    }
}

fn check_git() -> CheckResult {
    println!("[CHECK] Git");
    match Command::new("git").arg("--version").output() {
        Ok(out) if out.status.success() => {
            let version = String::from_utf8_lossy(&out.stdout).trim().to_string();
            CheckResult::pass("Git", version)
        }
        Ok(out) => {
            let stderr = String::from_utf8_lossy(&out.stderr).trim().to_string();
            CheckResult::fail("Git", format!("git --version failed: {}", stderr))
        }
        Err(e) => CheckResult::fail("Git", format!("git not found: {}", e)),
    }
}

fn check_rust_binary() -> CheckResult {
    println!("[CHECK] Rust binary");
    // Get the current binary's mtime
    let exe_path = match std::env::current_exe() {
        Ok(p) => p,
        Err(e) => return CheckResult::warn("Rust binary", format!("cannot determine binary path: {}", e)),
    };

    let bin_mtime = match std::fs::metadata(&exe_path).and_then(|m| m.modified()) {
        Ok(t) => t,
        Err(e) => return CheckResult::warn("Rust binary", format!("cannot read binary mtime: {}", e)),
    };

    // Derive source directory: binary is at <framework>/caf-hooks/target/release/caf-hooks
    // Go up: release/ -> target/ -> caf-hooks/ -> src/
    let src_dir = exe_path
        .parent() // release/
        .and_then(|p| p.parent()) // target/
        .and_then(|p| p.parent()) // caf-hooks/
        .map(|p| p.join("src"));

    let src_dir = match src_dir {
        Some(d) if d.exists() => d,
        _ => return CheckResult::pass("Rust binary", "PASS (source dir not found — skipping mtime check)"),
    };

    // Find the newest .rs file mtime
    let newest_src_mtime = find_newest_mtime(&src_dir);

    match newest_src_mtime {
        Some(src_mtime) if src_mtime > bin_mtime => {
            CheckResult::warn(
                "Rust binary",
                "binary older than source — run: cd caf-hooks && cargo build --release",
            )
        }
        _ => CheckResult::pass("Rust binary", "binary is up to date"),
    }
}

fn find_newest_mtime(dir: &Path) -> Option<std::time::SystemTime> {
    let mut newest: Option<std::time::SystemTime> = None;
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                if let Some(t) = find_newest_mtime(&path) {
                    if newest.map_or(true, |n| t > n) {
                        newest = Some(t);
                    }
                }
            } else if path.extension().and_then(|e| e.to_str()) == Some("rs") {
                if let Ok(meta) = std::fs::metadata(&path) {
                    if let Ok(t) = meta.modified() {
                        if newest.map_or(true, |n| t > n) {
                            newest = Some(t);
                        }
                    }
                }
            }
        }
    }
    newest
}

fn check_settings_json_exists() -> CheckResult {
    println!("[CHECK] settings.json exists");
    let path = match settings_json_path() {
        Some(p) => p,
        None => return CheckResult::fail("settings.json exists", "cannot determine home directory"),
    };
    if path.exists() {
        CheckResult::pass("settings.json exists", format!("{}", path.display()))
    } else {
        CheckResult::fail("settings.json exists", "~/.claude/settings.json not found — run install.sh")
    }
}

fn check_settings_json_path_has_uv() -> CheckResult {
    println!("[CHECK] settings.json PATH includes uv");
    let path = match settings_json_path() {
        Some(p) => p,
        None => return CheckResult::fail("settings.json PATH includes uv", "cannot determine home directory"),
    };
    let contents = match std::fs::read_to_string(&path) {
        Ok(c) => c,
        Err(_) => return CheckResult::warn("settings.json PATH includes uv", "settings.json not readable — skipping"),
    };
    let json: serde_json::Value = match serde_json::from_str(&contents) {
        Ok(v) => v,
        Err(e) => return CheckResult::warn("settings.json PATH includes uv", format!("settings.json parse error: {}", e)),
    };

    // env.PATH is typically a colon-separated string
    let env_path = json
        .get("env")
        .and_then(|e| e.get("PATH"))
        .and_then(|p| p.as_str())
        .unwrap_or("");

    if env_path.is_empty() {
        return CheckResult::warn(
            "settings.json PATH includes uv",
            "env.PATH not set in settings.json — hooks may fail if uv not in system PATH",
        );
    }

    // Check each directory in the colon-separated PATH for a uv binary
    let uv_found = env_path.split(':').any(|dir| {
        let uv_path = PathBuf::from(dir).join("uv");
        uv_path.exists()
    });

    if uv_found {
        CheckResult::pass("settings.json PATH includes uv", "uv found in a directory listed in env.PATH")
    } else {
        CheckResult::warn(
            "settings.json PATH includes uv",
            "uv not found in any directory in settings.json env.PATH — hooks will fail",
        )
    }
}

fn check_hook_scripts() -> CheckResult {
    println!("[CHECK] Hook scripts referenced in settings.json exist");
    let path = match settings_json_path() {
        Some(p) => p,
        None => return CheckResult::fail("Hook scripts referenced in settings.json exist", "cannot determine home directory"),
    };
    let contents = match std::fs::read_to_string(&path) {
        Ok(c) => c,
        Err(_) => return CheckResult::warn("Hook scripts referenced in settings.json exist", "settings.json not readable — skipping"),
    };
    let json: serde_json::Value = match serde_json::from_str(&contents) {
        Ok(v) => v,
        Err(e) => return CheckResult::warn("Hook scripts referenced in settings.json exist", format!("parse error: {}", e)),
    };

    let commands = extract_hook_commands(&json);
    if commands.is_empty() {
        return CheckResult::pass("Hook scripts referenced in settings.json exist", "no hook commands found in settings.json");
    }

    let total = commands.len();
    let mut missing: Vec<String> = Vec::new();

    for cmd in &commands {
        // Extract the checkable file path from the command string.
        // Patterns observed:
        //   "uv run --no-project /abs/path/to/script.py"
        //   "/abs/path/to/caf-hooks subcommand"
        //   "/abs/path/to/binary"
        // Strategy: find the first token that looks like an absolute path
        let file_to_check = cmd.split_whitespace()
            .find(|tok| tok.starts_with('/'));
        match file_to_check {
            Some(abs_path) => {
                if !PathBuf::from(abs_path).exists() {
                    missing.push(abs_path.to_string());
                }
            }
            None => {
                // No absolute path token — check the first token as-is
                if let Some(first) = cmd.split_whitespace().next() {
                    if !PathBuf::from(first).exists() {
                        // Skip bare commands like "uv" (already checked separately)
                        // Only flag if there's something that looks like a path
                    }
                }
            }
        }
    }

    if missing.is_empty() {
        CheckResult::pass(
            "Hook scripts referenced in settings.json exist",
            format!("{}/{} hooks found", total, total),
        )
    } else {
        CheckResult::fail(
            "Hook scripts referenced in settings.json exist",
            format!(
                "{}/{} hooks found — missing: {}",
                total - missing.len(),
                total,
                missing.join(", ")
            ),
        )
    }
}

/// Extract all "command" string values from settings.json hooks structure.
///
/// settings.json structure:
/// { "hooks": { "EventName": [ { "hooks": [ { "type": "command", "command": "..." } ] } ] } }
fn extract_hook_commands(json: &serde_json::Value) -> Vec<String> {
    let mut commands = Vec::new();
    if let Some(hooks_map) = json.get("hooks").and_then(|h| h.as_object()) {
        for (_event, event_hooks) in hooks_map {
            if let Some(arr) = event_hooks.as_array() {
                for hook_group in arr {
                    if let Some(inner_hooks) = hook_group.get("hooks").and_then(|h| h.as_array()) {
                        for hook in inner_hooks {
                            if let Some(cmd) = hook.get("command").and_then(|c| c.as_str()) {
                                commands.push(cmd.to_string());
                            }
                        }
                    }
                    // Also handle flat "command" at the group level
                    if let Some(cmd) = hook_group.get("command").and_then(|c| c.as_str()) {
                        commands.push(cmd.to_string());
                    }
                }
            }
        }
    }
    commands
}

fn check_required_dirs() -> CheckResult {
    println!("[CHECK] Required directories");
    let home = match dirs::home_dir() {
        Some(h) => h,
        None => return CheckResult::fail("Required directories", "cannot determine home directory"),
    };

    let required = [
        home.join(".claude/data"),
        home.join(".claude/logs"),
        home.join(".claude/skills"),
    ];

    let mut missing: Vec<String> = Vec::new();
    for dir in &required {
        if !dir.exists() {
            missing.push(dir.display().to_string());
        }
    }

    if missing.is_empty() {
        CheckResult::pass("Required directories", "~/.claude/data, ~/.claude/logs, ~/.claude/skills all exist")
    } else {
        CheckResult::warn(
            "Required directories",
            format!("missing (will be created on first run): {}", missing.join(", ")),
        )
    }
}

fn check_framework_integrity() -> CheckResult {
    println!("[CHECK] Framework repo integrity");
    // Derive framework dir from binary location:
    // binary: <framework>/caf-hooks/target/release/caf-hooks
    // framework dir: four levels up from binary
    let exe_path = match std::env::current_exe() {
        Ok(p) => p,
        Err(e) => return CheckResult::fail("Framework repo integrity", format!("cannot determine binary path: {}", e)),
    };

    let framework_dir = exe_path
        .parent() // release/
        .and_then(|p| p.parent()) // target/
        .and_then(|p| p.parent()) // caf-hooks/
        .and_then(|p| p.parent()); // framework root

    let framework_dir = match framework_dir {
        Some(d) => d.to_path_buf(),
        None => return CheckResult::fail("Framework repo integrity", "cannot derive framework directory from binary path"),
    };

    let required_dirs = [
        "global-hooks",
        "global-agents",
        "global-commands",
        "global-skills",
        "templates",
    ];

    let mut missing: Vec<&str> = Vec::new();
    for dir in &required_dirs {
        if !framework_dir.join(dir).exists() {
            missing.push(dir);
        }
    }

    if missing.is_empty() {
        CheckResult::pass(
            "Framework repo integrity",
            format!("all required directories found in {}", framework_dir.display()),
        )
    } else {
        CheckResult::fail(
            "Framework repo integrity",
            format!(
                "missing directories in {}: {}",
                framework_dir.display(),
                missing.join(", ")
            ),
        )
    }
}

fn check_python_version() -> CheckResult {
    println!("[CHECK] Python >= 3.10");
    match Command::new("python3")
        .args(["-c", "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}'); exit(0 if (v.major,v.minor) >= (3,10) else 1)"])
        .output()
    {
        Ok(out) => {
            let version = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if out.status.success() {
                CheckResult::pass("Python >= 3.10", format!("{}", version))
            } else {
                CheckResult::fail(
                    "Python >= 3.10",
                    format!("found {} — need 3.10+. Fix: uv python install 3.13", version),
                )
            }
        }
        Err(e) => CheckResult::fail("Python >= 3.10", format!("cannot check: {}", e)),
    }
}

fn check_claude_cli() -> CheckResult {
    println!("[CHECK] Claude Code CLI");
    match Command::new("claude").arg("--version").output() {
        Ok(out) if out.status.success() => {
            let version = String::from_utf8_lossy(&out.stdout).trim().to_string();
            CheckResult::pass("Claude Code CLI", version)
        }
        _ => CheckResult::fail(
            "Claude Code CLI",
            "not found — install: npm install -g @anthropic-ai/claude-code",
        ),
    }
}

fn check_cargo() -> CheckResult {
    println!("[CHECK] Cargo (Rust toolchain)");
    match Command::new("cargo").arg("--version").output() {
        Ok(out) if out.status.success() => {
            let version = String::from_utf8_lossy(&out.stdout).trim().to_string();
            CheckResult::pass("Cargo (Rust toolchain)", version)
        }
        _ => CheckResult::warn(
            "Cargo (Rust toolchain)",
            "not found — Rust hooks won't rebuild. Install: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
        ),
    }
}

fn check_officecli() -> CheckResult {
    println!("[CHECK] OfficeCLI");
    match Command::new("officecli").arg("--version").output() {
        Ok(out) if out.status.success() => {
            let version = String::from_utf8_lossy(&out.stdout).trim().to_string();
            CheckResult::pass("OfficeCLI", version)
        }
        _ => CheckResult::warn(
            "OfficeCLI",
            "not found — /docs skill will not work. Install: curl -fsSL https://raw.githubusercontent.com/iOfficeAI/OfficeCLI/main/install.sh | bash",
        ),
    }
}

fn check_symlinks() -> CheckResult {
    println!("[CHECK] Symlinks (commands/skills/agents)");
    let home = match dirs::home_dir() {
        Some(h) => h,
        None => return CheckResult::fail("Symlinks (commands/skills/agents)", "cannot determine home directory"),
    };

    let dirs_to_check = [
        (home.join(".claude/commands"), "commands"),
        (home.join(".claude/skills"), "skills"),
        (home.join(".claude/agents"), "agents"),
    ];

    let mut total = 0usize;
    let mut broken = 0usize;
    let mut missing_dirs: Vec<&str> = Vec::new();

    for (dir, label) in &dirs_to_check {
        if !dir.exists() {
            missing_dirs.push(label);
            continue;
        }
        if let Ok(entries) = std::fs::read_dir(dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_symlink() {
                    total += 1;
                    // Check if target exists
                    if !path.exists() {
                        broken += 1;
                    }
                }
            }
        }
    }

    if !missing_dirs.is_empty() {
        return CheckResult::fail(
            "Symlinks (commands/skills/agents)",
            format!("directories missing: {} — run install.sh", missing_dirs.join(", ")),
        );
    }

    if total == 0 {
        return CheckResult::fail(
            "Symlinks (commands/skills/agents)",
            "no symlinks found — run install.sh to link commands/skills/agents",
        );
    }

    if broken > 0 {
        CheckResult::warn(
            "Symlinks (commands/skills/agents)",
            format!("{} broken symlinks out of {} — run install.sh to repair", broken, total),
        )
    } else {
        CheckResult::pass(
            "Symlinks (commands/skills/agents)",
            format!("{} symlinks OK", total),
        )
    }
}

fn check_circuit_breaker_dir() -> CheckResult {
    println!("[CHECK] Circuit breaker directory");
    let home = match dirs::home_dir() {
        Some(h) => h,
        None => return CheckResult::warn("Circuit breaker directory", "cannot determine home directory"),
    };
    let dir = home.join(".claude/circuit_breakers");
    if dir.exists() {
        CheckResult::pass("Circuit breaker directory", format!("{}", dir.display()))
    } else {
        CheckResult::warn(
            "Circuit breaker directory",
            "~/.claude/circuit_breakers/ not found — will be created on first hook failure",
        )
    }
}

fn check_tmp_claude_dir() -> CheckResult {
    println!("[CHECK] /tmp/claude/ directory");
    let dir = Path::new("/tmp/claude");
    if dir.exists() {
        CheckResult::pass("/tmp/claude/ directory", "exists")
    } else {
        CheckResult::warn("/tmp/claude/ directory", "not found — will be created by install.sh. Run: mkdir -p /tmp/claude")
    }
}

fn check_memory_files() -> CheckResult {
    println!("[CHECK] Memory files");
    let home = match dirs::home_dir() {
        Some(h) => h,
        None => return CheckResult::warn("Memory files", "cannot determine home directory"),
    };

    let files = [
        home.join(".claude/FACTS.md"),
        home.join(".claude/MEMORY.md"),
    ];

    let missing: Vec<String> = files
        .iter()
        .filter(|f| !f.exists())
        .map(|f| f.display().to_string())
        .collect();

    if missing.is_empty() {
        CheckResult::pass("Memory files", "FACTS.md and MEMORY.md exist")
    } else {
        CheckResult::warn(
            "Memory files",
            format!("missing: {} — run install.sh or touch them", missing.join(", ")),
        )
    }
}

fn check_python_deps() -> CheckResult {
    println!("[CHECK] Python deps (pyyaml, pydantic)");
    // Write a temp script with inline deps and run via uv
    let script = r#"# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0.0","pydantic>=2.0.0"]
# ///
import yaml, pydantic; print(f"pyyaml={yaml.__version__} pydantic={pydantic.__version__}")
"#;
    match run_uv_script(script) {
        Ok(output) => CheckResult::pass("Python deps (pyyaml, pydantic)", output),
        Err(e) => CheckResult::warn(
            "Python deps (pyyaml, pydantic)",
            format!("not cached — first hook run may be slow. Error: {}", e),
        ),
    }
}

fn check_anthropic_sdk() -> CheckResult {
    println!("[CHECK] Anthropic SDK");
    let script = r#"# /// script
# requires-python = ">=3.10"
# dependencies = ["anthropic>=0.40.0"]
# ///
import anthropic; print(f"anthropic={anthropic.__version__}")
"#;
    match run_uv_script(script) {
        Ok(output) => CheckResult::pass("Anthropic SDK", output),
        Err(e) => CheckResult::warn(
            "Anthropic SDK",
            format!("not cached — kr_mode and caddy hooks will be slow on first run. {}", e),
        ),
    }
}

fn check_hook_smoke_test() -> CheckResult {
    println!("[CHECK] Hook smoke test");
    let script = r#"# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0.0","pydantic>=2.0.0"]
# ///
import yaml, pydantic, json, sys
print(json.dumps({"result": "pass"}))
"#;
    // Pipe empty JSON as stdin
    let tmp_path = "/tmp/caf_doctor_smoke.py";
    if std::fs::write(tmp_path, script).is_err() {
        return CheckResult::warn("Hook smoke test", "cannot write temp file");
    }

    let result = Command::new("uv")
        .args(["run", "--no-project", tmp_path])
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .output();

    let _ = std::fs::remove_file(tmp_path);

    match result {
        Ok(out) if out.status.success() => {
            let stdout = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if stdout.contains("\"result\"") {
                CheckResult::pass("Hook smoke test", "uv run + deps + JSON output OK")
            } else {
                CheckResult::warn("Hook smoke test", format!("ran but unexpected output: {}", stdout))
            }
        }
        Ok(out) => {
            let stderr = String::from_utf8_lossy(&out.stderr).trim().to_string();
            CheckResult::fail(
                "Hook smoke test",
                format!("uv run failed: {} — try: uv cache clean && bash install.sh", stderr),
            )
        }
        Err(e) => CheckResult::fail("Hook smoke test", format!("cannot run uv: {}", e)),
    }
}

/// Run a uv inline-script and return trimmed stdout or an error message.
fn run_uv_script(script: &str) -> Result<String, String> {
    let tmp_path = "/tmp/caf_doctor_check.py";
    std::fs::write(tmp_path, script).map_err(|e| format!("write: {}", e))?;

    let result = Command::new("uv")
        .args(["run", "--no-project", tmp_path])
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .output();

    let _ = std::fs::remove_file(tmp_path);

    match result {
        Ok(out) if out.status.success() => {
            Ok(String::from_utf8_lossy(&out.stdout).trim().to_string())
        }
        Ok(out) => {
            let stderr = String::from_utf8_lossy(&out.stderr).trim().to_string();
            Err(stderr)
        }
        Err(e) => Err(format!("{}", e)),
    }
}

fn check_mempalace() -> CheckResult {
    println!("[CHECK] Mempalace MCP server");
    let home = match dirs::home_dir() {
        Some(h) => h,
        None => return CheckResult::warn("Mempalace MCP server", "cannot determine home directory"),
    };

    let venv_python = home.join("Documents/mempalace/.venv/bin/python");
    if !venv_python.exists() {
        return CheckResult::warn(
            "Mempalace MCP server",
            "not installed — mempalace MCP features disabled. To enable: cd ~/Documents/mempalace && uv sync",
        );
    }

    // Verify the mempalace module is importable
    match Command::new(venv_python.to_str().unwrap_or("python3"))
        .args(["-c", "import mempalace; print(mempalace.__version__ if hasattr(mempalace, '__version__') else 'installed')"])
        .output()
    {
        Ok(out) if out.status.success() => {
            let version = String::from_utf8_lossy(&out.stdout).trim().to_string();
            CheckResult::pass("Mempalace MCP server", format!("mempalace {} ({})", version, venv_python.display()))
        }
        Ok(out) => {
            let stderr = String::from_utf8_lossy(&out.stderr).trim().to_string();
            CheckResult::warn(
                "Mempalace MCP server",
                format!("venv exists but import failed: {} — try: cd ~/Documents/mempalace && uv sync", stderr),
            )
        }
        Err(e) => CheckResult::warn("Mempalace MCP server", format!("cannot run venv python: {}", e)),
    }
}

fn check_aaak_compression() -> CheckResult {
    println!("[CHECK] AAAK compression");
    let home = match dirs::home_dir() {
        Some(h) => h,
        None => return CheckResult::warn("AAAK compression", "cannot determine home directory"),
    };

    // AAAK depends on mempalace venv — check site-packages exist
    let venv_lib = home.join("Documents/mempalace/.venv/lib");
    if !venv_lib.exists() {
        return CheckResult::warn(
            "AAAK compression",
            "disabled — mempalace venv not found. To enable: cd ~/Documents/mempalace && uv sync",
        );
    }

    // Find python3.X site-packages dir
    let sp_found = std::fs::read_dir(&venv_lib)
        .ok()
        .and_then(|entries| {
            entries
                .flatten()
                .find(|e| {
                    let name = e.file_name().to_string_lossy().to_string();
                    name.starts_with("python3") && e.path().join("site-packages").exists()
                })
                .map(|e| e.path().join("site-packages"))
        });

    match sp_found {
        Some(sp) => {
            // Verify mempalace package is in site-packages
            let mempalace_pkg = sp.join("mempalace");
            if mempalace_pkg.exists() {
                CheckResult::pass("AAAK compression", format!("enabled ({})", sp.display()))
            } else {
                CheckResult::warn(
                    "AAAK compression",
                    format!("site-packages found but mempalace package missing in {} — try: cd ~/Documents/mempalace && uv sync", sp.display()),
                )
            }
        }
        None => CheckResult::warn(
            "AAAK compression",
            "disabled — no python3.x/site-packages found in mempalace venv",
        ),
    }
}

// ── Helpers ──────────────────────────────────────────────────────────────────

fn settings_json_path() -> Option<PathBuf> {
    dirs::home_dir().map(|h| h.join(".claude/settings.json"))
}
