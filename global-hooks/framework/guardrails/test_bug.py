#!/usr/bin/env python3
"""Test state file initialization bug."""

from pathlib import Path
import tempfile
from state_schema import HookStateData
from hook_state_manager import HookStateManager

# Create temp directory, NOT temp file
temp_dir = Path(tempfile.mkdtemp())
state_file = temp_dir / "state.json"

print(f"Test file: {state_file}")
print(f"Initial exists: {state_file.exists()}")

# Create manager - this should initialize the file
print("\nCreating HookStateManager...")
try:
    manager = HookStateManager(state_file)
    print("Manager created successfully")
except Exception as e:
    print(f"ERROR creating manager: {e}")
    import traceback
    traceback.print_exc()

# Check what was written
print(f"\nAfter init exists: {state_file.exists()}")
if state_file.exists():
    print(f"After init size: {state_file.stat().st_size}")
    print(f"\nFile contents:")
    print(state_file.read_text())

# Cleanup
import shutil
shutil.rmtree(temp_dir)
print("\nTest complete")
