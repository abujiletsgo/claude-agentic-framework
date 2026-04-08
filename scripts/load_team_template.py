#!/usr/bin/env python3
"""
Load and spawn a team from a YAML template.

Usage:
    uv run load_team_template.py <template_name> [options]

Examples:
    uv run load_team_template.py review_team --files "src/api/**/*.py"
    uv run load_team_template.py architecture_team --requirements docs/spec.md
    uv run load_team_template.py research_team --topic "GraphQL vs REST"
    uv run load_team_template.py debug_team --bug-report .claude/bugs/issue_123.md

Dependencies:
    - PyYAML
"""

# /// script
# dependencies = ["pyyaml"]
# ///

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class TeamTemplateLoader:
    """Loads team templates and spawns agent teams."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.templates_dir = project_root / "data" / "team_templates"
        self.output_dir = Path(".claude") / "teams"

    def load_template(self, template_name: str) -> Dict[str, Any]:
        """Load a team template from YAML file."""
        template_path = self.templates_dir / f"{template_name}.yaml"

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path, "r") as f:
            template = yaml.safe_load(f)

        return template

    def list_templates(self) -> List[str]:
        """List all available team templates."""
        if not self.templates_dir.exists():
            return []

        templates = []
        for yaml_file in self.templates_dir.glob("*.yaml"):
            templates.append(yaml_file.stem)

        return sorted(templates)

    def spawn_agent(
        self,
        name: str,
        model: str,
        focus_area: str,
        responsibilities: List[str],
        shared_context: Dict[str, Any],
        output_path: Path,
    ) -> subprocess.Popen:
        """Spawn a single agent with specified configuration."""
        # Build agent prompt
        prompt_parts = [
            f"You are {name}, a specialized agent focused on: {focus_area}",
            "",
            "Your responsibilities:",
        ]

        for resp in responsibilities:
            prompt_parts.append(f"  - {resp}")

        prompt_parts.append("")
        prompt_parts.append("Shared context:")
        for key, value in shared_context.items():
            prompt_parts.append(f"  {key}: {value}")

        prompt_parts.append("")
        prompt_parts.append(f"Write your findings to: {output_path}")

        prompt = "\n".join(prompt_parts)

        # Spawn agent using claude command
        # Note: This is a simplified version - actual implementation would use
        # the Agent tool or claude CLI with proper model configuration
        cmd = [
            "claude",
            "--agent",
            name,
            "--model",
            model,
            "--output",
            str(output_path),
            prompt,
        ]

        # For now, just print what we would do
        print(f"[Spawn] {name} ({model})")
        print(f"  Output: {output_path}")

        # In a real implementation, return subprocess.Popen(cmd)
        # For this MVP, we'll use a placeholder
        return None

    def spawn_team(
        self,
        template: Dict[str, Any],
        shared_context: Dict[str, Any],
        background: bool = False,
    ) -> List[Any]:
        """Spawn all agents in a team according to the template."""
        team_name = template["name"]
        print(f"\n{'='*60}")
        print(f"Spawning team: {team_name}")
        print(f"Purpose: {template['purpose']}")
        print(f"{'='*60}\n")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        team_output_dir = self.output_dir / template["team_type"]
        team_output_dir.mkdir(exist_ok=True)

        # Spawn agents
        agents = []
        teammates = template["teammates"]

        for teammate in teammates:
            # Skip optional agents if not needed
            if teammate.get("optional", False):
                skip = input(
                    f"Include optional agent '{teammate['name']}'? [y/N]: "
                ).lower() not in ("y", "yes")
                if skip:
                    print(f"  Skipping optional agent: {teammate['name']}")
                    continue

            output_path = team_output_dir / f"{teammate['name']}_findings.md"

            agent = self.spawn_agent(
                name=teammate["name"],
                model=teammate["model"],
                focus_area=teammate["focus_area"],
                responsibilities=teammate["responsibilities"],
                shared_context=shared_context,
                output_path=output_path,
            )

            agents.append(
                {
                    "name": teammate["name"],
                    "process": agent,
                    "output_path": output_path,
                }
            )

        print(f"\nSpawned {len(agents)} agents")
        return agents

    def execute_team(
        self,
        template_name: str,
        shared_context: Dict[str, Any],
        background: bool = False,
    ) -> None:
        """Load template and execute team coordination strategy."""
        template = self.load_template(template_name)

        # Spawn team
        agents = self.spawn_team(template, shared_context, background)

        if not agents:
            print("No agents spawned. Exiting.")
            return

        # Execute coordination strategy
        coordination = template["coordination"]
        strategy = coordination["strategy"]

        print(f"\nCoordination strategy: {strategy}")
        print(f"Description: {coordination['description']}\n")

        # Execute phases
        for phase in coordination.get("phases", []):
            phase_name = phase["phase"]
            execution_type = phase["execution"]
            timeout = phase.get("timeout", 300)

            print(f"Phase: {phase_name} ({execution_type}, timeout={timeout}s)")

            if execution_type == "parallel":
                print("  Executing agents in parallel...")
                # In real implementation, wait for all agents or first to finish
                # For MVP, just show what we'd do
                phase_agents = phase.get("agents", [])
                for agent_name in phase_agents:
                    print(f"    - {agent_name}")

            elif execution_type == "sequential":
                print("  Executing agent sequentially...")
                agent_name = phase.get("agent", "")
                print(f"    - {agent_name}")

            print()

        # Show exit criteria
        exit_criteria = template["exit_criteria"]
        print("Exit criteria:")
        print(f"  Success: {exit_criteria['success']}")
        print(f"  Failure: {exit_criteria['failure']}")
        print(f"  Partial: {exit_criteria['partial_success']}")
        print()

        print(f"Results will be in: {self.output_dir / template['team_type']}")


def validate_path_input(path_str: str, param_name: str) -> str:
    """Validate path inputs to prevent injection attacks."""
    if not path_str:
        return path_str

    # Block dangerous patterns
    dangerous_patterns = [";", "|", "&", "$", "`", "\n", "\r"]
    for pattern in dangerous_patterns:
        if pattern in path_str:
            raise ValueError(
                f"Invalid character '{pattern}' in {param_name}: {path_str}"
            )

    # Ensure path is relative or absolute, no command injection
    if path_str.startswith("-"):
        raise ValueError(f"Invalid {param_name} starting with dash: {path_str}")

    return path_str


def validate_template_name(name: str) -> str:
    """Validate template name to ensure it's alphanumeric with underscores only."""
    if not name:
        return name

    if not name.replace("_", "").replace("-", "").isalnum():
        raise ValueError(f"Invalid template name (use only alphanumeric and _ - ): {name}")

    return name


