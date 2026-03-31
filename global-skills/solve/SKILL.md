---
name: solve
description: Launch the autonomous problem-solver. Combines RLM recursion, multi-agent research, fusion testing, and dynamic skill creation. Self-iterates until solved.
user-invocable: true
---

Launch the `solve` agent to autonomously investigate and fix the problem.

Pass the user's full message as context. The agent will interview, research, hypothesize, challenge, implement, verify, and improve in a loop.

```
Agent(subagent_type="solve", prompt="<user's problem description and any args passed to /solve>")
```

If args are provided, pass them as the problem statement. If no args, the agent will interview the user.
