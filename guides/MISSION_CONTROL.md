# Step 13: Mission Control - Multi-Agent Observability

> **2026 Update**: Mission Control now tracks model tier usage per agent and integrates with the continuous review system. Dashboard at apps/observability/. See [../docs/2026_UPGRADE_GUIDE.md](../docs/2026_UPGRADE_GUIDE.md).

## The Real-Time Command Center

**You have**: Autonomous agent fleets (Steps 11-12), Z-Threads, Living Software
**Missing**: Visibility into what agents are doing in real-time

**This step**: Build a real-time dashboard to monitor every agent, tool call, and event across your entire fleet.

---

## What is Mission Control?

**Definition**: A real-time dashboard that shows you **exactly what every agent is doing**, their costs, tool usage, and status - without digging through text logs.

### Before Mission Control
```
You have agents running but:
❌ No visibility into what they're doing
❌ Can't see which tools they're using
❌ No cost tracking
❌ Text logs are overwhelming
❌ Can't debug multi-agent workflows
❌ Don't know when agents start/stop
```

### After Mission Control
```
Real-time dashboard showing:
✅ Every active agent (swimlane view)
✅ Current status (Planning, Building, Testing, etc.)
✅ Tool calls in real-time
✅ Token usage and costs
✅ Agent lifecycle (start, stop, subagent spawning)
✅ Event timeline
✅ Session filtering
✅ WebSocket live updates
```

---

## Architecture

### Data Flow

```
┌──────────────────────────────────────────────────────┐
│  Claude Agents (Your Fleet)                          │
│  ├─ Orchestrator Agent                               │
│  ├─ Researcher Agent                                 │
│  ├─ Builder Agent (E2B sandbox)                      │
│  └─ Tester Agent                                     │
└──────────────────────────────────────────────────────┘
                    │
                    │ (Hooks as Sensors)
                    ↓
┌──────────────────────────────────────────────────────┐
│  Hook Scripts (send_event.py)                        │
│  ├─ PreToolUse                                       │
│  ├─ PostToolUse                                      │
│  ├─ SubagentStart                                    │
│  ├─ SubagentStop                                     │
│  └─ ... (12 hook events total)                       │
└──────────────────────────────────────────────────────┘
                    │
                    │ (HTTP POST)
                    ↓
┌──────────────────────────────────────────────────────┐
│  Bun Server (Port 4000)                              │
│  ├─ Receives hook events                             │
│  ├─ Stores in SQLite database                        │
│  └─ Broadcasts via WebSocket                         │
└──────────────────────────────────────────────────────┘
                    │
                    │ (WebSocket + REST API)
                    ↓
┌──────────────────────────────────────────────────────┐
│  Vue Dashboard (Port 5173)                           │
│  ├─ Real-time event stream                           │
│  ├─ Agent swimlanes                                  │
│  ├─ Token/cost tracking                              │
│  └─ Session filtering                                │
└──────────────────────────────────────────────────────┘
```

---

## Installation

The system is already installed at:
```
~/Documents/claude-code-hooks-multi-agent-observability/
```

### Verify Installation

```bash
cd ~/Documents/claude-code-hooks-multi-agent-observability
ls -la

# You should see:
# - apps/server/    (Bun server)
# - apps/client/    (Vue dashboard)
# - .claude/hooks/  (Hook scripts)
# - scripts/        (Start/stop scripts)
```

---

## Starting Mission Control

### Method 1: Quick Start (Recommended)

```bash
cd ~/Documents/claude-code-hooks-multi-agent-observability
./scripts/start-system.sh
```

**What happens**:
1. Kills any existing processes on ports 4000, 5173
2. Starts Bun server on port 4000
3. Starts Vue client on port 5173
4. Opens browser to http://localhost:5173

### Method 2: Manual Start

**Terminal 1 (Server)**:
```bash
cd ~/Documents/claude-code-hooks-multi-agent-observability/apps/server
bun install
bun run dev
```

**Terminal 2 (Client)**:
```bash
cd ~/Documents/claude-code-hooks-multi-agent-observability/apps/client
bun install
bun run dev
```

### Method 3: Background Service (Always-On)

**macOS (LaunchAgent)**:

Create: `~/Library/LaunchAgents/com.mission-control.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.mission-control</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/yourusername/Documents/claude-code-hooks-multi-agent-observability/scripts/start-system.sh</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
</dict>
</plist>
```

Load:
```bash
launchctl load ~/Library/LaunchAgents/com.mission-control.plist
```

**Result**: Mission Control starts automatically on login and stays running.

---

## Dashboard Features

### 1. Agent Swimlanes

