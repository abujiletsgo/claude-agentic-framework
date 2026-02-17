# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest", "pyyaml"]
# ///
"""
Skills System Tests
====================

Tests for the skills system:
  - YAML frontmatter parsing from SKILL.md files
  - Skills discovery (scanning directories)
  - Skills content validation
  - Integration with agent system

Run:
  uv run pytest test_skills.py -v
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

TESTING_DIR = Path(__file__).parent
FRAMEWORK_DIR = TESTING_DIR.parent
REPO_DIR = FRAMEWORK_DIR.parent.parent
SKILLS_DIR = REPO_DIR / "global-skills"
sys.path.insert(0, str(TESTING_DIR))

from test_utils import TempDirFixture


# ===========================================================================
# YAML Frontmatter Parsing Tests
# ===========================================================================


def parse_skill_frontmatter(content: str) -> dict:
    """
    Parse YAML frontmatter from a SKILL.md file.

    Expects format:
    ---
    name: skill-name
    description: "Skill description"
    ---
    # Content...
    """
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        frontmatter = yaml.safe_load(parts[1])
        return frontmatter if isinstance(frontmatter, dict) else {}
    except yaml.YAMLError:
        return {}


def get_skill_body(content: str) -> str:
    """Extract the body (after frontmatter) from a SKILL.md file."""
    if not content.startswith("---"):
        return content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content
    return parts[2].strip()


class TestFrontmatterParsing:
    """Tests for YAML frontmatter parsing from SKILL.md files."""

    def test_basic_frontmatter(self):
        content = """---
name: test-skill
description: "A test skill"
---
# Test Skill
Some content here.
"""
        fm = parse_skill_frontmatter(content)
        assert fm["name"] == "test-skill"
        assert fm["description"] == "A test skill"

    def test_frontmatter_with_quotes(self):
        content = """---
name: prime
description: "Intelligently prime agent with project context. Use when starting a new session."
---
# Prime
"""
        fm = parse_skill_frontmatter(content)
        assert fm["name"] == "prime"
        assert "prime agent" in fm["description"]

    def test_no_frontmatter(self):
        content = "# Just a heading\nNo frontmatter here."
        fm = parse_skill_frontmatter(content)
        assert fm == {}

    def test_empty_frontmatter(self):
        content = """---
---
# Content
"""
        fm = parse_skill_frontmatter(content)
        assert fm == {}

    def test_malformed_yaml(self):
        content = """---
