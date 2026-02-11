#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "httpx"]
# ///
"""
ANALYZE stage of the Knowledge Pipeline.

Hook: SessionEnd
Processes unprocessed observations from observations.jsonl using an LLM,
extracting actionable learnings in categories: LEARNED, PATTERN, INVESTIGATION.

Fallback chain: Anthropic -> OpenAI -> Ollama -> skip (store raw summary).
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CONFIG_PATH = Path.home() / ".claude" / "knowledge_pipeline.yaml"
OBSERVATIONS_DEFAULT = Path.home() / ".claude" / "observations.jsonl"
ANALYSIS_LOG = Path.home() / ".claude" / "analysis_log.jsonl"


def load_config():
    """Load pipeline config with safe defaults."""
    defaults = {
        "analyze": {
            "enabled": True,
            "llm_provider": "anthropic",
            "model": "claude-haiku-4-5",
            "openai_model": "gpt-4o-mini",
            "ollama_model": "llama3.2",
            "ollama_url": "http://localhost:11434",
            "min_observations_for_analysis": 10,
            "max_observations_for_llm": 200,
        }
    }
    if CONFIG_PATH.exists():
        try:
            import yaml
            with open(CONFIG_PATH, "r") as f:
                cfg = yaml.safe_load(f) or {}
            ana = cfg.get("analyze", {})
            for k, v in ana.items():
                defaults["analyze"][k] = v
        except Exception:
            pass
    return defaults["analyze"]


# ---------------------------------------------------------------------------
# Observation loading
# ---------------------------------------------------------------------------

def load_unprocessed_observations(obs_file, max_count=200):
    """Load unprocessed observations from JSONL file."""
    observations = []
    if not obs_file.exists():
        return observations

    try:
        with open(obs_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obs = json.loads(line)
                    if not obs.get("processed", False):
                        observations.append(obs)
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []

    # Return most recent observations up to max_count
    return observations[-max_count:]


def summarize_observations(observations):
    """Create a text summary of observations for the LLM prompt."""
    if not observations:
        return ""

    # Group by type
    by_type = {}
    for obs in observations:
        t = obs.get("type", "unknown")
        by_type.setdefault(t, []).append(obs)

    # Group by tool
    by_tool = {}
    for obs in observations:
        tool = obs.get("tool", "unknown")
        by_tool.setdefault(tool, []).append(obs)

    # Group by pattern
    by_pattern = {}
    for obs in observations:
        pattern = obs.get("pattern", "unknown")
        by_pattern.setdefault(pattern, []).append(obs)

    lines = []
    lines.append(f"Total observations: {len(observations)}")
    lines.append(f"Time range: {observations[0].get('timestamp', '?')} to {observations[-1].get('timestamp', '?')}")
    lines.append("")

    lines.append("## Tool Usage Frequency")
    for tool, items in sorted(by_tool.items(), key=lambda x: -len(x[1])):
        lines.append(f"  - {tool}: {len(items)} uses")

    lines.append("")
    lines.append("## Pattern Frequency")
    for pattern, items in sorted(by_pattern.items(), key=lambda x: -len(x[1])):
        lines.append(f"  - {pattern}: {len(items)} occurrences")

    # Errors
    errors = by_type.get("error", [])
    if errors:
        lines.append("")
        lines.append(f"## Errors ({len(errors)} total)")
        for err in errors[:10]:  # Show first 10
            snippet = err.get("context", {}).get("error_snippet", "")[:150]
            lines.append(f"  - [{err.get('tool', '?')}] {snippet}")

    # Sample observations (diverse selection)
    lines.append("")
    lines.append("## Sample Observations (detailed)")
    seen_patterns = set()
    samples = []
    for obs in observations:
        p = obs.get("pattern", "")
        if p not in seen_patterns and len(samples) < 15:
            seen_patterns.add(p)
            samples.append(obs)
    for s in samples:
        lines.append(f"  - tool={s.get('tool')}, pattern={s.get('pattern')}, type={s.get('type')}")
        ctx = s.get("context", {})
        # Show relevant context fields
        ctx_summary = {k: v for k, v in ctx.items() if v and k not in ("error_snippet",)}
        if ctx_summary:
            lines.append(f"    context: {json.dumps(ctx_summary)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM Providers
# ---------------------------------------------------------------------------

ANALYSIS_PROMPT = """Analyze these tool usage observations from a coding session.
Extract learnings in these categories:
- LEARNED: Lessons from mistakes or successes (things to remember)
- PATTERN: Recurring behaviors or approaches (workflow patterns)
- INVESTIGATION: Open questions to explore (areas needing attention)

