#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""
Caddy Auto-Delegation Logic - UserPromptSubmit Hook
====================================================

Implements the Caddy decision tree for automatic delegation.
This hook runs after analyze_request.py and provides concrete
execution plans when confidence is high enough.

Decision Tree:
  Simple task (< 3 steps)     -> Direct execution (no delegation)
  Research task                -> /research or Explore agent
  Multi-step task              -> /orchestrate
  Iterative / large codebase   -> /rlm (Ralph Loop)
  Critical quality             -> /fusion (Best-of-N)
  New project setup            -> project-scaffolder skill
  Planning task                -> brainstorm-before-code skill

The hook outputs a structured execution plan that the Caddy agent
(or the main agent) can follow. It does NOT auto-execute; it provides
recommendations with sufficient detail to act on.

Exit: Always 0 (never blocks)
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime


# ---------------------------------------------------------------------------
# Delegation templates
# ---------------------------------------------------------------------------

DELEGATION_PLANS = {
    "direct": {
        "strategy": "direct",
        "description": "Execute directly without orchestration overhead",
        "steps": [
            "Execute the task using available tools",
            "Verify the result",
            "Report completion",
        ],
        "agents_needed": 0,
        "estimated_time": "1-5 minutes",
    },
    "research": {
        "strategy": "research",
        "description": "Delegate exploration to sub-agents, synthesize findings",
        "steps": [
            "Spawn 1-3 Explore agents for parallel investigation",
            "Each agent searches a different aspect of the question",
            "Collect and synthesize findings",
            "Present structured summary to user",
        ],
        "agents_needed": 2,
        "estimated_time": "3-8 minutes",
        "command": "/research",
    },
    "orchestrate": {
        "strategy": "orchestrate",
        "description": "Multi-agent coordination with specialized roles",
        "steps": [
            "Plan agent team (research, build, test, document)",
            "Spawn research/analysis agents in parallel",
            "Feed research results to builder agents",
            "Spawn tester/validator agents",
            "Synthesize results into executive summary",
        ],
        "agents_needed": 4,
        "estimated_time": "10-25 minutes",
        "command": "/orchestrate",
    },
    "rlm": {
        "strategy": "rlm",
        "description": (
            "Iterative exploration for large codebases "
            "using search-isolate-delegate-synthesize"
        ),
        "steps": [
            "Search for relevant patterns across codebase",
            "Isolate specific sections (max 50 lines each)",
            "Delegate analysis of each section to sub-agents",
            "Synthesize findings",
            "If more exploration needed, repeat",
            "Produce final consolidated answer",
        ],
        "agents_needed": 5,
        "estimated_time": "10-30 minutes",
        "command": "/rlm",
    },
    "fusion": {
        "strategy": "fusion",
        "description": (
            "Best-of-N approach with 3 parallel agents "
            "for critical quality decisions"
        ),
        "steps": [
            "Spawn 3 agents with different perspectives (Pragmatist, Architect, Optimizer)",
            "Each independently solves the task",
            "Score all solutions against quality rubric",
            "Fuse best solution with cherry-picked improvements",
            "Apply the fused result",
        ],
        "agents_needed": 3,
        "estimated_time": "8-15 minutes",
        "command": "/fusion",
    },
    "brainstorm": {
        "strategy": "brainstorm",
        "description": (
            "Structured design exploration before implementation"
        ),
        "steps": [
            "Clarify requirements via Socratic questioning",
            "Present 2-3 design options with trade-offs",
            "Get user approval on chosen approach",
            "Document design decision",
            "Proceed to implementation (optionally via /orchestrate)",
        ],
        "agents_needed": 0,
        "estimated_time": "5-15 minutes",
        "skill": "brainstorm-before-code",
    },
}


# ---------------------------------------------------------------------------
# Refinement logic
# ---------------------------------------------------------------------------

def refine_strategy(
    base_strategy: str,
    prompt: str,
    complexity: str,
    task_type: str,
    quality: str,
) -> dict:
    """Refine the base strategy with task-specific details.

    Returns a concrete execution plan with customized steps.
    """
    plan = dict(DELEGATION_PLANS.get(base_strategy, DELEGATION_PLANS["direct"]))
    prompt_lower = prompt.lower()

    # Add skill recommendations based on task type
    skills_to_invoke = []

    if task_type == "implement" and complexity != "simple":
        skills_to_invoke.append("brainstorm-before-code")
        skills_to_invoke.append("task-decomposition")

    if quality == "critical":
        skills_to_invoke.append("security-scanner")
        skills_to_invoke.append("verification-checklist")

    if task_type == "refactor":
        skills_to_invoke.append("refactoring-assistant")

    if task_type == "test":
        skills_to_invoke.append("tdd-workflow")

    if any(kw in prompt_lower for kw in ["deploy", "release", "ci/cd"]):
        skills_to_invoke.append("git-workflow")

    if any(kw in prompt_lower for kw in ["new project", "scaffold", "bootstrap"]):
        skills_to_invoke.append("project-scaffolder")
        plan["strategy"] = "direct"
        plan["skill"] = "project-scaffolder"

    if any(kw in prompt_lower for kw in ["dependencies", "outdated", "upgrade"]):
        skills_to_invoke.append("dependency-audit")

    plan["skills_to_invoke"] = list(dict.fromkeys(skills_to_invoke))  # Dedupe

    # Add model recommendations
    plan["model_recommendations"] = get_model_recommendations(task_type, quality)

    # Add context loading recommendation
    plan["context_needed"] = determine_context_needs(prompt, complexity)

    return plan


