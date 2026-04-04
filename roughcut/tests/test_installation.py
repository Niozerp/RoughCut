"""Test basic RoughCut installation."""
import subprocess
import sys


def test_python_entry_point():
    """Verify Python module can be executed."""
    result = subprocess.run(
        [sys.executable, "-m", "roughcut"],
        capture_output=True,
        text=True
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
    print("✅ All tests passed!")
