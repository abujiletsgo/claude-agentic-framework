"""
Pytest configuration for guardrails tests.

This file ensures that the parent directory is added to sys.path
so that tests can import the guardrails modules properly.
"""

# IMPORTANT: Add path BEFORE any other imports
import sys
from pathlib import Path
import tempfile
import shutil
import pytest

# Add parent directory to path for imports - must be first!
guardrails_dir = str(Path(__file__).parent.parent)
if guardrails_dir not in sys.path:
    sys.path.insert(0, guardrails_dir)


@pytest.fixture
def temp_state_file():
    """
    Create a temporary state file path (file does NOT exist yet).

    This fixture creates a temporary directory with a non-existing state.json file.
    The HookStateManager will properly initialize the file on first use.

    Yields:
        Path to non-existing state file
    """
    temp_dir = Path(tempfile.mkdtemp())
    state_file = temp_dir / "state.json"

    yield state_file

    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def temp_config_file():
    """
    Create a temporary config file path (file does NOT exist yet).

    Yields:
        Path to non-existing config file
    """
    temp_dir = Path(tempfile.mkdtemp())
    config_file = temp_dir / "config.yaml"

    yield config_file

    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
