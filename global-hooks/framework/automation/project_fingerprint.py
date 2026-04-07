#!/usr/bin/env python3
"""CwdChanged hook: auto-detect project stack, inject fingerprint context.
Saves to ~/.claude/data/project_fingerprints/ for cross-session memory. Always exit 0."""

import hashlib, json, os, sys
from pathlib import Path


def _json(p: Path) -> dict:
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}


def _has(p: Path, s: str) -> bool:
    try: return s in p.read_text(encoding="utf-8", errors="ignore")
    except Exception: return False


def detect_stack(d: Path):
    """Returns (language, framework, package_manager) or None."""
    pkg = d / "package.json"
    if pkg.exists():
        deps = {**_json(pkg).get("dependencies", {}), **_json(pkg).get("devDependencies", {})}
        fw = "Node.js"
        for name, label in [("next","Next.js"),("react","React"),("vue","Vue"),
                            ("@angular/core","Angular"),("express","Express"),("svelte","Svelte"),("nuxt","Nuxt")]:
            if name in deps: fw = label; break
        pm = "pnpm" if (d/"pnpm-lock.yaml").exists() else "yarn" if (d/"yarn.lock").exists() \
             else "bun" if (d/"bun.lockb").exists() else "npm"
        return "JavaScript/TypeScript", fw, pm
    if any((d/f).exists() for f in ["pyproject.toml","setup.py","requirements.txt"]):
        fw = "Python"
        for marker, label in [("django","Django"),("flask","Flask"),("fastapi","FastAPI"),("starlette","Starlette")]:
            for f in ["pyproject.toml","requirements.txt","setup.py"]:
                if (d/f).exists() and _has(d/f, marker): fw = label; break
            if fw != "Python": break
        pm = "uv" if (d/"uv.lock").exists() else "poetry" if (d/"poetry.lock").exists() else "pip"
        return "Python", fw, pm
    simple = [("Cargo.toml","Rust","Rust","cargo"),("go.mod","Go","Go","go"),
              ("pom.xml","Java","Maven","maven"),("Gemfile","Ruby","Ruby","bundler"),
              ("Package.swift","Swift","Swift Package","swift")]
    for marker, lang, fw, pm in simple:
        if (d/marker).exists(): return lang, fw, pm
    if (d/"build.gradle").exists() or (d/"build.gradle.kts").exists():
        return "Java", "Gradle", "gradle"
    return None


def detect_tests(d: Path, lang: str) -> str:
    if lang.startswith("JavaScript"):
        deps = {**_json(d/"package.json").get("dependencies",{}), **_json(d/"package.json").get("devDependencies",{})}
        for k in ["vitest","jest"]:
            if k in deps: return k
        return "unknown"
    if lang == "Python":
        for f in ["pyproject.toml","setup.cfg","pytest.ini","conftest.py"]:
            if (d/f).exists() and (f == "conftest.py" or _has(d/f, "pytest")): return "pytest"
        return "tox" if (d/"tox.ini").exists() else "unittest"
    return {"Rust":"cargo test","Go":"go test","Java":"junit",
            "Ruby":"rspec" if (d/".rspec").exists() else "minitest"}.get(lang, "unknown")


def detect_ci(d: Path) -> str:
    for path, name in [(".github/workflows","GitHub Actions"),(".gitlab-ci.yml","GitLab CI"),
                       ("Jenkinsfile","Jenkins"),(".circleci","CircleCI")]:
        p = d / path
        if p.is_dir() or p.is_file(): return name
    return "none"


def detect_db(d: Path) -> str:
    if (d/"prisma").is_dir(): return "Prisma"
    if (d/"migrations").is_dir() or (d/"alembic").is_dir(): return "SQL (migrations)"
    if (d/".env").exists() and _has(d/".env", "DATABASE_URL"): return "yes (DATABASE_URL)"
    return "none"


def main():
    try:
        cwd = Path(json.loads(sys.stdin.read()).get("cwd", os.getcwd()))
        if not cwd.is_dir():
            print(json.dumps({})); return
        result = detect_stack(cwd)
        if not result:
            print(json.dumps({})); return
        lang, fw, pm = result
        tr, ci, db = detect_tests(cwd, lang), detect_ci(cwd), detect_db(cwd)
        fp = dict(language=lang, framework=fw, test_runner=tr, ci_cd=ci, database=db, package_manager=pm)
        # Persist for cross-session memory
        store = Path.home() / ".claude" / "data" / "project_fingerprints"
        store.mkdir(parents=True, exist_ok=True)
        h = hashlib.sha256(str(cwd.resolve()).encode()).hexdigest()[:12]
        (store / f"{h}.json").write_text(json.dumps({"cwd": str(cwd.resolve()), **fp}, indent=2))
        summary = f"Project fingerprint: {lang} + {fw}, tests: {tr}, CI: {ci}, DB: {db}, pkg: {pm}"
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "CwdChanged", "additionalContext": summary}}))
    except Exception as e:
        print(f"project_fingerprint error (non-blocking): {e}", file=sys.stderr)
        print(json.dumps({}))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
