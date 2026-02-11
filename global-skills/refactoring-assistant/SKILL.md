---
name: Refactoring Assistant
version: 0.1.0
description: "This skill should be used when the user asks to refactor, restructure, clean up, simplify, or reorganize code. It guides and executes code refactoring safely with testing and incremental changes."
---

# Refactoring Assistant Skill

Safe, systematic code refactoring with test coverage, incremental changes, and rollback capability.

## When to Use

- User asks to refactor, clean up, simplify, restructure, or reorganize
- Code smells detected during review
- Before adding features to messy code
- Tech debt reduction

## Principles

1. Never refactor without tests - add tests first if none exist
2. Small incremental changes - one refactoring at a time
3. Verify after each step - run tests between refactorings
4. Preserve behavior - must not change functionality
5. Commit frequently - each step gets its own commit

## Workflow

1. Assess: Read files, check tests, identify dependencies
2. Ensure test coverage: Write tests for current behavior FIRST
3. Plan steps: Break into atomic changes with risk assessment
4. Execute: Make change, run tests, commit if pass, revert if fail
5. Verify: All tests pass, no warnings, code improved

## Common Refactorings

- Extract Method: Function longer than 30 lines
- Replace Magic Numbers: Literal values to named constants
- Introduce Parameter Object: More than 4 parameters
- Decompose Conditional: Complex boolean expressions
- Extract Class: Too many responsibilities

## Examples

### Example 1: Long Function
Identify sections, extract into named helpers, test after each.

### Example 2: Duplicate Code
Find duplicates, create shared utility, replace and test.