Each active agent gets its own swimlane showing:
- **Agent Name** (Orchestrator, Researcher, Builder, etc.)
- **Current Status** (Planning, Building, Testing, Deploying, etc.)
- **Session ID** (for filtering)
- **Tool Calls** (Read, Write, Edit, Bash, Task, etc.)
- **Timeline** (when events occurred)

### 2. Real-Time Event Stream

Live events appear instantly via WebSocket:
- **PreToolUse**: Agent about to call a tool
- **PostToolUse**: Tool call completed
- **SubagentStart**: New agent spawned
- **SubagentStop**: Agent completed
- **UserPromptSubmit**: User sent a message
- **... (12 event types total)**

### 3. Token & Cost Tracking

Dashboard tracks:
- **Total tokens used** (input + output)
- **Cost per agent** (based on model pricing)
- **Cost per session** (aggregate)
- **Cost over time** (trending)

### 4. Session Filtering

Filter view by:
- **Session ID** (focus on specific workflow)
- **Agent Name** (focus on specific agent)
- **Event Type** (focus on tool calls, errors, etc.)
- **Time Range** (last hour, today, etc.)

### 5. Tool Call Details

Click any tool call to see:
- **Tool name** (Read, Write, Bash, etc.)
- **Input parameters**
- **Output results**
- **Duration** (how long it took)
- **Status** (success/failure)

---

## Hook Configuration

Your hooks are already configured in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [{
      "hooks": [
        {
          "type": "command",
          "command": "uv run /path/to/hooks/pre_tool_use.py"
        },
        {
          "type": "command",
          "command": "uv run /path/to/hooks/send_event.py --source-app global-system --event-type PreToolUse --summarize"
        }
      ]
    }],
    "PostToolUse": [{
      "hooks": [
        {
          "type": "command",
          "command": "uv run /path/to/hooks/post_tool_use.py"
        },
        {
          "type": "command",
          "command": "uv run /path/to/hooks/send_event.py --source-app global-system --event-type PostToolUse --summarize"
        }
      ]
    }],
    // ... (all 12 hook events configured)
  }
}
```

**Key Parameter**: `--source-app global-system`
- This identifies your project in the dashboard
- Change to different names for different projects

---

## Using Mission Control

### Workflow 1: Monitor Agent Teams

**Start Mission Control**:
```bash
cd ~/Documents/claude-code-hooks-multi-agent-observability
./scripts/start-system.sh
```

**Run Agent Team**:
```bash
# In separate terminal
claude

# In conversation:
/orchestrate "Implement OAuth2 authentication"
```

**Watch in Dashboard**:
1. Orchestrator appears (swimlane)
2. Spawns Researcher agent (new swimlane)
3. Spawns Security Analyst agent (new swimlane)
4. Spawns Builder agent (new swimlane)
5. Watch tool calls in real-time (Read, Edit, Write, Bash)
6. See status changes (Planning → Building → Testing)
7. Track token usage per agent
8. View completion status

**Time**: Real-time visibility into entire workflow

---

### Workflow 2: Monitor Z-Thread

**Start Mission Control**:
```bash
./scripts/start-system.sh
```

**Run Z-Thread**:
```bash
/z-thread implement-feature "Add two-factor authentication"
```

**Watch in Dashboard**:
1. Research stage (Researcher agent)
2. Security stage (Security agent, parallel)
3. Implementation stage (Builder agent in E2B sandbox)
4. Testing stage (Tester agent)
5. Security scan stage (Scanner agent)
6. Deployment stage (Deployer agent)
7. Monitoring stage (Monitor agent)
8. Report stage (Reporter agent)

**Total visibility**: Every stage, every tool call, every decision

---

### Workflow 3: Debug Failed Agent

**Scenario**: Builder agent fails during implementation

**Mission Control Shows**:
1. **Agent swimlane** turns red (error)
2. **Last tool call** shows error details
3. **Event timeline** shows exactly when it failed
4. **PostToolUseFailure** hook captures error
5. **Click event** to see full error message

**Debug**:
- See which file it was editing (Read tool shows file_path)
- See what command failed (Bash tool shows command)
- See error message (PostToolUseFailure shows details)

**Result**: Instant debugging instead of searching logs

---

## Generative UI (Advanced)

### What is Generative UI?

Instead of agents outputting markdown text, they output **HTML/React components** that render as interactive dashboards.

### Example: Performance Report

**Traditional Output** (Markdown):
```markdown
## Performance Report

