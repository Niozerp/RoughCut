"""Test basic RoughCut installation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


PACKAGE_SRC = Path(__file__).resolve().parents[1] / "src"

if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))


def test_python_entry_point():
    """Verify Python module can be executed."""
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(PACKAGE_SRC)
        if not existing_pythonpath
        else os.pathsep.join([str(PACKAGE_SRC), existing_pythonpath])
    )
    result = subprocess.run(
        [sys.executable, "-m", "roughcut"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0
    assert "RoughCut Backend v0.1.0" in result.stdout
    assert "Installation successful" in result.stdout


def test_package_import():
    """Verify package can be imported."""
    import roughcut
    assert roughcut.__version__ == "0.1.0"


if __name__ == "__main__":
    test_package_import()
    test_python_entry_point()
    print("All tests passed!")
