import os, stat
target = os.path.join(os.path.expanduser("~"), "Documents", "claude-agentic-framework", "global-hooks", "framework", "knowledge", "session_knowledge.py")
os.makedirs(os.path.dirname(target), exist_ok=True)
# Read template from sibling file
tmpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session_knowledge_template.py")
with open(tmpl) as r, open(target, "w") as w:
    w.write(r.read())
os.chmod(target, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
print(f"Created {target}")
