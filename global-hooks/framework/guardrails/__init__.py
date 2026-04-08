"""
Guardrails package for hook failure tracking and circuit breaker functionality.

This package provides thread-safe state management for tracking hook failures
and implementing circuit breaker patterns to prevent infinite loops.
"""

# Try relative imports first (when used as package), fall back to absolute (when used as module)
try:
    from .state_schema import (
        CircuitState,
        HookState,
        GlobalStats,
        HookStateData,
        get_current_timestamp,
    )
    from .hook_state_manager import HookStateManager
    from .config_loader import (
        CircuitBreakerConfig,
        ConfigLoader,
        GuardrailsConfig,
        LoggingConfig,
        create_default_config_file,
        load_config,
    )
    from .circuit_breaker import (
        CircuitBreaker,
        CircuitBreakerDecision,
        CircuitBreakerResult,
    )
except ImportError:
    from state_schema import (
        CircuitState,
        HookState,
        GlobalStats,
        HookStateData,
        get_current_timestamp,
    )
    from hook_state_manager import HookStateManager
    from config_loader import (
        CircuitBreakerConfig,
        ConfigLoader,
        GuardrailsConfig,
        LoggingConfig,
        create_default_config_file,
        load_config,
    )
    from circuit_breaker import (
        CircuitBreaker,
        CircuitBreakerDecision,
        CircuitBreakerResult,
    )

__version__ = "0.1.0"

__all__ = [
    "CircuitState",
    "HookState",
    "GlobalStats",
    "HookStateData",
    "HookStateManager",
    "get_current_timestamp",
    "CircuitBreakerConfig",
    "ConfigLoader",
    "GuardrailsConfig",
    "LoggingConfig",
    "create_default_config_file",
    "load_config",
    "CircuitBreaker",
    "CircuitBreakerDecision",
    "CircuitBreakerResult",
]
