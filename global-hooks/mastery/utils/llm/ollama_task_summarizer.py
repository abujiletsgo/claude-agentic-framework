#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "openai",
#     "python-dotenv",
# ]
# ///

"""
Task Summarizer LLM Utility (Ollama version)

Generates natural language summaries of subagent task completions using local Ollama.
Designed for TTS announcements to provide personalized feedback.
"""

import os
import sys
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv


def debug_log(message: str) -> None:
    """Write debug message to logs/subagent_debug.log"""
    try:
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        debug_path = os.path.join(log_dir, "subagent_debug.log")
        timestamp = datetime.now().isoformat()
        with open(debug_path, 'a') as f:
            f.write(f"[{timestamp}] [SUMMARIZER-OLLAMA] {message}\n")
    except Exception:
        pass


def summarize_subagent_task(task_description: str, agent_name: Optional[str] = None) -> str:
    """
    Generate a natural language summary of a completed subagent task using Ollama.

    Args:
        task_description: Description of the task that was completed
        agent_name: Optional name of the agent that completed the task

    Returns:
        str: A conversational summary suitable for TTS announcement
    """
    load_dotenv()
    debug_log(f"summarize_subagent_task called with: {task_description[:50]}...")

    # Get Ollama configuration
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    api_key = os.getenv("OLLAMA_API_KEY", "ollama")  # Dummy key for Ollama

    debug_log(f"Using Ollama at {base_url} with model {model}")

    # Build agent context for the prompt
    if agent_name:
        agent_context = f"The agent named '{agent_name}' completed this task."
        agent_instruction = f"You can reference the agent by name ('{agent_name}') naturally."
    else:
        agent_context = "A subagent completed this task."
        agent_instruction = "Refer to it as 'your agent' or similar."

    # Get engineer name from environment
    engineer_name = os.getenv("ENGINEER_NAME", "").strip()
    if engineer_name:
        user_address = f"Address the user as \"{engineer_name}\" directly (but not always at the start)"
    else:
        user_address = "Address the user naturally"

    prompt = f"""Generate a brief, conversational summary of a completed task for audio announcement.

Task completed: {task_description}

Context: {agent_context}

Requirements:
- {user_address}
- Keep it under 20 words
- Focus on the outcome and value delivered
- Be conversational and personalized
- {agent_instruction}
- Do NOT include quotes, formatting, or explanations
- Return ONLY the summary text

Example styles:
- "Authentication is ready with secure JWT token support."
- "Your file watcher is now monitoring for changes."
- "Builder finished setting up the TTS queue with file locks."
- "The new API endpoints are live and tested."

Generate ONE summary:"""

    try:
        from openai import OpenAI
        debug_log("OpenAI module imported successfully")

        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        debug_log("OpenAI client created for Ollama")

        debug_log(f"Calling Ollama API with model {model}...")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.3,
        )
        debug_log("API call completed")

        result = response.choices[0].message.content.strip()
        debug_log(f"Raw response: {result}")

        # Clean up response - remove quotes and extra formatting
        if result:
            result = result.strip().strip('"').strip("'").strip()
            # Take first line if multiple lines
            result = result.split("\n")[0].strip()
            debug_log(f"Cleaned response: {result}")
            return result

        debug_log("Response was empty, returning fallback")
        return "done"

    except Exception as e:
        debug_log(f"EXCEPTION: {type(e).__name__}: {str(e)}")
        return "done"


def main() -> None:
    """Command line interface for testing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate natural language summaries of subagent task completions using Ollama"
    )
    parser.add_argument(
        "task_description",
        nargs="?",
        help="Description of the completed task"
    )
    parser.add_argument(
        "--agent-name",
        "-a",
        type=str,
        default=None,
        help="Name of the agent that completed the task"
    )

    args = parser.parse_args()

    if not args.task_description:
        parser.print_help()
        print("\nExamples:")
        print('  uv run ollama_task_summarizer.py "Built authentication system"')
        print('  uv run ollama_task_summarizer.py "Built authentication system" --agent-name "builder"')
        sys.exit(1)

    summary = summarize_subagent_task(args.task_description, args.agent_name)
    print(summary)


if __name__ == "__main__":
    main()
