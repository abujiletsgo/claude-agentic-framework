---
name: security-scanner
description: "Lightweight security pattern scan of specific files or a small codebase for common vulnerabilities, misconfigurations, and unsafe patterns — no external tools required."
when_to_use: "Use for a quick single-file or offline security pass. For a full audit (STRIDE threat model, dependency supply chain, secrets archaeology, trend tracking), prefer the gstack `cso` skill when installed; use this as the lightweight fallback."
---

# Security Scanner Skill

Comprehensive security analysis covering code vulnerabilities, dependency issues, and configuration weaknesses.

## When to Use

- User asks for security audit, vulnerability scan, or security check
- Before production deployment
- After adding authentication or authorization code
- When handling user input or network operations

## Workflow

1. Scope: Determine full audit, targeted scan, deps-only, or secret detection
2. Code analysis: Scan for injection, auth gaps, data exposure, misconfig
3. Pattern detection: Grep for vulnerability patterns in code
4. Dependency audit: Run npm audit, pip-audit, cargo audit, govulncheck
5. Generate report: Severity levels, file locations, impact, remediation

## Vulnerability Categories

- Injection: SQL, XSS, command, path traversal, YAML/XML
- Authentication: Hardcoded creds, weak passwords, missing auth
- Data Exposure: Secrets in code, verbose errors, debug mode
- Configuration: CORS, headers, cookies, default credentials

## OWASP Top 10

Check for: Broken Access Control, Cryptographic Failures, Injection, Insecure Design, Security Misconfiguration, Vulnerable Components, Auth Failures, Data Integrity, Logging Failures, SSRF.

## Examples

### Example 1: Full Audit
Detect language, run code scans, audit deps, check configs, generate report.

### Example 2: Secret Detection
Grep for secret patterns, check config files, scan git history.
