#!/usr/bin/env python3
"""Stop Failure Recovery - StopFailure Hook.

Fires on API error. Classifies error type, injects recovery advice, logs to
~/.claude/data/stop_failures.jsonl. Always exits 0.
"""
import json, sys
from datetime import datetime, timezone
from pathlib import Path

RECOVERY = {
    "rate_limit": (
        "[Rate Limit] API rate limit hit. Wait ~60s before retrying. "
        "Reduce request frequency or batch operations to avoid throttling."
    ),
    "authentication_failed": (
        "[Auth Failed] Authentication error. Re-authenticate: "
        "run `claude auth` or check your API key / session token."
    ),
    "billing_error": (
        "[Billing] Billing issue preventing API access. "
        "Check plan status and payment method at console.anthropic.com."
    ),
    "server_error": (
        "[Server Error] Anthropic API returned a server-side error. "
        "This is usually transient — retry in a few seconds."
    ),
    "max_output_tokens": (
        "[Max Output] Response hit the output token limit. "
        "Consider breaking the task into smaller pieces or using /rlm for iterative work."
    ),
}
LOG_PATH = Path.home() / ".claude" / "data" / "stop_failures.jsonl"


def classify(hook_input: dict) -> str:
    combined = f"{hook_input.get('hook_event_name', '')} {hook_input.get('error', '')}".lower()
    for key in RECOVERY:
        if key in combined:
            return key
    return "server_error"


def log_failure(error_type: str, session_id: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.now(timezone.utc).isoformat(),
             "error_type": error_type, "session_id": session_id}
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
        error_type = classify(hook_input)
        session_id = hook_input.get("session_id", "unknown")
        log_failure(error_type, session_id)
        print(json.dumps({"hookSpecificOutput": {
            "additionalContext": RECOVERY[error_type]}}))
    except Exception:
        print(json.dumps({}))
    sys.exit(0)


if __name__ == "__main__":
    main()