def main():
    parser = argparse.ArgumentParser(
        description="Load and spawn agent teams from templates"
    )
    parser.add_argument(
        "template",
        nargs="?",
        help="Template name (review_team, architecture_team, research_team, debug_team)",
    )
    parser.add_argument(
        "--list", action="store_true", help="List available templates"
    )
    parser.add_argument(
        "--files", help="File pattern for review team (e.g., 'src/**/*.py')"
    )
    parser.add_argument(
        "--diff", help="Git diff reference for review team (e.g., 'HEAD~1')"
    )
    parser.add_argument("--requirements", help="Requirements file for architecture team")
    parser.add_argument("--topic", help="Research topic for research team")
    parser.add_argument("--bug-report", help="Bug report file for debug team")
    parser.add_argument(
        "--background",
        action="store_true",
        help="Run agents in background (non-blocking)",
    )

    args = parser.parse_args()

    # Validate inputs
    try:
        if args.template:
            args.template = validate_template_name(args.template)
        if args.files:
            args.files = validate_path_input(args.files, "files")
        if args.requirements:
            args.requirements = validate_path_input(args.requirements, "requirements")
        if args.bug_report:
            args.bug_report = validate_path_input(args.bug_report, "bug_report")
    except ValueError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)

    # Find project root (directory containing this script)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    loader = TeamTemplateLoader(project_root)

    # List templates
    if args.list:
        templates = loader.list_templates()
        print("Available team templates:")
        for template_name in templates:
            template = loader.load_template(template_name)
            print(f"  {template_name:20s} - {template['purpose']}")
        return

    if not args.template:
        parser.error("template name is required (use --list to see available templates)")

    # Build shared context based on template type
    shared_context = {}

    if args.template == "review_team":
        if args.files:
            shared_context["target_files"] = args.files
        if args.diff:
            shared_context["review_scope"] = f"diff:{args.diff}"
        else:
            shared_context["review_scope"] = "full"

    elif args.template == "architecture_team":
        if args.requirements:
            shared_context["project_requirements"] = args.requirements
        # Could add more context like tech_stack, constraints, etc.

    elif args.template == "research_team":
        if args.topic:
            shared_context["research_question"] = args.topic
        else:
            parser.error("--topic is required for research_team")

    elif args.template == "debug_team":
        if args.bug_report:
            shared_context["bug_report"] = args.bug_report
        else:
            parser.error("--bug-report is required for debug_team")

    # Execute team
    try:
        loader.execute_team(args.template, shared_context, args.background)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
