#!/usr/bin/env python3
"""
Example usage of the guardrails configuration loader.

This script demonstrates how to:
1. Load configuration from file/env/defaults
2. Access configuration values
3. Create default configuration file
4. Validate configuration
"""

import os
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from guardrails.config_loader import load_config, create_default_config_file


def example_1_basic_usage():
    """Example 1: Basic configuration loading."""
    print("=" * 60)
    print("Example 1: Basic Configuration Loading")
    print("=" * 60)

    # Load configuration (uses defaults if no file exists)
    config = load_config()

    # Access circuit breaker settings
    print(f"Circuit Breaker Enabled: {config.circuit_breaker.enabled}")
    print(f"Failure Threshold: {config.circuit_breaker.failure_threshold}")
    print(f"Cooldown Seconds: {config.circuit_breaker.cooldown_seconds}")
    print(f"Success Threshold: {config.circuit_breaker.success_threshold}")

    # Access logging settings
    print(f"\nLog File: {config.logging.file}")
    print(f"Log Level: {config.logging.level}")

    # Access state file
    print(f"\nState File: {config.state_file}")
    print()


def example_2_custom_config_path():
    """Example 2: Load from custom configuration path."""
    print("=" * 60)
    print("Example 2: Custom Configuration Path")
    print("=" * 60)

    # Create a custom config in temp directory
    import tempfile
    import yaml

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({
            "circuit_breaker": {
                "failure_threshold": 10,
                "cooldown_seconds": 600
            },
            "logging": {
                "level": "DEBUG"
            }
        }, f)
        temp_path = Path(f.name)

    try:
        # Load from custom path
        config = load_config(temp_path)

        print(f"Loaded from: {temp_path}")
        print(f"Failure Threshold: {config.circuit_breaker.failure_threshold}")
        print(f"Cooldown Seconds: {config.circuit_breaker.cooldown_seconds}")
        print(f"Log Level: {config.logging.level}")
        print()
    finally:
        temp_path.unlink()


def example_3_environment_override():
    """Example 3: Override configuration with environment variables."""
    print("=" * 60)
    print("Example 3: Environment Variable Override")
    print("=" * 60)

    # Set environment variables
    os.environ["GUARDRAILS_CIRCUIT_BREAKER_FAILURE_THRESHOLD"] = "7"
    os.environ["GUARDRAILS_CIRCUIT_BREAKER_COOLDOWN_SECONDS"] = "900"
    os.environ["GUARDRAILS_LOGGING_LEVEL"] = "WARNING"

    try:
        # Load configuration (env vars take precedence)
        config = load_config()

        print("Environment variables set:")
        print("  GUARDRAILS_CIRCUIT_BREAKER_FAILURE_THRESHOLD=7")
        print("  GUARDRAILS_CIRCUIT_BREAKER_COOLDOWN_SECONDS=900")
        print("  GUARDRAILS_LOGGING_LEVEL=WARNING")
        print()
        print("Loaded configuration:")
        print(f"  Failure Threshold: {config.circuit_breaker.failure_threshold}")
        print(f"  Cooldown Seconds: {config.circuit_breaker.cooldown_seconds}")
        print(f"  Log Level: {config.logging.level}")
        print()
    finally:
        # Clean up environment
        del os.environ["GUARDRAILS_CIRCUIT_BREAKER_FAILURE_THRESHOLD"]
        del os.environ["GUARDRAILS_CIRCUIT_BREAKER_COOLDOWN_SECONDS"]
        del os.environ["GUARDRAILS_LOGGING_LEVEL"]


def example_4_create_default_config():
    """Example 4: Create default configuration file."""
    print("=" * 60)
    print("Example 4: Create Default Configuration File")
    print("=" * 60)

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "guardrails.yaml"

        # Create default config file
        create_default_config_file(output_path)

        print(f"Created default configuration at: {output_path}")
        print("\nFile contents:")
        print("-" * 60)
        with open(output_path) as f:
            print(f.read())
        print("-" * 60)
        print()


def example_5_path_methods():
    """Example 5: Using path helper methods."""
    print("=" * 60)
    print("Example 5: Path Helper Methods")
    print("=" * 60)

    config = load_config()

    # Get paths as Path objects
    state_path = config.get_state_file_path()
    log_path = config.get_log_file_path()

    print(f"State file path (Path object): {state_path}")
    print(f"State file type: {type(state_path)}")
    print(f"State file exists: {state_path.parent.exists()}")

    print(f"\nLog file path (Path object): {log_path}")
    print(f"Log file type: {type(log_path)}")
    print(f"Log file exists: {log_path.parent.exists()}")
    print()


def example_6_exclude_hooks():
    """Example 6: Excluding hooks from circuit breaker."""
    print("=" * 60)
    print("Example 6: Excluding Hooks from Circuit Breaker")
    print("=" * 60)

    import tempfile
    import yaml

    # Create config with excluded hooks
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({
            "circuit_breaker": {
                "exclude": [
                    "damage-control/bash-tool-damage-control.py",
                    "damage-control/edit-tool-damage-control.py",
                    "validators/critical_check.py"
                ]
            }
        }, f)
        temp_path = Path(f.name)

    try:
        config = load_config(temp_path)

        print("Excluded hooks (will never be disabled by circuit breaker):")
        for hook in config.circuit_breaker.exclude:
            print(f"  - {hook}")
        print()
    finally:
        temp_path.unlink()


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "GUARDRAILS CONFIGURATION EXAMPLES" + " " * 15 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    example_1_basic_usage()
    example_2_custom_config_path()
    example_3_environment_override()
    example_4_create_default_config()
    example_5_path_methods()
    example_6_exclude_hooks()

    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
