# Configuration System

Quick reference for the guardrails configuration system.

## Quick Start

```python
from guardrails.config_loader import load_config

# Load configuration (auto-merges defaults + file + env)
config = load_config()

# Use configuration
if config.circuit_breaker.enabled:
    threshold = config.circuit_breaker.failure_threshold
```

## CLI Commands

```bash
# Create default configuration file
python -m guardrails.config_loader --create-default

# Validate configuration
python -m guardrails.config_loader --validate

# Dump loaded configuration
python -m guardrails.config_loader --dump
```

## Configuration File

**Location:** `~/.claude/guardrails.yaml`

**Minimal example:**
```yaml
circuit_breaker:
  failure_threshold: 5
  cooldown_seconds: 600

logging:
  level: DEBUG
```

## Environment Variables

Override any setting using environment variables:

```bash
export GUARDRAILS_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
export GUARDRAILS_CIRCUIT_BREAKER_COOLDOWN_SECONDS=600
export GUARDRAILS_LOGGING_LEVEL=DEBUG
```

## Configuration Priority

1. **Environment variables** (highest)
2. **Configuration file**
3. **Built-in defaults** (lowest)

## Key Settings

### Circuit Breaker

- `failure_threshold`: Failures before disabling (default: 3)
- `cooldown_seconds`: Time before retry (default: 300)
- `success_threshold`: Successes to re-enable (default: 2)
- `exclude`: Hooks to never disable (default: [])

### Logging

- `level`: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
- `file`: Log file path (default: ~/.claude/logs/circuit_breaker.log)

## Full Documentation

See [CONFIG.md](CONFIG.md) for complete documentation including:
- All configuration options
- Validation rules
- Tuning guidelines
- Examples
- Troubleshooting

## Examples

See [examples/config_example.py](examples/config_example.py) for working examples of:
- Basic usage
- Custom config paths
- Environment overrides
- Creating default configs
- Excluding hooks

## Dependencies

- **PyYAML**: YAML parsing
- **pydantic**: Configuration validation

Install with:
```bash
pip install pyyaml pydantic
```

Or using uv:
```bash
uv pip install pyyaml pydantic
```
