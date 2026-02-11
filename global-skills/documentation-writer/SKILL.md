---
name: Documentation Writer
version: 0.1.0
description: "This skill should be used when the user asks to write docs, document code, create README, or generate API documentation. It generates and maintains technical documentation including README files, API docs, architecture docs, and inline code documentation."
---

# Documentation Writer Skill

Generate clear, comprehensive technical documentation following best practices for various documentation types.

## When to Use

- User asks: "write docs", "create README", "document this", "API documentation"
- New project needs initial documentation
- Code lacks inline documentation
- Architecture decisions need recording

## Documentation Types

### README.md
Structure:
1. Project name and badge row
2. One-line description
3. Quick start (3 steps or less)
4. Installation
5. Usage with examples
6. Configuration
7. Contributing
8. License

### API Documentation
Structure:
1. Endpoint: METHOD /path
2. Description
3. Parameters (path, query, body)
4. Request example
5. Response example (success + error)
6. Authentication requirements

### Architecture Decision Records (ADR)
Structure:
1. Title: ADR-NNN: Decision Title
2. Status: Proposed/Accepted/Deprecated
3. Context: Why this decision was needed
4. Decision: What was decided
5. Consequences: Trade-offs and implications

### Code Comments
- Document WHY, not WHAT
- Public API: document parameters, returns, throws
- Complex algorithms: explain the approach
- Non-obvious: explain business rules

## Workflow

### Step 1: Analyze Codebase
```bash
# Understand project structure
ls -la
git ls-files | head -50
```

### Step 2: Identify Documentation Gaps
- Missing README sections
- Undocumented public APIs
- Missing architecture context
- Outdated documentation

### Step 3: Generate Documentation
- Use project-specific terminology
- Include real code examples from the codebase
- Keep language clear and concise
- Follow existing documentation style

### Step 4: Verify
- All code examples compile/run
- Links are valid
- No outdated information
- Consistent formatting

## Examples

### Example 1: Generate README
User: "Create a README for this project"

1. Analyze project structure and purpose
2. Detect tech stack
3. Generate comprehensive README following the template
4. Include real usage examples from the codebase

### Example 2: Document an API
User: "Document the REST API endpoints"

1. Find all route definitions
2. Extract parameters and response shapes
3. Generate OpenAPI-style documentation
4. Include curl examples
