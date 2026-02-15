#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///

import json
import sys
from pathlib import Path
from utils.constants import ensure_session_log_dir


# Agent-to-model-tier lookup (kept in sync with data/model_tiers.yaml)
_AGENT_TIERS = {
    "orchestrator": "opus", "project-architect": "opus",
    "critical-analyst": "opus", "rlm-root": "opus", "caddy": "opus",
    "builder": "sonnet", "researcher": "sonnet", "meta-agent": "sonnet",
    "project-skill-generator": "sonnet", "scout-report-suggest": "sonnet",
    "llm-ai-agents-and-eng-research": "sonnet", "fetch-docs-sonnet45": "sonnet",
    "combo-optimizer": "sonnet", "strategy-advisor": "sonnet",
    "market-researcher": "sonnet", "performance-analyzer": "sonnet",
    "risk-assessor": "sonnet", "circuit-breaker-agent": "sonnet",
    "cli-tool-agent": "sonnet", "integration-agent": "sonnet",
    "state-manager-agent": "sonnet",
    "validator": "haiku", "create-worktree-subagent": "haiku",
    "scout-report-suggest-fast": "haiku", "docs-scraper": "haiku",
    "fetch-docs-haiku45": "haiku", "hello-world-agent": "haiku",
    "work-completion-summary": "haiku", "data-ingestion-helper": "haiku",
    "trader-data-validator": "haiku", "config-agent": "haiku",
    "docs-agent": "haiku", "qa-validator-agent": "haiku",
    "test-agent": "haiku",
}


def _resolve_model_tier(agent_type: str) -> str:
    """Look up model tier for an agent type. Returns 'sonnet' as default."""
    # Normalize: strip path prefix, lowercase, strip .md
    name = agent_type.rsplit("/", 1)[-1].replace(".md", "").lower()
    return _AGENT_TIERS.get(name, "sonnet")


def main():
    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)

        # Extract session_id
        session_id = input_data.get('session_id', 'unknown')

        # Enrich with model tier info
        agent_type = input_data.get('agent_type', '')
        input_data['model_tier'] = _resolve_model_tier(agent_type)

        # Ensure session log directory exists
        log_dir = ensure_session_log_dir(session_id)
        log_path = log_dir / 'subagent_start.json'

        # Read existing log data or initialize empty list
        if log_path.exists():
            with open(log_path, 'r') as f:
                try:
                    log_data = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    log_data = []
        else:
            log_data = []

        # Append new data
        log_data.append(input_data)

        # Write back to file with formatting
        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)

        sys.exit(0)

    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Exit cleanly on any other error
        sys.exit(0)


if __name__ == '__main__':
    main()
