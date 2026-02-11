# Security Best Practices

**Version**: 2.0.1 (February 2026)

This guide documents the security infrastructure in the Claude Agentic Framework, how to use it effectively, and how to maintain a secure skill ecosystem.

---

## Table of Contents

- [Security Architecture Overview](#security-architecture-overview)
- [Skills Integrity Verification](#skills-integrity-verification)
- [Automatic Skill Auditing](#automatic-skill-auditing)
- [Input Validation in Skills](#input-validation-in-skills)
- [File Permission Model](#file-permission-model)
- [The --force Flag Convention](#the---force-flag-convention)
- [Import and Path Restrictions](#import-and-path-restrictions)
- [Security Commands Reference](#security-commands-reference)
- [How to Audit a New Skill](#how-to-audit-a-new-skill)
- [How to Generate and Verify skills.lock](#how-to-generate-and-verify-skillslock)
- [Vulnerability Response Process](#vulnerability-response-process)
- [Known Mitigations](#known-mitigations)
- [Security Checklist for Skill Authors](#security-checklist-for-skill-authors)

---

## Security Architecture Overview

The framework implements defense-in-depth with multiple overlapping security layers:

```
Layer 1: Permissions (settings.json allow/deny rules)
Layer 2: Command Hooks (pattern-matching, ~50ms)
Layer 3: Prompt Hooks (LLM semantic validation, ~2-5s)
Layer 4: Skills Integrity (SHA-256 hash verification on session start)
Layer 5: Skill Auditing (Caddy automatic security scanning)
Layer 6: Input Validation (per-skill validation at runtime)
Layer 7: File Permissions (0o600 on sensitive data files)
```

Each layer is independent. A bypass at one layer is caught by another.

---

## Skills Integrity Verification

The `skills.lock` system detects unauthorized or accidental modifications to skill files using SHA-256 hashes.

### How It Works

1. `generate_skills_lock.py` scans all files in `global-skills/` and computes SHA-256 hashes
2. Hashes are stored in `~/.claude/skills.lock` with an overall checksum
3. On every session start, `verify_skills.py` compares current file hashes against the lock
4. Any discrepancy is reported as an advisory warning (modified, deleted, new, missing, or unlocked)

### When to Regenerate the Lock

Regenerate `skills.lock` after any of the following:

- Adding a new skill to `global-skills/`
- Modifying any file within an existing skill
- Removing a skill
- After running `install.sh` if skills were updated
- After pulling changes that modify skills
- After applying security patches to skills

```bash
# Regenerate the lock file
just skills-lock

# Verify immediately after
just skills-verify
```

### What Warnings Mean

| Warning | Meaning | Action |
|---------|---------|--------|
| MODIFIED | File hash differs from lock | If intentional, regenerate lock. If unexpected, investigate. |
| DELETED | File in lock but not on disk | If intentional, regenerate lock. If unexpected, restore from git. |
| NEW FILE | File on disk but not in lock | If legitimate, regenerate lock. If unknown, investigate and remove. |
| MISSING SKILL | Entire skill directory absent | Check symlinks, re-run `install.sh`. |
| UNLOCKED SKILL | Skill present but not in lock | Run `just skills-lock` to include it. |

### Security Notes

- The lock file is not cryptographically signed; it relies on filesystem permissions
- The verification hook follows symlinks, checking actual file content
- Hidden files, `__pycache__`, and `.pyc`/`.pyo` files are excluded from hashing

---

## Automatic Skill Auditing

The Caddy meta-orchestrator automatically audits skills for security issues before recommending them to users.

### What Gets Checked

The `SkillAuditor` (in `global-hooks/framework/caddy/skill_auditor.py`) scans skill files for:

| Category | Patterns Detected |
|----------|-------------------|
| **Code injection** | `eval()`, `exec()`, `shell=True`, `subprocess.call(shell=True)` |
| **Dangerous commands** | `rm -rf`, `curl\|bash`, `wget\|bash`, `chmod 777` |
| **Sensitive file access** | `.ssh/`, `.env`, `.aws/`, credentials files |
| **Insecure permissions** | `chmod 777`, world-readable sensitive files |
| **Network security** | Unencrypted HTTP endpoints, insecure downloads |
| **Secret handling** | Hardcoded API keys, passwords, tokens |

### Severity Levels

| Level | Behavior | Example |
|-------|----------|---------|
| **Critical** | Skill is blocked from Caddy recommendations; user is warned | `eval()` on user input |
| **Warning** | Skill is allowed but user sees a security notice | HTTP instead of HTTPS |
| **Info** | Logged but not shown by default | Reference to `.env` file |

### Configuration

In `data/caddy_config.yaml`:

```yaml
skill_audit:
  enabled: true          # Master switch for auditing
  block_critical: true   # Block skills with critical issues
  warn_on_warnings: true # Show warnings in suggestions
  cache_results: true    # Cache results until skill files change
```

---

## Input Validation in Skills

Skills that accept user input must validate it before passing to shell commands, file operations, or git commands. This prevents command injection and path traversal attacks.

### worktree-manager-skill

The worktree manager validates all feature names through `scripts/validate_name.sh`:

| Rule | Details |
|------|---------|
| Allowed characters | `a-z A-Z 0-9 . _ -` only |
| Blocked characters | `/`, spaces, `;`, `&`, `\|`, `$`, backticks, `(`, `)`, `{`, `}` |
| Path traversal | `..` sequences are blocked |
| Hidden directories | Leading `.` is blocked |
| Length | 2-50 characters |
| Port offset | Non-negative integer, max 99 |

Additionally, computed worktree paths are validated to stay within the parent directory (path containment check).

### video-processor

All input and output paths are validated:

- Input files must exist, be regular files, and be readable
- Special files (`/dev/*`, `/proc/*`, `/sys/*`) are blocked
- Symlinks pointing outside the working directory are rejected
- Output paths must resolve within the current working directory
- System directories (`/bin`, `/etc`, `/usr`, `/var`, etc.) are write-blocked

### knowledge-db

Import paths are restricted to a whitelist of safe directories:

- `~/.claude/data/` (primary data storage)
- `~/.claude/` (configuration directory)
- Current working directory

Path traversal (`..`) and absolute paths outside allowed directories are rejected.

### Writing Validation for New Skills

When creating a new skill that handles user input, follow this pattern:

```python
import re
import os

def validate_input(name: str) -> bool:
    """Validate user-provided input before shell use."""
    # 1. Check allowed characters only
    if not re.match(r'^[a-zA-Z0-9._-]+$', name):
        return False
    # 2. Block path traversal
    if '..' in name:
        return False
    # 3. Enforce length limits
    if len(name) < 1 or len(name) > 100:
        return False
    return True

def validate_path(path: str, allowed_parent: str) -> bool:
    """Validate a file path stays within expected boundaries."""
    resolved = os.path.realpath(path)
    return resolved.startswith(os.path.realpath(allowed_parent))
```

---

## File Permission Model

Sensitive data files are created with restrictive permissions to prevent other users on the system from reading them.

### Enforced Permissions

| File | Permission | Mode | Reason |
|------|------------|------|--------|
| `knowledge.db` | Owner read/write only | `0o600` | Contains project knowledge and decisions |
| `knowledge.jsonl` | Owner read/write only | `0o600` | Append-only durability log |
| `skills.lock` | Owner read/write only | `0o600` | Integrity verification data |

### How Permissions Are Enforced

Permissions are set at two points:

1. **On file creation**: `os.open()` with mode flags or `os.chmod()` immediately after creation
2. **On every open**: Before writing, the code checks and resets permissions if they have drifted

### Best Practice for New Skills

When creating files that contain sensitive data (API keys, knowledge, configuration):

```python
import os
import stat

def secure_write(filepath: str, content: str) -> None:
    """Write content to a file with owner-only permissions."""
    fd = os.open(filepath, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, content.encode())
    finally:
        os.close(fd)
```

---

## The --force Flag Convention

Destructive or overwriting operations across the framework follow a consistent `--force` flag convention:

### Principle

**Default to safe behavior. Require explicit opt-in for destructive actions.**

### Where --force Is Used

| Skill | Operation | Default (no --force) | With --force |
|-------|-----------|---------------------|--------------|
| worktree-manager | Remove worktree | Aborts if uncommitted changes | Removes despite uncommitted changes |
| worktree-manager | Delete branch | Uses `-d` (safe delete) | Uses `-D` (force delete) |
| video-processor | Write output file | Prompts if file exists | Overwrites silently |
| video-processor | All write commands | Checks before overwriting | Skips overwrite check |

### Guidelines for Skill Authors

1. Never silently overwrite files -- always check for existence first
2. Never remove user data without warning -- print what will be lost
3. Use `--force` as the universal opt-in flag name (not `--overwrite`, `--yes`, etc.)
4. Document the `--force` behavior in the skill's SKILL.md
5. Log a warning when `--force` is used so the action is traceable

---

## Import and Path Restrictions

### knowledge-db Import Restrictions

The `import-json` command only reads files from trusted directories:

```
Allowed:
  ~/.claude/data/     (primary data)
  ~/.claude/          (configuration)
  $(pwd)/             (current working directory)

Blocked:
  /etc/passwd         (system files)
  /tmp/anything       (temp directory)
  ../../etc/shadow    (path traversal)
  /dev/random         (device files)
```

### video-processor Output Restrictions

Output files must resolve within the current working directory:

```
Allowed:
  ./output.mp4
  ./subdir/output.webm

Blocked:
  /tmp/output.mp4          (absolute path outside CWD)
  ../../../etc/crontab     (path traversal)
  /usr/local/bin/payload   (system directory)
```

### worktree-manager Path Containment

Worktree directories must reside within the parent directory of the project:

```
Allowed:
  ~/projects/my-app-feature-auth/    (sibling directory)

Blocked:
  ~/../../tmp/evil-worktree/         (path traversal)
  /tmp/worktree/                     (arbitrary location)
```

---

## Security Commands Reference

All security commands are available via the `just` task runner:

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `just skills-lock` | Generate `skills.lock` with SHA-256 hashes | After any skill file change |
| `just skills-verify` | Verify skill files against `skills.lock` | Before sessions, after git pull |
| `just audit-skill <name>` | Audit one skill for security issues | Before using untrusted skills |
| `just audit-all-skills` | Audit every installed skill | Periodic security review |

### Direct Script Invocation

If `just` is not available:

```bash
# Generate lock file
python3 scripts/generate_skills_lock.py

# Verify skills integrity
uv run global-hooks/framework/security/verify_skills.py

# Audit a specific skill
python3 scripts/audit_skill.py <skill-name>
```

---

## How to Audit a New Skill

Before installing or using a new skill (especially from external sources), follow this process:

### Step 1: Review the SKILL.md

Read the skill's `SKILL.md` for:
- What tools it requests (`allowed-tools` in frontmatter)
- What operations it performs
- Whether it accesses the network, filesystem, or runs shell commands

### Step 2: Run the Automated Audit

```bash
# Audit the skill
just audit-skill <skill-name>

# Check exit code: 0 = no critical issues, 1 = critical issues found
echo $?
```

### Step 3: Review Findings

The audit report categorizes findings by severity:

```
--- CRITICAL ---
[line 42] eval() on user input: eval(user_data)

--- WARNING ---
[line 18] HTTP endpoint: http://example.com/api

--- INFO ---
[line 5] References .env file
```

### Step 4: Decide

| Finding | Action |
|---------|--------|
| No findings | Safe to use |
| Info only | Safe to use |
| Warnings only | Use with awareness; consider hardening |
| Critical findings | Do NOT use until issues are resolved |

### Step 5: Lock It

After approving a skill, include it in the integrity lock:

```bash
just skills-lock
```

---

## How to Generate and Verify skills.lock

### Full Workflow

```bash
# 1. Generate the lock (creates ~/.claude/skills.lock)
just skills-lock

# 2. Verify immediately
just skills-verify

# 3. After pulling changes or modifying skills, repeat:
just skills-lock && just skills-verify
```

### Lock File Contents

The lock file (`~/.claude/skills.lock`) contains:

```json
{
  "version": "1.0.0",
  "generated_at": "2026-02-11T12:00:00Z",
  "skills_dir": "/Users/you/Documents/claude-agentic-framework/global-skills",
  "skills": {
    "code-review": {
      "SKILL.md": "sha256:abc123...",
      "scripts/review.py": "sha256:def456..."
    }
  },
  "overall_checksum": "sha256:789abc..."
}
```

### Automating Verification

The verification hook runs automatically on session start when configured in `settings.json`:

```json
{
  "type": "command",
  "command": "uv run __REPO_DIR__/global-hooks/framework/security/verify_skills.py",
  "timeout": 5,
  "statusMessage": "Verifying skills integrity..."
}
```

---

## Vulnerability Response Process

When a security vulnerability is discovered in a skill:

### Priority Levels

| Priority | Definition | Response Time |
|----------|------------|---------------|
| P0 | Command injection, arbitrary code execution, data exfiltration | Immediate fix |
| P1 | Path traversal, file overwrite, privilege escalation | Fix within 24 hours |
| P2 | Information disclosure, insecure defaults | Fix within 1 week |
| P3 | Hardening opportunities, best practice violations | Next release |

### Response Steps

1. **Identify**: Run `just audit-all-skills` or review reported vulnerability
2. **Assess**: Determine priority level and blast radius
3. **Fix**: Apply the minimal fix (input validation, path checks, permission hardening)
4. **Test**: Verify the fix does not break functionality
5. **Lock**: Regenerate `skills.lock` to capture the patched files
6. **Document**: Update the skill's SKILL.md with a Security section
7. **Version**: Bump the skill version in SKILL.md frontmatter

---

## Known Mitigations

The following P0 vulnerabilities were identified and fixed in February 2026:

### 1. Command Injection in worktree-manager-skill

**Problem**: Feature names were passed directly to shell commands without validation, allowing injection of arbitrary commands via names like `; rm -rf /`.

**Fix**: Added `scripts/validate_name.sh` with strict character allowlist (`a-zA-Z0-9._-`), length limits, path traversal blocking, and path containment verification.

**Version**: 0.1.0 -> 0.2.0

### 2. File Overwrite in video-processor

**Problem**: Output files were silently overwritten without user confirmation, allowing an attacker to craft commands that overwrite arbitrary files.

**Fix**: Added overwrite protection (prompts before overwriting), `--force` flag for explicit opt-in, output path restriction to CWD, system directory write-blocking, and input path validation.

**Version**: 0.1.0 -> 0.2.0

### 3. Missing Access Control in knowledge-db

**Problem**: The knowledge database and log files were created with default permissions (potentially world-readable). The import command accepted any file path, enabling reading of sensitive system files.

**Fix**: Added `0o600` permissions on database and log files, restricted import paths to `~/.claude/` and CWD, blocked path traversal in imports, and added export limits to prevent unbounded memory usage.

**Version**: 0.1.0 -> 0.2.0 (pending bump)

---

## Security Checklist for Skill Authors

When creating a new skill, verify the following:

### Input Handling
- [ ] All user-provided strings are validated before shell use
- [ ] Character allowlists are used (not blocklists)
- [ ] Path traversal (`..`) is explicitly blocked
- [ ] Input length limits are enforced
- [ ] Special characters are rejected or escaped

### File Operations
- [ ] Output files check for existence before writing
- [ ] `--force` flag is required for overwrites
- [ ] Output paths are validated to stay within expected directories
- [ ] System directories are write-blocked
- [ ] Sensitive files use `0o600` permissions
- [ ] Symlinks are validated to point within allowed directories

### Shell Commands
- [ ] No string interpolation of user input into shell commands
- [ ] `subprocess` uses list arguments, not `shell=True`
- [ ] All command arguments are validated or sanitized

### Network Operations
- [ ] HTTPS is used instead of HTTP where possible
- [ ] No `curl | bash` or `wget | bash` patterns
- [ ] Downloaded content is verified before execution

### Secrets
- [ ] No hardcoded API keys, passwords, or tokens
- [ ] Secrets are read from environment variables or secure storage
- [ ] Secrets are not logged or printed to stdout

### Documentation
- [ ] SKILL.md has a Security section documenting protections
- [ ] `--force` behavior is documented
- [ ] Path restrictions are documented
- [ ] Version is bumped when security changes are made

---

## Related Documentation

- [SKILLS_INTEGRITY.md](SKILLS_INTEGRITY.md) -- Detailed skills.lock documentation
- [2026_UPGRADE_GUIDE.md](2026_UPGRADE_GUIDE.md) -- Full upgrade guide with security improvements
- `global-hooks/prompt-hooks/README.md` -- LLM semantic validation hooks
- `global-hooks/framework/ANTI_LOOP_GUARDRAILS.md` -- Anti-loop protection
- `global-agents/caddy.md` -- Caddy meta-orchestrator with skill auditing
