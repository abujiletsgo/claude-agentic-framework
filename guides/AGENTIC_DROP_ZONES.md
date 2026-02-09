# Agentic Drop Zones - Out-of-Loop Automation

## The Final Evolution

You've mastered the progression:

```
Step 1-5: Elite Context Engineering
    ↓
Step 8: Multi-Agent Orchestration
    ↓
Step 9: Agentic Drop Zones ✨
```

**From**: "In-Loop" (babysitting terminal, typing commands)
**To**: "Out-of-Loop" (drag file, walk away, find results later)

---

## What Are Drop Zones?

**File-system interfaces that trigger agent workflows automatically.**

```
Traditional (In-Loop):
  You: [Open terminal]
  You: [Type command]
  You: [Wait and watch]
  You: [Copy output]

Drop Zones (Out-of-Loop):
  You: [Drag file into folder]
  You: [Walk away]
  System: [Detects file, spawns agent, completes work]
  You: [Find results in _completed folder later]
```

**The Operating System IS your UI.**

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│   ~/drop-zones/                                 │
│   ├── refactor/         ← Drop code here       │
│   ├── image-gen/        ← Drop prompts here    │
│   ├── code-review/      ← Drop files here      │
│   └── training-data/    ← Drop CSVs here       │
└─────────────────────────────────────────────────┘
                  │
                  ↓
         [Watchdog Monitors]
                  │
                  ↓
         File Detected Event
                  │
                  ↓
┌──────────────────────────────────────────────────┐
│ drops.yaml Configuration                         │
│ - Pattern match: *.txt, *.csv, *.py             │
│ - Load template: .claude/commands/refactor.md   │
│ - Replace variable: FILE_PATH                    │
│ - Select agent: claude_code                      │
│ - Select model: sonnet                           │
└──────────────────────────────────────────────────┘
                  │
                  ↓
┌──────────────────────────────────────────────────┐
│ Agent Execution (Automatic)                      │
│ - Claude Code reads FILE_PATH                    │
│ - Executes predefined prompt                     │
│ - Streams response to console                    │
│ - Saves output to zone/_completed/              │
└──────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites (Already Done ✅)
- ✅ UV installed (`~/.local/bin/uv`)
- ✅ Claude Code available
- ✅ ANTHROPIC_API_KEY configured

### Step 1: Clone Repo

The repo is at: `/tmp/claude/agentic-drop-zones/`

To make it permanent, copy to your preferred location:

```bash
# Option 1: Copy to home directory
cp -r /tmp/claude/agentic-drop-zones ~/agentic-drop-zones

# Option 2: Copy to Documents
cp -r /tmp/claude/agentic-drop-zones ~/Documents/agentic-drop-zones
```

### Step 2: Setup Environment

```bash
cd ~/agentic-drop-zones  # Or wherever you copied it

# Create .env file
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
CLAUDE_CODE_PATH=claude
EOF

# Optional: Setup MCP servers (for advanced tools)
cp .mcp.json.sample .mcp.json
# Edit .mcp.json to add API keys for tools (Replicate, etc.)
```

### Step 3: Test Installation

```bash
cd ~/agentic-drop-zones

# Run the watcher
~/.local/bin/uv run sfs_agentic_drop_zone.py
```

You should see:
```
╔══════════════════════════════════════════╗
║     Agentic Drop Zone System Starting    ║
╚══════════════════════════════════════════╝

Monitoring zones:
  ✓ Echo Drop Zone (agentic_drop_zone/echo_zone)
  ✓ Image Generation Drop Zone
  ✓ Morning Debrief Zone
  ...

Watching for file drops...
```

### Step 4: Test with Example File

Open **new terminal** (keep watcher running):

```bash
cd ~/agentic-drop-zones

# Copy example file to trigger agent
cp example_input_files/echo.txt agentic_drop_zone/echo_zone/
```

Watch the original terminal - you'll see:
```
╔══════════════════════════════════════════╗
║  Echo Drop Zone - Processing             ║
╚══════════════════════════════════════════╝

File: echo.txt
Agent: claude_code (sonnet)

[Streaming response...]
```

---

## Configuration (drops.yaml)

### Basic Zone Structure

```yaml
drop_zones:
  - name: "Zone Display Name"
    file_patterns: ["*.txt", "*.md"]           # What files trigger
    reusable_prompt: ".claude/commands/task.md" # Prompt template
    zone_dirs: ["drop_folder_name"]            # Where to watch
    events: ["created"]                        # When to trigger
    agent: "claude_code"                       # Which agent
    model: "sonnet"                           # Which model
    color: "cyan"                             # Console color
    create_zone_dir_if_not_exists: true       # Auto-create folder
```

