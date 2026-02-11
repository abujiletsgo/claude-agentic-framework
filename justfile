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

# ─── Observability System ─────────────────────────────────

# Start observability server + client (foreground, Ctrl+C to stop)
obs-start:
    {{project_root}}/scripts/start-system.sh

# Stop observability processes and clean up
obs-stop:
    {{project_root}}/scripts/reset-system.sh

# Stop then start observability
obs-restart: obs-stop obs-start

# ─── Observability Server (Bun, port 4000) ────────────────

# Install server dependencies
server-install:
    cd {{project_root}}/apps/observability/server && bun install

# Start server in dev mode (watch)
server:
    cd {{project_root}}/apps/observability/server && SERVER_PORT={{server_port}} bun run dev

# Start server in production mode
server-prod:
    cd {{project_root}}/apps/observability/server && SERVER_PORT={{server_port}} bun run start

# ─── Observability Client (Vue + Vite, port 5173) ─────────

# Install client dependencies
client-install:
    cd {{project_root}}/apps/observability/client && bun install

# Start client dev server
client:
    cd {{project_root}}/apps/observability/client && VITE_PORT={{client_port}} bun run dev

# Build client for production
client-build:
    cd {{project_root}}/apps/observability/client && bun run build

# Install all observability dependencies (server + client)
obs-install: server-install client-install

# ─── Database ──────────────────────────────────────────────

# Clear SQLite WAL files
db-clean-wal:
    rm -f {{project_root}}/apps/observability/server/events.db-wal {{project_root}}/apps/observability/server/events.db-shm
    @echo "WAL files removed"

# Delete the entire events database
db-reset:
    rm -f {{project_root}}/apps/observability/server/events.db {{project_root}}/apps/observability/server/events.db-wal {{project_root}}/apps/observability/server/events.db-shm
    @echo "Database reset"

# ─── Testing ───────────────────────────────────────────────

# Send a test event to the observability server
test-event:
    curl -s -X POST http://localhost:{{server_port}}/events \
      -H "Content-Type: application/json" \
      -d '{"source_app":"test","session_id":"test-1234","hook_event_type":"PreToolUse","payload":{"tool_name":"Bash","tool_input":{"command":"echo hello"}}}' \
      | head -c 200
    @echo ""

# Check server + client health
health:
    @curl -sf http://localhost:{{server_port}}/health > /dev/null 2>&1 \
      && echo "Server: UP (port {{server_port}})" \
      || echo "Server: DOWN (port {{server_port}})"
    @curl -sf http://localhost:{{client_port}} > /dev/null 2>&1 \
      && echo "Client: UP (port {{client_port}})" \
      || echo "Client: DOWN (port {{client_port}})"

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
    python3 {{project_root}}/global-hooks/framework/monitoring/model_usage_cli.py --last-week --by-agent

# Show today's costs
model-usage-today:
    python3 {{project_root}}/global-hooks/framework/monitoring/model_usage_cli.py --today --by-agent

# Show daily cost breakdown
model-usage-daily days="7":
    python3 {{project_root}}/global-hooks/framework/monitoring/model_usage_cli.py --daily {{days}}

# Show cost projection
model-usage-projection days="7":
    python3 {{project_root}}/global-hooks/framework/monitoring/model_usage_cli.py --projection {{days}}

# Generate sample cost data for testing
model-usage-sample days="7":
    python3 {{project_root}}/global-hooks/framework/monitoring/model_usage_cli.py --generate-sample {{days}}

# ─── Security ─────────────────────────────────────────────

# Generate skills.lock with SHA-256 hashes of all skill files
skills-lock:
    python3 {{project_root}}/scripts/generate_skills_lock.py

# Verify skills integrity against skills.lock
skills-verify:
    uv run {{project_root}}/global-hooks/framework/security/verify_skills.py

# Audit a single skill for security issues (e.g. just audit-skill code-review)
audit-skill skill:
    python3 {{project_root}}/scripts/audit_skill.py {{skill}}

# Audit all installed skills for security issues
audit-all-skills:
    @for skill in {{project_root}}/global-skills/*/; do \
        name=$(basename "$skill"); \
        echo "--- $name ---"; \
        python3 {{project_root}}/scripts/audit_skill.py "$name" || true; \
        echo ""; \
    done

# ─── Open ──────────────────────────────────────────────────

# Open the observability dashboard in browser
open:
    open http://localhost:{{client_port}}
