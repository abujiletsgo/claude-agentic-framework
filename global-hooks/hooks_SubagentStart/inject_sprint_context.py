#!/usr/bin/env python3
"""SubagentStart hook: inject orchestrate job context into lead agents."""
import json
import os
import sys
from pathlib import Path

MAX_CONTEXT_CHARS = 2500

def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        hook_input = {}

    orch_id = os.environ.get("CAF_ORCH_ID", "")
    role    = os.environ.get("CAF_ORCH_ROLE", "")

    if not orch_id:
        print(json.dumps({}))
        return

    ipc_dir = Path(f"/tmp/caf_orch/{orch_id}")
    context_parts = []
    total_chars = 0

    try:
        # 1. This lead's mission (first ~400 chars)
        prompt_file = ipc_dir / "prompts" / f"{role}.md"
        if prompt_file.exists():
            mission = prompt_file.read_text()[:400]
            context_parts.append(f"## Your Mission\n{mission}")
            total_chars += len(context_parts[-1])

        # 2. Acceptance criteria for this role (NEW)
        ac_file = ipc_dir / "acceptance_criteria.md"
        if ac_file.exists() and role:
            ac_text = ac_file.read_text()
            # Find section header matching this role
            header = f"### {role}"
            idx = ac_text.find(header)
            if idx != -1:
                # Take next 5 lines after the header line
                after = ac_text[idx:]
                lines = after.splitlines()
                section_lines = []
                for line in lines[1:]:
                    if line.startswith("###") and line.strip() != header:
                        break
                    section_lines.append(line)
                    if len(section_lines) >= 5:
                        break
                criteria_body = "\n".join(section_lines).strip()
                if criteria_body:
                    section = f"## Your Acceptance Criteria\n{criteria_body}"
                    budget = 300
                    if total_chars + min(len(section), budget) <= MAX_CONTEXT_CHARS:
                        context_parts.append(section[:budget])
                        total_chars += len(context_parts[-1])

        # 3. Last 3 working_memory entries (replaces global orch status)
        wm_file = ipc_dir / "shared" / "working_memory.jsonl"
        if wm_file.exists():
            lines = [l for l in wm_file.read_text().splitlines() if l.strip()][-3:]
            entries = []
            for line in lines:
                try:
                    e = json.loads(line)
                    lead    = e.get("lead", "?")
                    summary = e.get("summary", "")
                    reason  = e.get("reason", "")
                    reason_str = f" (why: {reason})" if reason else ""
                    entries.append(f"- [{lead}] {summary}{reason_str}")
                except Exception:
                    pass
            if entries:
                section = "## Team Activity (recent)\n" + "\n".join(entries)
                budget = 400
                if total_chars + min(len(section), budget) <= MAX_CONTEXT_CHARS:
                    context_parts.append(section[:budget])
                    total_chars += len(context_parts[-1])

        # 4. Pending questions notice (NEW)
        q_file = ipc_dir / "shared" / "questions.jsonl"
        if q_file.exists():
            pending_count = 0
            for line in q_file.read_text().splitlines():
                try:
                    e = json.loads(line)
                    if e.get("status") == "pending":
                        pending_count += 1
                except Exception:
                    pass
            if pending_count > 0:
                notice = (
                    f"Note: {pending_count} question(s) awaiting PM response "
                    f"— check orch-shared pending-questions if blocked."
                )
                budget = 100
                if total_chars + min(len(notice), budget) <= MAX_CONTEXT_CHARS:
                    context_parts.append(notice[:budget])
                    total_chars += len(context_parts[-1])

        # 5. Completed lead summaries (first 200 chars each, max 3)
        results_dir = ipc_dir / "results"
        if results_dir.exists():
            result_files = sorted(results_dir.glob("*_result.md"))[:3]
            summaries = []
            for rf in result_files:
                text = rf.read_text()[:200]
                summaries.append(f"### {rf.stem}\n{text}")
            if summaries:
                section = "## Prior Lead Results\n" + "\n".join(summaries)
                budget = 600
                if total_chars + min(len(section), budget) <= MAX_CONTEXT_CHARS:
                    context_parts.append(section[:budget])
                    total_chars += len(context_parts[-1])

    except Exception:
        pass  # fail-open

    if context_parts:
        combined = "\n\n".join(context_parts)[:MAX_CONTEXT_CHARS]
        print(json.dumps({"additionalContext": combined}))
    else:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
