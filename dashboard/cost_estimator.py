"""Cost estimator — pure utility module. No Textual, no UI.

Estimates API cost from model tier and agent duration.
Formula: output_tokens = duration_s * output_rate
         total_tokens  = output_tokens * 4  (3:1 input:output ratio + output)
         cost_usd      = total_tokens / 1_000_000 * avg_rate
"""
import json
import time
from pathlib import Path

LIVE_FILE = Path("/tmp/caf_live_agents.json")

MODEL_RATES = {
    "haiku":  {"avg_per_million": 0.40, "output_tokens_per_sec": 200},
    "sonnet": {"avg_per_million": 6.00, "output_tokens_per_sec": 100},
    "opus":   {"avg_per_million": 30.00, "output_tokens_per_sec": 60},
}

# Rough token-per-run estimates used by TopBar token counter
TOKENS_PER_RUN = {
    "haiku":  8_000,
    "sonnet": 25_000,
    "opus":   60_000,
}


def estimate_cost_for_agent(model: str, duration_s: float) -> float:
    """Estimate cost in USD for one agent run.

    Args:
        model: one of "haiku", "sonnet", "opus" (case-insensitive substring match)
        duration_s: wall-clock seconds the agent ran

    Returns:
        Estimated cost in USD as a float.
    """
    model_key = _resolve_model_key(model)
    if model_key is None:
        return 0.0

    rates = MODEL_RATES[model_key]
    output_tokens = duration_s * rates["output_tokens_per_sec"]
    total_tokens = output_tokens * 4  # 3:1 input:output ratio + the output itself
    cost = total_tokens / 1_000_000 * rates["avg_per_million"]
    return cost


def estimate_session_cost(agents: list[dict]) -> dict:
    """Estimate total session cost from a list of agent records.

    Args:
        agents: list from caf_live_agents.json  (each dict has keys: model,
                status, started, duration_s)

    Returns:
        {
            "total_usd": float,
            "by_model": {"haiku": float, "sonnet": float, "opus": float},
            "rate_per_min": float,   # rolling rate based on last 5 minutes
            "agent_count": int,
        }
    """
    by_model: dict[str, float] = {"haiku": 0.0, "sonnet": 0.0, "opus": 0.0}
    total_usd = 0.0

    now = time.time()
    five_min_ago = now - 300.0
    recent_cost = 0.0
    recent_duration_s = 0.0

    for agent in agents:
        model = agent.get("model", "")
        started = agent.get("started", 0.0)

        if agent.get("status") == "running":
            duration_s = now - started if started else 0.0
        else:
            duration_s = agent.get("duration_s", 0.0)

        cost = estimate_cost_for_agent(model, duration_s)
        total_usd += cost

        model_key = _resolve_model_key(model)
        if model_key:
            by_model[model_key] += cost

        # Accumulate recent activity for rate calculation
        if started and started >= five_min_ago:
            recent_cost += cost
            recent_duration_s += duration_s

    # rate_per_min: cost generated in last 5-min window, normalised to per-minute
    rate_per_min = (recent_cost / 5.0) if recent_duration_s > 0 else 0.0

    return {
        "total_usd": total_usd,
        "by_model": by_model,
        "rate_per_min": rate_per_min,
        "agent_count": len(agents),
    }


def format_cost(usd: float) -> str:
    """Format a USD cost for compact display, e.g. '~$1.24'."""
    return f"~${usd:.2f}"


def load_agents() -> list[dict]:
    """Load /tmp/caf_live_agents.json and return the agents list (or [])."""
    try:
        if LIVE_FILE.exists():
            data = json.loads(LIVE_FILE.read_text())
            return data.get("agents", [])
    except (json.JSONDecodeError, OSError):
        pass
    return []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_model_key(model: str) -> str | None:
    """Map a raw model string to one of the three rate-table keys."""
    model_lower = model.lower()
    for key in ("haiku", "sonnet", "opus"):
        if key in model_lower:
            return key
    return None
