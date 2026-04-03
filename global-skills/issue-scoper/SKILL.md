---
name: issue-scoper
description: Narrows context to a specific issue or task. Finds relevant files, related tests, blast radius, and similar past fixes. Writes /tmp/caf_issue_context.md. Agents read this to start with laser focus instead of searching the whole codebase.
user-invocable: true
---

Generate an issue-specific context snapshot for the described problem.

**Skip condition**: If the issue description already contains a specific `file:line` reference AND a clear description of what to change (e.g., "fix the null check at auth.py:42"), skip the scoper entirely — the issue is already scoped. Just confirm to the user: "Issue is already specific — skipping scope analysis."

Otherwise, proceed:

First, ensure `/tmp/caf_project_context.md` exists. If not, run the `project-adapter` skill first:
```
Agent(name="project-adapter", model="haiku", maxTurns=10, prompt="[project-adapter full prompt]")
```

Then spawn a Sonnet agent to scope the issue (needs search + reasoning):

```
Agent(
    name="issue-scoper",
    model="sonnet",
    maxTurns=15,
    prompt="""You are an issue context builder. Your job: given an issue description, find everything relevant to solving it and write a focused context file.

Read /tmp/caf_project_context.md first — it has the project structure, test commands, and known paths.

Issue/task to scope: [USER'S ISSUE DESCRIPTION]

## What to find

### 1. Relevant source files
Search for files directly related to the issue:
- Grep for key terms from the issue description
- Grep for function/class names mentioned
- Check files in the path the error trace mentions (if any)
- Limit to top 5 most relevant files. More is noise.

For each file found, note: why it's relevant (one sentence, cite the grep match).

### 2. Related tests  
Find tests that cover the affected code:
- Grep for the affected function/class names in the test directory (from project context)
- List test files with the specific test names that are relevant
- Note which test command runs them (from project context)

### 3. Similar past fixes
Check .claude/solve-history/ for similar problems:
- List files in .claude/solve-history/ if the directory exists
- For each, check the frontmatter: does `problem:` match the current issue?
- If yes, extract: root_cause + files_changed from that history entry
- Limit to top 3 matches

### 4. Blast radius
For each relevant source file found:
- Grep for its imports in the rest of the codebase
- Count how many files depend on it
- Flag files with 5+ dependents as "high blast radius"

### 5. Error pattern (if issue has an error message)
If the issue description contains an error or exception:
- Grep for the exact error string in the codebase
- Find where it's thrown/generated
- Note the file:line

## Write output

Write to /tmp/caf_issue_context.md:

```markdown
# Issue Context
GENERATED: [ISO timestamp]
ISSUE: [issue description, one line]
COMPLEXITY_ESTIMATE: simple | medium | hard
(simple = 1 file, obvious fix; medium = 2-5 files; hard = cross-cutting or unclear)

## Relevant Files (top 5)
| File | Why Relevant | Blast Radius |
|------|-------------|--------------|
| /path/to/file | [grep match or reason] | [N dependents] |

## Related Tests
| Test File | Test Name/Function | Run With |
|-----------|-------------------|----------|
| /path/to/test | [test function name] | [exact command] |

## Similar Past Fixes
[If any found in .claude/solve-history/]
- [date] [problem] → [approach that worked] (files: [list])
[If none: "No similar fixes found in solve-history"]

## Error Origin (if applicable)
- Error: [exact error text]
- Thrown at: [file:line]
- Caught/handled at: [file:line if found]

## Blast Radius Warning
[List any files with 5+ dependents that would be affected]
[Or: "No high blast-radius files identified"]

## Suggested Approach (one sentence)
[Based on complexity and blast radius — builder should start here]
```

Exit immediately after writing the file.
"""
)
```

After completion, show the user the issue context and confirm the complexity estimate.

Pass the user's full message (the issue description) as the issue to scope.
