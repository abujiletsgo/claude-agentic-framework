"""
Framework Automation Hooks
===========================

Tier 3 automations (nice to have):

1. auto_refine.py - Detects review completion and prompts to run /refine
2. auto_knowledge_indexing.py - Indexes commits to knowledge DB
3. auto_dependency_audit.py - Runs dependency audits at intervals

All hooks exit 0 (never block operations).
"""

__all__ = [
    "auto_refine",
    "auto_knowledge_indexing",
    "auto_dependency_audit",
]