name: [invalid
  yaml: {broken
---
# Content
"""
        fm = parse_skill_frontmatter(content)
        assert fm == {}

    def test_frontmatter_with_extra_fields(self):
        content = """---
name: test
description: "desc"
version: "1.0"
tags:
  - utility
  - workflow
---
# Test
"""
        fm = parse_skill_frontmatter(content)
        assert fm["name"] == "test"
        assert fm["version"] == "1.0"
        assert fm["tags"] == ["utility", "workflow"]

    def test_body_extraction(self):
        content = """---
name: test
description: "desc"
---
# Skill Content

This is the body.
"""
        body = get_skill_body(content)
        assert "# Skill Content" in body
        assert "This is the body." in body

    def test_body_extraction_no_frontmatter(self):
        content = "# Just content\nNo frontmatter."
        body = get_skill_body(content)
        assert body == content


# ===========================================================================
# Skills Discovery Tests
# ===========================================================================


def discover_skills(skills_dir: Path) -> list[dict]:
    """
    Discover all skills in a directory.

    Each skill is a subdirectory containing a SKILL.md file.
    Returns list of dicts with: name, description, path, has_frontmatter.
    """
    skills = []
    if not skills_dir.exists():
        return skills

    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        skill_file = entry / "SKILL.md"
        if not skill_file.exists():
            continue

        content = skill_file.read_text()
        fm = parse_skill_frontmatter(content)
        skills.append({
            "dir_name": entry.name,
            "name": fm.get("name", entry.name),
            "description": fm.get("description", ""),
            "path": str(skill_file),
            "has_frontmatter": bool(fm),
        })

    return skills


class TestSkillsDiscovery:
    """Tests for skills discovery."""

    def test_discover_skills_in_temp_dir(self):
        with TempDirFixture() as tmp:
            # Create test skills
            (tmp.path / "skill-a").mkdir()
            (tmp.path / "skill-a" / "SKILL.md").write_text("""---
name: skill-a
description: "Skill A"
---
# Skill A
""")
            (tmp.path / "skill-b").mkdir()
            (tmp.path / "skill-b" / "SKILL.md").write_text("""---
name: skill-b
description: "Skill B"
---
# Skill B
""")
            # Directory without SKILL.md should be ignored
            (tmp.path / "not-a-skill").mkdir()

            skills = discover_skills(tmp.path)
            assert len(skills) == 2
            names = [s["name"] for s in skills]
            assert "skill-a" in names
            assert "skill-b" in names

    def test_discover_skills_empty_dir(self):
        with TempDirFixture() as tmp:
            skills = discover_skills(tmp.path)
            assert skills == []

    def test_discover_skills_nonexistent_dir(self):
        skills = discover_skills(Path("/nonexistent/dir"))
        assert skills == []

    def test_discover_skill_without_frontmatter(self):
        with TempDirFixture() as tmp:
            (tmp.path / "basic").mkdir()
            (tmp.path / "basic" / "SKILL.md").write_text("# Basic Skill\nNo frontmatter.")
            skills = discover_skills(tmp.path)
            assert len(skills) == 1
            assert skills[0]["has_frontmatter"] is False
            assert skills[0]["name"] == "basic"  # Falls back to dir name


class TestRealSkillsDirectory:
    """Tests against the actual global-skills directory."""

    @pytest.fixture
    def real_skills(self):
        if not SKILLS_DIR.exists():
            pytest.skip("global-skills directory not found")
        return discover_skills(SKILLS_DIR)

    def test_skills_exist(self, real_skills):
        assert len(real_skills) > 0, "No skills found in global-skills/"

    def test_all_skills_have_frontmatter(self, real_skills):
        for skill in real_skills:
            assert skill["has_frontmatter"], (
                f"Skill {skill['dir_name']} missing YAML frontmatter in SKILL.md"
            )

    def test_all_skills_have_name(self, real_skills):
        for skill in real_skills:
            assert skill["name"], (
                f"Skill {skill['dir_name']} missing 'name' in frontmatter"
            )

    def test_all_skills_have_description(self, real_skills):
        for skill in real_skills:
            assert skill["description"], (
                f"Skill {skill['dir_name']} missing 'description' in frontmatter"
            )

    def test_known_skills_present(self, real_skills):
        """Check that key expected skills exist (v2.1.0 set)."""
        names = [s["dir_name"] for s in real_skills]
        expected_skills = [
            "code-review",
            "test-generator",
            "knowledge-db",
            "error-analyzer",
            "security-scanner",
            "refactoring-assistant",
        ]
        for skill_name in expected_skills:
            assert skill_name in names, f"Expected skill '{skill_name}' not found"

    def test_skills_count_reasonable(self, real_skills):
        """Should have a reasonable number of skills (v2.1.0 has 6 framework skills)."""
        assert len(real_skills) >= 6, f"Only {len(real_skills)} skills found, expected >= 6"
        assert len(real_skills) <= 100, f"{len(real_skills)} skills found, seems too many"


# ===========================================================================
# Skill Content Validation Tests
# ===========================================================================


class TestSkillContentValidation:
    """Tests for validating skill content structure."""

    def test_skill_has_heading(self):
        content = """---
name: test
description: "test"
---
# Test Skill

Content here.
"""
        body = get_skill_body(content)
        assert body.startswith("#")

    def test_skill_description_not_too_long(self):
        """Description should be concise (for CLI display)."""
        content = """---
name: test
description: "A reasonable length description for the skill that explains what it does."
---
# Test
"""
        fm = parse_skill_frontmatter(content)
        assert len(fm["description"]) < 500

    def test_skill_name_valid_format(self):
        """Skill names should be lowercase with hyphens."""
        valid_names = ["prime", "code-review", "tdd-workflow", "test-generator"]
        for name in valid_names:
            assert name == name.lower(), f"Name '{name}' should be lowercase"
            assert " " not in name, f"Name '{name}' should not contain spaces"

    def test_skill_name_no_special_chars(self):
        """Skill names should not contain special characters."""
        import re
        valid_pattern = re.compile(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$|^[a-z0-9]$')
        names = ["prime", "code-review", "multi-model-tiers", "tdd-workflow"]
        for name in names:
            assert valid_pattern.match(name), f"Name '{name}' does not match valid pattern"


# ===========================================================================
# Skills Loading Tests (3-level loading)
# ===========================================================================


class TestSkillsLoading:
    """Tests for the 3-level skill loading mechanism."""

    def test_level_1_name_and_description_only(self):
        """Level 1: Just name + description for skill listing."""
        content = """---
name: test-skill
description: "A test skill for unit testing"
---
# Test Skill

## When to Use
Use this when testing.

## Workflow
1. Step one
2. Step two
"""
        fm = parse_skill_frontmatter(content)
        # Level 1 only needs these two fields
        assert "name" in fm
        assert "description" in fm

    def test_level_2_frontmatter_plus_heading(self):
        """Level 2: Frontmatter + first section for quick context."""
        content = """---
name: test-skill
description: "A test skill"
---
# Test Skill

## When to Use This Skill

This skill should be invoked when:
- User says: "test something"
- Running test suites

## Workflow

### Step 1: Setup
Do setup things.
"""
        fm = parse_skill_frontmatter(content)
        body = get_skill_body(content)
        # Level 2 includes the heading and first section
        lines = body.split("\n")
        heading = lines[0]
        assert heading.startswith("#")

    def test_level_3_full_content(self):
        """Level 3: Full skill content for execution."""
        content = """---
name: test-skill
description: "A test skill"
---
# Test Skill

## When to Use
Details here.

## Workflow

### Step 1
```bash
echo "step 1"
```

### Step 2
```bash
echo "step 2"
```

## Notes
Additional notes.
"""
        fm = parse_skill_frontmatter(content)
        body = get_skill_body(content)
        # Level 3 includes everything
        assert "Step 1" in body
        assert "Step 2" in body
        assert "Notes" in body
        assert "```bash" in body


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