- Endpoint: /api/checkout
- P95 Latency: 850ms
- Error Rate: 0.2%
- Recommendation: Add database index on orders.user_id
```

**Generative UI Output** (HTML):
```html
<div class="performance-dashboard">
  <h2>Performance Report</h2>
  <div class="metric-card critical">
    <h3>/api/checkout</h3>
    <div class="latency">
      <span class="value">850ms</span>
      <span class="label">P95 Latency</span>
      <progress value="850" max="500"></progress>
    </div>
    <div class="error-rate">
      <span class="value">0.2%</span>
      <span class="label">Error Rate</span>
    </div>
  </div>
  <div class="recommendation">
    <h4>🔧 Recommended Fix</h4>
    <pre><code>CREATE INDEX idx_orders_user_id ON orders(user_id);</code></pre>
    <button onclick="applyFix()">Apply Fix</button>
  </div>
  <div class="before-after">
    <canvas id="latency-chart"></canvas>
  </div>
</div>
```

**Result**: Interactive dashboard instead of text report

---

### How to Enable Generative UI

**Step 1: Update Agent Prompt**

Add to agent definition (e.g., `~/.claude/agents/performance.md`):

```markdown
---
name: performance
output_format: html
---

# Performance Agent

## Output Style

You MUST output HTML instead of markdown for all reports.

### HTML Guidelines:
1. Use semantic HTML5 elements
2. Include inline CSS for styling
3. Add interactive elements (buttons, charts)
4. Use color coding (red=critical, yellow=warning, green=good)

### Template:
```html
<div class="report-container">
  <h1>Report Title</h1>
  <div class="metrics">
    <!-- Metrics cards -->
  </div>
  <div class="visualization">
    <!-- Charts using Chart.js -->
  </div>
  <div class="actions">
    <!-- Action buttons -->
  </div>
</div>
```

Your reports should be **interactive dashboards**, not static text.
```

**Step 2: Mission Control Renders HTML**

The Mission Control dashboard automatically detects HTML output and renders it:

```javascript
// Dashboard detects HTML in agent output
if (isHTML(agentOutput)) {
  renderHTMLComponent(agentOutput);
} else {
  renderMarkdown(agentOutput);
}
```

---

### Generative UI Examples

#### Example 1: Security Audit Dashboard

**Agent Output**:
```html
<div class="security-audit">
  <h2>Security Audit Results</h2>
  <div class="severity-summary">
    <div class="critical">
      <span class="count">3</span>
      <span class="label">Critical</span>
    </div>
    <div class="warning">
      <span class="count">12</span>
      <span class="label">Warnings</span>
    </div>
    <div class="info">
      <span class="count">25</span>
      <span class="label">Info</span>
    </div>
  </div>
  <div class="issues-list">
    <div class="issue critical" data-file="api/auth.py">
      <h3>🔴 SQL Injection Vulnerability</h3>
      <p>Line 42: User input not sanitized</p>
      <pre><code>cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")</code></pre>
      <button onclick="showFix('issue-1')">Show Fix</button>
    </div>
    <!-- More issues -->
  </div>
</div>
```

**Result**: Interactive security dashboard with clickable issues

---

#### Example 2: Test Coverage Heatmap

**Agent Output**:
```html
<div class="coverage-heatmap">
  <h2>Test Coverage</h2>
  <div class="overall-stats">
    <div class="stat">
      <span class="value">87%</span>
      <span class="label">Total Coverage</span>
    </div>
  </div>
  <div class="file-grid">
    <div class="file" data-coverage="95" style="background: #00ff00">
      api/auth.py
    </div>
    <div class="file" data-coverage="45" style="background: #ff0000">
      api/payments.py
    </div>
    <!-- Color-coded by coverage -->
  </div>
  <canvas id="coverage-trend"></canvas>
</div>
```

**Result**: Visual heatmap of test coverage

---

#### Example 3: Performance Timeline

**Agent Output**:
```html
<div class="performance-timeline">
  <h2>Performance Optimization</h2>
  <div class="before-after">
    <div class="before">
      <h3>Before</h3>
      <div class="metric">850ms</div>
    </div>
    <div class="arrow">→</div>
    <div class="after">
      <h3>After</h3>
      <div class="metric">220ms</div>
    </div>
  </div>
  <div class="improvement">74% faster</div>
  <canvas id="latency-timeline"></canvas>
</div>
```

**Result**: Before/after visualization with charts

---

## Integration with Steps 1-12

### Mission Control Enhances Every Step

**Step 11 (Agent Teams)**:
```bash
/orchestrate "Implement OAuth2"

# Mission Control shows:
# - Orchestrator planning (thinking)
# - Researcher spawned (SubagentStart)
# - Researcher reading docs (Read tool)
# - Builder spawned (SubagentStart)
# - Builder implementing (Edit, Write tools)
# - Real-time visibility into entire team
```

**Step 12 (Z-Threads)**:
```bash
/z-thread implement-feature "Add 2FA"

