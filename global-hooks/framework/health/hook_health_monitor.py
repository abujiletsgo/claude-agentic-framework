#!/usr/bin/env python3
"""
Async Stop hook: passive CB health monitor + periodic doctor trigger.
- Detects open circuit breakers, injects warnings into Claude's context
- Auto-resets expired circuits (age > 300s past cooldown)
- Cleans stale orchestration state
- Periodically runs caf-hooks doctor (every 10 Stop events)
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CAF_HEALTH_DIR = Path.home() / '.caf' / 'health'
CAF_ORCH_STATE_DIR = Path.home() / '.caf' / 'orch_state'
HOOK_STATE_FILE = Path.home() / '.claude' / 'hook_state.json'
MONITOR_LOG = CAF_HEALTH_DIR / 'monitor.log'
CIRCUIT_COOLDOWN_SECS = 300
STALE_ORCH_SECS = 86400
DOCTOR_INTERVAL = 10


def log(msg: str):
    CAF_HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    with open(MONITOR_LOG, 'a') as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")


def load_hook_state() -> dict:
    if not HOOK_STATE_FILE.exists():
        return {}
    try:
        return json.loads(HOOK_STATE_FILE.read_text())
    except Exception:
        return {}


def save_hook_state(state: dict):
    import fcntl
    tmp = HOOK_STATE_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, indent=2, default=str))
    with open(HOOK_STATE_FILE, 'r+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            # Re-read under lock to avoid races
            fresh = json.loads(f.read()) if HOOK_STATE_FILE.stat().st_size > 0 else {}
            # Apply our changes (open circuit resets)
            for key, val in state.get('hooks', {}).items():
                if key in fresh.get('hooks', {}):
                    fresh['hooks'][key] = val
            if 'global_stats' in state:
                fresh.setdefault('global_stats', {}).update(state['global_stats'])
            tmp.write_text(json.dumps(fresh, indent=2, default=str))
            tmp.replace(HOOK_STATE_FILE)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def reset_hook_circuit(state: dict, key: str) -> dict:
    """Reset a circuit breaker to closed state."""
    if 'hooks' in state and key in state['hooks']:
        state['hooks'][key]['state'] = 'closed'
        state['hooks'][key]['consecutive_failures'] = 0
        state['hooks'][key]['disabled_at'] = None
        state['hooks'][key]['retry_after'] = None
    return state


def parse_ts(ts_str) -> float:
    """Parse RFC3339 or ISO timestamp to unix time. Returns 0 on failure."""
    if not ts_str:
        return 0
    try:
        dt = datetime.fromisoformat(str(ts_str).replace('Z', '+00:00'))
        return dt.timestamp()
    except Exception:
        return 0


def check_circuits(state: dict) -> tuple:
    """
    Returns (open_circuits_list, updated_state).
    Auto-resets circuits past their cooldown.
    """
    now = time.time()
    open_circuits = []

    for key, hook in state.get('hooks', {}).items():
        if hook.get('state') != 'open':
            continue
        disabled_at = parse_ts(hook.get('disabled_at'))
        age = now - disabled_at if disabled_at else 0

        if age > CIRCUIT_COOLDOWN_SECS:
            # Past cooldown — auto-reset
            state = reset_hook_circuit(state, key)
            log(f"[AUTO-RESET] hook={key} age={age:.0f}s last_error={hook.get('last_error', '')[:80]}")
        else:
            retry_at = parse_ts(hook.get('retry_after'))
            reset_in = max(0, retry_at - now) if retry_at else max(0, CIRCUIT_COOLDOWN_SECS - age)
            open_circuits.append({
                'key': key,
                'last_error': hook.get('last_error', 'unknown'),
                'age_s': int(age),
                'reset_in_s': int(reset_in),
            })

    return open_circuits, state


def cleanup_stale_orch_state():
    depth_file = CAF_ORCH_STATE_DIR / 'depth'
    marker_file = CAF_ORCH_STATE_DIR / 'guard.marker'
    if not depth_file.exists():
        return
    try:
        data = json.loads(depth_file.read_text())
        ts = parse_ts(data.get('ts'))
        age = time.time() - ts if ts else STALE_ORCH_SECS + 1
        if age > STALE_ORCH_SECS:
            depth_file.unlink(missing_ok=True)
            marker_file.unlink(missing_ok=True)
            log(f"[STALE-CLEANUP] orch_state age={age:.0f}s")
    except Exception:
        pass


def find_caf_hooks_binary() -> str | None:
    """Find caf-hooks binary via PATH or common locations."""
    import shutil
    if binary := shutil.which('caf-hooks'):
        return binary
    # Check common install location
    local_bin = Path.home() / '.local' / 'bin' / 'caf-hooks'
    if local_bin.exists():
        return str(local_bin)
    # Check repo target dir (look for CLAUDE_PROJECT_DIR or CAF_HOOKS_DIR)
    for env_var in ('CLAUDE_PROJECT_DIR', 'CAF_HOOKS_DIR'):
        if d := os.environ.get(env_var):
            candidate = Path(d).parent / 'target' / 'release' / 'caf-hooks'
            if candidate.exists():
                return str(candidate)
    return None


def run_periodic_doctor(state: dict) -> dict:
    """Run caf-hooks doctor every DOCTOR_INTERVAL Stop events."""
    stats = state.setdefault('global_stats', {})
    count = stats.get('doctor_run_count', 0)
    stats['doctor_run_count'] = count + 1

    if count % DOCTOR_INTERVAL != 0:
        return state

    binary = find_caf_hooks_binary()
    if not binary:
        log("[DOCTOR] caf-hooks binary not found, skipping periodic doctor run")
        return state

    try:
        CAF_HEALTH_DIR.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [binary, 'doctor'],
            capture_output=True, text=True, timeout=30
        )
        doctor_output = result.stdout + result.stderr
        (CAF_HEALTH_DIR / 'doctor_last.txt').write_text(
            f"# Doctor run at {datetime.now().isoformat()}\n{doctor_output}"
        )
        log(f"[DOCTOR] Periodic run complete (exit={result.returncode}, lines={doctor_output.count(chr(10))})")
    except Exception as e:
        log(f"[DOCTOR] Failed to run: {e}")

    return state


def inject_context(open_circuits: list, binary_missing: bool):
    """Write context injection to stdout if there are issues."""
    messages = []

    if binary_missing:
        messages.append(
            "[CAF HEALTH] caf-hooks binary missing. "
            "Run: cargo build --release from repo root to rebuild."
        )

    if open_circuits:
        lines = [f"[CAF HEALTH] {len(open_circuits)} hook(s) currently disabled by circuit breaker:"]
        for c in open_circuits:
            reset_str = f"resets in {c['reset_in_s']}s" if c['reset_in_s'] > 0 else "ready to reset"
            lines.append(f"  - {c['key']}: {c['last_error'][:60]} (disabled {c['age_s']}s ago, {reset_str})")
        lines.append("Run `caf-hooks doctor` to diagnose.")
        messages.append('\n'.join(lines))

    if messages:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "additionalContext": '\n\n'.join(messages)
            }
        }
        print(json.dumps(output))


def main():
    binary = find_caf_hooks_binary()
    binary_missing = binary is None

    # Load state
    state = load_hook_state()
    if not state:
        sys.exit(0)  # No state file yet, nothing to monitor

    # Check and auto-reset circuits
    open_circuits, state = check_circuits(state)

    # Clean stale orch state
    cleanup_stale_orch_state()

    # Periodic doctor
    state = run_periodic_doctor(state)

    # Save updated state (resets + count increment)
    try:
        save_hook_state(state)
    except Exception as e:
        log(f"[WARN] Failed to save state: {e}")

    # Inject context if needed
    inject_context(open_circuits, binary_missing)

    sys.exit(0)


if __name__ == '__main__':
    main()
