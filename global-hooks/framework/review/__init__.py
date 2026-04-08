"""
Continuous Background Review System (roborev-style)
====================================================

Automatically reviews every commit in the background, stores findings,
and feeds them back to the agent on session start for resolution.

Components:
- post_commit_review.py  - Git post-commit hook entry point
- review_engine.py       - Core review orchestration
- findings_store.py      - Persistent findings storage (JSON)
- findings_notifier.py   - SessionStart context injection
- analyzers/             - Pluggable analysis modules

Integration:
- Circuit breaker: Review failures tracked; too many -> disable review
- Knowledge DB: Review patterns stored as PATTERN/INVESTIGATION tags
- Config: ~/.claude/review_config.yaml for thresholds and toggles
"""