For each learning, provide:
- tag: one of LEARNED, PATTERN, INVESTIGATION
- content: a concise, actionable statement (1-2 sentences)
- context: brief explanation of what evidence led to this conclusion
- confidence: 0.0-1.0 how confident you are in this learning

Return ONLY a JSON array of objects with these fields. No markdown, no commentary.
Example:
[
  {"tag": "LEARNED", "content": "Always check file existence before editing", "context": "Multiple edit failures due to missing files", "confidence": 0.8},
  {"tag": "PATTERN", "content": "Grep before Edit is the standard search-then-modify workflow", "context": "Grep followed by Edit in 80% of modification sequences", "confidence": 0.9}
]

Here are the observations:

"""


def call_anthropic(prompt, model):
    """Call Anthropic API using httpx."""
    import httpx

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            text = data.get("content", [{}])[0].get("text", "")
            return text
    except Exception:
        pass
    return None


def call_openai(prompt, model):
    """Call OpenAI-compatible API using httpx."""
    import httpx

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None

    try:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        pass
    return None


def call_ollama(prompt, model, base_url):
    """Call Ollama local API using httpx."""
    import httpx

    try:
        resp = httpx.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("response", "")
    except Exception:
        pass
    return None


def call_llm(summary, config):
    """Call LLM with fallback chain: Anthropic -> OpenAI -> Ollama -> None."""
    prompt = ANALYSIS_PROMPT + summary

    # Try Anthropic
    result = call_anthropic(prompt, config.get("model", "claude-haiku-4-5"))
    if result:
        return result, "anthropic"

    # Try OpenAI
    result = call_openai(prompt, config.get("openai_model", "gpt-4o-mini"))
    if result:
        return result, "openai"

    # Try Ollama
    result = call_ollama(
        prompt,
        config.get("ollama_model", "llama3.2"),
        config.get("ollama_url", "http://localhost:11434"),
    )
    if result:
        return result, "ollama"

    return None, None


def parse_llm_response(response_text):
    """Parse LLM response into a list of learning dicts."""
    if not response_text:
        return []

    # Try to find JSON array in the response
    text = response_text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
        if isinstance(data, list):
            # Validate each entry
            valid = []
            for item in data:
                if isinstance(item, dict) and "tag" in item and "content" in item:
                    valid.append({
                        "tag": item["tag"],
                        "content": item["content"],
                        "context": item.get("context", ""),
                        "confidence": float(item.get("confidence", 0.5)),
                    })
            return valid
    except (json.JSONDecodeError, ValueError):
        pass

    return []


# ---------------------------------------------------------------------------
# Mark observations as processed
# ---------------------------------------------------------------------------

def mark_observations_processed(obs_file, session_id):
    """Mark all observations for this session as processed."""
    if not obs_file.exists():
        return

    lines = []
    try:
        with open(obs_file, "r") as f:
            for line in f:
                line_stripped = line.strip()
                if not line_stripped:
                    lines.append(line)
                    continue
                try:
                    obs = json.loads(line_stripped)
                    if obs.get("session_id") == session_id:
                        obs["processed"] = True
                    lines.append(json.dumps(obs) + "\n")
                except json.JSONDecodeError:
                    lines.append(line)
    except Exception:
        return

    try:
        with open(obs_file, "w") as f:
            f.writelines(lines)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Analysis log
# ---------------------------------------------------------------------------

def log_analysis(session_id, observation_count, learnings_count, provider, duration_ms):
    """Log analysis metadata for monitoring."""
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session_id": session_id,
        "observation_count": observation_count,
        "learnings_extracted": learnings_count,
        "llm_provider": provider,
        "duration_ms": duration_ms,
    }
    try:
        ANALYSIS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(ANALYSIS_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    config = load_config()

    if not config.get("enabled", True):
        sys.exit(0)

    session_id = input_data.get("session_id", "unknown")

    # Load unprocessed observations
    obs_file_str = str(OBSERVATIONS_DEFAULT)
    # Check if config overrides observation file path
    pipeline_cfg_path = CONFIG_PATH
    if pipeline_cfg_path.exists():
        try:
            import yaml
            with open(pipeline_cfg_path, "r") as f:
                full_cfg = yaml.safe_load(f) or {}
            obs_file_str = full_cfg.get("observe", {}).get(
                "observations_file", str(OBSERVATIONS_DEFAULT)
            )
        except Exception:
            pass

    obs_file = Path(os.path.expanduser(obs_file_str))
    max_obs = config.get("max_observations_for_llm", 200)
    observations = load_unprocessed_observations(obs_file, max_obs)

    min_obs = config.get("min_observations_for_analysis", 10)
    if len(observations) < min_obs:
        sys.exit(0)

    # Summarize observations for LLM
    summary = summarize_observations(observations)

    # Call LLM
    start_time = time.time()
    response_text, provider = call_llm(summary, config)
    duration_ms = int((time.time() - start_time) * 1000)

    # Parse learnings
    learnings = parse_llm_response(response_text)

    # Store learnings as a JSON file for the LEARN stage to pick up
    learnings_output = Path.home() / ".claude" / "pending_learnings.json"
    try:
        output_data = {
            "session_id": session_id,
            "analyzed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "observation_count": len(observations),
            "llm_provider": provider,
            "learnings": learnings,
        }
        learnings_output.parent.mkdir(parents=True, exist_ok=True)
        with open(learnings_output, "w") as f:
            json.dump(output_data, f, indent=2)
    except Exception:
        pass

    # Mark observations as processed
    mark_observations_processed(obs_file, session_id)

    # Log analysis
    log_analysis(session_id, len(observations), len(learnings), provider, duration_ms)

    # If no LLM was available, create a raw summary fallback
    if not learnings and not provider:
        fallback_learnings = []
        # Extract basic patterns from observation data
        tool_counts = {}
        error_count = 0
        for obs in observations:
            tool = obs.get("tool", "unknown")
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
            if obs.get("type") == "error":
                error_count += 1

        if tool_counts:
            top_tool = max(tool_counts, key=tool_counts.get)
            fallback_learnings.append({
                "tag": "PATTERN",
                "content": f"Most used tool in session: {top_tool} ({tool_counts[top_tool]} uses)",
                "context": f"Tool distribution: {json.dumps(tool_counts)}",
                "confidence": 0.6,
            })

        if error_count > 0:
            fallback_learnings.append({
                "tag": "INVESTIGATION",
                "content": f"Session had {error_count} errors out of {len(observations)} operations",
                "context": "Error rate analysis - consider investigating common failure modes",
                "confidence": 0.5,
            })

        if fallback_learnings:
            try:
                output_data = {
                    "session_id": session_id,
                    "analyzed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "observation_count": len(observations),
                    "llm_provider": "fallback_raw",
                    "learnings": fallback_learnings,
                }
                with open(learnings_output, "w") as f:
                    json.dump(output_data, f, indent=2)
            except Exception:
                pass

    sys.exit(0)


if __name__ == "__main__":
    main()
