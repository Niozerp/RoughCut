"""Test package bootstrap for RoughCut."""

from __future__ import annotations

import sys
from pathlib import Path


PACKAGE_SRC = Path(__file__).resolve().parents[1] / "src"
PACKAGE_ROOT = PACKAGE_SRC / "roughcut"

if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))

roughcut_package = sys.modules.get("roughcut")
if roughcut_package is not None and hasattr(roughcut_package, "__path__"):
    roughcut_paths = [str(path) for path in roughcut_package.__path__]
    if str(PACKAGE_ROOT) not in roughcut_paths:
        roughcut_package.__path__.append(str(PACKAGE_ROOT))
