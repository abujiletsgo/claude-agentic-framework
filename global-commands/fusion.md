# F-Thread: Fusion Thread (Best of N)

## Instructions

You are executing an **F-Thread** (Fusion Thread). This runs multiple agents in parallel on the same task, then fuses the best results into a final output.

**Input**: $ARGUMENTS

---

## Phase 1: Spawn N Parallel Agents

Launch **3 sub-agents** in parallel, all working on the **same task** but independently. Each agent gets a different "persona" to maximize solution diversity.

### Agent 1: "The Pragmatist"
Use the Task tool with subagent_type="general-purpose":
```
Prompt: "You are a pragmatic, ship-fast engineer. Solve this task with the simplest, most direct approach. Prioritize readability and minimal dependencies. TASK: $ARGUMENTS"
```

### Agent 2: "The Architect"
Use the Task tool with subagent_type="general-purpose":
```
Prompt: "You are a senior architect who designs for scale and maintainability. Solve this task with clean abstractions, proper error handling, and extensibility. TASK: $ARGUMENTS"
```

### Agent 3: "The Optimizer"
Use the Task tool with subagent_type="general-purpose":
```
Prompt: "You are a performance-obsessed engineer. Solve this task with the most efficient approach possible. Minimize allocations, optimize hot paths, and benchmark your choices. TASK: $ARGUMENTS"
```

**CRITICAL**: Launch all 3 agents in a SINGLE message (parallel tool calls). Do NOT wait for one before launching the next.

---

## Phase 2: Collect Results

After all 3 agents return, collect their outputs. Label them:
- **Solution A** (Pragmatist)
- **Solution B** (Architect)
- **Solution C** (Optimizer)

---

## Phase 3: Fusion (Selection + Merge)

Now act as the **Fusion Judge**. Evaluate all 3 solutions against these criteria:

### Scoring Rubric (1-5 each)

| Criteria | Weight | Description |
|----------|--------|-------------|
| Correctness | 3x | Does it solve the task correctly? |
| Simplicity | 2x | Is the code easy to understand? |
| Robustness | 2x | Does it handle edge cases? |
| Performance | 1x | Is it efficient? |
| Maintainability | 1x | Is it easy to modify? |

### Evaluation Process

1. **Score each solution** against the rubric
2. **Identify the winner** (highest weighted score)
3. **Cherry-pick improvements** from losing solutions that enhance the winner
4. **Produce the final fused output** - the best solution enhanced with the best ideas from the others

### Output Format

```
## F-Thread Results

### Scores
| Solution | Correctness | Simplicity | Robustness | Performance | Maintainability | Total |
|----------|-------------|------------|------------|-------------|-----------------|-------|
| A (Pragmatist) | x/5 | x/5 | x/5 | x/5 | x/5 | xx |
| B (Architect)  | x/5 | x/5 | x/5 | x/5 | x/5 | xx |
| C (Optimizer)  | x/5 | x/5 | x/5 | x/5 | x/5 | xx |

### Winner: Solution [X]
Reason: [why this solution won]

### Cherry-Picked Enhancements
- From Solution [Y]: [what was borrowed and why]
- From Solution [Z]: [what was borrowed and why]

### Final Fused Solution
[The actual code/output - the winning solution enhanced with cherry-picked improvements]
```

---

## Phase 4: Apply

After fusion, apply the final solution to the codebase:
1. Write/Edit the files with the fused solution
2. Report what was applied and why it was the best choice

---

## Rules

1. **Always launch agents in parallel** (single message, multiple Task tool calls)
2. **Never bias toward any persona** - let the rubric decide
3. **Always cherry-pick** - even losers may have good ideas
4. **The fused result should be better than any individual solution**
5. **If all 3 solutions are equivalent**, pick the simplest one
