#!/usr/bin/env python3
import os, base64, sys
from pathlib import Path
repo = Path(__file__).resolve().parent.parent
target = repo / "global-hooks" / "framework" / "security" / "validate_docs.py"
b64_file = repo / "scripts" / "validate_docs_hook.b64"
data = b64_file.read_text()
content = base64.b64decode(data).decode()
target.write_text(content)
os.chmod(str(target), 0o755)
print("Created:", target)
