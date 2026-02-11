#!/usr/bin/env python3
"""
Configuration loader for the guardrails system.

Handles loading, validation, and merging of configuration from:
1. Default configuration (safe defaults)
2. YAML configuration file (~/.claude/guardrails.yaml)
3. Environment variable overrides

Configuration priority (highest to lowest):
1. Environment variables (GUARDRAILS_*)
2. Configuration file (~/.claude/guardrails.yaml)
3. Default configuration
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    from pydantic import BaseModel, Field, field_validator, ValidationError
except ImportError:
    print("Error: Pydantic is required. Install with: pip install pydantic", file=sys.stderr)
    sys.exit(1)


# Configuration Models (Pydantic for validation)


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable circuit breaker globally"
    )
    failure_threshold: int = Field(
        default=3,
        ge=1,
        le=100,
        description="Number of consecutive failures before opening circuit"
    )
    cooldown_seconds: int = Field(
        default=300,
        ge=0,
        le=86400,
        description="Cooldown period (seconds) before testing recovery"
    )
    success_threshold: int = Field(
        default=2,
        ge=1,
        le=100,
        description="Consecutive successes needed to close circuit from half-open"
    )
    exclude: list[str] = Field(
        default_factory=list,
        description="Hooks to exclude from circuit breaker (always execute)"
    )

    @field_validator("exclude")
    @classmethod
    def validate_exclude(cls, v):
        """Validate exclude list contains strings."""
        if not isinstance(v, list):
            raise ValueError("exclude must be a list")
        for item in v:
            if not isinstance(item, str):
                raise ValueError(f"exclude items must be strings, got {type(item)}")
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""

    file: str = Field(
        default="~/.claude/logs/circuit_breaker.log",
        description="Log file for circuit breaker activity"
    )
    level: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    format: str = Field(
        default="%(asctime)s | %(levelname)s | %(hook_cmd)s | %(message)s",
        description="Log format string"
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v):
        """Validate log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper


class GuardrailsConfig(BaseModel):
    """Root configuration for guardrails system."""

    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=CircuitBreakerConfig,
        description="Circuit breaker configuration"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration"
    )
    state_file: str = Field(
        default="~/.claude/hook_state.json",
        description="State file location"
    )

    def expand_paths(self) -> None:
        """Expand ~ and environment variables in path fields."""
        self.state_file = os.path.expanduser(os.path.expandvars(self.state_file))
        self.logging.file = os.path.expanduser(os.path.expandvars(self.logging.file))

    def get_state_file_path(self) -> Path:
        """Get state file path as Path object."""
        return Path(self.state_file)

    def get_log_file_path(self) -> Path:
        """Get log file path as Path object."""
        return Path(self.logging.file)


# Configuration Loader


