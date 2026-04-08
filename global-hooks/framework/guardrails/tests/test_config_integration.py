#!/usr/bin/env python3
"""
Integration tests for configuration system with other guardrails components.

Tests that configuration can be loaded and used by:
- State manager
- Circuit breaker
- CLI tools
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from guardrails.config_loader import load_config, GuardrailsConfig


class TestConfigIntegration:
    """Integration tests for configuration system."""

    def test_config_with_state_manager(self):
        """Test configuration integration with state manager."""
        # Create temporary config with custom state file
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "custom_state.json"
            config_file = Path(tmpdir) / "config.yaml"

            # Write config
            with open(config_file, "w") as f:
                yaml.dump({
                    "state_file": str(state_file)
                }, f)

            # Load config
            config = load_config(config_file)

            # Verify state file path
            assert config.state_file == str(state_file)
            state_path = config.get_state_file_path()
            assert state_path == state_file

    def test_config_for_circuit_breaker(self):
        """Test configuration provides all required circuit breaker settings."""
        config = load_config()

        # Verify all required settings are present
        assert isinstance(config.circuit_breaker.enabled, bool)
        assert isinstance(config.circuit_breaker.failure_threshold, int)
        assert config.circuit_breaker.failure_threshold > 0
        assert isinstance(config.circuit_breaker.cooldown_seconds, int)
        assert config.circuit_breaker.cooldown_seconds >= 0
        assert isinstance(config.circuit_breaker.success_threshold, int)
        assert config.circuit_breaker.success_threshold > 0
        assert isinstance(config.circuit_breaker.exclude, list)

    def test_config_for_logging(self):
        """Test configuration provides all required logging settings."""
        config = load_config()

        # Verify all required settings are present
        assert isinstance(config.logging.file, str)
        assert len(config.logging.file) > 0
        assert isinstance(config.logging.level, str)
        assert config.logging.level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        assert isinstance(config.logging.format, str)
        assert len(config.logging.format) > 0

    def test_config_path_expansion_for_state_manager(self):
        """Test that paths are properly expanded for state manager use."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"

            # Write config with tilde
            with open(config_file, "w") as f:
                yaml.dump({
                    "state_file": "~/test_state.json",
                    "logging": {
                        "file": "~/test_log.log"
                    }
                }, f)

            # Load config
            config = load_config(config_file)

            # Verify expansion happened
            assert "~" not in config.state_file
            assert "~" not in config.logging.file

            # Verify paths are absolute
            state_path = config.get_state_file_path()
            log_path = config.get_log_file_path()
            assert state_path.is_absolute()
            assert log_path.is_absolute()

    def test_config_exclude_list_for_circuit_breaker(self):
        """Test exclude list configuration for circuit breaker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"

            # Write config with excluded hooks
            excluded_hooks = [
                "damage-control/bash-tool-damage-control.py",
                "damage-control/edit-tool-damage-control.py"
            ]

            with open(config_file, "w") as f:
                yaml.dump({
                    "circuit_breaker": {
                        "exclude": excluded_hooks
                    }
                }, f)

            # Load config
            config = load_config(config_file)

            # Verify exclude list
            assert config.circuit_breaker.exclude == excluded_hooks

            # Simulate circuit breaker check
            def should_apply_circuit_breaker(hook_cmd: str, config: GuardrailsConfig) -> bool:
                """Check if circuit breaker should apply to hook."""
                if not config.circuit_breaker.enabled:
                    return False

                # Check if hook is in exclude list
                for excluded in config.circuit_breaker.exclude:
                    if excluded in hook_cmd:
                        return False

                return True

            # Test excluded hooks
            assert not should_apply_circuit_breaker(
                "uv run damage-control/bash-tool-damage-control.py",
                config
            )
            assert not should_apply_circuit_breaker(
                "uv run damage-control/edit-tool-damage-control.py",
                config
            )

            # Test non-excluded hook
            assert should_apply_circuit_breaker(
                "uv run validators/validate_file_contains.py",
                config
            )

    def test_config_loading_robustness(self):
        """Test that config loading is robust to missing/invalid files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test 1: Nonexistent file (should use defaults)
            nonexistent = Path(tmpdir) / "nonexistent.yaml"
            config1 = load_config(nonexistent)
            assert config1.circuit_breaker.failure_threshold == 3  # Default

            # Test 2: Empty file (should use defaults)
            empty_file = Path(tmpdir) / "empty.yaml"
            empty_file.touch()
            config2 = load_config(empty_file)
            assert config2.circuit_breaker.failure_threshold == 3  # Default

            # Test 3: File with only partial config (should merge with defaults)
            partial_file = Path(tmpdir) / "partial.yaml"
            with open(partial_file, "w") as f:
                yaml.dump({
                    "circuit_breaker": {
                        "failure_threshold": 10
                    }
                }, f)
            config3 = load_config(partial_file)
            assert config3.circuit_breaker.failure_threshold == 10  # From file
            assert config3.circuit_breaker.enabled is True  # Default
            assert config3.circuit_breaker.cooldown_seconds == 300  # Default

    def test_config_for_cli_display(self):
        """Test that config can be easily displayed in CLI tools."""
        config = load_config()

        # Simulate CLI display
        display_data = {
            "Circuit Breaker": {
                "Enabled": config.circuit_breaker.enabled,
                "Failure Threshold": config.circuit_breaker.failure_threshold,
                "Cooldown (seconds)": config.circuit_breaker.cooldown_seconds,
                "Success Threshold": config.circuit_breaker.success_threshold,
                "Excluded Hooks": len(config.circuit_breaker.exclude),
            },
            "Logging": {
                "Level": config.logging.level,
                "File": config.logging.file,
            },
            "State File": config.state_file,
        }

        # Verify all fields are serializable for display
        assert all(isinstance(v, (str, int, bool)) for section in display_data.values()
                   for v in (section.values() if isinstance(section, dict) else [section]))

    def test_config_serialization_roundtrip(self):
        """Test that config can be serialized and loaded back."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"

            # Create config
            config1 = load_config()

            # Serialize to dict
            config_dict = config1.model_dump()

            # Write to file
            with open(config_file, "w") as f:
                yaml.dump(config_dict, f)

            # Load back
            config2 = load_config(config_file)

            # Compare
            assert config2.circuit_breaker.enabled == config1.circuit_breaker.enabled
            assert config2.circuit_breaker.failure_threshold == config1.circuit_breaker.failure_threshold
            assert config2.circuit_breaker.cooldown_seconds == config1.circuit_breaker.cooldown_seconds
            assert config2.logging.level == config1.logging.level


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
