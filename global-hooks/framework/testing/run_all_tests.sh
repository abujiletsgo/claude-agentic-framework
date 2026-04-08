#!/bin/bash
# ===========================================================================
# Comprehensive Hook Test Runner
# ===========================================================================
#
# Runs all tests in the framework testing suite.
#
# Usage:
#   ./run_all_tests.sh              # Run all tests
#   ./run_all_tests.sh -v           # Verbose output
#   ./run_all_tests.sh -k "keyword" # Run tests matching keyword
#   ./run_all_tests.sh --quick      # Skip slow integration tests
#
# Requirements:
#   - uv (Python package manager)
#   - pytest, pyyaml, pydantic (installed via uv)
#
# ===========================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMEWORK_DIR="$(dirname "$SCRIPT_DIR")"
REPO_DIR="$(dirname "$(dirname "$FRAMEWORK_DIR")")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}============================================${NC}"
echo -e "${BOLD}  Hook Framework Test Runner${NC}"
echo -e "${BOLD}============================================${NC}"
echo ""
echo -e "  Test directory: ${BLUE}${SCRIPT_DIR}${NC}"
echo -e "  Framework dir:  ${BLUE}${FRAMEWORK_DIR}${NC}"
echo -e "  Repository:     ${BLUE}${REPO_DIR}${NC}"
echo ""

# Parse arguments
PYTEST_ARGS=()
QUICK_MODE=false

for arg in "$@"; do
    case "$arg" in
        --quick)
            QUICK_MODE=true
            PYTEST_ARGS+=("-m" "not slow")
            ;;
        *)
            PYTEST_ARGS+=("$arg")
            ;;
    esac
done

# Test files in execution order
TEST_FILES=(
    "test_knowledge_pipeline.py"
    "test_circuit_breaker_integration.py"
    "test_prompt_hook_validation.py"
    "test_skills.py"
    "test_model_tiers.py"
    "test_integration.py"
)

# Check which test files exist
echo -e "${BOLD}Test files:${NC}"
EXISTING_FILES=()
for f in "${TEST_FILES[@]}"; do
    filepath="${SCRIPT_DIR}/${f}"
    if [ -f "$filepath" ]; then
        echo -e "  ${GREEN}[found]${NC} $f"
        EXISTING_FILES+=("$filepath")
    else
        echo -e "  ${YELLOW}[skip]${NC}  $f (not found)"
    fi
done

# Also check for existing test files (test_hooks.py, review tests)
if [ -f "${SCRIPT_DIR}/test_hooks.py" ]; then
    echo -e "  ${GREEN}[found]${NC} test_hooks.py (legacy, separate runner)"
fi

REVIEW_TESTS="${FRAMEWORK_DIR}/review/tests/test_review_system.py"
if [ -f "$REVIEW_TESTS" ]; then
    echo -e "  ${GREEN}[found]${NC} review/tests/test_review_system.py"
    EXISTING_FILES+=("$REVIEW_TESTS")
fi

GUARDRAILS_TESTS_DIR="${FRAMEWORK_DIR}/guardrails/tests"
if [ -d "$GUARDRAILS_TESTS_DIR" ]; then
    for gt in "$GUARDRAILS_TESTS_DIR"/test_*.py; do
        if [ -f "$gt" ]; then
            echo -e "  ${GREEN}[found]${NC} guardrails/tests/$(basename "$gt")"
            EXISTING_FILES+=("$gt")
        fi
    done
fi

echo ""

if [ ${#EXISTING_FILES[@]} -eq 0 ]; then
    echo -e "${RED}No test files found!${NC}"
    exit 1
fi

echo -e "${BOLD}Running ${#EXISTING_FILES[@]} test files...${NC}"
echo ""

# Run pytest with all test files
# Use uv to ensure dependencies are available
uv run --with pytest --with pyyaml --with "pydantic>=2.0.0" \
    pytest "${EXISTING_FILES[@]}" \
    -v \
    --tb=short \
    --no-header \
    ${PYTEST_ARGS[@]+"${PYTEST_ARGS[@]}"} \
    2>&1

EXIT_CODE=$?

echo ""
echo -e "${BOLD}============================================${NC}"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "  ${GREEN}ALL TESTS PASSED${NC}"
else
    echo -e "  ${RED}SOME TESTS FAILED (exit code: $EXIT_CODE)${NC}"
fi
echo -e "${BOLD}============================================${NC}"

exit $EXIT_CODE
