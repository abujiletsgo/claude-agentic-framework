import os, sys
base = "/Users/tomkwon/Documents/claude-agentic-framework/global-skills"
data_dir = os.path.dirname(os.path.abspath(__file__))
for name in ["project-scaffolder", "refactoring-assistant", "security-scanner"]:
    src = os.path.join(data_dir, f"{name}.md")
    dst = os.path.join(base, name, "SKILL.md")
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(src) as r, open(dst, "w") as w:
            w.write(r.read())
        print(f"Created {dst}")
    else:
        print(f"Missing {src}", file=sys.stderr)
