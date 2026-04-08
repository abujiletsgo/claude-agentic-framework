---
name: Security Scanner
version: 0.1.0
description: "This skill should be used when the user asks for a security audit, vulnerability scan, or security hardening. It scans code for security vulnerabilities, misconfigurations, and unsafe patterns."
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