### Template Variables

Your prompt templates can use `FILE_PATH` variable:

**.claude/commands/refactor.md**:
```markdown
# Refactor Code

Read the file at: FILE_PATH

Refactor this code to:
1. Follow our style guide
2. Improve readability
3. Add type hints
4. Add docstrings

Save the refactored code to: FILE_PATH.refactored
```

When file `api.py` is dropped, `FILE_PATH` becomes `agentic_drop_zone/refactor/api.py`.

---

## Pre-Built Zones

The repo includes these ready-to-use zones:

### 1. **Echo Zone** (Test/Demo)
- **Trigger**: Drop `.txt` file
- **Action**: Echoes content back
- **Use**: Test that system works

### 2. **Image Generation Zone**
- **Trigger**: Drop `.txt` with image prompt
- **Action**: Generates image via Replicate API
- **Requires**: `REPLICATE_API_TOKEN` in .env
- **Output**: Generated images + metadata

### 3. **Image Edit Zone**
- **Trigger**: Drop `.json` with edit instructions
- **Action**: Edits images via AI
- **Requires**: Image URL + edit description

### 4. **Training Data Zone**
- **Trigger**: Drop `.csv` or `.jsonl`
- **Action**: Generates synthetic training data
- **Output**: Expanded dataset with new rows

### 5. **Morning Debrief Zone**
- **Trigger**: Drop audio file (`.mp3`, `.wav`, `.m4a`)
- **Action**: Transcribes with Whisper, extracts priorities/todos
- **Output**: Structured markdown debrief

### 6. **Finance Categorizer Zone**
- **Trigger**: Drop bank statement `.csv`
- **Action**: Auto-categorizes transactions
- **Output**: Categorized CSV

---

## Create Custom Zones

### Example: Code Review Zone

**Step 1: Create prompt template**

`.claude/commands/code_review.md`:
```markdown
# Code Review

Review the code at: FILE_PATH

Perform comprehensive code review:

## Security
- Check for SQL injection vulnerabilities
- Check for XSS vulnerabilities
- Check for auth bypass issues

## Quality
- Code complexity analysis
- Naming conventions
- Error handling

## Performance
- Inefficient queries
- Memory leaks
- N+1 problems

## Output Format
Create a markdown report at: FILE_PATH.review.md

Include:
- Severity ratings (🔴 Critical, 🟡 Warning, 🟢 Good)
- Specific line references
- Suggested fixes
```

**Step 2: Add to drops.yaml**

```yaml
drop_zones:
  # ... existing zones ...

  - name: "Code Review Zone"
    file_patterns: ["*.py", "*.js", "*.ts", "*.go"]
    reusable_prompt: ".claude/commands/code_review.md"
    zone_dirs: ["agentic_drop_zone/code_review"]
    events: ["created"]
    agent: "claude_code"
    model: "opus"  # Use opus for thorough review
    color: "red"
    create_zone_dir_if_not_exists: true
```

**Step 3: Use it**

```bash
# Drop any code file for automatic review
cp ~/projects/myapp/api.py ~/agentic-drop-zones/agentic_drop_zone/code_review/
```

Agent automatically:
1. Reads `api.py`
2. Performs comprehensive review
3. Creates `api.py.review.md` with findings

---

## Advanced: Multi-Agent Workflows

### Pattern: Best of N Code Solutions

Create 3 zones for same task, different models:

```yaml
drop_zones:
  - name: "Refactor Zone - Sonnet"
    file_patterns: ["*.py"]
    reusable_prompt: ".claude/commands/refactor.md"
    zone_dirs: ["agentic_drop_zone/refactor_sonnet"]
    agent: "claude_code"
    model: "sonnet"

  - name: "Refactor Zone - Opus"
    file_patterns: ["*.py"]
    reusable_prompt: ".claude/commands/refactor.md"
    zone_dirs: ["agentic_drop_zone/refactor_opus"]
    agent: "claude_code"
    model: "opus"

  - name: "Refactor Zone - Gemini"
    file_patterns: ["*.py"]
    reusable_prompt: ".claude/commands/refactor.md"
    zone_dirs: ["agentic_drop_zone/refactor_gemini"]
    agent: "gemini_cli"
    model: "gemini-2.5-pro"
```

