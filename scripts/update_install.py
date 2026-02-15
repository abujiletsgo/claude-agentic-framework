#!/usr/bin/env python3
from pathlib import Path
repo = Path(__file__).resolve().parent.parent
install = repo / "install.sh"
text = install.read_text()
ll = text.split(chr(10))
out = []
for line in ll:
    line = line.replace("[1/5]", "[1/7]")
    line = line.replace("[2/5]", "[2/7]")
    line = line.replace("[3/5]", "[3/7]")
    line = line.replace("[4/6]", "[4/7]")
    line = line.replace("[5/6]", "[5/7]")
    line = line.replace("[6/6]", "[7/7]")
    line = line.replace("# 6. Verify", "# 7. Verify")
    if line.strip() == "# 7. Verify dependencies":
        out.append("# 6. Generate documentation from repo state")
        q = chr(34)
        d = chr(36)
        out.append("echo " + q + "[6/7] Generating docs..." + q)
        out.append("if command -v uv >/dev/null 2>&1; then")
        out.append("  uv run " + q + d + "REPO_DIR/scripts/generate_docs.py" + q)
        out.append("else")
        out.append("  python3 " + q + d + "REPO_DIR/scripts/generate_docs.py" + q)
        out.append("fi")
        out.append("")
    out.append(line)
install.write_text(chr(10).join(out))
print("Updated install.sh")
