#!/usr/bin/env python3
"""SubagentStart hook: inject sprint context + KG decisions into lead."""
import json
import os
import sys
from pathlib import Path

MAX_CONTEXT_CHARS = 2000
MAX_KG_CHARS = 1500

def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        hook_input = {}

    sprint_id = os.environ.get("CAF_SPRINT_ID", "")
    role = os.environ.get("CAF_SPRINT_ROLE", "")

    # Fast path: not a sprint session
    if not sprint_id:
        print(json.dumps({}))
        return

    ipc_dir = Path(f"/tmp/caf_sprint/{sprint_id}")
    context_parts = []
    total_chars = 0

    try:
        # 1. Lead mission (first ~400 chars)
        prompt_file = ipc_dir / "prompts" / f"{role}.md"
        if prompt_file.exists():
            mission = prompt_file.read_text()[:400]
            context_parts.append(f"## Your Mission\n{mission}")
            total_chars += len(context_parts[-1])

        # 2. Last 5 events (situational awareness)
        events_file = ipc_dir / "events.jsonl"
        if events_file.exists():
            lines = events_file.read_text().strip().split("\n")
            recent = lines[-5:] if len(lines) >= 5 else lines
            events_summary = []
            for line in recent:
                try:
                    evt = json.loads(line)
                    events_summary.append(f"- [{evt.get('type','')}] {evt.get('ts','')}")
                except json.JSONDecodeError:
                    pass
            if events_summary:
                section = "## Recent Events\n" + "\n".join(events_summary)
                if total_chars + len(section) < MAX_CONTEXT_CHARS:
                    context_parts.append(section)
                    total_chars += len(section)

        # 3. Completed lead summaries (first 200 chars each, max 3)
        results_dir = ipc_dir / "results"
        if results_dir.exists():
            result_files = sorted(results_dir.glob("*_result.md"))[:3]
            summaries = []
            for rf in result_files:
                summary = rf.read_text()[:200]
                summaries.append(f"### {rf.stem}\n{summary}")
            if summaries:
                section = "## Prior Lead Results\n" + "\n".join(summaries)
                if total_chars + len(section) < MAX_CONTEXT_CHARS:
                    context_parts.append(section)
                    total_chars += len(section)

        # 4. KG decisions (via direct import, not MCP)
        try:
            sys.path.insert(0, str(Path.home() / "Documents/claude-agentic-framework/lib"))
            import palace_init
            kg_data = palace_init.get_project_kg()
            if kg_data:
                decisions = []
                for triple in kg_data[:10]:
                    if hasattr(triple, 'predicate') and 'decided' in str(triple.predicate):
                        decisions.append(f"- {triple.subject}: {triple.object}")
                    elif isinstance(triple, (list, tuple)) and len(triple) >= 3:
                        decisions.append(f"- {triple[0]}: {triple[2]}")
                if decisions:
                    section = "## Prior Decisions (KG)\n" + "\n".join(decisions)
                    section = section[:MAX_KG_CHARS]
                    if total_chars + len(section) < MAX_CONTEXT_CHARS:
                        context_parts.append(section)
        except ImportError:
            pass  # mempalace not available — skip KG
        except Exception:
            pass  # fail-open

    except Exception:
        pass  # fail-open on any error

    if context_parts:
        combined = "\n\n".join(context_parts)[:MAX_CONTEXT_CHARS]
        print(json.dumps({"additionalContext": combined}))
    else:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
