#!/usr/bin/env python3
"""SubagentStop hook: store sprint lead results in mempalace palace + KG."""
import json
import os
import subprocess
import sys
from pathlib import Path

MAX_STORE_CHARS = 4000

def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        hook_input = {}

    role = os.environ.get("CAF_SPRINT_ROLE", "")
    sprint_id = os.environ.get("CAF_SPRINT_ID", "")

    # Guard: only fire for sprint leads
    if not role or not sprint_id:
        print(json.dumps({}))
        return

    ipc_dir = Path(f"/tmp/caf_sprint/{sprint_id}")
    result_file = ipc_dir / "results" / f"{role}_result.md"
    script_dir = Path(__file__).resolve().parent.parent.parent
    sprint_event = script_dir / "bin" / "sprint-event"

    try:
        # Read lead result (plain text — never modify the IPC copy)
        if not result_file.exists():
            print(json.dumps({}))
            return

        result_text = result_file.read_text()[:MAX_STORE_CHARS]

        # Attempt palace storage with AAAK compression
        try:
            sys.path.insert(0, str(Path.home() / "Documents/claude-agentic-framework/lib"))
            import palace_init

            # AAAK compress for storage only
            compressed = result_text
            try:
                from mempalace.dialect import Dialect
                dialect = Dialect()
                compressed = dialect.compress(result_text)
            except ImportError:
                pass  # AAAK unavailable — store plain text
            except Exception:
                pass  # AAAK failed — store plain text

            # Write to palace
            palace_init.write_palace(
                content=compressed,
                wing="claude-agentic-framework",
                room="sprint_results",
                metadata={"sprint": sprint_id, "role": role}
            )

            # Emit event
            if sprint_event.exists():
                subprocess.run(
                    [str(sprint_event), sprint_id, "mempalace_stored",
                     json.dumps({"role": role, "chars": len(result_text)})],
                    timeout=5, capture_output=True
                )

        except ImportError:
            print("palace_init not available — skipping palace storage", file=sys.stderr)
        except Exception as e:
            print(f"palace storage failed: {e}", file=sys.stderr)

        # Extract decisions → KG triples
        try:
            import palace_init
            # Simple decision extraction: lines starting with "Decision:" or "Decided:"
            for line in result_text.split("\n"):
                line_stripped = line.strip()
                for prefix in ["Decision:", "Decided:", "- Decision:", "- Decided:"]:
                    if line_stripped.startswith(prefix):
                        decision = line_stripped[len(prefix):].strip()
                        if decision:
                            palace_init.add_kg_triple(
                                subject="project",
                                predicate="decided",
                                obj=decision
                            )
                            if sprint_event.exists():
                                subprocess.run(
                                    [str(sprint_event), sprint_id, "kg_triple_written",
                                     json.dumps({"role": role, "decision": decision[:100]})],
                                    timeout=5, capture_output=True
                                )
        except ImportError:
            pass
        except Exception as e:
            print(f"KG extraction failed: {e}", file=sys.stderr)

    except Exception as e:
        print(f"sprint_palace_store error: {e}", file=sys.stderr)

    print(json.dumps({}))

if __name__ == "__main__":
    main()
