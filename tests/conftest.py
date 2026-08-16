"""Shared fixtures and configuration for change-ringing test suite."""

import pathlib
import sys

# Ensure repository root and scripts/ are on sys.path for test discovery
ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "data"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
