---
name: Project Scaffolder
version: 0.1.0
description: "This skill should be used when the user wants to create a new project or initialize a repository. It scaffolds new projects with proper structure and Claude Code integration."
---

# Project Scaffolder Skill

Create well-structured projects with configuration, tooling, and Claude Code integration.

## When to Use

- User asks to create a new project, scaffold, init, or start a new app
- Setting up a new repository
- Adding Claude Code integration to an existing project

## Workflow

1. Gather requirements: project type, language, framework, features
2. Create directory structure: src, tests, docs, .claude directories
3. Language-specific setup: config files for build tools, linters, test runners
4. Create CLAUDE.md with project instructions
5. Add .claude/settings.json with permissions
6. Initialize git with gitignore and initial commit
7. Verify all configs are valid and initial build passes

## Examples

### Example 1: Python CLI
Create structure with click, pyproject.toml, src package, pytest config.

### Example 2: TypeScript API
Init Node project, install TypeScript and Express, create routes and middleware.