class ConfigLoader:
    """Loads and merges configuration from multiple sources."""

    DEFAULT_CONFIG_PATH = Path.home() / ".claude" / "guardrails.yaml"
    ENV_PREFIX = "GUARDRAILS_"

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration loader.

        Args:
            config_path: Path to configuration file. If None, uses default path.
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH

    def load(self) -> GuardrailsConfig:
        """
        Load and validate configuration.

        Returns:
            Validated configuration object.

        Raises:
            ValidationError: If configuration is invalid.
        """
        # Start with default configuration
        config_dict = self._get_default_config()

        # Merge with file configuration if exists
        if self.config_path.exists():
            try:
                file_config = self._load_yaml_file(self.config_path)
                config_dict = self._deep_merge(config_dict, file_config)
            except Exception as e:
                print(f"Warning: Failed to load config file {self.config_path}: {e}", file=sys.stderr)
                print("Continuing with default configuration...", file=sys.stderr)

        # Merge with environment variables
        env_config = self._load_from_env()
        config_dict = self._deep_merge(config_dict, env_config)

        # Validate and create config object
        try:
            config = GuardrailsConfig(**config_dict)
            config.expand_paths()
            return config
        except ValidationError as e:
            print(f"Configuration validation error:", file=sys.stderr)
            for error in e.errors():
                loc = ".".join(str(x) for x in error["loc"])
                msg = error["msg"]
                print(f"  {loc}: {msg}", file=sys.stderr)
            raise

    @staticmethod
    def _get_default_config() -> dict[str, Any]:
        """Get default configuration as dictionary."""
        return {
            "circuit_breaker": {
                "enabled": True,
                "failure_threshold": 3,
                "cooldown_seconds": 300,
                "success_threshold": 2,
                "exclude": [],
            },
            "logging": {
                "file": "~/.claude/logs/circuit_breaker.log",
                "level": "INFO",
                "format": "%(asctime)s | %(levelname)s | %(hook_cmd)s | %(message)s",
            },
            "state_file": "~/.claude/hook_state.json",
        }

    @staticmethod
    def _load_yaml_file(path: Path) -> dict[str, Any]:
        """Load YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
            return data if data is not None else {}

    def _load_from_env(self) -> dict[str, Any]:
        """
        Load configuration from environment variables.

        Environment variable format:
            GUARDRAILS_CIRCUIT_BREAKER_ENABLED=true
            GUARDRAILS_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
            GUARDRAILS_LOGGING_LEVEL=DEBUG
            GUARDRAILS_STATE_FILE=/custom/path/state.json
        """
        config = {}

        for key, value in os.environ.items():
            if not key.startswith(self.ENV_PREFIX):
                continue

            # Remove prefix and convert to lowercase
            config_key = key[len(self.ENV_PREFIX):].lower()

            # Split into parts
            parts = config_key.split("_")

            # Handle compound names (e.g., "circuit_breaker", "failure_threshold")
            # Join consecutive parts if they form known config keys
            normalized_parts = []
            i = 0
            while i < len(parts):
                # Try two-part compound first
                if i + 1 < len(parts):
                    two_part = f"{parts[i]}_{parts[i+1]}"
                    if two_part in ["circuit_breaker", "failure_threshold", "cooldown_seconds",
                                     "success_threshold", "state_file", "log_file"]:
                        normalized_parts.append(two_part)
                        i += 2
                        continue
                # Single part
                normalized_parts.append(parts[i])
                i += 1

            parts = normalized_parts

            # Build nested dictionary
            current = config
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Set the value with type conversion
            final_key = parts[-1]
            current[final_key] = self._parse_env_value(value)

        return config

    @staticmethod
    def _parse_env_value(value: str) -> Any:
        """
        Parse environment variable value with type inference.

        Supports:
        - Boolean: true/false (case-insensitive)
        - Integer: numeric strings without decimal
        - String: everything else
        """
        # Boolean
        if value.lower() in ("true", "yes", "1", "on"):
            return True
        if value.lower() in ("false", "no", "0", "off"):
            return False

        # Integer
        if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
            return int(value)

        # String (default)
        return value

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """
        Deep merge two dictionaries.

        Args:
            base: Base dictionary
            override: Override dictionary (takes precedence)

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = ConfigLoader._deep_merge(result[key], value)
            else:
                # Override value
                result[key] = value

        return result


# Convenience functions


def load_config(config_path: Optional[Path] = None) -> GuardrailsConfig:
    """
    Load configuration from default or specified path.

    Args:
        config_path: Optional path to configuration file

    Returns:
        Validated configuration object
    """
    loader = ConfigLoader(config_path)
    return loader.load()


def create_default_config_file(output_path: Optional[Path] = None) -> None:
    """
    Create a default configuration file.

    Args:
        output_path: Path to write configuration file. If None, uses default path.
    """
    output_path = output_path or ConfigLoader.DEFAULT_CONFIG_PATH

    # Create parent directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load default config from file in same directory
    default_yaml_path = Path(__file__).parent / "default_config.yaml"
    if default_yaml_path.exists():
        # Copy existing default config
        import shutil
        shutil.copy(default_yaml_path, output_path)
    else:
        # Generate from defaults
        config = GuardrailsConfig()
        config_dict = config.model_dump()

        with open(output_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

    print(f"Created default configuration file: {output_path}")


# CLI for testing/debugging


def main():
    """CLI for testing configuration loading."""
    import argparse

    parser = argparse.ArgumentParser(description="Guardrails configuration loader")
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file (default: ~/.claude/guardrails.yaml)"
    )
    parser.add_argument(
        "--create-default",
        action="store_true",
        help="Create default configuration file"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate configuration and exit"
    )
    parser.add_argument(
        "--dump",
        action="store_true",
        help="Dump loaded configuration as YAML"
    )

    args = parser.parse_args()

    if args.create_default:
        create_default_config_file(args.config)
        return

    try:
        config = load_config(args.config)

        if args.validate:
            print("Configuration is valid!")
            return

        if args.dump:
            print(yaml.dump(config.model_dump(), default_flow_style=False, sort_keys=False))
        else:
            print("Configuration loaded successfully!")
            print(f"  State file: {config.state_file}")
            print(f"  Log file: {config.logging.file}")
            print(f"  Log level: {config.logging.level}")
            print(f"  Circuit breaker enabled: {config.circuit_breaker.enabled}")
            print(f"  Failure threshold: {config.circuit_breaker.failure_threshold}")
            print(f"  Cooldown: {config.circuit_breaker.cooldown_seconds}s")
            print(f"  Success threshold: {config.circuit_breaker.success_threshold}")
            if config.circuit_breaker.exclude:
                print(f"  Excluded hooks: {', '.join(config.circuit_breaker.exclude)}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
