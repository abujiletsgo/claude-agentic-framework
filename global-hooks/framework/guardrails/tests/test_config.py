#!/usr/bin/env python3
"""
Unit tests for configuration loader.

Tests configuration loading, validation, merging, and environment variable overrides.
"""

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import yaml
from pydantic import ValidationError

from guardrails.config_loader import (
    CircuitBreakerConfig,
    ConfigLoader,
    GuardrailsConfig,
    LoggingConfig,
    create_default_config_file,
    load_config,
)


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        assert config.enabled is True
        assert config.failure_threshold == 3
        assert config.cooldown_seconds == 300
        assert config.success_threshold == 2
        assert config.exclude == []

    def test_valid_configuration(self):
        """Test valid configuration values."""
        config = CircuitBreakerConfig(
            enabled=False,
            failure_threshold=5,
            cooldown_seconds=600,
            success_threshold=3,
            exclude=["hook1.py", "hook2.py"]
        )
        assert config.enabled is False
        assert config.failure_threshold == 5
        assert config.cooldown_seconds == 600
        assert config.success_threshold == 3
        assert config.exclude == ["hook1.py", "hook2.py"]

    def test_failure_threshold_validation(self):
        """Test failure_threshold range validation."""
        # Valid values
        CircuitBreakerConfig(failure_threshold=1)
        CircuitBreakerConfig(failure_threshold=50)
        CircuitBreakerConfig(failure_threshold=100)

        # Invalid: too low
        with pytest.raises(ValidationError):
            CircuitBreakerConfig(failure_threshold=0)

        # Invalid: too high
        with pytest.raises(ValidationError):
            CircuitBreakerConfig(failure_threshold=101)

    def test_cooldown_seconds_validation(self):
        """Test cooldown_seconds range validation."""
        # Valid values
        CircuitBreakerConfig(cooldown_seconds=0)
        CircuitBreakerConfig(cooldown_seconds=300)
        CircuitBreakerConfig(cooldown_seconds=86400)

        # Invalid: negative
        with pytest.raises(ValidationError):
            CircuitBreakerConfig(cooldown_seconds=-1)

        # Invalid: too high
        with pytest.raises(ValidationError):
            CircuitBreakerConfig(cooldown_seconds=86401)

    def test_success_threshold_validation(self):
        """Test success_threshold range validation."""
        # Valid values
        CircuitBreakerConfig(success_threshold=1)
        CircuitBreakerConfig(success_threshold=50)
        CircuitBreakerConfig(success_threshold=100)

        # Invalid: too low
        with pytest.raises(ValidationError):
            CircuitBreakerConfig(success_threshold=0)

        # Invalid: too high
        with pytest.raises(ValidationError):
            CircuitBreakerConfig(success_threshold=101)

    def test_exclude_validation(self):
        """Test exclude list validation."""
        # Valid: empty list
        config = CircuitBreakerConfig(exclude=[])
        assert config.exclude == []

        # Valid: list of strings
        config = CircuitBreakerConfig(exclude=["hook1.py", "hook2.py"])
        assert config.exclude == ["hook1.py", "hook2.py"]

        # Invalid: not a list
        with pytest.raises(ValidationError):
            CircuitBreakerConfig(exclude="hook1.py")


class TestLoggingConfig:
    """Tests for LoggingConfig model."""

    def test_default_values(self):
        """Test default logging configuration values."""
        config = LoggingConfig()
        assert config.file == "~/.claude/logs/circuit_breaker.log"
        assert config.level == "INFO"
        assert "%(asctime)s" in config.format
        assert "%(levelname)s" in config.format

    def test_valid_configuration(self):
        """Test valid logging configuration."""
        config = LoggingConfig(
            file="/var/log/test.log",
            level="DEBUG",
            format="%(message)s"
        )
        assert config.file == "/var/log/test.log"
        assert config.level == "DEBUG"
        assert config.format == "%(message)s"

    def test_log_level_validation(self):
        """Test log level validation."""
        # Valid levels (case-insensitive)
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LoggingConfig(level=level)
            assert config.level == level.upper()

        for level in ["debug", "info", "warning", "error", "critical"]:
            config = LoggingConfig(level=level)
            assert config.level == level.upper()

        # Invalid level
        with pytest.raises(ValidationError) as exc_info:
            LoggingConfig(level="INVALID")
        assert "Invalid log level" in str(exc_info.value)


