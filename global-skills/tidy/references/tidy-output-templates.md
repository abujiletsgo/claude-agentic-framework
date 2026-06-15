# Tidy Output Templates

## Tidy Report (Phase 1 output)

The detection scan outputs a report with these sections:

```
## Tidy Report

### Project Type
- Layout source: CLAUDE.md `## Structure` section (or inferred from directories)
- Detected directories: src/, Data/, docs/, tests/, deploy/, assets/
- Protected root files: bot.py, monitor.py, dashboard.py, app.py, analysis.py, ...

### Misplaced Files (root)
- `results_2026-03-15.csv` → should be `Data/` (data file)
- `backtest_report.html` → should be `analysis/` or `reports/` (report)
- `new_agent.md` → should be `global-agents/new-agent.md` (framework agent)
- `my_script.py` → should be `scripts/my-script.py` (utility script)

### Cleanup Targets
- `__pycache__/` (3 found) → delete
- `*.pyc` (5 found) → delete

### Naming Violations
- `global-skills/MySkill/` → should be `global-skills/my-skill/`

### New This Session (untracked)
- `global-agents/solve.md` (new)
- `global-skills/solve/SKILL.md` (new)

### Candidates for Archive
- `docs/old-migration-guide.md` (last modified 120 days ago)

### Reference Impact
- Moving `new_agent.md` would break 0 references
- Moving `my_script.py` would break 2 references:
  - `install.sh:45` — `source my_script.py`
  - `README.md:120` — `see my_script.py`
```

## Doc Staleness Audit section (appended by Phase 4h)

```markdown
### Doc Staleness Audit
| Entity | Status | Referenced In | Action |
|--------|--------|---------------|--------|
| `old-module` | DELETED | docs/API.md:42, README.md:15 | Update or archive |
| "14 agents" | STALE COUNT | docs/guide.html:100 (actual: 11) | Update number |

⚠️ N stale references found. These require manual updates — prose can't be auto-generated.
```
