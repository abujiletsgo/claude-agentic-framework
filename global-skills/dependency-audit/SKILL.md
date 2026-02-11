---
name: Dependency Audit
version: 0.1.0
description: "This skill should be used when the user asks about dependency security, outdated packages, vulnerability scanning, or license compliance. It audits project dependencies for security vulnerabilities, outdated versions, and license issues."
---

# Dependency Audit Skill

Comprehensive dependency auditing: security vulnerabilities, version freshness, license compliance, and unused dependencies.

## When to Use

- User asks: "audit dependencies", "check for vulnerabilities", "update packages", "license check"
- Before deploying to production
- During security reviews
- Periodic maintenance

## Workflow

### Step 1: Detect Package Manager

```bash
# Check which package managers are in use
ls package.json pyproject.toml Cargo.toml go.mod Gemfile pom.xml 2>/dev/null
```

### Step 2: Security Audit

**Node.js**:
```bash
npm audit --json 2>/dev/null | head -100
# or
npx better-npm-audit audit
```

**Python**:
```bash
pip-audit 2>/dev/null || pip install pip-audit && pip-audit
# or check with safety
safety check 2>/dev/null
```

**Rust**:
```bash
cargo audit 2>/dev/null
```

**Go**:
```bash
govulncheck ./... 2>/dev/null
```

### Step 3: Version Freshness

Check for outdated dependencies:
```bash
# Node.js
npm outdated --json 2>/dev/null

# Python
pip list --outdated 2>/dev/null

# Rust
cargo outdated 2>/dev/null
```

### Step 4: License Compliance

```bash
# Node.js
npx license-checker --summary 2>/dev/null

# Python
pip-licenses 2>/dev/null
```

### Step 5: Unused Dependencies

```bash
# Node.js
npx depcheck 2>/dev/null

# Python - check imports vs installed
```

### Step 6: Generate Report

```markdown
## Dependency Audit Report

### Security Vulnerabilities
| Package | Severity | CVE | Fix Available |
|---------|----------|-----|---------------|
| ...     | ...      | ... | ...           |

### Outdated Packages
| Package | Current | Latest | Type |
|---------|---------|--------|------|
| ...     | ...     | ...    | ...  |

### License Issues
- Copyleft licenses in proprietary project: [list]
- Unknown licenses: [list]

### Unused Dependencies
- [list of unused packages]

### Recommendations
1. Critical: Update X immediately (CVE-YYYY-NNNN)
2. High: Update Y to fix security issue
3. Low: Remove unused dependency Z
```

## Examples

### Example 1: Full Audit
User: "Audit all dependencies in this project"

1. Detect package manager
2. Run security audit
3. Check outdated versions
4. Scan licenses
5. Find unused deps
6. Generate comprehensive report

### Example 2: Security-Only
User: "Any security vulnerabilities in our dependencies?"

1. Run security audit tool
2. Report critical and high severity issues
3. Provide remediation steps
