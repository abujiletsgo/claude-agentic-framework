# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest", "pyyaml"]
# ///
"""
Shared pytest configuration and fixtures for the testing framework.
"""

import sys
from pathlib import Path

# Add framework paths for imports
TESTING_DIR = Path(__file__).parent
FRAMEWORK_DIR = TESTING_DIR.parent
HOOKS_DIR = FRAMEWORK_DIR.parent

# Add all framework modules to sys.path
sys.path.insert(0, str(FRAMEWORK_DIR / "knowledge"))
sys.path.insert(0, str(FRAMEWORK_DIR / "guardrails"))
sys.path.insert(0, str(FRAMEWORK_DIR / "review"))
sys.path.insert(0, str(FRAMEWORK_DIR / "review" / "analyzers"))
