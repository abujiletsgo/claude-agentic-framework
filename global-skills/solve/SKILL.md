---
name: solve
description: "Alias for /orchestrate — DO NOT dispatch independently. Routes all input directly to the orchestrator. Not a competing trigger."
user-invocable: true
---

`/solve` is now `/orchestrate`.

```
Agent(subagent_type="orchestrator", description="Unified orchestration", prompt="<user's full message and any args passed to /solve>")
```

The orchestrator handles everything `/solve` did: consultant-driven spec (Wave 0a), parallel research (Wave 0b), parallel builders (Wave 1), and the self-healing QA/evaluator loop (Wave 2). No separate entry point needed.
