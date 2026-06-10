# Claude Agentic Framework
# Usage: just <recipe>

set dotenv-load
set quiet

server_port := env("SERVER_PORT", "4000")
client_port := env("CLIENT_PORT", "5173")
project_root := justfile_directory()

# List available recipes
default:
    @just --list

# ─── Install ───────────────────────────────────────────────

# Run the full installer (symlinks + settings.json)
install:
    bash {{project_root}}/install.sh

# Run the uninstaller
uninstall:
    bash {{project_root}}/uninstall.sh

# ─── Database ──────────────────────────────────────────────
# (events.db is written by hooks and read by apps/run-explorer)

# Clear SQLite WAL files
db-clean-wal:
    rm -f {{project_root}}/apps/observability/server/events.db-wal {{project_root}}/apps/observability/server/events.db-shm
    @echo "WAL files removed"

# Delete the entire events database
db-reset:
    rm -f {{project_root}}/apps/observability/server/events.db {{project_root}}/apps/observability/server/events.db-wal {{project_root}}/apps/observability/server/events.db-shm
    @echo "Database reset"

# ─── Hooks ─────────────────────────────────────────────────

# Test a hook script directly (e.g. just hook-test mastery/pre_tool_use)
hook-test name:
    echo '{"session_id":"test-hook","tool_name":"Bash"}' | uv run {{project_root}}/global-hooks/{{name}}.py

# List all hook scripts across all namespaces
hooks:
    @echo "=== mastery ===" && ls -1 {{project_root}}/global-hooks/mastery/*.py 2>/dev/null | xargs -I{} basename {} .py
    @echo "=== observability ===" && ls -1 {{project_root}}/global-hooks/observability/*.py 2>/dev/null | xargs -I{} basename {} .py
    @echo "=== damage-control ===" && ls -1 {{project_root}}/global-hooks/damage-control/*.py 2>/dev/null | xargs -I{} basename {} .py
    @echo "=== framework ===" && ls -1 {{project_root}}/global-hooks/framework/*.py 2>/dev/null | xargs -I{} basename {} .py

# ─── Model Tiers ─────────────────────────────────────────

# Show model tier assignments and distribution dashboard
model-tiers:
    bash {{project_root}}/scripts/model-tiers.sh

# ─── Cost Tracking ────────────────────────────────────────────

# Show model usage costs for the last week
model-usage:
    uv run {{project_root}}/global-hooks/framework/monitoring/model_usage_cli.py --last-week --by-agent

# Show today's costs
model-usage-today:
    uv run {{project_root}}/global-hooks/framework/monitoring/model_usage_cli.py --today --by-agent

# Show daily cost breakdown
model-usage-daily days="7":
    uv run {{project_root}}/global-hooks/framework/monitoring/model_usage_cli.py --daily {{days}}

# Show cost projection
model-usage-projection days="7":
    uv run {{project_root}}/global-hooks/framework/monitoring/model_usage_cli.py --projection {{days}}

# Generate sample cost data for testing
model-usage-sample days="7":
    uv run {{project_root}}/global-hooks/framework/monitoring/model_usage_cli.py --generate-sample {{days}}

# ─── Security ─────────────────────────────────────────────

# Generate skills.lock with SHA-256 hashes of all skill files
skills-lock:
    uv run {{project_root}}/scripts/generate_skills_lock.py

# Verify skills integrity against skills.lock
skills-verify:
    uv run {{project_root}}/global-hooks/framework/security/verify_skills.py

# Audit a single skill for security issues (e.g. just audit-skill code-review)
audit-skill skill:
    uv run {{project_root}}/scripts/audit_skill.py {{skill}}

# Audit all installed skills for security issues
audit-all-skills:
    @for skill in {{project_root}}/global-skills/*/; do \
        name=$(basename "$skill"); \
        echo "--- $name ---"; \
        uv run {{project_root}}/scripts/audit_skill.py "$name" || true; \
        echo ""; \
    done

