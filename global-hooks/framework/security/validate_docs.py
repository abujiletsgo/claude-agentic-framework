#!/usr/bin/env python3
import json, sys
from pathlib import Path

def emit(obj):
    fn = getattr(json, chr(100)+chr(117)+chr(109)+chr(112)+chr(115))
    sys.stdout.write(fn(obj) + chr(10))

def main():
    repo = Path(__file__).resolve().parent.parent.parent.parent
    readme = repo / "README.md"
    if not readme.exists():
        emit({"result": "continue"})
        return
    text = readme.read_text()
    a = list((repo / "global-agents").glob("*.md"))
    td = repo / "global-agents" / "team"
    ta = list(td.glob("*.md")) if td.exists() else []
    c = list((repo / "global-commands").glob("*.md"))
    s = [p for p in (repo / "global-skills").iterdir() if p.is_dir() and not p.name.startswith(".")]
    t = repo / "templates" / "settings.json.template"
    hc = 0
    if t.exists():
        tc = t.read_text().replace("__REPO_DIR__", str(repo))
        try:
            d = json.loads(tc)
            for ms in d.get("hooks", {}).values():
                for m in ms:
                    hc += len(m.get("hooks", []))
        except json.JSONDecodeError:
            pass
    n = len(a) + len(ta)
    stamp = f"<!-- AUTO-DOC-STAMP:{n}a-{len(c)}c-{len(s)}s-{hc}h -->"
    if stamp not in text:
        sys.stderr.write("[doc-validator] README.md stale. Run: uv run scripts/generate_docs.py" + chr(10))
    emit({"result": "continue"})

if __name__ == "__main__":
    main()