class TestGuardrailsConfig:
    """Tests for GuardrailsConfig model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = GuardrailsConfig()
        assert isinstance(config.circuit_breaker, CircuitBreakerConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert config.state_file == "~/.claude/hook_state.json"

    def test_nested_configuration(self):
        """Test nested configuration objects."""
        config = GuardrailsConfig(
            circuit_breaker=CircuitBreakerConfig(failure_threshold=5),
            logging=LoggingConfig(level="DEBUG"),
            state_file="/tmp/state.json"
        )
        assert config.circuit_breaker.failure_threshold == 5
        assert config.logging.level == "DEBUG"
        assert config.state_file == "/tmp/state.json"

    def test_expand_paths(self):
        """Test path expansion."""
        config = GuardrailsConfig(
            state_file="~/test_state.json",
            logging=LoggingConfig(file="~/test_log.log")
        )
        config.expand_paths()

        # Paths should be expanded
        assert "~" not in config.state_file
        assert "~" not in config.logging.file
        assert config.state_file.startswith(str(Path.home()))
        assert config.logging.file.startswith(str(Path.home()))

    def test_get_path_methods(self):
        """Test path getter methods."""
        config = GuardrailsConfig(
            state_file="/tmp/state.json",
            logging=LoggingConfig(file="/tmp/log.log")
        )

        state_path = config.get_state_file_path()
        log_path = config.get_log_file_path()

        assert isinstance(state_path, Path)
        assert isinstance(log_path, Path)
        assert str(state_path) == "/tmp/state.json"
        assert str(log_path) == "/tmp/log.log"


class TestConfigLoader:
    """Tests for ConfigLoader."""

    def test_default_config(self):
        """Test loading default configuration."""
        loader = ConfigLoader()
        default_config = loader._get_default_config()

        assert "circuit_breaker" in default_config
        assert "logging" in default_config
        assert "state_file" in default_config
        assert default_config["circuit_breaker"]["enabled"] is True
        assert default_config["circuit_breaker"]["failure_threshold"] == 3

    def test_load_yaml_file(self):
        """Test loading YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({
                "circuit_breaker": {
                    "failure_threshold": 5
                }
            }, f)
            temp_path = Path(f.name)

        try:
            config_dict = ConfigLoader._load_yaml_file(temp_path)
            assert config_dict["circuit_breaker"]["failure_threshold"] == 5
        finally:
            temp_path.unlink()

    def test_load_empty_yaml_file(self):
        """Test loading empty YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")  # Empty file
            temp_path = Path(f.name)

        try:
            config_dict = ConfigLoader._load_yaml_file(temp_path)
            assert config_dict == {}
        finally:
            temp_path.unlink()

    def test_parse_env_value_boolean(self):
        """Test environment value parsing for booleans."""
        # True values
        for value in ["true", "TRUE", "True", "yes", "YES", "1", "on", "ON"]:
            assert ConfigLoader._parse_env_value(value) is True

        # False values
        for value in ["false", "FALSE", "False", "no", "NO", "0", "off", "OFF"]:
            assert ConfigLoader._parse_env_value(value) is False

    def test_parse_env_value_integer(self):
        """Test environment value parsing for integers."""
        assert ConfigLoader._parse_env_value("0") == 0
        assert ConfigLoader._parse_env_value("42") == 42
        assert ConfigLoader._parse_env_value("300") == 300
        assert ConfigLoader._parse_env_value("-5") == -5

    def test_parse_env_value_string(self):
        """Test environment value parsing for strings."""
        assert ConfigLoader._parse_env_value("hello") == "hello"
        assert ConfigLoader._parse_env_value("DEBUG") == "DEBUG"
        assert ConfigLoader._parse_env_value("/path/to/file") == "/path/to/file"

    def test_load_from_env(self):
        """Test loading configuration from environment variables."""
        loader = ConfigLoader()

        with mock.patch.dict(os.environ, {
            "GUARDRAILS_CIRCUIT_BREAKER_ENABLED": "false",
            "GUARDRAILS_CIRCUIT_BREAKER_FAILURE_THRESHOLD": "5",
            "GUARDRAILS_LOGGING_LEVEL": "DEBUG",
            "GUARDRAILS_STATE_FILE": "/tmp/state.json",
            "OTHER_VAR": "ignored"  # Should be ignored
        }):
            env_config = loader._load_from_env()

            assert env_config["circuit_breaker"]["enabled"] is False
            assert env_config["circuit_breaker"]["failure_threshold"] == 5
            assert env_config["logging"]["level"] == "DEBUG"
            assert env_config["state_file"] == "/tmp/state.json"
            assert "OTHER_VAR" not in env_config

    def test_deep_merge(self):
        """Test deep merging of configuration dictionaries."""
        base = {
            "circuit_breaker": {
                "enabled": True,
                "failure_threshold": 3,
                "cooldown_seconds": 300
            },
            "logging": {
                "level": "INFO"
            }
        }

        override = {
            "circuit_breaker": {
                "failure_threshold": 5  # Override this
                # Keep enabled and cooldown_seconds from base
            },
            "logging": {
                "level": "DEBUG",  # Override this
                "file": "/tmp/log"  # Add new key
            }
        }

        result = ConfigLoader._deep_merge(base, override)

        assert result["circuit_breaker"]["enabled"] is True  # From base
        assert result["circuit_breaker"]["failure_threshold"] == 5  # From override
        assert result["circuit_breaker"]["cooldown_seconds"] == 300  # From base
        assert result["logging"]["level"] == "DEBUG"  # From override
        assert result["logging"]["file"] == "/tmp/log"  # From override

    def test_load_with_nonexistent_file(self):
        """Test loading when config file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent_path = Path(tmpdir) / "nonexistent.yaml"
            loader = ConfigLoader(nonexistent_path)

            # Should load defaults without error
            config = loader.load()
            assert config.circuit_breaker.failure_threshold == 3  # Default value

    def test_load_with_file_only(self):
        """Test loading configuration from file only."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({
                "circuit_breaker": {
                    "failure_threshold": 10,
                    "cooldown_seconds": 600
                }
            }, f)
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader(temp_path)
            config = loader.load()

            assert config.circuit_breaker.failure_threshold == 10  # From file
            assert config.circuit_breaker.cooldown_seconds == 600  # From file
            assert config.circuit_breaker.enabled is True  # From defaults
        finally:
            temp_path.unlink()

    def test_load_with_env_override(self):
        """Test loading configuration with environment variable override."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({
                "circuit_breaker": {
                    "failure_threshold": 5
                }
            }, f)
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader(temp_path)

            with mock.patch.dict(os.environ, {
                "GUARDRAILS_CIRCUIT_BREAKER_FAILURE_THRESHOLD": "10",
                "GUARDRAILS_CIRCUIT_BREAKER_COOLDOWN_SECONDS": "120"
            }):
                config = loader.load()

                assert config.circuit_breaker.failure_threshold == 10  # From env (highest priority)
                assert config.circuit_breaker.cooldown_seconds == 120  # From env
                assert config.circuit_breaker.enabled is True  # From defaults
        finally:
            temp_path.unlink()

    def test_load_with_invalid_yaml(self):
        """Test loading with invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: syntax:")
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader(temp_path)

            # Should fall back to defaults with warning
            config = loader.load()
            assert config.circuit_breaker.failure_threshold == 3  # Default value
        finally:
            temp_path.unlink()

    def test_load_with_invalid_values(self):
        """Test loading with invalid configuration values."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({
                "circuit_breaker": {
                    "failure_threshold": 999  # Invalid: > 100
                }
            }, f)
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader(temp_path)

            with pytest.raises(ValidationError):
                loader.load()
        finally:
            temp_path.unlink()


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_load_config_default(self):
        """Test load_config with default path."""
        # Should not raise even if file doesn't exist
        config = load_config()
        assert isinstance(config, GuardrailsConfig)

    def test_load_config_custom_path(self):
        """Test load_config with custom path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({
                "circuit_breaker": {
                    "failure_threshold": 7
                }
            }, f)
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config.circuit_breaker.failure_threshold == 7
        finally:
            temp_path.unlink()

    def test_create_default_config_file(self):
        """Test creating default configuration file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_config.yaml"

            create_default_config_file(output_path)

            assert output_path.exists()

            # Verify it's valid YAML
            with open(output_path) as f:
                config_dict = yaml.safe_load(f)

            assert "circuit_breaker" in config_dict
            assert "logging" in config_dict
            assert "state_file" in config_dict


