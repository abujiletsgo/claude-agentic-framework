#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""
Caddy Request Analyzer - UserPromptSubmit Hook
===============================================

Analyzes incoming user prompts to:
1. Classify task complexity, type, quality need, and scope
2. Identify relevant skills that could help
3. Suggest execution strategy (direct, orchestrate, rlm, fusion, research)
4. Inject skill suggestions as context into the conversation

This hook runs on every UserPromptSubmit event. It NEVER blocks (exit 0 always).
It outputs JSON with skill suggestions that get injected into the agent context.

Exit: Always 0 (never blocks)
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime

# Import skill auditor (same package)
_caddy_dir = Path(__file__).parent
if str(_caddy_dir) not in sys.path:
    sys.path.insert(0, str(_caddy_dir))
from skill_auditor import SkillAuditor


# ---------------------------------------------------------------------------
# Keyword / pattern registries
# ---------------------------------------------------------------------------

SKILL_PATTERNS = {
    "brainstorm-before-code": {
        "keywords": [
            "brainstorm", "design first", "think before", "plan this",
            "new feature", "build from scratch", "architect", "design",
        ],
        "description": "Design-thinking phase before implementation",
    },
    "feasibility-analysis": {
        "keywords": [
            "feasible", "feasibility", "can we", "is it possible",
            "viable", "evaluate", "assessment",
        ],
        "description": "Viability and feasibility scoring",
    },
    "tdd-workflow": {
        "keywords": [
            "tdd", "test-driven", "test first", "red green refactor",
        ],
        "description": "Test-driven development workflow",
    },
    "code-review": {
        "keywords": [
            "review", "code review", "audit code", "check quality",
            "review this", "look at this code",
        ],
        "description": "Code quality review and analysis",
    },
    "security-scanner": {
        "keywords": [
            "security", "vulnerab", "exploit", "injection", "xss",
            "csrf", "auth", "penetration", "scan for",
        ],
        "description": "Security vulnerability detection",
    },
    "performance-profiler": {
        "keywords": [
            "performance", "slow", "optimize", "profil", "latency",
            "bottleneck", "speed up", "benchmark",
        ],
        "description": "Performance analysis and optimization",
    },
    "test-generator": {
        "keywords": [
            "add tests", "generate tests", "write tests", "test coverage",
            "unit test", "integration test",
        ],
        "description": "Automated test generation",
    },
    "documentation-writer": {
        "keywords": [
            "document", "docs", "readme", "api docs", "jsdoc",
            "docstring", "write docs",
        ],
        "description": "Documentation generation",
    },
    "refactoring-assistant": {
        "keywords": [
            "refactor", "restructure", "clean up", "reorganize",
            "simplify", "extract", "decompose",
        ],
        "description": "Safe code refactoring",
    },
    "dependency-audit": {
        "keywords": [
            "dependencies", "outdated", "vulnerable dep", "npm audit",
            "pip audit", "upgrade packages",
        ],
        "description": "Dependency health check",
    },
    "task-decomposition": {
        "keywords": [
            "break down", "decompose", "steps", "plan the steps",
            "task list", "subtasks",
        ],
        "description": "Break complex tasks into manageable steps",
    },
    "project-scaffolder": {
        "keywords": [
            "scaffold", "new project", "init", "bootstrap",
            "create project", "starter",
        ],
        "description": "New project scaffolding",
    },
    "git-workflow": {
        "keywords": [
            "git workflow", "branching", "merge strategy", "git flow",
        ],
        "description": "Git best practices and workflow",
    },
    "verification-checklist": {
        "keywords": [
            "verify", "checklist", "final check", "qa", "quality gate",
        ],
        "description": "Final verification and quality gate",
    },
}