def get_model_recommendations(task_type: str, quality: str) -> dict:
    """Recommend models for each agent role based on task."""
    if quality == "critical":
        return {
            "primary": "opus",
            "builder": "opus",
            "reviewer": "opus",
            "tester": "sonnet",
            "researcher": "sonnet",
        }
    elif task_type in ("research", "review"):
        return {
            "primary": "sonnet",
            "researcher": "sonnet",
            "reviewer": "opus",
        }
    else:
        return {
            "primary": "sonnet",
            "builder": "sonnet",
            "tester": "sonnet",
            "researcher": "sonnet",
            "quick_tasks": "haiku",
        }


def determine_context_needs(prompt: str, complexity: str) -> dict:
    """Determine what context needs to be loaded before execution."""
    needs = {
        "prime_project": False,
        "load_specific_files": False,
        "explore_codebase": False,
    }

    prompt_lower = prompt.lower()

    # If mentions specific files/directories, we need targeted loading
    if re.search(r'[a-zA-Z_/]+\.(py|ts|js|rs|go|java|md)', prompt):
        needs["load_specific_files"] = True

    # If task involves broad changes, prime the project
    if complexity in ("complex", "massive"):
        needs["prime_project"] = True

    # If research or unknown scope, explore first
    if any(kw in prompt_lower for kw in [
        "how does", "find all", "across the codebase",
        "everything", "entire", "all files",
    ]):
        needs["explore_codebase"] = True

    return needs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        input_data = json.load(sys.stdin)

        prompt = input_data.get("prompt", "")
        session_id = input_data.get("session_id", "unknown")

        if not prompt or not prompt.strip():
            sys.exit(0)

        # Skip slash commands
        if prompt.strip().startswith("/"):
            sys.exit(0)

        # Load the analysis from analyze_request.py
        # (we re-analyze here since hooks are independent)
        # Import the classification functions from the sibling module
        hook_dir = Path(__file__).parent
        sys.path.insert(0, str(hook_dir))

        from analyze_request import (
            classify_complexity,
            classify_task_type,
            classify_quality_need,
            select_strategy,
            estimate_confidence,
            detect_skills,
        )

        complexity = classify_complexity(prompt)
        task_type = classify_task_type(prompt)
        quality = classify_quality_need(prompt)
        skills = detect_skills(prompt)
        base_strategy = select_strategy(complexity, task_type, quality)
        confidence = estimate_confidence(
            complexity, task_type, quality, skills, len(prompt)
        )

        # Build refined execution plan
        plan = refine_strategy(
            base_strategy, prompt, complexity, task_type, quality
        )
        plan["confidence"] = round(confidence, 2)
        plan["classification"] = {
            "complexity": complexity,
            "task_type": task_type,
            "quality_need": quality,
        }

        # Log the delegation plan
        log_dir = Path.home() / ".claude" / "logs" / "caddy"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "delegations.jsonl"
        with open(log_file, "a") as f:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "prompt_preview": prompt[:200],
                "plan": plan,
            }
            f.write(json.dumps(log_entry) + "\n")

        # Build output message
        output_lines = []

        # Only show delegation plan for non-simple tasks
        if base_strategy != "direct":
            output_lines.append(
                f"[Caddy Delegation] Strategy: {plan['strategy'].upper()}"
            )
            output_lines.append(
                f"[Caddy Delegation] {plan['description']}"
            )

            if plan.get("command"):
                output_lines.append(
                    f"[Caddy Delegation] Suggested command: {plan['command']}"
                )

            if plan.get("skill"):
                output_lines.append(
                    f"[Caddy Delegation] Suggested skill: {plan['skill']}"
                )

            if plan.get("skills_to_invoke"):
                output_lines.append(
                    "[Caddy Delegation] Skills pipeline: "
                    + " -> ".join(plan["skills_to_invoke"])
                )

            if plan["context_needed"].get("prime_project"):
                output_lines.append(
                    "[Caddy Delegation] Context: "
                    "Prime project first (/prime)"
                )

        if output_lines:
            output = {
                "message": "\n".join(output_lines),
                "caddy_delegation": plan,
            }
            print(json.dumps(output))

        sys.exit(0)

    except Exception:
        # Never block
        sys.exit(0)


if __name__ == "__main__":
    main()
