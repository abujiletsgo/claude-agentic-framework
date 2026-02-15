"""
State schema for hook failure tracking.

This module defines the data structures used for tracking hook execution state,
including circuit breaker states, failure counts, and timing information.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Disabled due to failures
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class HookState:
    """
    State tracking for a single hook command.

    Attributes:
        state: Current circuit breaker state
        failure_count: Total failures since last reset
        consecutive_failures: Current consecutive failure streak
        consecutive_successes: Current consecutive success streak
        first_failure: Timestamp of first failure in current failure period
        last_failure: Timestamp of most recent failure
        last_success: Timestamp of most recent success
        last_error: Error message from most recent failure
        disabled_at: Timestamp when circuit was opened (disabled)
        retry_after: Timestamp when circuit can transition to half-open
    """
    state: str = CircuitState.CLOSED.value
    failure_count: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    first_failure: Optional[str] = None
    last_failure: Optional[str] = None
    last_success: Optional[str] = None
    last_error: Optional[str] = None
    disabled_at: Optional[str] = None
    retry_after: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HookState":
        """Create HookState from dictionary."""
        # Filter out any extra keys not in dataclass
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


@dataclass
class GlobalStats:
    """
    Global statistics across all hooks.

    Attributes:
        total_executions: Total number of hook executions
        total_failures: Total number of failures across all hooks
        hooks_disabled: Number of hooks currently in OPEN state
        last_updated: Timestamp of last state update
    """
    total_executions: int = 0
    total_failures: int = 0
    hooks_disabled: int = 0
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GlobalStats":
        """Create GlobalStats from dictionary."""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


@dataclass
class HookStateData:
    """
    Complete state data structure.

    This represents the entire state file contents, including per-hook
    states and global statistics.

    Attributes:
        hooks: Dictionary mapping hook commands to their state
        global_stats: Global statistics across all hooks
    """
    hooks: Dict[str, HookState] = field(default_factory=dict)
    global_stats: GlobalStats = field(default_factory=GlobalStats)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "hooks": {cmd: state.to_dict() for cmd, state in self.hooks.items()},
            "global_stats": self.global_stats.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HookStateData":
        """Create HookStateData from dictionary."""
        hooks = {
            cmd: HookState.from_dict(state_dict)
            for cmd, state_dict in data.get("hooks", {}).items()
        }
        global_stats = GlobalStats.from_dict(data.get("global_stats", {}))
        return cls(hooks=hooks, global_stats=global_stats)


def get_current_timestamp() -> str:
    """Get current timestamp in ISO 8601 format with UTC timezone."""
    return datetime.now(timezone.utc).isoformat()
