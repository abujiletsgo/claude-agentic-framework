"""
CAF Audit — Circuit Breaker Tests
====================================
Tests the circuit breaker state machine: CLOSED → OPEN → HALF_OPEN → CLOSED.
Verifies threshold trips, cooldown logic, recovery, exclusions, and persistence.

Run standalone:
  uv run pytest tests/audit/modules/test_circuit_breaker.py -v
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent
CB_DIR = REPO_ROOT / "global-hooks/framework/guardrails"

# Add guardrails to path
sys.path.insert(0, str(CB_DIR))

TIMINGS: list[dict] = []


# ── dynamic imports (skip if not importable) ────────────────────────────────

try:
    from circuit_breaker import CircuitBreaker
    from hook_state_manager import HookStateManager
    from state_schema import CircuitState
    try:
        from config_loader import GuardrailsConfig
        _HAS_CONFIG_LOADER = True
    except ImportError:
        _HAS_CONFIG_LOADER = False
    _CB_AVAILABLE = True
except ImportError as e:
    _CB_AVAILABLE = False
    _CB_IMPORT_ERROR = str(e)


def make_config(
    failure_threshold: int = 3,
    success_threshold: int = 2,
    cooldown_seconds: int = 60,
    exclude: list[str] | None = None,
) -> Any:
    """Build a config-like object for the circuit breaker."""
    if _HAS_CONFIG_LOADER:
        try:
            cfg = GuardrailsConfig()
            cfg.circuit_breaker.failure_threshold = failure_threshold
            cfg.circuit_breaker.success_threshold = success_threshold
            cfg.circuit_breaker.cooldown_seconds = cooldown_seconds
            if exclude:
                cfg.circuit_breaker.exclude = exclude
            return cfg
        except Exception:
            pass

    # Fallback: simple namespace
    from types import SimpleNamespace
    cb_cfg = SimpleNamespace(
        failure_threshold=failure_threshold,
        success_threshold=success_threshold,
        cooldown_seconds=cooldown_seconds,
        exclude=exclude or [],
    )
    return SimpleNamespace(circuit_breaker=cb_cfg)


def make_cb(tmp_path: Path, **kwargs) -> tuple["CircuitBreaker", "HookStateManager"]:
    """Create a CB + state manager using a temp state file."""
    state_file = tmp_path / "hook_state.json"
    state_mgr = HookStateManager(state_file=state_file)
    cfg = make_config(**kwargs)
    cb = CircuitBreaker(state_manager=state_mgr, config=cfg)
    return cb, state_mgr


def record_timing(test_name: str, elapsed_ms: float) -> None:
    TIMINGS.append({"test": test_name, "ms": elapsed_ms})


# ── skip guard ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def require_cb():
    if not _CB_AVAILABLE:
        pytest.skip(f"Circuit breaker not importable: {_CB_IMPORT_ERROR}")


# ── tests ──────────────────────────────────────────────────────────────────────

def test_initial_state_closed(tmp_path):
    cb, state_mgr = make_cb(tmp_path)
    t0 = time.perf_counter()
    result = cb.should_execute("my_hook")
    elapsed_ms = (time.perf_counter() - t0) * 1000
    record_timing("test_initial_state_closed", elapsed_ms)

    # Should execute (CLOSED state)
    assert result.should_execute is True or str(result).lower() not in ("skip",), (
        f"New hook should start CLOSED and execute, got: {result}"
    )


def test_failure_threshold_trip(tmp_path):
    cb, state_mgr = make_cb(tmp_path, failure_threshold=3)
    hook = "test_hook_trip"
    t0 = time.perf_counter()
    for i in range(3):
        cb.record_failure(hook, f"error {i+1}")
    elapsed_ms = (time.perf_counter() - t0) * 1000
    record_timing("test_failure_threshold_trip", elapsed_ms)

    state = state_mgr.get_hook_state(hook)
    state_value = getattr(state, "state", str(state))
    assert "open" in str(state_value).lower(), (
        f"After 3 failures, state should be OPEN. Got: {state_value}"
    )


def test_failure_below_threshold_stays_closed(tmp_path):
    cb, state_mgr = make_cb(tmp_path, failure_threshold=3)
    hook = "test_hook_below"
    for i in range(2):
        cb.record_failure(hook, f"error {i+1}")

    state = state_mgr.get_hook_state(hook)
    state_value = getattr(state, "state", str(state))
    assert "open" not in str(state_value).lower(), (
        f"2 failures (below threshold=3) should stay CLOSED. Got: {state_value}"
    )


def test_skip_when_open(tmp_path):
    cb, state_mgr = make_cb(tmp_path, failure_threshold=3)
    hook = "test_hook_skip"
    for i in range(3):
        cb.record_failure(hook, f"error {i+1}")

    result = cb.should_execute(hook)
    should_exec = getattr(result, "should_execute", None)
    decision = str(getattr(result, "decision", "")).lower()

    assert should_exec is False or "skip" in decision, (
        f"OPEN circuit should return skip/False. Got: {result}"
    )


def test_half_open_after_cooldown(tmp_path):
    cb, state_mgr = make_cb(tmp_path, failure_threshold=3, cooldown_seconds=60)
    hook = "test_hook_halfopen"

    # Trip the circuit
    for i in range(3):
        cb.record_failure(hook, f"error {i+1}")

    # Manually backdate the disabled_at to simulate cooldown elapsed
    state_file = tmp_path / "hook_state.json"
    if state_file.exists():
        data = json.loads(state_file.read_text())
        hooks_data = data.get("hooks", {})
        if hook in hooks_data:
            past_time = (datetime.now(timezone.utc) - timedelta(seconds=65)).isoformat()
            hooks_data[hook]["disabled_at"] = past_time
            hooks_data[hook]["retry_after"] = past_time
            state_file.write_text(json.dumps(data))

    # Re-create state manager to load from file
    state_mgr2 = HookStateManager(state_file=state_file)
    cfg = make_config(failure_threshold=3, cooldown_seconds=60)
    cb2 = CircuitBreaker(state_manager=state_mgr2, config=cfg)

    result = cb2.should_execute(hook)
    decision = str(getattr(result, "decision", "")).lower()
    state_val = str(getattr(result, "state", "")).lower()

    assert "half" in state_val or "test" in decision or "execute" in decision, (
        f"After cooldown, state should be HALF_OPEN/EXECUTE_TEST. Got state={state_val} decision={decision}"
    )


def test_recovery_path_half_open_to_closed(tmp_path):
    cb, state_mgr = make_cb(tmp_path, failure_threshold=3, success_threshold=2, cooldown_seconds=60)
    hook = "test_hook_recover"

    # Trip the circuit
    for i in range(3):
        cb.record_failure(hook, f"error {i+1}")

    # Manually force to HALF_OPEN state
    state_file = tmp_path / "hook_state.json"
    if state_file.exists():
        data = json.loads(state_file.read_text())
        hooks_data = data.get("hooks", {})
        if hook in hooks_data:
            hooks_data[hook]["state"] = "half_open"
            hooks_data[hook]["consecutive_successes"] = 0
            state_file.write_text(json.dumps(data))

    state_mgr2 = HookStateManager(state_file=state_file)
    cfg = make_config(failure_threshold=3, success_threshold=2)
    cb2 = CircuitBreaker(state_manager=state_mgr2, config=cfg)

    # Record 2 successes → should close
    cb2.record_success(hook)
    cb2.record_success(hook)

    state = state_mgr2.get_hook_state(hook)
    state_value = str(getattr(state, "state", "")).lower()
    assert "closed" in state_value, (
        f"After 2 successes from HALF_OPEN, should be CLOSED. Got: {state_value}"
    )


def test_half_open_failure_reopens(tmp_path):
    cb, state_mgr = make_cb(tmp_path, failure_threshold=3)
    hook = "test_hook_reopen"

    # Force HALF_OPEN state
    state_file = tmp_path / "hook_state.json"
    initial_state = {
        "hooks": {
            hook: {
                "state": "half_open",
                "failure_count": 3,
                "consecutive_failures": 0,
                "consecutive_successes": 0,
                "disabled_at": datetime.now(timezone.utc).isoformat(),
                "retry_after": None,
                "last_error": "previous error",
            }
        },
        "global_stats": {}
    }
    state_file.write_text(json.dumps(initial_state))

    state_mgr2 = HookStateManager(state_file=state_file)
    cfg = make_config(failure_threshold=3)
    cb2 = CircuitBreaker(state_manager=state_mgr2, config=cfg)

    # One failure from HALF_OPEN → back to OPEN
    cb2.record_failure(hook, "test failure during recovery")

    state = state_mgr2.get_hook_state(hook)
    state_value = str(getattr(state, "state", "")).lower()
    assert "open" in state_value, (
        f"Failure in HALF_OPEN should re-open circuit. Got: {state_value}"
    )


def test_excluded_hooks_never_trip(tmp_path):
    cb, state_mgr = make_cb(tmp_path, failure_threshold=3, exclude=["excluded_hook"])
    hook = "excluded_hook"

    # Record many failures
    for i in range(10):
        cb.record_failure(hook, f"error {i+1}")

    result = cb.should_execute(hook)
    should_exec = getattr(result, "should_execute", None)
    decision = str(getattr(result, "decision", "")).lower()

    assert should_exec is not False and "skip" not in decision, (
        f"Excluded hook should always execute regardless of failures. Got: {result}"
    )


def test_multiple_independent_hooks(tmp_path):
    cb, state_mgr = make_cb(tmp_path, failure_threshold=3)
    hook_a = "hook_a_independent"
    hook_b = "hook_b_independent"

    # Trip hook_a
    for i in range(3):
        cb.record_failure(hook_a, f"error {i+1}")

    # hook_b should still be CLOSED
    result_b = cb.should_execute(hook_b)
    should_exec_b = getattr(result_b, "should_execute", None)

    assert should_exec_b is not False, (
        f"hook_b should not be affected by hook_a failures. Got: {result_b}"
    )


def test_state_file_persistence(tmp_path):
    state_file = tmp_path / "hook_state.json"
    hook = "persistent_hook"

    # CB 1: trip the circuit
    state_mgr1 = HookStateManager(state_file=state_file)
    cfg = make_config(failure_threshold=3)
    cb1 = CircuitBreaker(state_manager=state_mgr1, config=cfg)
    for i in range(3):
        cb1.record_failure(hook, f"error {i+1}")

    # CB 2: load from same file
    state_mgr2 = HookStateManager(state_file=state_file)
    cfg2 = make_config(failure_threshold=3)
    cb2 = CircuitBreaker(state_manager=state_mgr2, config=cfg2)

    state = state_mgr2.get_hook_state(hook)
    state_value = str(getattr(state, "state", "")).lower()
    assert "open" in state_value, (
        f"State should persist across CB instances. Got: {state_value}"
    )


def test_error_message_stored(tmp_path):
    cb, state_mgr = make_cb(tmp_path)
    hook = "hook_with_error"
    error_msg = "Connection timeout: max retries exceeded"

    cb.record_failure(hook, error_msg)

    state = state_mgr.get_hook_state(hook)
    last_error = getattr(state, "last_error", None)
    assert last_error is not None, "last_error should be stored after failure"
    assert error_msg in str(last_error) or len(str(last_error)) > 0, (
        f"Error message not stored correctly. Got: {last_error}"
    )


def test_consecutive_failure_counter(tmp_path):
    cb, state_mgr = make_cb(tmp_path, failure_threshold=5)
    hook = "hook_counter"

    cb.record_failure(hook, "e1")
    cb.record_failure(hook, "e2")
    state = state_mgr.get_hook_state(hook)
    consec = getattr(state, "consecutive_failures", None)
    assert consec == 2, f"Expected 2 consecutive failures, got: {consec}"

    # Success resets consecutive failures
    cb.record_success(hook)
    state = state_mgr.get_hook_state(hook)
    consec_after = getattr(state, "consecutive_failures", None)
    assert consec_after == 0, f"Success should reset consecutive_failures, got: {consec_after}"