# Audit local project skills in .claude/skills/ (used by /prime)
audit-local-skills:
    @if [ -d ".claude/skills" ]; then \
        echo "Scanning local project skills..."; \
        echo ""; \
        for skill_dir in .claude/skills/*/; do \
            if [ -d "$skill_dir" ]; then \
                uv run {{project_root}}/scripts/audit_local_skill.py "$skill_dir" || true; \
                echo ""; \
            fi \
        done; \
    else \
        echo "No .claude/skills/ directory found in current project"; \
    fi

# ─── Team Health ─────────────────────────────────────────

# Check health of all agent team components
team-health:
    #!/usr/bin/env bash
    set -euo pipefail
    PROJECT_ROOT="{{project_root}}"
    PASS=0
    FAIL=0
    echo "========================================"
    echo "  Agent Team Health Check"
    echo "========================================"
    echo ""
    # ── 1. Team Templates ──────────────────────
    echo "=== Team Templates ==="
    TEMPLATES_DIR="$PROJECT_ROOT/data/team_templates"
    for tmpl in review_team.yaml architecture_team.yaml research_team.yaml debug_team.yaml; do
        FILE="$TEMPLATES_DIR/$tmpl"
        if [ ! -f "$FILE" ]; then
            echo "  [FAIL] $tmpl - file not found"
            FAIL=$((FAIL + 1))
            continue
        fi
        if [ ! -s "$FILE" ]; then
            echo "  [FAIL] $tmpl - file is empty"
            FAIL=$((FAIL + 1))
            continue
        fi
        HAS_NAME=$(grep -c "^name:" "$FILE" 2>/dev/null || true)
        HAS_TEAMMATES=$(grep -c "^teammates:" "$FILE" 2>/dev/null || true)
        if [ "$HAS_NAME" -ge 1 ] && [ "$HAS_TEAMMATES" -ge 1 ]; then
            echo "  [OK]   $tmpl - valid (has name + teammates)"
            PASS=$((PASS + 1))
        else
            echo "  [FAIL] $tmpl - missing required keys (name/teammates)"
            FAIL=$((FAIL + 1))
        fi
    done
    echo ""
    # ── 2. Coordination Hooks ──────────────────
    echo "=== Coordination Hooks ==="
    HOOKS_DIR="$HOME/.claude/hooks/validators"
    if [ ! -d "$HOOKS_DIR" ]; then
        echo "  [FAIL] Hooks directory not found: $HOOKS_DIR"
        FAIL=$((FAIL + 1))
    else
        for hook in "$HOOKS_DIR"/*.py; do
            HOOK_NAME=$(basename "$hook")
            if [ -L "$hook" ]; then
                TARGET=$(readlink "$hook")
                if [ -f "$TARGET" ]; then
                    echo "  [OK]   $HOOK_NAME -> $(basename "$TARGET") (symlink valid)"
                    PASS=$((PASS + 1))
                else
                    echo "  [FAIL] $HOOK_NAME -> $TARGET (broken symlink)"
                    FAIL=$((FAIL + 1))
                fi
            elif [ -f "$hook" ]; then
                echo "  [OK]   $HOOK_NAME (regular file)"
                PASS=$((PASS + 1))
            else
                echo "  [FAIL] $HOOK_NAME - not found"
                FAIL=$((FAIL + 1))
            fi
        done
    fi
    echo ""
    # ── 3. Active Teams ────────────────────────
    echo "=== Active Teams ==="
    TEAMS_DIR="$HOME/.claude/teams"
    if [ ! -d "$TEAMS_DIR" ]; then
        echo "  No teams directory found (~/.claude/teams/)"
    else
        TEAM_COUNT=$(find "$TEAMS_DIR" -mindepth 1 -maxdepth 1 -not -name "README.md" -not -name ".*" 2>/dev/null | wc -l | tr -d ' ')
        if [ "$TEAM_COUNT" -eq 0 ]; then
            echo "  No active teams"
        else
            echo "  Found $TEAM_COUNT active team(s):"
            find "$TEAMS_DIR" -mindepth 1 -maxdepth 1 -not -name "README.md" -not -name ".*" -exec basename {} \; 2>/dev/null | sort | while read -r team; do
                echo "    - $team"
            done
        fi
    fi
    echo ""
    # ── 4. Context Manager Summaries ───────────
    echo "=== Context Manager Summaries ==="
    CONTEXT_DIR="$PROJECT_ROOT/data/team-context"
    if [ ! -d "$CONTEXT_DIR" ]; then
        echo "  [FAIL] Context directory not found: $CONTEXT_DIR"
        FAIL=$((FAIL + 1))
    else
        SUMMARY_COUNT=$(find "$CONTEXT_DIR" -maxdepth 1 -name "*.md" -not -name "README.md" 2>/dev/null | wc -l | tr -d ' ')
        if [ "$SUMMARY_COUNT" -eq 0 ]; then
            echo "  No team context summaries found"
        else
            echo "  Found $SUMMARY_COUNT summary file(s):"
            find "$CONTEXT_DIR" -maxdepth 1 -name "*.md" -not -name "README.md" -exec basename {} \; 2>/dev/null | sort | while read -r f; do
                echo "    - $f"
            done
        fi
        echo "  [OK]   Context directory exists"
        PASS=$((PASS + 1))
    fi
    echo ""
    # ── Summary ────────────────────────────────
    echo "========================================"
    TOTAL=$((PASS + FAIL))
    echo "  Results: $PASS passed, $FAIL failed (out of $TOTAL checks)"
    if [ "$FAIL" -eq 0 ]; then
        echo "  Status: ALL HEALTHY"
    else
        echo "  Status: ISSUES FOUND"
    fi
    echo "========================================"