COMPLEXITY_SIGNALS = {
    "simple": [
        "fix typo", "rename", "update version", "change color",
        "add comment", "remove unused", "small change", "quick fix",
        "one line", "simple",
    ],
    "moderate": [
        "add feature", "implement", "create endpoint", "add validation",
        "refactor", "update", "modify", "extend", "enhance",
    ],
    "complex": [
        "authentication", "authorization", "migrate", "redesign",
        "full stack", "end to end", "comprehensive", "overhaul",
        "integrate", "pipeline", "rest api", "graphql", "rate limit",
        "caching", "websocket", "middleware", "api with",
    ],
    "massive": [
        "entire codebase", "all files", "whole project", "everything",
        "from scratch", "rewrite", "rebuild", "migrate database",
        "monorepo", "microservices",
    ],
}

TASK_TYPE_SIGNALS = {
    "implement": [
        "build", "create", "add", "implement", "develop", "make",
        "write", "new feature", "scaffold",
    ],
    "fix": [
        "fix", "bug", "broken", "error", "crash", "failing",
        "not working", "issue", "debug", "repair",
    ],
    "refactor": [
        "refactor", "restructure", "clean", "reorganize", "simplify",
        "extract", "decouple", "modularize",
    ],
    "research": [
        "how does", "understand", "explain", "analyze", "investigate",
        "find out", "explore", "what is", "research",
    ],
    "test": [
        "test", "coverage", "unit test", "integration test", "e2e",
        "spec", "assert",
    ],
    "review": [
        "review", "audit", "scan", "check", "inspect", "evaluate",
        "assess",
    ],
    "document": [
        "document", "readme", "docs", "api doc", "comment", "jsdoc",
    ],
    "deploy": [
        "deploy", "release", "publish", "package", "build", "ship",
        "ci/cd",
    ],
    "plan": [
        "plan", "design", "architect", "roadmap", "strategy",
        "brainstorm", "think about",
    ],
}

QUALITY_SIGNALS = {
    "critical": [
        "security", "auth", "payment", "production", "database migration",
        "encryption", "credential", "secret", "irreversible", "critical",
    ],
    "high": [
        "important", "careful", "thorough", "comprehensive", "robust",
        "reliable", "tested",
    ],
}

