# Team Context Storage

This directory stores compressed summaries of teammate work created by the Context Manager agent.

## Purpose

The Context Manager (global-agents/team/context-manager.md) monitors all teammate activity and creates concise summaries that allow the main agent to understand what happened without loading full context.

## File Structure

- `{task-id}.md` - Summary for a completed task
- `{teammate}-{timestamp}.md` - Checkpoint summary for long-running tasks
- Archived summaries (90+ days old) moved to `archive/` subdirectory

## File Format

Each summary file contains:
- Frontmatter: task_id, teammate, timestamp, status
- Goal: What the task was trying to accomplish
- Outcome: What was achieved
- File Changes: List of modified files with brief descriptions
- Key Decisions: Important choices made and rationale
- Blockers/Issues: Any problems encountered
- Follow-Up Items: Action items for future work
- Compressed Summary: 3-5 bullet points for quick scanning

## Usage

The Context Manager automatically:
- Creates summaries when teammates finish tasks
- Stores checkpoint summaries for long-running work
- Makes summaries searchable by task ID, teammate, or timestamp

The main agent can:
- Query past summaries: "What did builder do last session?"
- Review decisions made on specific tasks
- Track blockers and follow-up items
- Understand team progress without full context reload

## Maintenance

- Summaries are kept under 500 words each
- Old summaries (90+ days) are archived to reduce clutter
- Only the Context Manager writes to this directory
- Other agents read summaries as needed
