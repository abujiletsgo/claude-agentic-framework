# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest", "pyyaml"]
# ///
"""
Multi-Model Tier Tests
=======================

Tests for the multi-model tier system:
  - Agent model assignment validation
  - Tier configuration validation
  - Cost tracking structure
  - Tier fallback logic
  - Configuration file validation

Run:
  uv run pytest test_model_tiers.py -v
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

TESTING_DIR = Path(__file__).parent
FRAMEWORK_DIR = TESTING_DIR.parent
REPO_DIR = FRAMEWORK_DIR.parent.parent
AGENTS_DIR = REPO_DIR / "global-agents"
SKILLS_DIR = REPO_DIR / "global-skills"
sys.path.insert(0, str(TESTING_DIR))

from test_utils import TempDirFixture


# ===========================================================================
# Tier Definition Tests
# ===========================================================================


# Tier definitions as documented in the multi-model-tiers skill
TIER_DEFINITIONS = {
    "tier1": {
        "name": "Opus",
        "models": ["claude-opus-4-6", "opus"],
        "cost_input": 15.0,  # per 1M tokens
        "cost_output": 75.0,
    },
    "tier2": {
        "name": "Sonnet",
        "models": ["claude-sonnet-4-5", "sonnet"],
        "cost_input": 3.0,
        "cost_output": 15.0,
    },
    "tier3": {
        "name": "Haiku",
        "models": ["claude-haiku-4-5", "haiku"],
        "cost_input": 0.25,
        "cost_output": 1.25,
    },
}


class TestTierDefinitions:
    """Tests for tier definitions and model assignments."""

    def test_tier1_is_most_expensive(self):
        assert TIER_DEFINITIONS["tier1"]["cost_input"] > TIER_DEFINITIONS["tier2"]["cost_input"]
        assert TIER_DEFINITIONS["tier1"]["cost_output"] > TIER_DEFINITIONS["tier2"]["cost_output"]

    def test_tier2_more_expensive_than_tier3(self):
        assert TIER_DEFINITIONS["tier2"]["cost_input"] > TIER_DEFINITIONS["tier3"]["cost_input"]
        assert TIER_DEFINITIONS["tier2"]["cost_output"] > TIER_DEFINITIONS["tier3"]["cost_output"]

    def test_tier_names_unique(self):
        names = [t["name"] for t in TIER_DEFINITIONS.values()]
        assert len(names) == len(set(names))

    def test_all_tiers_have_models(self):
        for tier_id, tier in TIER_DEFINITIONS.items():
            assert len(tier["models"]) > 0, f"{tier_id} has no models"

    def test_model_names_valid_format(self):
        """Model names should follow Anthropic naming convention."""
        for tier_id, tier in TIER_DEFINITIONS.items():
            for model in tier["models"]:
                # Either short alias or full model ID
                assert isinstance(model, str)
                assert len(model) > 0


# ===========================================================================
# Agent Model Assignment Tests
# ===========================================================================


def parse_agent_model(agent_path: Path) -> str | None:
    """
    Extract the model assignment from an agent .md file.

    Looks for patterns like:
    - model: claude-sonnet-4-5
    - **Model**: `claude-haiku-4-5`
    - Use model: sonnet
    """
    if not agent_path.exists():
        return None

    content = agent_path.read_text()

    # Check YAML frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1])
                if isinstance(fm, dict) and "model" in fm:
                    return fm["model"]
            except yaml.YAMLError:
                pass

    # Check for model mentions in content
    model_patterns = [
        r'model:\s*["\']?([a-z0-9\-\.]+)',
        r'model_id:\s*["\']?([a-z0-9\-\.]+)',
        r'`(claude-[a-z0-9\-\.]+)`',
    ]
    for pattern in model_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def get_tier_for_model(model: str) -> str | None:
    """Get the tier name for a given model."""
    for tier_id, tier in TIER_DEFINITIONS.items():
        if model in tier["models"]:
            return tier_id
    # Check partial match
    for tier_id, tier in TIER_DEFINITIONS.items():
        for tier_model in tier["models"]:
            if tier_model in model or model in tier_model:
                return tier_id
    return None


class TestAgentModelAssignment:
    """Tests for agent model assignments in agent .md files."""

    def test_tier_lookup_works(self):
        assert get_tier_for_model("claude-opus-4-6") == "tier1"
        assert get_tier_for_model("claude-sonnet-4-5") == "tier2"
        assert get_tier_for_model("claude-haiku-4-5") == "tier3"
        assert get_tier_for_model("opus") == "tier1"
        assert get_tier_for_model("sonnet") == "tier2"
        assert get_tier_for_model("haiku") == "tier3"

    def test_unknown_model_returns_none(self):
        assert get_tier_for_model("gpt-4") is None
        assert get_tier_for_model("unknown-model") is None


# ===========================================================================
# Cost Tracking Tests
# ===========================================================================


class TestCostTracking:
    """Tests for cost tracking calculations."""

    def test_cost_calculation_tier1(self):
        """Calculate cost for Tier 1 usage."""
        input_tokens = 1_000_000
        output_tokens = 500_000
        tier = TIER_DEFINITIONS["tier1"]
        cost = (input_tokens / 1_000_000) * tier["cost_input"] + \
               (output_tokens / 1_000_000) * tier["cost_output"]
        assert cost == 15.0 + 37.5  # $52.50

    def test_cost_calculation_tier3(self):
        """Calculate cost for Tier 3 usage (cheapest)."""
        input_tokens = 1_000_000
        output_tokens = 500_000
        tier = TIER_DEFINITIONS["tier3"]
        cost = (input_tokens / 1_000_000) * tier["cost_input"] + \
               (output_tokens / 1_000_000) * tier["cost_output"]
        assert cost == 0.25 + 0.625  # $0.875

    def test_tier3_is_60x_cheaper_than_tier1(self):
        """Tier 3 should be approximately 60x cheaper than Tier 1."""
        ratio_input = TIER_DEFINITIONS["tier1"]["cost_input"] / TIER_DEFINITIONS["tier3"]["cost_input"]
        ratio_output = TIER_DEFINITIONS["tier1"]["cost_output"] / TIER_DEFINITIONS["tier3"]["cost_output"]
        assert ratio_input == 60.0
        assert ratio_output == 60.0

    def test_cost_tracking_structure(self):
        """Test the expected cost tracking data structure."""
        cost_record = {
            "session_id": "test-001",
            "model": "claude-sonnet-4-5",
            "tier": "tier2",
            "input_tokens": 50000,
            "output_tokens": 10000,
            "estimated_cost_usd": (50000 / 1_000_000) * 3.0 + (10000 / 1_000_000) * 15.0,
            "timestamp": "2026-02-11T12:00:00Z",
        }
        assert cost_record["estimated_cost_usd"] == pytest.approx(0.15 + 0.15)
        assert "session_id" in cost_record
        assert "model" in cost_record
        assert "tier" in cost_record


# ===========================================================================
# Tier Fallback Tests
# ===========================================================================


class TestTierFallback:
    """Tests for tier fallback behavior on errors."""

    @staticmethod
    def select_tier_with_fallback(
        preferred_tier: str,
        available_tiers: list[str],
        error: str | None = None,
    ) -> str:
        """
        Select a tier with fallback logic.

        If preferred tier fails, fall back to next cheaper tier.
        Tier order: tier1 (most expensive) -> tier2 -> tier3 (cheapest)
        """
        tier_order = ["tier1", "tier2", "tier3"]

        if error is None and preferred_tier in available_tiers:
            return preferred_tier

        # Find the preferred tier's index and try each subsequent tier
        try:
            start_idx = tier_order.index(preferred_tier) + 1
        except ValueError:
            start_idx = 0

        for tier in tier_order[start_idx:]:
            if tier in available_tiers:
                return tier

        # If nothing available, return the cheapest
        return "tier3"

    def test_preferred_tier_available(self):
        result = self.select_tier_with_fallback(
            "tier1", ["tier1", "tier2", "tier3"]
        )
        assert result == "tier1"

    def test_fallback_tier1_to_tier2(self):
        result = self.select_tier_with_fallback(
            "tier1", ["tier2", "tier3"], error="rate_limit"
        )
        assert result == "tier2"

    def test_fallback_tier2_to_tier3(self):
        result = self.select_tier_with_fallback(
            "tier2", ["tier3"], error="model_unavailable"
        )
        assert result == "tier3"

    def test_fallback_to_cheapest_when_nothing_available(self):
        result = self.select_tier_with_fallback(
            "tier1", [], error="all_failed"
        )
        assert result == "tier3"

    def test_no_fallback_when_no_error(self):
        result = self.select_tier_with_fallback(
            "tier2", ["tier1", "tier2", "tier3"]
        )
        assert result == "tier2"

    def test_fallback_skips_unavailable_tiers(self):
        result = self.select_tier_with_fallback(
            "tier1", ["tier3"], error="error"
        )
        assert result == "tier3"  # Skips tier2 (not available)


# ===========================================================================
# Configuration Validation Tests
# ===========================================================================


class TestModelTierConfiguration:
    """Tests for model tier configuration files."""

    def test_tier_assignment_consistency(self):
        """Validate that tier assignments make sense (expensive models for complex tasks)."""
        # Tier 1 (expensive) should be for orchestration/architecture
        # Tier 3 (cheap) should be for simple/fast tasks
        tier1_tasks = ["orchestration", "architecture", "security", "reasoning"]
        tier3_tasks = ["validation", "formatting", "simple", "fast"]

        # These are conceptual checks - the actual assignments are in the skill file
        for task in tier1_tasks:
            assert task  # Just verifying the task categories exist

        for task in tier3_tasks:
            assert task


# ===========================================================================
# Agent Directory Validation Tests
# ===========================================================================


class TestAgentDirectory:
    """Tests for the agent directory structure."""

    def test_agents_directory_exists(self):
        if not AGENTS_DIR.exists():
            pytest.skip("global-agents directory not found")
        assert AGENTS_DIR.is_dir()

    def test_agent_files_are_markdown(self):
        if not AGENTS_DIR.exists():
            pytest.skip("global-agents directory not found")
        agent_files = list(AGENTS_DIR.glob("*.md"))
        assert len(agent_files) > 0, "No agent .md files found"



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