# Mission Control shows:
# - All 9 stages in swimlanes
# - Parallel execution visible
# - Blocking stages highlighted
# - Rollback triggers visible
# - Complete workflow transparency
```

**Drop Zones (Step 9)**:
```bash
# Drop file in zone

# Mission Control shows:
# - File detected event
# - Agent spawned
# - Processing stages
# - Completion status
```

---

## Advanced Features

### 1. Custom Metrics

Add custom metrics to dashboard:

```python
# In agent code or hooks
import requests

requests.post('http://localhost:4000/metrics', json={
    'name': 'deployment_success_rate',
    'value': 0.96,
    'timestamp': datetime.now().isoformat(),
    'labels': {
        'environment': 'production',
        'feature': 'oauth2'
    }
})
```

Dashboard shows custom metrics alongside agent events.

---

### 2. Alerts & Notifications

Configure alerts for critical events:

```json
{
  "alerts": [
    {
      "condition": "error_rate > 0.1",
      "action": "slack",
      "channel": "#alerts"
    },
    {
      "condition": "cost_per_session > 5.00",
      "action": "email",
      "to": "admin@company.com"
    }
  ]
}
```

---

### 3. Historical Analysis

Query past sessions:

```bash
# Via API
curl http://localhost:4000/sessions?start=2024-01-01&end=2024-01-31

# Get session details
curl http://localhost:4000/sessions/<session-id>

# Export to CSV
curl http://localhost:4000/export?format=csv&session=<id>
```

---

### 4. Multi-Project Monitoring

Monitor multiple projects simultaneously:

```json
// Project 1: Frontend
{
  "--source-app": "frontend-app"
}

// Project 2: API
{
  "--source-app": "api-server"
}

// Dashboard shows both with color coding
```

---

## Cost Tracking

### Token Pricing (Example)

```javascript
const pricing = {
  'opus': {
    input: 0.015,   // per 1k tokens
    output: 0.075   // per 1k tokens
  },
  'sonnet': {
    input: 0.003,
    output: 0.015
  },
  'haiku': {
    input: 0.00025,
    output: 0.00125
  }
};
```

### Dashboard Calculations

```
Total Cost = Σ (input_tokens * input_price + output_tokens * output_price)
Per Agent Cost = Cost for all events by agent
Per Session Cost = Cost for all events in session
```

**Example**:
```
Agent: Builder (sonnet)
Input: 15,000 tokens × $0.003 = $0.045
Output: 5,000 tokens × $0.015 = $0.075
Total: $0.12
```

---

## Troubleshooting

### Issue: Dashboard not receiving events

**Check**:
1. Is server running? `curl http://localhost:4000/health`
2. Are hooks sending events? Check `.claude/hooks/send_event.py`
3. Is `--source-app` parameter set in settings.json?

**Solution**:
```bash
# Check server logs
cd ~/Documents/claude-code-hooks-multi-agent-observability/apps/server
bun run dev

# Check hook execution
uv run .claude/hooks/send_event.py --test
```

---

### Issue: WebSocket disconnected

**Cause**: Server restarted or network issue

**Solution**: Dashboard auto-reconnects. Refresh page if needed.

---

### Issue: Missing events

**Check**: Ensure all hook types are configured in settings.json:
- PreToolUse
- PostToolUse
- SubagentStart
- SubagentStop
- Notification
- Stop
- UserPromptSubmit
- PreCompact
- SessionStart
- SessionEnd
- PermissionRequest
- PostToolUseFailure

---

## Summary

### What You've Built

- ✅ **Real-Time Dashboard**: See every agent, tool call, and event
- ✅ **Agent Swimlanes**: Visual representation of agent activities
- ✅ **Cost Tracking**: Token usage and costs per agent/session
- ✅ **Event Filtering**: Focus on specific agents, sessions, or events
- ✅ **Generative UI**: Agents output interactive dashboards
- ✅ **Historical Analysis**: Query past sessions and events

### The Complete Stack

```
Step 1-5: Context Engineering (efficiency)
    ↓
Step 8-9: Multi-Agent + Drop Zones (automation)
    ↓
Step 10: Agentic Layer (framework)
    ↓
Step 11: Agent Teams (coordination)
    ↓
Step 12: Z-Threads + Plugins (scale + autonomy)
    ↓
Step 13: Mission Control (observability) ✨
    ↓
Result: Fully observable, autonomous Living Software
```

### What This Enables

**Before**: Blind fleet management
- No visibility into agent activities
- Can't debug multi-agent workflows
- No cost tracking
- Text logs are overwhelming

**After**: Mission Control command center
- Real-time visibility into every agent
- Interactive debugging
- Live cost tracking
- Visual dashboards

---

**You now have Mission Control. Welcome to fully observable Living Software.** 🚀
