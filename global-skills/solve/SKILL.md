---
name: solve
description: Redirect to /orchestrate — the unified entry point for all complex work including autonomous problem-solving.
user-invocable: true
---

`/solve` is now `/orchestrate`.

```
Agent(subagent_type="orchestrator", description="Unified orchestration", prompt="<user's full message and any args passed to /solve>")
```

The orchestrator handles everything `/solve` did: interview mode, RLM recursion, parallel research, recovery loop, guardian validation, spiral detection, and self-correction. No separate entry point needed.
