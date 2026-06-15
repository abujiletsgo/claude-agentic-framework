# Knowledge DB — Hook Integration Reference

These are illustrative pseudocode examples showing how hooks can interact with the knowledge DB. The actual hook files (`session_start.py`, `pre_compact.py`, `stop.py`) live in `global-hooks/` and may differ in implementation.

## Session Start Hook

Auto-load recent relevant knowledge at session start:
```python
# In session_start.py
entries = search_knowledge(project=current_project, limit=5)
# Inject as context
```

## Pre-Compact Hook

Save important learnings before context compaction:
```python
# In pre_compact.py
store_knowledge(
    category="context",
    title="Session context before compaction",
    content=summarize_session()
)
```

## Stop Hook

Extract and store learnings on task completion:
```python
# In stop.py
if task_completed:
    store_knowledge(category="learning", ...)
```
