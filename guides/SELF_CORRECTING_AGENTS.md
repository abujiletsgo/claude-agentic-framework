# Self-Correcting Agents - The Z-Thread Trust Model

## The Trust Problem

**You have**: Z-Threads (Step 12) that can deploy autonomously
**Problem**: How do you **trust** them to deploy without review?

**Answer**: **Self-correcting agents** - agents that cannot finish until deterministic validators pass.

---

## The Core Principle

> **"Trust the System, not the Agent"**

You achieve Z-Threads by replacing **human review** with **deterministic scripts** that force agents to fix their own mistakes before they ever report "Task Complete".

---

## Architecture of Self-Correction

### The Two Validation Loops

```
┌─────────────────────────────────────────────────┐
│  Loop 1: Immediate Feedback (PostToolUse)       │
│  ├─ Agent: Edit file                            │
│  ├─ Hook: Run linter                            │
│  ├─ IF PASS: Continue                           │
│  └─ IF FAIL: Send error to agent → Agent fixes  │
│                                                  │
│  Frequency: Every Edit/Write (tight loop)       │
│  Purpose: Catch syntax errors immediately       │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  Loop 2: Quality Gate (Stop/SubagentStop)       │
│  ├─ Agent: Attempts to finish                   │
│  ├─ Hook: Run test suite                        │
│  ├─ IF PASS: Allow stop                         │
│  └─ IF FAIL: Block stop → Agent must fix        │
│                                                  │
│  Frequency: Once (at completion)                │
│  Purpose: Comprehensive validation              │
└─────────────────────────────────────────────────┘
```

---

## Implementation

### Directory Structure

```
.claude/
├── hooks/
│   └── validators/
│       ├── run_linter.py           # Syntax validation
│       ├── run_tests.py            # Test suite
│       ├── check_coverage.py       # Code coverage
│       ├── validate_json.py        # JSON format
│       ├── validate_sql.py         # SQL injection check
│       ├── check_imports.py        # Import validation
│       ├── check_types.py          # Type checking
│       └── security_scan.py        # Security vulnerabilities
```

---

## Loop 1: Immediate Feedback (PostToolUse)

### Configuration

**File**: `.claude/settings.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "uv run .claude/hooks/validators/run_linter.py",
            "timeout": 10
          },
          {
            "type": "command",
            "command": "uv run .claude/hooks/validators/validate_imports.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

### Validator Script: run_linter.py

**File**: `.claude/hooks/validators/run_linter.py`

```python
#!/usr/bin/env python3
"""
Immediate Linter Validation
Runs after every Edit/Write to catch syntax errors
"""

import json
import sys
import subprocess
from pathlib import Path

