#!/bin/bash
#
# Test runner for hook state manager
#
# Usage:
#   ./run_tests.sh           # Run all tests
#   ./run_tests.sh -v        # Verbose output
#   ./run_tests.sh --cov     # With coverage report
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "Hook State Manager - Test Suite"
echo "=============================================="
echo ""

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo "Error: pytest not found"
    echo "Install with: pip install -r requirements.txt"
    exit 1
fi

# Parse arguments
PYTEST_ARGS=""
RUN_COVERAGE=false

for arg in "$@"; do
    case $arg in
        --cov|--coverage)
            RUN_COVERAGE=true
            ;;
        *)
            PYTEST_ARGS="$PYTEST_ARGS $arg"
            ;;
    esac
done

# Run tests
if [ "$RUN_COVERAGE" = true ]; then
    echo "Running tests with coverage..."
    pytest tests/test_state_manager.py \
        --cov=. \
        --cov-report=term-missing \
        --cov-report=html \
        $PYTEST_ARGS
    echo ""
    echo "Coverage report generated in htmlcov/index.html"
else
    echo "Running tests..."
    pytest tests/test_state_manager.py $PYTEST_ARGS
fi

echo ""
echo "=============================================="
echo "Tests completed"
echo "=============================================="
