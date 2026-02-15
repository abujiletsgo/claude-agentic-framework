#!/usr/bin/env python3
"""
Auto Dependency Audit - PostToolUse Hook

Tracks tool use count and triggers dependency audits at regular intervals
(50 tool uses OR 7 days since last audit).

Usage:
    Called automatically after each tool use by Claude Code.
    Maintains counter in ~/.claude/auto_audit_state.json.
    Runs npm/pip-audit/cargo audit when threshold reached.

Supported audit tools:
- npm audit (Node.js)
- pip-audit (Python)
- cargo audit (Rust)

Exit codes:
    0: Always (never block workflow)
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone


def get_state_path():
    """Get path to audit state file."""
    claude_dir = Path.home() / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    return claude_dir / "auto_audit_state.json"


def load_state(session_id):
    """Load audit state from file."""
    state_path = get_state_path()
    if not state_path.exists():
        return {
            "tool_use_count": 0,
            "last_audit_timestamp": None,
            "session_id": session_id,
        }

    try:
        with open(state_path, "r") as f:
            state = json.load(f)
            # Reset counter if session changed
            if state.get("session_id") != session_id:
                state["tool_use_count"] = 0
                state["session_id"] = session_id
            return state
    except (json.JSONDecodeError, OSError):
        return {
            "tool_use_count": 0,
            "last_audit_timestamp": None,
            "session_id": session_id,
        }


def save_state(state):
    """Save audit state to file."""
    state_path = get_state_path()
    try:
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)
        # Secure the file (0o600 = owner read/write only)
        import os
        os.chmod(state_path, 0o600)
    except (OSError, ImportError):
        pass


def should_trigger_audit(state):
    """
    Check if audit should be triggered.

    Triggers when:
    - Tool use count >= 50, OR
    - Last audit was more than 7 days ago (or never)
    """
    # Check tool use count
    if state["tool_use_count"] >= 50:
        return True, "50 tool uses reached"

    # Check time since last audit
    last_audit = state.get("last_audit_timestamp")
    if not last_audit:
        # Never audited, but don't trigger immediately
        # Wait until at least 10 tool uses
        if state["tool_use_count"] >= 10:
            return True, "initial audit"
        return False, None

    try:
        last_audit_dt = datetime.fromisoformat(last_audit)
        days_since = (datetime.now(timezone.utc) - last_audit_dt).days
        if days_since >= 7:
            return True, f"{days_since} days since last audit"
    except (ValueError, TypeError):
        pass

    return False, None


def detect_package_managers():
    """
    Detect available package managers in the current directory.

    Returns list of (manager_name, audit_command) tuples.
    """
    managers = []
    cwd = Path.cwd()

    # npm (Node.js)
    if (cwd / "package.json").exists():
        managers.append(("npm", ["npm", "audit", "--json"]))

    # pip (Python) - check for requirements.txt or pyproject.toml
    if (cwd / "requirements.txt").exists() or (cwd / "pyproject.toml").exists():
        # Check if pip-audit is available
        try:
            result = subprocess.run(
                ["pip-audit", "--version"],
                capture_output=True,
                timeout=2,
            )
            if result.returncode == 0:
                managers.append(("pip-audit", ["pip-audit", "--format", "json"]))
        except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
            pass

    # cargo (Rust)
    if (cwd / "Cargo.toml").exists():
        # Check if cargo-audit is available
        try:
            result = subprocess.run(
                ["cargo", "audit", "--version"],
                capture_output=True,
                timeout=2,
            )
            if result.returncode == 0:
                managers.append(("cargo", ["cargo", "audit", "--json"]))
        except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
            pass

    return managers


def run_audit(manager_name, command):
    """
    Run a dependency audit command.

    Returns (success, output_text, vulnerability_count).
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path.cwd(),
        )

        # Parse output for vulnerabilities
        vuln_count = 0
        output_lines = []

        if manager_name == "npm":
            try:
                data = json.loads(result.stdout)
                vulnerabilities = data.get("vulnerabilities", {})
                vuln_count = sum(
                    1 for v in vulnerabilities.values()
                    if isinstance(v, dict) and v.get("severity") in ["high", "critical", "moderate"]
                )
                if vuln_count > 0:
                    output_lines.append(f"npm: Found {vuln_count} vulnerabilities")
                    # Extract top 5
                    for name, info in list(vulnerabilities.items())[:5]:
                        if isinstance(info, dict):
                            severity = info.get("severity", "unknown")
                            output_lines.append(f"  - {name}: {severity}")
            except json.JSONDecodeError:
                # Fallback: count lines with severity keywords
                for line in result.stdout.split("\n"):
                    if any(s in line.lower() for s in ["high", "critical", "moderate"]):
                        vuln_count += 1
                        output_lines.append(f"  {line.strip()}")

        elif manager_name == "pip-audit":
            try:
                data = json.loads(result.stdout)
                dependencies = data.get("dependencies", [])
                vuln_count = len(dependencies)
                if vuln_count > 0:
                    output_lines.append(f"pip-audit: Found {vuln_count} vulnerabilities")
                    for dep in dependencies[:5]:
                        name = dep.get("name", "unknown")
                        vulns = dep.get("vulns", [])
                        if vulns:
                            vuln_id = vulns[0].get("id", "unknown")
                            output_lines.append(f"  - {name}: {vuln_id}")
            except json.JSONDecodeError:
                pass

        elif manager_name == "cargo":
            try:
                data = json.loads(result.stdout)
                vulnerabilities = data.get("vulnerabilities", {}).get("list", [])
                vuln_count = len(vulnerabilities)
                if vuln_count > 0:
                    output_lines.append(f"cargo: Found {vuln_count} vulnerabilities")
                    for vuln in vulnerabilities[:5]:
                        package = vuln.get("package", {}).get("name", "unknown")
                        advisory = vuln.get("advisory", {})
                        vuln_id = advisory.get("id", "unknown")
                        output_lines.append(f"  - {package}: {vuln_id}")
            except json.JSONDecodeError:
                pass

        output_text = "\n".join(output_lines) if output_lines else None
        return True, output_text, vuln_count

    except subprocess.TimeoutExpired:
        return False, "Audit timed out", 0
    except (OSError, FileNotFoundError):
        return False, "Audit command not found", 0