def lint_file(file_path):
    """Run appropriate linter based on file type"""

    file_path = Path(file_path)

    # Python files
    if file_path.suffix == '.py':
        try:
            # Run ruff (fast Python linter)
            result = subprocess.run(
                ['ruff', 'check', str(file_path)],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return {
                    "valid": False,
                    "errors": result.stdout,
                    "message": f"Linting failed for {file_path}"
                }
        except subprocess.TimeoutExpired:
            pass  # Don't block on timeout
        except FileNotFoundError:
            pass  # Linter not installed, skip

    # JavaScript/TypeScript files
    elif file_path.suffix in ['.js', '.ts', '.jsx', '.tsx']:
        try:
            result = subprocess.run(
                ['eslint', str(file_path)],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return {
                    "valid": False,
                    "errors": result.stdout,
                    "message": f"ESLint failed for {file_path}"
                }
        except:
            pass

    return {"valid": True}

def main():
    """Main validator entry point"""

    # Read tool input from stdin (provided by hook system)
    try:
        tool_input = json.loads(sys.stdin.read())
    except:
        sys.exit(0)  # No input, skip validation

    # Extract file path from Edit/Write tool input
    file_path = tool_input.get('file_path')
    if not file_path:
        sys.exit(0)  # No file path, skip

    # Run linter
    result = lint_file(file_path)

    if not result.get('valid', True):
        # Print error for agent to see
        print(json.dumps({
            "validation_failed": True,
            "file": file_path,
            "errors": result['errors'],
            "instruction": "Fix the linting errors above and try again."
        }, indent=2))

        sys.exit(1)  # Non-zero exit = validation failed

    sys.exit(0)  # Success

if __name__ == "__main__":
    main()
```

**Make executable**:
```bash
chmod +x .claude/hooks/validators/run_linter.py
```

### How It Works

```
1. Agent: Edits api/auth.py
   └─→ Introduces syntax error: "def login(user"  # Missing closing paren

2. PostToolUse Hook: Runs run_linter.py
   └─→ Detects: SyntaxError on line 42

3. Hook Output (sent to agent):
   {
     "validation_failed": true,
     "file": "api/auth.py",
     "errors": "SyntaxError: invalid syntax (line 42)",
     "instruction": "Fix the linting errors above and try again."
   }

4. Agent: Sees error, realizes mistake
   └─→ Fixes: "def login(user):"

5. PostToolUse Hook: Runs run_linter.py again
   └─→ Passes ✓

6. Agent: Continues with next step
```

**Result**: Agent **cannot proceed** with broken code.

---

## Loop 2: Quality Gate (Stop Hook)

### Configuration

**File**: `.claude/settings.json`

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run .claude/hooks/validators/run_tests.py",
            "timeout": 60
          },
          {
            "type": "command",
            "command": "uv run .claude/hooks/validators/check_coverage.py",
            "timeout": 30
          },
          {
            "type": "command",
            "command": "uv run .claude/hooks/validators/security_scan.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

### Validator Script: run_tests.py

**File**: `.claude/hooks/validators/run_tests.py`

```python
#!/usr/bin/env python3
"""
Quality Gate: Test Suite Validation
Blocks agent from finishing if tests fail
"""

import json
import sys
import subprocess
from pathlib import Path

def run_tests():
    """Run test suite and return results"""

    # Detect test framework
    if Path('pytest.ini').exists() or Path('pyproject.toml').exists():
        # Python: pytest
        try:
            result = subprocess.run(
                ['pytest', '-v', '--tb=short'],
                capture_output=True,
                text=True,
                timeout=60
            )

            return {
                "framework": "pytest",
                "passed": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "framework": "pytest",
                "passed": False,
                "errors": "Tests timed out after 60 seconds"
            }

    elif Path('package.json').exists():
        # JavaScript: npm test
        try:
            result = subprocess.run(
                ['npm', 'test'],
                capture_output=True,
                text=True,
                timeout=60
            )

            return {
                "framework": "npm",
                "passed": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "framework": "npm",
                "passed": False,
                "errors": "Tests timed out after 60 seconds"
            }

    # No test framework detected
    return {
        "framework": "none",
        "passed": True,
        "warning": "No test framework detected"
    }

def main():
    """Main quality gate"""

    print("🧪 Running test suite (Quality Gate)...")

    result = run_tests()

    if not result['passed']:
        # Tests failed - block agent from finishing
        print(json.dumps({
            "quality_gate_failed": True,
            "reason": "Tests failed",
            "framework": result['framework'],
            "output": result['output'],
            "errors": result['errors'],
            "instruction": (
                "TESTS FAILED. You cannot finish until all tests pass. "
                "Review the test failures above, fix the issues, and try again."
            )
        }, indent=2))

        sys.exit(1)  # Block agent from stopping

    print(f"✅ All tests passed ({result['framework']})")
    sys.exit(0)  # Allow agent to finish

if __name__ == "__main__":
    main()
```

### Validator Script: check_coverage.py

**File**: `.claude/hooks/validators/check_coverage.py`

```python
#!/usr/bin/env python3
"""
Quality Gate: Code Coverage Check
Ensures minimum test coverage (e.g., 80%)
"""

import json
import sys
import subprocess
import re

MINIMUM_COVERAGE = 80  # Configurable threshold

def check_coverage():
    """Run coverage check"""

    try:
        # Run pytest with coverage
        result = subprocess.run(
            ['pytest', '--cov=.', '--cov-report=term-missing'],
            capture_output=True,
            text=True,
            timeout=60
        )

        # Parse coverage percentage from output
        # Example line: "TOTAL  1234  567  54%"
        match = re.search(r'TOTAL.*?(\d+)%', result.stdout)

        if match:
            coverage = int(match.group(1))

            if coverage < MINIMUM_COVERAGE:
                return {
                    "passed": False,
                    "coverage": coverage,
                    "minimum": MINIMUM_COVERAGE,
                    "output": result.stdout
                }

            return {
                "passed": True,
                "coverage": coverage,
                "minimum": MINIMUM_COVERAGE
            }

    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "error": "Coverage check timed out"
        }
    except FileNotFoundError:
        # pytest-cov not installed, skip
        return {"passed": True, "skipped": True}

    return {"passed": True}

def main():
    """Main coverage gate"""

    print("📊 Checking test coverage (Quality Gate)...")

    result = check_coverage()

    if result.get('skipped'):
        print("⚠️  Coverage check skipped (pytest-cov not installed)")
        sys.exit(0)

    if not result['passed']:
        # Coverage too low - block agent
        print(json.dumps({
            "quality_gate_failed": True,
            "reason": "Insufficient test coverage",
            "coverage": result.get('coverage', 0),
            "minimum": result['minimum'],
            "output": result.get('output', ''),
            "instruction": (
                f"Test coverage is {result.get('coverage', 0)}%, "
                f"but minimum required is {result['minimum']}%. "
                "Add more tests to increase coverage before finishing."
            )
        }, indent=2))

        sys.exit(1)  # Block agent

    print(f"✅ Coverage: {result['coverage']}% (minimum: {result['minimum']}%)")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### Validator Script: security_scan.py

**File**: `.claude/hooks/validators/security_scan.py`

```python
#!/usr/bin/env python3
"""
Quality Gate: Security Vulnerability Scan
Checks for common security issues
"""

import json
import sys
import subprocess
from pathlib import Path

def scan_python_security():
    """Scan Python code for vulnerabilities"""

    try:
        # Run bandit (Python security linter)
        result = subprocess.run(
            ['bandit', '-r', '.', '-f', 'json'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            try:
                report = json.loads(result.stdout)

                # Count high/medium severity issues
                critical = [r for r in report.get('results', [])
                           if r.get('issue_severity') == 'HIGH']

                if critical:
                    return {
                        "passed": False,
                        "critical_issues": len(critical),
                        "details": critical[:5]  # First 5 issues
                    }
            except json.JSONDecodeError:
                pass

    except subprocess.TimeoutExpired:
        return {"passed": False, "error": "Security scan timed out"}
    except FileNotFoundError:
        # bandit not installed, skip
        return {"passed": True, "skipped": True}

    return {"passed": True}

def scan_javascript_security():
    """Scan JavaScript code for vulnerabilities"""

    try:
        # Run npm audit
        result = subprocess.run(
            ['npm', 'audit', '--json'],
            capture_output=True,
            text=True,
            timeout=30
        )

        try:
            report = json.loads(result.stdout)

            # Check for high/critical vulnerabilities
            vulnerabilities = report.get('metadata', {}).get('vulnerabilities', {})
            critical = vulnerabilities.get('critical', 0)
            high = vulnerabilities.get('high', 0)

            if critical > 0 or high > 0:
                return {
                    "passed": False,
                    "critical": critical,
                    "high": high,
                    "details": report.get('advisories', {})
                }
        except json.JSONDecodeError:
            pass

    except subprocess.TimeoutExpired:
        return {"passed": False, "error": "npm audit timed out"}
    except FileNotFoundError:
        return {"passed": True, "skipped": True}

    return {"passed": True}

def main():
    """Main security gate"""

    print("🔒 Running security scan (Quality Gate)...")

    # Detect project type and run appropriate scanner
    if Path('pyproject.toml').exists() or Path('setup.py').exists():
        result = scan_python_security()
    elif Path('package.json').exists():
        result = scan_javascript_security()
    else:
        print("⚠️  No recognized project type, skipping security scan")
        sys.exit(0)

    if result.get('skipped'):
        print("⚠️  Security scanner not installed, skipped")
        sys.exit(0)

    if not result['passed']:
        # Security issues found - block agent
        print(json.dumps({
            "quality_gate_failed": True,
            "reason": "Security vulnerabilities detected",
            "critical_issues": result.get('critical_issues', 0),
            "details": result.get('details', []),
            "instruction": (
                "SECURITY VULNERABILITIES FOUND. You cannot finish until "
                "all critical security issues are resolved. "
                "Review the issues above and fix them."
            )
        }, indent=2))

        sys.exit(1)  # Block agent

    print("✅ No critical security issues detected")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

---

## The Builder/Validator Team Pattern

For complex Z-Threads, use **specialized agent teams**:

### Configuration

```yaml
# z-threads/feature-implementation.yaml

stages:
  - stage: "implementation"
    agent: "builder"
    hooks:
      PostToolUse:
        - run_linter.py        # Immediate syntax check
        - validate_imports.py   # Import validation

  - stage: "validation"
    agent: "validator"
    task: |
      Review the implementation by Builder agent:

      1. Run comprehensive test suite
      2. Check code coverage (minimum 80%)
      3. Review code quality
      4. Scan for security vulnerabilities
      5. Validate edge cases

      If ANY issues found:
      - Document them clearly
      - Reject the implementation
      - Send back to Builder agent

      If ALL checks pass:
      - Approve for deployment

    hooks:
      Stop:
        - run_tests.py          # Test suite
        - check_coverage.py     # Coverage gate
        - security_scan.py      # Security gate
```

### How Builder/Validator Teams Work

```
┌─────────────────────────────────────────────────┐
│  Builder Agent                                  │
│  ├─ Focuses on implementation                   │
│  ├─ Has PostToolUse hooks (syntax checks)       │
│  └─ Reports: "Implementation complete"          │
└─────────────────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────┐
│  Validator Agent                                │
│  ├─ Reviews Builder's work                      │
│  ├─ Runs comprehensive tests                    │
│  ├─ Checks coverage, security, quality          │
│  ├─ Has Stop hooks (quality gates)              │
│  └─ Decision:                                   │
│      ├─ PASS → Approve deployment               │
│      └─ FAIL → Reject, send back to Builder     │
└─────────────────────────────────────────────────┘
                    │
                    ↓ (if approved)
┌─────────────────────────────────────────────────┐
│  Deployer Agent                                 │
│  ├─ Gradual rollout (1% → 100%)                 │
│  └─ Monitors metrics                            │
└─────────────────────────────────────────────────┘
```

---

## Real-World Z-Thread Example

### Scenario: Add Two-Factor Authentication

**User**: `/z-thread implement-feature "Add two-factor authentication"`

### Stage 1: Builder Agent

```
Builder: Starts implementation
  ├─ Edits: api/auth.py (adds 2FA logic)
  ├─ PostToolUse Hook: run_linter.py
  │   └─→ FAIL: Missing import for `pyotp`
  ├─ Builder: Sees error, adds import
  ├─ PostToolUse Hook: run_linter.py
  │   └─→ PASS ✓
  ├─ Writes: api/two_factor.py (2FA service)
  ├─ PostToolUse Hook: run_linter.py
  │   └─→ PASS ✓
  └─ Builder: Reports "Implementation complete"
```

### Stage 2: Validator Agent

```
Validator: Reviews implementation
  ├─ Attempts to finish (trigger Stop hook)
  ├─ Stop Hook: run_tests.py
  │   └─→ FAIL: 3 tests failing
  ├─ Validator: Blocked from finishing
  ├─ Validator: Analyzes failures:
  │   - test_two_factor_setup: AssertionError
  │   - test_two_factor_verify: KeyError
  │   - test_two_factor_backup: AttributeError
  ├─ Validator: Creates fixes
  │   ├─ Fix 1: Handle missing user.phone_number
  │   ├─ Fix 2: Add backup codes generation
  │   └─ Fix 3: Validate TOTP token format
  ├─ Validator: Attempts to finish again
  ├─ Stop Hook: run_tests.py
  │   └─→ PASS ✓ (all tests passing)
  ├─ Stop Hook: check_coverage.py
  │   └─→ PASS ✓ (85% coverage, minimum 80%)
  ├─ Stop Hook: security_scan.py
  │   └─→ PASS ✓ (no critical vulnerabilities)
  └─ Validator: Approves deployment
```

### Stage 3: Deployment

```
Deployer: Gradual rollout
  ├─ Deploy to 1% traffic
  ├─ Monitor for 5 minutes
  ├─ Deploy to 10% traffic
  ├─ Monitor for 5 minutes
  ├─ Deploy to 100% traffic
  └─ Reports: "2FA deployed successfully"
```

**Total Time**: 15 minutes
**Human Intervention**: ZERO
**Confidence**: HIGH (all quality gates passed)

---

## Complete Hook Configuration

**File**: `.claude/settings.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "uv run .claude/hooks/validators/run_linter.py",
            "timeout": 10,
            "description": "Immediate syntax validation"
          },
          {
            "type": "command",
            "command": "uv run .claude/hooks/validators/validate_imports.py",
            "timeout": 5,
            "description": "Import validation"
          },
          {
            "type": "command",
            "command": "uv run .claude/hooks/validators/check_types.py",
            "timeout": 10,
            "description": "Type checking (if mypy/typescript available)"
          }
        ]
      }
    ],

    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run .claude/hooks/validators/run_tests.py",
            "timeout": 60,
            "description": "Comprehensive test suite"
          },
          {
            "type": "command",
            "command": "uv run .claude/hooks/validators/check_coverage.py",
            "timeout": 30,
            "description": "Code coverage gate (minimum 80%)"
          },
          {
            "type": "command",
            "command": "uv run .claude/hooks/validators/security_scan.py",
            "timeout": 30,
            "description": "Security vulnerability scan"
          },
          {
            "type": "command",
            "command": "uv run .claude/hooks/validators/validate_docs.py",
            "timeout": 10,
            "description": "Documentation validation"
          }
        ]
      }
    ],

    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run .claude/hooks/validators/run_tests.py",
            "timeout": 60,
            "description": "Test suite for sub-agents"
          }
        ]
      }
    ]
  }
}
```

---

## Benefits of Self-Correcting Agents

### 1. Zero Touch Deployment

```
Traditional:
  Agent → Human Review → Human Approval → Deploy
  Time: Hours
  Bottleneck: Human

