"""Bootstrap legacy root-level tests against the packaged RoughCut source tree."""

from __future__ import annotations

import sys
from pathlib import Path


PACKAGE_SRC = Path(__file__).resolve().parents[1] / "roughcut" / "src"

if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))