def run_dependency_audit():
    """
    Run dependency audits for all detected package managers.

    Outputs vulnerabilities to stderr, returns total vulnerability count.
    """
    managers = detect_package_managers()

    if not managers:
        # No package managers detected
        return 0

    total_vulnerabilities = 0
    audit_outputs = []

    for manager_name, command in managers:
        success, output, vuln_count = run_audit(manager_name, command)
        if success and output:
            audit_outputs.append(output)
            total_vulnerabilities += vuln_count

    if audit_outputs:
        # Output to stderr
        print("\n=== Dependency Audit Results ===", file=sys.stderr)
        for output in audit_outputs:
            print(output, file=sys.stderr)
        print(f"\nTotal vulnerabilities: {total_vulnerabilities}", file=sys.stderr)
        print("Run 'npm audit fix' or equivalent to resolve.\n", file=sys.stderr)

    return total_vulnerabilities


def main():
    """Main entry point for auto dependency audit hook."""
    try:
        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        # Extract session info
        session_id = hook_input.get("session_id", "unknown")

        # Load state
        state = load_state(session_id)

        # Increment tool use count
        state["tool_use_count"] += 1

        # Check if audit should trigger
        should_trigger, reason = should_trigger_audit(state)

        if should_trigger:
            # Run audit
            vuln_count = run_dependency_audit()

            # Reset counter and update timestamp
            state["tool_use_count"] = 0
            state["last_audit_timestamp"] = datetime.now(timezone.utc).isoformat()

            # Save state
            save_state(state)

            # Log to stderr if vulnerabilities found
            if vuln_count > 0:
                print(f"\n⚠️  Audit triggered: {reason}", file=sys.stderr)
        else:
            # Save updated counter
            save_state(state)

    except Exception as e:
        # Never fail, just log error
        print(f"Auto dependency audit error (non-blocking): {e}", file=sys.stderr)

    # Always exit 0 (never block workflow)
    sys.exit(0)


if __name__ == "__main__":
    main()
