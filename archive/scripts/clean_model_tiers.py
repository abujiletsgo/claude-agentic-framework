#\!/usr/bin/env python3
"""Clean model_tiers.yaml by removing ghost agent references."""
from pathlib import Path
import os

repo = Path(__file__).resolve().parent.parent

# Get actual agents on disk
root_agents = {p.stem for p in (repo / "global-agents").glob("*.md") if p.is_file()}
team_dir = repo / "global-agents" / "team"
team_agents = {p.stem for p in team_dir.glob("*.md") if p.is_file()} if team_dir.exists() else set()
all_agents = root_agents | team_agents

# Read and filter model_tiers.yaml
tiers_path = repo / "data" / "model_tiers.yaml"
content = tiers_path.read_text()
lines = content.split(chr(10))
out = []
in_agent_tiers = False
current_tier = None
removed = []

for line in lines:
    s = line.strip()
    if s == "agent_tiers:":
        in_agent_tiers = True
        out.append(line)
        continue
    if in_agent_tiers:
        if s in ("opus:", "sonnet:", "haiku:"):
            current_tier = s.rstrip(":")
            out.append(line)
            continue
        if s.startswith("- ") and current_tier:
            agent_name = s[2:].split("#")[0].strip()
            if agent_name in all_agents:
                out.append(line)
            else:
                removed.append(f"{current_tier}/{agent_name}")
            continue
        if s and not s.startswith("#") and not s.startswith("-"):
            in_agent_tiers = False
            current_tier = None
    out.append(line)

# Update tier counts in comments
new_content = chr(10).join(out)

# Fix the tier count comments
opus_count = sum(1 for r in removed if not r.startswith("opus/"))
# Actually let us just write it cleanly
tiers_path.write_text(new_content)

print(f"Removed {len(removed)} ghost agents from model_tiers.yaml:")
for r in removed:
    print(f"  - {r}")