Self-Correcting:
  Agent → Validators (automatic) → Deploy
  Time: Minutes
  Bottleneck: None
```

### 2. Consistent Quality

```
Human Review:
  - Subjective (varies by reviewer)
  - Incomplete (humans miss things)
  - Slow (hours or days)

Validator Scripts:
  - Objective (deterministic)
  - Complete (checks everything)
  - Fast (seconds)
```

### 3. Continuous Improvement

```
Agent learns from validator feedback:
  Mistake 1: Missing import → Agent adds import
  Mistake 2: Test fails → Agent fixes logic
  Mistake 3: Low coverage → Agent adds tests

Over time: Agent makes fewer mistakes
```

---

## Advanced Patterns

### Pattern 1: Cascading Validators

**Progressive validation** with increasing strictness:

```python
# PostToolUse: Fast validators (< 5 seconds)
- Syntax check
- Import validation
- Basic type check

# Stop: Comprehensive validators (< 60 seconds)
- Full test suite
- Code coverage
- Security scan
- Documentation check
- Performance profiling
```

### Pattern 2: Context-Aware Validation

**Different validators for different file types**:

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "context": "*.py",
      "hooks": [
        {"command": "ruff check $FILE"}
      ]
    },
    {
      "matcher": "Edit|Write",
      "context": "*.sql",
      "hooks": [
        {"command": "sqlfluff lint $FILE"}
      ]
    }
  ]
}
```

