# This script creates the knowledge pipeline hook
import os, stat
target_dir = os.path.join(os.path.expanduser("~"), "Documents", "claude-agentic-framework", "global-hooks", "framework", "knowledge")
os.makedirs(target_dir, exist_ok=True)
target = os.path.join(target_dir, "session_knowledge.py")
# Read from base64 encoded content
import base64
encoded = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook_b64.txt")).read().strip()
with open(target, "w") as w:
    w.write(base64.b64decode(encoded).decode())
os.chmod(target, 0o755)
print(f"Created {target}")
