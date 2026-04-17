---
name: quickstart
description: Walk new contributors through setup and first contribution. Covers prerequisites, installation, testing, project structure, and how to create a branch and make a first commit.
user-invocable: true
---

Help a new contributor get started with this project.

## Step 1: Check for existing quickstart guide

If `.claude/QUICKSTART.md` exists in this repository, read and display it in full. This is the authoritative guide for this project — skip to the end.

If it doesn't exist, proceed to Step 2.

## Step 2: Extract build commands from CLAUDE.md

Read `CLAUDE.md` (or `.claude/CLAUDE.md` if the root version doesn't exist) and extract:
- **Tech Stack** section → language, framework, package manager, test runner
- **Build Commands** section → install, test, build, lint commands
- **Code Style** section → any style conventions
- **Architecture** section → major directories and structure

## Step 3: Detect prerequisites

Infer from CLAUDE.md and project files:
- Node.js (if package.json exists)
- Python (if pyproject.toml or setup.py exists)
- Rust (if Cargo.toml exists)
- Go (if go.mod exists)
- Java (if pom.xml or build.gradle exists)
- Elixir (if mix.exs exists)

## Step 4: Walk through setup

Present the following steps to the user:

1. **Clone and navigate** — guide to `cd` into the repo
2. **Check prerequisites** — tell user what to install (node/python/rust/etc.) based on detection
3. **Install dependencies** — show the exact install command from CLAUDE.md
4. **Run tests** — show the exact test command and confirm it passes
5. **Explore structure** — walk through the Architecture section from CLAUDE.md
6. **Create a branch** — show `git checkout -b feature/my-first-feature`
7. **Make a small change** — guide the user to edit a file (e.g., README, add a comment)
8. **Stage and commit** — show `git add` and `git commit -m` workflow
9. **Answer questions** — be ready to explain any setup issues or ask clarifying questions

## Step 5: Provide interactive support

As the user works through these steps, answer their setup questions and troubleshoot issues. If tests fail, help debug. If they get stuck on branching/committing, provide git guidance.

Keep the tone welcoming and focus on unblocking them to make their first contribution.