### Pattern 3: Staged Deployment with Validation

**Validate at each rollout stage**:

```yaml
deployment:
  - stage: 1%
    validate:
      - error_rate < 0.1%
      - response_time_p95 < 500ms

  - stage: 10%
    validate:
      - error_rate < 0.05%
      - response_time_p95 < 450ms

  - stage: 100%
    validate:
      - error_rate < 0.01%
      - response_time_p95 < 400ms
```

---

## Troubleshooting

### Issue: Validator blocks legitimate code

**Symptom**: Agent keeps getting blocked even though code looks correct

**Causes**:
1. Validator threshold too strict (e.g., 95% coverage impossible)
2. Validator has false positives
3. Test suite flaky

**Solutions**:
```python
# Adjust thresholds in validator scripts
MINIMUM_COVERAGE = 75  # Lower from 80%

# Add skip conditions for known issues
if "flaky_test" in test_name:
    skip_test()

# Add validator configuration file
# .claude/validators.json
{
  "coverage": {
    "minimum": 75,
    "exclude": ["tests/", "migrations/"]
  }
}
```

---

### Issue: Validators too slow

**Symptom**: PostToolUse hooks take >10 seconds, slowing agent down

**Solutions**:
```python
# Use faster linters
# BAD: pylint (slow)
# GOOD: ruff (fast)

# Cache validator results
@cache
def validate_file(file_path):
    ...

# Run only on changed files
if not file_changed_since_last_validation(file_path):
    return cached_result
```

---

## Summary

### What You've Built

- ✅ **Immediate Feedback Loop**: PostToolUse hooks catch syntax errors instantly
- ✅ **Quality Gates**: Stop hooks block completion until all checks pass
- ✅ **Self-Correction**: Agents fix their own mistakes automatically
- ✅ **Zero Touch**: Deploy without human review (with confidence)
- ✅ **Builder/Validator Teams**: Specialized agents for complex workflows

### The Trust Model

```
Traditional Z-Threads:
  Hope agent does good work
  ❌ Risk: Agent might make mistakes
  ❌ Solution: Human review (bottleneck)

Self-Correcting Z-Threads:
  Deterministic validators force correctness
  ✅ Certainty: Agent CANNOT finish with mistakes
  ✅ Solution: Automated validation (no bottleneck)
```

### The Paradigm Shift

**Before**: Trust the Agent
- "I hope the agent did this correctly"
- Manual review required
- Human bottleneck

**After**: Trust the System
- "The system won't let the agent finish if it's wrong"
- Automated validation
- No human required

---

**You now have Self-Correcting Agents - the foundation for true Zero Touch workflows.** 🔄

**Z-Threads are no longer aspirational - they're operational.** 🚀