STRATEGY_MAP = {
    ("simple", "standard"): "direct",
    ("simple", "high"): "direct",
    ("simple", "critical"): "fusion",
    ("moderate", "standard"): "orchestrate",
    ("moderate", "high"): "orchestrate",
    ("moderate", "critical"): "fusion",
    ("complex", "standard"): "orchestrate",
    ("complex", "high"): "orchestrate",
    ("complex", "critical"): "fusion",
    ("massive", "standard"): "rlm",
    ("massive", "high"): "rlm",
    ("massive", "critical"): "rlm",
}


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def match_keywords(text: str, keyword_lists: dict[str, list[str]]) -> str:
    """Return the category whose keywords have the most matches in text."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for category, keywords in keyword_lists.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[category] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else list(keyword_lists.keys())[0]


def detect_skills(text: str) -> list[dict]:
    """Return list of skills that match the user prompt, ranked by relevance."""
    text_lower = text.lower()
    matches = []
    for skill_name, info in SKILL_PATTERNS.items():
        score = sum(1 for kw in info["keywords"] if kw in text_lower)
        if score > 0:
            matches.append({
                "skill": skill_name,
                "relevance": score,
                "description": info["description"],
            })
    matches.sort(key=lambda x: x["relevance"], reverse=True)
    return matches[:5]  # Top 5 matches


def classify_complexity(text: str) -> str:
    """Classify task complexity."""
    return match_keywords(text, COMPLEXITY_SIGNALS)


def classify_task_type(text: str) -> str:
    """Classify task type."""
    return match_keywords(text, TASK_TYPE_SIGNALS)


def classify_quality_need(text: str) -> str:
    """Classify quality requirement."""
    text_lower = text.lower()
    for level in ["critical", "high"]:
        for kw in QUALITY_SIGNALS[level]:
            if kw in text_lower:
                return level
    return "standard"


def select_strategy(
    complexity: str,
    task_type: str,
    quality: str,
) -> str:
    """Select execution strategy based on classification."""
    # Research tasks always start with research
    if task_type == "research":
        return "research"

    # Plan tasks use brainstorm pattern
    if task_type == "plan":
        return "brainstorm"

    # Look up in strategy map
    return STRATEGY_MAP.get((complexity, quality), "orchestrate")


def estimate_confidence(
    complexity: str,
    task_type: str,
    quality: str,
    skills: list[dict],
    prompt_length: int,
) -> float:
    """Estimate confidence in the analysis (0.0 to 1.0).

    Higher confidence means the analysis is more reliable and
    auto-execution is safer.
    """
    confidence = 0.5  # Base confidence

    # Clear task type signal increases confidence
    if task_type != "implement":
        confidence += 0.1

    # Matching skills increase confidence
    if skills:
        top_relevance = skills[0]["relevance"]
        confidence += min(top_relevance * 0.05, 0.2)

    # Very short prompts are ambiguous
    if prompt_length < 20:
        confidence -= 0.2

    # Very long prompts are usually well-specified
    if prompt_length > 200:
        confidence += 0.1

    # Simple tasks are easier to classify correctly
    if complexity == "simple":
        confidence += 0.15

    # Critical quality needs should lower auto-exec confidence
    if quality == "critical":
        confidence -= 0.15

    return max(0.0, min(1.0, confidence))


# ---------------------------------------------------------------------------
# Skill security audit
# ---------------------------------------------------------------------------

def audit_detected_skills(detected_skills: list[dict]) -> dict:
    """Audit detected skills for security issues before recommendation.

    Args:
        detected_skills: List of skill dicts from detect_skills() with 'skill' key.

    Returns:
        Dictionary mapping skill names to audit results with 'blocked', 'findings' keys.
    """
    auditor = SkillAuditor()
    audit_results = {}

    # Check both global-skills in the framework and ~/.claude/skills
    skills_dirs = [
        Path(__file__).parent.parent.parent.parent / "global-skills",
        Path.home() / ".claude" / "skills",
    ]

    for skill_info in detected_skills:
        skill_name = skill_info["skill"]

        # Find the skill directory
        skill_path = None
        for skills_dir in skills_dirs:
            candidate = skills_dir / skill_name
            if candidate.exists() and candidate.is_dir():
                skill_path = candidate
                break

        if skill_path is None:
            continue

        findings = auditor.audit_skill(skill_path)

        if findings["critical"]:
            audit_results[skill_name] = {
                "blocked": True,
                "reason": f"Critical security issues: {len(findings['critical'])} found",
                "summary": auditor.summary(findings),
                "findings": {
                    k: [(f, l, d) for f, l, d in v]
                    for k, v in findings.items() if v
                },
            }
        elif findings["warning"]:
            audit_results[skill_name] = {
                "blocked": False,
                "warning": f"Security warnings: {len(findings['warning'])} found",
                "summary": auditor.summary(findings),
            }
        else:
            audit_results[skill_name] = {
                "blocked": False,
                "clean": True,
            }

    return audit_results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_caddy_config() -> dict:
    """Load Caddy configuration from yaml file."""
    config_path = Path.home() / ".claude" / "caddy_config.yaml"
    if not config_path.exists():
        return {
            "caddy": {
                "enabled": True,
                "auto_invoke_threshold": 0.8,
                "always_suggest": True,
                "background_monitoring": True,
            }
        }
    try:
        # Simple YAML-like parsing (avoid requiring pyyaml dependency)
        config = {}
        with open(config_path) as f:
            content = f.read()
        # Use json fallback for config if yaml not available
        # The config file includes a JSON-compatible section
        return config
    except Exception:
        return {"caddy": {"enabled": True, "auto_invoke_threshold": 0.8}}


def main():
    try:
        input_data = json.load(sys.stdin)

        # Extract user prompt
        prompt = input_data.get("prompt", "")
        session_id = input_data.get("session_id", "unknown")

        if not prompt or not prompt.strip():
            # Empty prompt, nothing to analyze
            sys.exit(0)

        # Skip slash commands - they already have a clear execution path
        if prompt.strip().startswith("/"):
            sys.exit(0)

        # Load configuration
        config = load_caddy_config()
        caddy_config = config.get("caddy", {})

        if not caddy_config.get("enabled", True):
            sys.exit(0)

        # Classify the request
        complexity = classify_complexity(prompt)
        task_type = classify_task_type(prompt)
        quality = classify_quality_need(prompt)
        skills = detect_skills(prompt)

        # Security audit: scan detected skills for dangerous patterns
        audit_results = audit_detected_skills(skills)

        # Filter out blocked skills (critical security issues)
        blocked_skills = [
            name for name, result in audit_results.items()
            if result.get("blocked")
        ]
        warned_skills = [
            name for name, result in audit_results.items()
            if not result.get("blocked") and result.get("warning")
        ]
        skills = [
            s for s in skills
            if s["skill"] not in blocked_skills
        ]

        strategy = select_strategy(complexity, task_type, quality)
        confidence = estimate_confidence(
            complexity, task_type, quality, skills, len(prompt)
        )

        # Build analysis result
        analysis = {
            "caddy_analysis": {
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "classification": {
                    "complexity": complexity,
                    "task_type": task_type,
                    "quality_need": quality,
                },
                "recommended_strategy": strategy,
                "confidence": round(confidence, 2),
                "relevant_skills": [
                    {"name": s["skill"], "description": s["description"]}
                    for s in skills
                ],
                "skill_audit": {
                    "blocked": blocked_skills,
                    "warned": warned_skills,
                    "details": {
                        name: result.get("reason") or result.get("warning", "clean")
                        for name, result in audit_results.items()
                    },
                },
            }
        }

        # Log analysis to file for monitoring
        log_dir = Path.home() / ".claude" / "logs" / "caddy"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "analyses.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(analysis) + "\n")

        # Build context message for the agent
        threshold = caddy_config.get("auto_invoke_threshold", 0.8)
        always_suggest = caddy_config.get("always_suggest", True)

        if always_suggest or confidence >= threshold:
            # Build suggestion message
            suggestions = []

            suggestions.append(
                f"[Caddy] Task classified as: "
                f"{complexity} {task_type} (quality: {quality})"
            )
            suggestions.append(
                f"[Caddy] Recommended strategy: {strategy} "
                f"(confidence: {confidence:.0%})"
            )

            if skills:
                skill_list = ", ".join(s["skill"] for s in skills[:3])
                suggestions.append(
                    f"[Caddy] Relevant skills: {skill_list}"
                )

            # Skill audit warnings
            if blocked_skills:
                suggestions.append(
                    f"[Caddy] BLOCKED skills (critical security issues): "
                    f"{', '.join(blocked_skills)}"
                )
                for name in blocked_skills:
                    reason = audit_results[name].get("reason", "unknown")
                    suggestions.append(
                        f"[Caddy]   - {name}: {reason}"
                    )

            if warned_skills:
                suggestions.append(
                    f"[Caddy] Skills with security warnings: "
                    f"{', '.join(warned_skills)}"
                )

            # Strategy-specific guidance
            strategy_guidance = {
                "direct": (
                    "Simple task - execute directly without orchestration overhead."
                ),
                "orchestrate": (
                    "Multi-step task - consider using /orchestrate "
                    "or spawning specialized sub-agents."
                ),
                "rlm": (
                    "Large codebase task - consider using /rlm "
                    "for iterative exploration without context rot."
                ),
                "fusion": (
                    "Critical quality task - consider using /fusion "
                    "for best-of-N approach with multiple perspectives."
                ),
                "research": (
                    "Information gathering needed - consider using /research "
                    "to delegate exploration to sub-agents."
                ),
                "brainstorm": (
                    "Planning task - consider using brainstorm-before-code "
                    "skill for structured design exploration."
                ),
            }
            if strategy in strategy_guidance:
                suggestions.append(
                    f"[Caddy] Guidance: {strategy_guidance[strategy]}"
                )

            # Output as user-visible context injection
            output = {
                "message": "\n".join(suggestions),
                "caddy": analysis["caddy_analysis"],
            }
            print(json.dumps(output))

        sys.exit(0)

    except Exception:
        # Never block the user prompt
        sys.exit(0)


if __name__ == "__main__":
    main()