**Usage**:
```bash
# Drop file in all 3 zones
cp code.py agentic_drop_zone/refactor_sonnet/
cp code.py agentic_drop_zone/refactor_opus/
cp code.py agentic_drop_zone/refactor_gemini/

# Get 3 different refactored versions
# Compare and pick best
```

---

## Integration with Elite Context Engineering

### The Complete Stack

```
Level 1: Context Reduction
  └─→ Strip permanent overhead

Level 2: On-Demand Priming
  └─→ /prime when entering new project

Level 3: Sub-Agent Delegation
  └─→ /research for heavy tasks

Level 4: Context Bundles
  └─→ /loadbundle for resilience

Level 5: Multi-Agent Orchestration
  └─→ E2B sandboxes for parallel agents

Level 6: Agentic Drop Zones ✨
  └─→ File-system automation (no chat needed)
```

### Workflow Example

**Before Drop Zones** (In-Loop):
```
8:00am: Open terminal
8:01am: Type: "Review yesterday's PRs"
8:02am: Wait for agent
8:10am: Copy review to Notion
8:11am: Type: "Generate training data"
8:12am: Wait for agent
8:20am: Download CSV
```

**After Drop Zones** (Out-of-Loop):
```
8:00am: Drop PR files in review_zone/
8:01am: Drop base CSV in training_zone/
8:02am: Go make coffee ☕
9:00am: Check _completed folders
        → All reviews done
        → Training data generated
```

**Time saved**: 18 minutes → 2 minutes (90% reduction)

---

## Safety Warnings

⚠️ **CRITICAL SAFETY NOTES**:

1. **Agents Run with Full Permissions**
   - Claude Code: `bypassPermissions` mode
   - All tools auto-approved
   - No confirmation dialogs

2. **Agents Can Modify Your System**
   - Read any file
   - Write any file
   - Execute any command
   - Delete files

3. **You Are Responsible**
   - Review prompt templates carefully
   - Test in safe directories first
   - Use sandboxes for untrusted code
   - Monitor the watcher terminal

4. **Best Practices**:
   - Start with `echo_zone` to test
   - Use specific directories (not `~/` or `/`)
   - Review templates before running
   - Monitor first few runs closely

---

## Troubleshooting

### Watcher Not Detecting Files

```bash
# Check zones are created:
ls -la agentic_drop_zone/

# Verify drops.yaml syntax:
cat drops.yaml

# Check file patterns match:
# If zone expects *.txt, don't drop *.md
```

### Agent Not Executing

```bash
# Verify API key:
echo $ANTHROPIC_API_KEY

# Check Claude Code path:
which claude

# Test manually:
claude "echo test"
```

### Permission Errors

```bash
# Ensure zone directories are writable:
chmod -R u+w agentic_drop_zone/

# Check script permissions:
chmod +x sfs_agentic_drop_zone.py
```

---

## Systemd Integration (Run as Service)

### Auto-start on Login

Create: `~/.config/systemd/user/agentic-drop-zones.service`

```ini
[Unit]
Description=Agentic Drop Zones Watcher
After=network.target

[Service]
Type=simple
WorkingDirectory=/Users/yourusername/agentic-drop-zones
ExecStart=/Users/yourusername/.local/bin/uv run sfs_agentic_drop_zone.py
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

Enable:
```bash
systemctl --user enable agentic-drop-zones.service
systemctl --user start agentic-drop-zones.service
```

---

## macOS LaunchAgent (Alternative)

Create: `~/Library/LaunchAgents/com.agentic.dropzones.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.agentic.dropzones</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/yourusername/.local/bin/uv</string>
    <string>run</string>
    <string>sfs_agentic_drop_zone.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/yourusername/agentic-drop-zones</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
</dict>
</plist>
```

Load:
```bash
launchctl load ~/Library/LaunchAgents/com.agentic.dropzones.plist
```

---

## Summary

### You've Achieved Out-of-Loop Automation

**Capabilities**:
- ✅ File-system triggers agent workflows
- ✅ Zero chat interface needed
- ✅ Automatic execution on file drop
- ✅ Multi-zone parallel processing
- ✅ Custom zones for any task
- ✅ Background service operation

**Use Cases**:
- Code review automation
- Training data generation
- Image generation/editing
- Audio transcription
- Financial categorization
- Refactoring pipelines
- Documentation generation
- Test generation
- ...literally anything an agent can do

**The Final Evolution**: Your OS is now an agentic interface. You've moved from "typing commands" to "dropping files". From "in-loop" to "out-of-loop".

**Welcome to True Agentic Automation.** 🚀
