---
name: buddy
description: "Switch your dashboard companion. Available buddies: cat (Neko), dog (Byte), owl (Sage), ghost (Cinder), robot (Chip). Trigger on '/buddy', 'switch buddy', 'change companion'."
user-invocable: true
---

# /buddy — Dashboard Companion Manager

Switch the animated companion in your cteam dashboard.

## Usage

```
/buddy              # Show current buddy + list all available
/buddy cat          # Switch to Neko the cat
/buddy dog          # Switch to Byte the dog
/buddy owl          # Switch to Sage the owl
/buddy ghost        # Switch to Cinder the ghost
/buddy robot        # Switch to Chip the robot
```

## Available Buddies

| Key | Name | Personality |
|-----|------|------------|
| cat | Neko | Chill, curious, occasionally knocks things off the table |
| dog | Byte | Enthusiastic, supportive, doesn't understand code but believes in you |
| owl | Sage | Wise, observant, slightly judgemental |
| ghost | Cinder | Mysterious, sees dead code, haunts buggy sprints |
| robot | Chip | Logical, efficient, speaks in beep-boop |

## Implementation

Read the argument. Write the selection to `.claude/buddy.json`:

```bash
# Get argument
BUDDY="${1:-}"

if [[ -z "$BUDDY" ]]; then
  # Show current + list
  CURRENT=$(python3 -c "
import json; print(json.load(open('$HOME/Documents/caf-team/.claude/buddy.json')).get('active','cat'))
" 2>/dev/null || echo "cat")
  echo "Current buddy: $CURRENT"
  echo ""
  echo "Available: cat (Neko), dog (Byte), owl (Sage), ghost (Cinder), robot (Chip)"
  echo "Switch: /buddy <name>"
  exit 0
fi

# Validate
VALID="cat dog owl ghost robot"
if ! echo "$VALID" | grep -qw "$BUDDY"; then
  echo "Unknown buddy: $BUDDY"
  echo "Available: $VALID"
  exit 1
fi

# Write selection — buddy widget auto-reloads from this file
python3 -c "
import json
from pathlib import Path
f = Path('$HOME/Documents/caf-team/.claude/buddy.json')
f.parent.mkdir(parents=True, exist_ok=True)
f.write_text(json.dumps({'active': '$BUDDY'}) + '\n')
"

echo "Switched to $BUDDY! The dashboard buddy pane will update automatically."
```

The buddy widget (`bin/cteam-buddy`) polls `.claude/buddy.json` every tick and switches live — no restart needed.

## Interactions

The buddy reacts to system state:
- **Idle**: random chatter, stretching, sleeping after long inactivity
- **Sprint start**: excited/alert
- **Sprint running**: watches agents, comments on builds
- **Sprint done**: celebrates
- **Sprint failed**: reacts to errors
- **Click/pet**: happy response

You can also interact in the buddy pane directly:
- **Click** the buddy to pet it
- **Tab** to cycle through buddies
- **1-5** to jump to a specific buddy
- **Click** a name at the bottom to switch
