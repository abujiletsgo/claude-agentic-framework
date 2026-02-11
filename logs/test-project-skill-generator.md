# Test Report: project-skill-generator Agent

**Date**: 2026-02-11
**Tester**: Builder Agent (Task #34)
**Agent Under Test**: `project-skill-generator` (`global-agents/team/project-skill-generator.md`)
**Test Project**: `/tmp/test-skill-gen-project/` (TaskFlow API -- Express.js/TypeScript)

---

## Test Summary

| Check | Result | Notes |
|-------|--------|-------|
| Test project created | PASS | 17-file Express.js/TypeScript project |
| Phase 1: Project analysis | PASS | All 8 discovery steps executed successfully |
| Phase 2: Skill generation (3-5 skills) | PASS | 5 skills generated |
| Phase 3: Hook generation | PASS | 1 hook generated (db-protection) |
| Phase 4: CLAUDE.md generation | PASS | Complete documentation created |
| Phase 5: Verification | PASS | All files present, frontmatter valid |
| Skills follow Anthropic format | PASS | YAML frontmatter + 5 required sections each |
| /prime integration | PASS (with caveat) | Skills discoverable; naming inconsistency noted |

**Overall Result**: PASS (with 1 bug found)

---

## Test Environment

**Test Project**: TaskFlow API
- **Language**: TypeScript 5.3
- **Framework**: Express.js 4.18
- **Database**: PostgreSQL via Prisma ORM
- **Testing**: Vitest + Supertest
- **CI**: GitHub Actions
- **Deploy**: Docker + docker-compose
- **Structure**: Layered architecture (controllers/services/models/middleware/utils)
- **Files**: 17 source files across src/, tests/, .github/, config/, docs/

---

## Phase 1: Project Analysis Results

The agent's discovery commands correctly identified:

| Detection Area | Found | Details |
|---------------|-------|---------|
| Language/Framework | Yes | TypeScript, Express.js, Node.js (via package.json) |
| Testing | Yes | Vitest (vitest.config.ts, 2 test files) |
| CI/CD | Yes | GitHub Actions (ci.yml) |
| Build System | Yes | tsc + esbuild, Docker |
| Architecture | Yes | Layered: controllers/services/models/middleware/utils |
| Documentation | Yes | README.md found |
| Deployment | Yes | Dockerfile + docker-compose.yml |
| Database | Yes | PostgreSQL (Prisma in package.json, docker-compose) |

---

## Phase 2: Skills Generated

### Skill 1: taskflow-test-runner
- **Path**: `.claude/skills/taskflow-test-runner/skill.md`
- **Description**: Run and manage tests for TaskFlow API
- **Covers**: All tests, single file, watch mode, coverage, pattern matching
- **Format check**: PASS (frontmatter + all 5 sections)

### Skill 2: taskflow-build
- **Path**: `.claude/skills/taskflow-build/skill.md`
- **Description**: Build and run in development and production modes
- **Covers**: Dev server (tsx watch), production build (tsc+esbuild), clean build, lint/format
- **Format check**: PASS (frontmatter + all 5 sections)

### Skill 3: taskflow-deploy
- **Path**: `.claude/skills/taskflow-deploy/skill.md`
- **Description**: Docker deployment and container management
- **Covers**: Docker build, docker-compose, pre-deploy checklist, logs, rollback
- **Format check**: PASS (frontmatter + all 5 sections)

### Skill 4: taskflow-debug
- **Path**: `.claude/skills/taskflow-debug/skill.md`
- **Description**: Debug and troubleshoot issues
- **Covers**: Log files, debug mode, API testing, database inspection, common errors table
- **Format check**: PASS (frontmatter + all 5 sections)

### Skill 5: taskflow-architecture
- **Path**: `.claude/skills/taskflow-architecture/skill.md`
- **Description**: Navigate codebase and understand data flow
- **Covers**: Layer structure, data flow diagram, integration points, adding features, naming conventions
- **Format check**: PASS (frontmatter + all 5 sections)

### Format Validation

All 5 skills have:
- [x] Valid YAML frontmatter with `name` and `description`
- [x] `## When to Use` section with trigger conditions
- [x] `## Prerequisites` section with requirements
- [x] `## Workflow` section with numbered steps and bash commands
- [x] `## Examples` section with user scenarios
- [x] `## Notes` section with caveats and tips

---

## Phase 3: Hooks Generated

### Hook: db-protection
- **Path**: `.claude/hooks/db-protection.md`
- **Purpose**: Prevent destructive database operations
- **Sections**: Trigger, Rule, Examples
- **Format check**: PASS

---

## Phase 4: CLAUDE.md Generated

- **Path**: `.claude/CLAUDE.md`
- **Sections present**: Quick Start, Architecture, Key Technologies, Development Workflow, Available Skills, Common Tasks, Conventions, Important Notes
- **Skill references**: All 5 skills correctly listed with matching names
- **Format check**: PASS

---

## /prime Integration Test

The prime skill (from `global-skills/prime/SKILL.md`) discovers project-specific skills via:
1. `ls -1 .claude/skills/ 2>/dev/null` -- **PASS**: Lists all 5 skill directories
2. `.claude/skills/*/SKILL.md` reading -- **CAVEAT**: See bug below
3. CLAUDE.md reading -- **PASS**: `.claude/CLAUDE.md` exists and is comprehensive

---

## Bug Found: Filename Case Inconsistency

**Severity**: Medium (breaks on case-sensitive filesystems like Linux)

**Issue**: The `project-skill-generator` agent template (Phase 2) specifies the output path as:
```
.claude/skills/<skill-name>/skill.md   (lowercase)
```

But the `prime` skill (Step 2) reads:
```
.claude/skills/*/SKILL.md              (uppercase)
```

And all global skills in the framework use `SKILL.md` (uppercase):
```
global-skills/prime/SKILL.md
global-skills/code-review/SKILL.md
global-skills/test-generator/SKILL.md
...
```

**Impact**: On macOS (case-insensitive HFS+/APFS), this works fine. On Linux (ext4, case-sensitive), `skill.md` would NOT be found by a glob for `SKILL.md`.

**Recommendation**: Update the `project-skill-generator` agent template to use `SKILL.md` (uppercase) to match the convention established by the prime skill and all global skills.

---

## Sample Generated Skill (Full Content)

### taskflow-test-runner/skill.md

```markdown
---
name: taskflow-test-runner
description: "Run and manage tests for TaskFlow API. Use when running tests,
  checking coverage, adding new tests, or debugging test failures."
---

# TaskFlow Test Runner

## When to Use
- User asks to run tests or check test status
- User wants to run a specific test file or test case
- User needs test coverage report
- User is adding a new feature and needs to write tests

## Prerequisites
- Node.js 20+ installed
- Dependencies installed (`npm install`)
- For integration tests: PostgreSQL running (via docker-compose)

## Workflow

### Step 1: Run All Tests
  npm run test
- Runs vitest in single-run mode

### Step 2: Run a Specific Test File
  npx vitest run tests/unit/taskService.test.ts

### Step 3: Run Tests in Watch Mode
  npm run test:watch

### Step 4: Run Tests with Coverage
  npm run test:coverage
- Uses v8 coverage provider
- Generates text, JSON, and HTML reports

### Step 5: Run Tests Matching a Pattern
  npx vitest run -t "should create a task"

## Examples

### Example 1: Run tests before committing
User: "run the tests"
Steps:
1. Run `npm run test`
2. Check for failures

### Example 2: Add a new test
User: "add tests for the auth controller"
Steps:
1. Create `tests/unit/authController.test.ts`
2. Import from `../../src/controllers/authController`
3. Use `describe`/`it`/`expect` from vitest
4. Run the new test file

## Notes
- Test files follow the pattern `*.test.ts`
- Vitest config is in `vitest.config.ts` at project root
- Tests use `globals: true` so no need to import describe/it/expect
```

---

## Recommendations

1. **Fix filename case**: Change `skill.md` to `SKILL.md` in the agent template to match framework convention
2. **Add eslint skill**: Project has ESLint configured; a dedicated linting skill could be generated
3. **Add database skill**: Prisma migrations/seeding/studio warrant a separate skill for database-heavy projects
4. **Consider auto-detecting `.env.example`**: The agent could read env examples to populate prerequisite environment variables in skills

---

## Files Created During Test

### Test Project (`/tmp/test-skill-gen-project/`)
```
.claude/
  CLAUDE.md
  hooks/
    db-protection.md
  skills/
    taskflow-test-runner/skill.md
    taskflow-build/skill.md
    taskflow-deploy/skill.md
    taskflow-debug/skill.md
    taskflow-architecture/skill.md
```

### Source Project (17 files)
```
src/index.ts
src/controllers/taskController.ts
src/controllers/authController.ts
src/services/taskService.ts
src/models/taskSchema.ts
src/middleware/auth.ts
src/middleware/errorHandler.ts
src/utils/logger.ts
tests/unit/taskService.test.ts
tests/integration/api.test.ts
package.json
tsconfig.json
vitest.config.ts
Dockerfile
docker-compose.yml
.github/workflows/ci.yml
README.md
```
