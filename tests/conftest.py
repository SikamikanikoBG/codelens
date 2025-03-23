"""
Configuration for pytest to ensure proper module imports and coverage.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the path so that imports work correctly
src_dir = Path(__file__).parent.parent / "src"
if src_dir.exists():
    sys.path.insert(0, str(src_dir))