class TestConfigurationMerging:
    """Integration tests for configuration merging."""

    def test_priority_order(self):
        """Test configuration priority: env > file > defaults."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({
                "circuit_breaker": {
                    "failure_threshold": 5,  # File sets to 5
                    "cooldown_seconds": 600  # File sets to 600
                }
            }, f)
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader(temp_path)

            with mock.patch.dict(os.environ, {
                "GUARDRAILS_CIRCUIT_BREAKER_FAILURE_THRESHOLD": "10"  # Env overrides to 10
            }):
                config = loader.load()

                # Priority verification
                assert config.circuit_breaker.failure_threshold == 10  # Env (highest)
                assert config.circuit_breaker.cooldown_seconds == 600  # File
                assert config.circuit_breaker.success_threshold == 2  # Default (lowest)
        finally:
            temp_path.unlink()

    def test_partial_override(self):
        """Test partial override of nested configuration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({
                "circuit_breaker": {
                    "failure_threshold": 5
                    # Other fields use defaults
                }
            }, f)
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader(temp_path)
            config = loader.load()

            # Overridden value
            assert config.circuit_breaker.failure_threshold == 5

            # Default values preserved
            assert config.circuit_breaker.enabled is True
            assert config.circuit_breaker.cooldown_seconds == 300
            assert config.circuit_breaker.success_threshold == 2
        finally:
            temp_path.unlink()


class TestPathExpansion:
    """Tests for path expansion."""

    def test_tilde_expansion(self):
        """Test tilde expansion in paths."""
        config = GuardrailsConfig(
            state_file="~/test/state.json",
            logging=LoggingConfig(file="~/test/log.log")
        )
        config.expand_paths()

        assert "~" not in config.state_file
        assert "~" not in config.logging.file
        assert config.state_file.startswith(str(Path.home()))

    def test_env_var_expansion(self):
        """Test environment variable expansion in paths."""
        with mock.patch.dict(os.environ, {"TEST_DIR": "/tmp/test"}):
            config = GuardrailsConfig(
                state_file="$TEST_DIR/state.json",
                logging=LoggingConfig(file="$TEST_DIR/log.log")
            )
            config.expand_paths()

            assert config.state_file == "/tmp/test/state.json"
            assert config.logging.file == "/tmp/test/log.log"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
