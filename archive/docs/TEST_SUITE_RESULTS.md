# Test Suite Results

**Date**: 2026-02-11
**Platform**: macOS Darwin 25.2.0
**Python**: 3.12.12
**pytest**: 9.0.2
**Runner**: `global-hooks/framework/testing/run_all_tests.sh`

---

## Summary

| Metric | Value |
|---|---|
| **Total Tests** | 435 |
| **Passed** | 435 |
| **Failed** | 0 |
| **Errors** | 0 |
| **Skipped** | 0 |
| **Duration** | 88.69s (1m 28s) |
| **Overall Coverage** | **81%** (6662 statements, 1276 missed) |

**Result: ALL 435 TESTS PASSED**

---

## Test Files (12 files, 435 tests)

| Test File | Tests | Status |
|---|---|---|
| `testing/test_knowledge_pipeline.py` | 84 | PASSED |
| `testing/test_circuit_breaker_integration.py` | 56 | PASSED |
| `guardrails/tests/test_cli.py` | 40 | PASSED |
| `testing/test_prompt_hook_validation.py` | 38 | PASSED |
| `guardrails/tests/test_circuit_breaker.py` | 37 | PASSED |
| `guardrails/tests/test_state_manager.py` | 35 | PASSED |
| `review/tests/test_review_system.py` | 34 | PASSED |
| `guardrails/tests/test_config.py` | 33 | PASSED |
| `testing/test_skills.py` | 26 | PASSED |
| `testing/test_model_tiers.py` | 25 | PASSED |
| `testing/test_integration.py` | 19 | PASSED |
| `guardrails/tests/test_config_integration.py` | 8 | PASSED |

All paths relative to `global-hooks/framework/`.

---

## Coverage Report

### Coverage by Module

#### Guardrails Module

| File | Statements | Missed | Coverage |
|---|---|---|---|
| `guardrails/__init__.py` | 12 | 5 | 58% |
| `guardrails/circuit_breaker.py` | 89 | 3 | **97%** |
| `guardrails/circuit_breaker_wrapper.py` | 83 | 43 | 48% |
| `guardrails/claude_hooks_cli.py` | 339 | 89 | 74% |
| `guardrails/config_loader.py` | 180 | 43 | 76% |
| `guardrails/hook_state_manager.py` | 177 | 22 | **88%** |
| `guardrails/state_schema.py` | 53 | 0 | **100%** |

#### Knowledge Module

| File | Statements | Missed | Coverage |
|---|---|---|---|
| `knowledge/analyze_session.py` | 256 | 121 | 53% |
| `knowledge/inject_knowledge.py` | 71 | 39 | 45% |
| `knowledge/observe_patterns.py` | 158 | 46 | 71% |
| `knowledge/store_learnings.py` | 151 | 67 | 56% |

#### Review Module

| File | Statements | Missed | Coverage |
|---|---|---|---|
| `review/analyzers/architecture.py` | 94 | 11 | **88%** |
| `review/analyzers/complexity.py` | 130 | 45 | 65% |
| `review/analyzers/dead_code.py` | 148 | 72 | 51% |
| `review/analyzers/duplication.py` | 119 | 54 | 55% |
| `review/analyzers/test_coverage.py` | 91 | 42 | 54% |
| `review/findings_notifier.py` | 55 | 13 | 76% |
| `review/findings_store.py` | 145 | 95 | 34% |
| `review/review_engine.py` | 236 | 119 | 50% |

### Coverage Summary by Module

| Module | Avg Coverage | Notes |
|---|---|---|
| **Guardrails** | ~77% | Strong coverage; `state_schema` at 100%, `circuit_breaker` at 97% |
| **Knowledge** | ~56% | Lower coverage; pipeline logic with LLM calls harder to unit test |
| **Review** | ~59% | Analyzers well-tested via integration; engine/store need more unit tests |
| **Test files** | ~95%+ | Test code itself is well-exercised |

---

## Bug Fixed During Validation

### `run_all_tests.sh` -- Unbound Variable Error

**File**: `global-hooks/framework/testing/run_all_tests.sh`, line 120

**Problem**: The script used `set -euo pipefail` (strict mode with `nounset`). When no arguments were passed, `"${PYTEST_ARGS[@]}"` triggered an "unbound variable" error because the array was empty.

**Fix**: Changed `"${PYTEST_ARGS[@]}"` to `${PYTEST_ARGS[@]+"${PYTEST_ARGS[@]}"}` which uses the `${var+value}` parameter expansion to only expand the array when it is set and non-empty.

---

## Coverage HTML Report

The interactive HTML coverage report is available at:

```
docs/coverage-html/index.html
```

Open in a browser to explore per-file, per-line coverage details.

---

## Areas for Coverage Improvement

The following source files have below 50% coverage and would benefit from additional tests:

1. **`review/findings_store.py`** (34%) -- Findings persistence and retrieval
2. **`knowledge/inject_knowledge.py`** (45%) -- Knowledge injection into prompts
3. **`guardrails/circuit_breaker_wrapper.py`** (48%) -- Wrapper that integrates circuit breaker with hook execution
4. **`review/review_engine.py`** (50%) -- Core review orchestration engine
5. **`review/analyzers/dead_code.py`** (51%) -- Dead code detection analyzer

These modules involve I/O operations (file system, LLM calls) that require more extensive mocking to achieve higher coverage.

---

## Test Categories Covered

- **Unit Tests**: Data structures, schemas, parsing, classification, configuration
- **Integration Tests**: Multi-hook coordination, session lifecycle, pipeline end-to-end
- **Circuit Breaker Tests**: State transitions, cooldown logic, concurrent access, error handling
- **Knowledge Pipeline Tests**: Tool pattern classification, LLM response parsing, observation processing
- **Review System Tests**: All 5 analyzers (architecture, complexity, dead code, duplication, test coverage), findings notification
- **Skills Tests**: Skill discovery, frontmatter parsing, content validation, real directory scanning
- **Model Tier Tests**: Tier definitions, fallback chains, cost tracking, agent assignments
- **Prompt Hook Tests**: Decision parsing, settings validation, argument substitution, template consistency
- **Config Tests**: YAML loading, environment variable override, path expansion, config merging
- **CLI Tests**: Time formatting, enable/disable operations, reset, health reports
- **State Manager Tests**: Initialization, persistence, concurrent access, error recovery, timestamps
