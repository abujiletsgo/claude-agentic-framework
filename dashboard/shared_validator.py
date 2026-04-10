#!/usr/bin/env python3
"""
CAF Shared Validator — persistent pane that services test requests from any lead.

Polls shared/test_queue.jsonl for queued requests, runs each command,
writes results to shared/test_results.jsonl, and notifies the requesting
lead via cmux send-agent.

Usage:
  uv run python dashboard/shared_validator.py <orch_id>
"""
import sys
import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timezone

CAF_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CAF_DIR / "lib"))
import cmux_client as cmux  # noqa

POLL_INTERVAL = 3  # seconds


def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_test(command: str, cwd: str) -> tuple[str, str, int]:
    """Run command, return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=300, cwd=cwd,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT after 300s", 1
    except Exception as e:
        return "", str(e), 1


def notify_lead(orch_id: str, lead: str, message: str) -> None:
    """Send result notification to the requesting lead's pane."""
    surfaces_path = Path(f"/tmp/caf_orch/{orch_id}/surfaces.json")
    try:
        surfaces = json.loads(surfaces_path.read_text())
    except Exception:
        return
    if lead not in surfaces:
        return
    cmux_bin = CAF_DIR / "bin" / "cmux-sprint"
    try:
        subprocess.run(
            [sys.executable, str(cmux_bin), "send-agent", orch_id, lead, message],
            check=False, timeout=10,
        )
    except Exception:
        pass


def process_queue(orch_id: str, cwd: str) -> None:
    """Process all queued (unprocessed) test requests."""
    queue_path = Path(f"/tmp/caf_orch/{orch_id}/shared/test_queue.jsonl")
    results_path = Path(f"/tmp/caf_orch/{orch_id}/shared/test_results.jsonl")

    if not queue_path.exists():
        return

    lines = queue_path.read_text().splitlines()
    if not lines:
        return

    # Find already-processed request timestamps
    processed: set[str] = set()
    if results_path.exists():
        for line in results_path.read_text().splitlines():
            try:
                e = json.loads(line)
                if "request_ts" in e:
                    processed.add(e["request_ts"])
            except Exception:
                pass

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        if req.get("status") != "queued":
            continue
        if req.get("ts") in processed:
            continue

        lead    = req.get("lead", "unknown")
        command = req.get("command", "")
        req_ts  = req.get("ts", "")

        if not command:
            continue

        print(f"[validator] running for {lead}: {command[:60]}", flush=True)
        stdout, stderr, rc = run_test(command, cwd)

        status  = "passed" if rc == 0 else "failed"
        passed  = f"exit {rc}"
        output  = (stdout + stderr)[:2000]

        result_entry = {
            "ts":         ts(),
            "request_ts": req_ts,
            "lead":       lead,
            "command":    command,
            "status":     status,
            "passed":     passed,
            "output":     output,
        }

        with results_path.open("a") as f:
            f.write(json.dumps(result_entry) + "\n")

        # Notify the requesting lead
        icon = "✓" if status == "passed" else "✗"
        notify_msg = (
            f"[VALIDATOR RESULT {icon}] {status.upper()}\n"
            f"Command: {command}\n"
            f"Exit: {rc}\n"
        )
        if output.strip():
            notify_msg += f"Output (first 500 chars):\n{output[:500]}"

        notify_lead(orch_id, lead, notify_msg)
        print(f"[validator] {icon} {status} — notified {lead}", flush=True)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: shared_validator.py <orch_id>", file=sys.stderr)
        sys.exit(1)

    orch_id = sys.argv[1]
    cwd = os.environ.get("PWD", str(Path.cwd()))

    print(f"[validator] started for job {orch_id!r} — polling every {POLL_INTERVAL}s")
    print(f"[validator] test queue: /tmp/caf_orch/{orch_id}/shared/test_queue.jsonl")
    print(f"[validator] results:    /tmp/caf_orch/{orch_id}/shared/test_results.jsonl")
    print()

    while True:
        try:
            process_queue(orch_id, cwd)
        except Exception as e:
            print(f"[validator] error: {e}", flush=True)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[validator] stopped")
