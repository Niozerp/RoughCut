# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest"]
# ///

"""Tests for installation detection logic."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from install import (
    check_backend_installed,
    check_poetry_installed,
    check_python_version,
    parse_version,
)


class TestParseVersion:
    """Tests for version parsing utility."""

    def test_parses_standard_python_version(self) -> None:
        """Test parsing 'Python 3.10.4' format."""
        result = parse_version("Python 3.10.4")
        assert result == (3, 10, 4)

    def test_parses_poetry_version(self) -> None:
        """Test parsing 'Poetry version 2.0.0' format."""
        result = parse_version("Poetry version 2.0.0")
        assert result == (2, 0, 0)

    def test_parses_version_with_prefix(self) -> None:
        """Test parsing version with various prefixes."""
        result = parse_version("some-tool version 1.2.3")
        assert result == (1, 2, 3)

    def test_returns_none_on_invalid_version(self) -> None:
        """Test handling of non-version strings."""
        result = parse_version("not a version")
        assert result is None


class TestCheckPythonVersion:
    """Tests for Python version detection."""

    @patch("subprocess.run")
    def test_detects_python_3_10(self, mock_run: MagicMock) -> None:
        """Test detection of Python 3.10+."""
        mock_run.return_value = MagicMock(
            stdout="Python 3.11.4\n",
            stderr="",
            returncode=0,
        )
        result = check_python_version()
        assert result["installed"] is True
        assert result["version"] == "3.11.4"
        assert result["meets_requirement"] is True

    @patch("subprocess.run")
    def test_detects_python_3_9_as_insufficient(self, mock_run: MagicMock) -> None:
        """Test that Python 3.9 fails requirement."""
        mock_run.return_value = MagicMock(
            stdout="Python 3.9.7\n",
            stderr="",
            returncode=0,
        )
        result = check_python_version()
        assert result["installed"] is True
        assert result["version"] == "3.9.7"
        assert result["meets_requirement"] is False

    @patch("subprocess.run")
    def test_handles_python_not_found(self, mock_run: MagicMock) -> None:
        """Test handling when Python is not installed."""
        mock_run.side_effect = FileNotFoundError("python3 not found")
        result = check_python_version()
        assert result["installed"] is False
        assert result["version"] is None
        assert result["meets_requirement"] is False

    @patch("subprocess.run")
    def test_handles_python_command_failure(self, mock_run: MagicMock) -> None:
        """Test handling when Python command fails."""
        mock_run.return_value = MagicMock(
            stdout="",
            stderr="Error",
            returncode=1,
        )
        result = check_python_version()
        assert result["installed"] is False
        assert result["version"] is None
        assert result["meets_requirement"] is False


class TestCheckPoetryInstalled:
    """Tests for Poetry installation detection."""

    @patch("subprocess.run")
    def test_detects_poetry_installed(self, mock_run: MagicMock) -> None:
        """Test detection of installed Poetry."""
        mock_run.return_value = MagicMock(
            stdout="Poetry version 2.0.0\n",
            stderr="",
            returncode=0,
        )
        result = check_poetry_installed()
        assert result["installed"] is True
        assert result["version"] == "2.0.0"

    @patch("subprocess.run")
    def test_handles_poetry_not_found(self, mock_run: MagicMock) -> None:
        """Test handling when Poetry is not installed."""
        mock_run.side_effect = FileNotFoundError("poetry not found")
        result = check_poetry_installed()
        assert result["installed"] is False
        assert result["version"] is None

    @patch("subprocess.run")
    def test_handles_poetry_command_failure(self, mock_run: MagicMock) -> None:
        """Test handling when Poetry command fails."""
        mock_run.return_value = MagicMock(
            stdout="",
            stderr="Error",
            returncode=1,
        )
        result = check_poetry_installed()
        assert result["installed"] is False
        assert result["version"] is None


class TestCheckBackendInstalled:
    """Tests for backend package installation detection."""

    @patch("subprocess.run")
    def test_detects_backend_installed(self, mock_run: MagicMock) -> None:
        """Test detection of installed roughcut backend."""
        mock_run.return_value = MagicMock(
            stdout="OK",
            stderr="",
            returncode=0,
        )
        project_path = Path("/test/project")
        result = check_backend_installed(project_path)
        assert result["installed"] is True
        assert result["error"] is None

    @patch("subprocess.run")
    def test_handles_backend_not_importable(self, mock_run: MagicMock) -> None:
        """Test handling when backend package not found."""
        mock_run.return_value = MagicMock(
            stdout="",
            stderr="ModuleNotFoundError: No module named 'roughcut'",
            returncode=1,
        )
        project_path = Path("/test/project")
        result = check_backend_installed(project_path)
        assert result["installed"] is False
        assert "roughcut" in result["error"].lower()

    @patch("subprocess.run")
    def test_handles_poetry_run_failure(self, mock_run: MagicMock) -> None:
        """Test handling when poetry run command fails."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "poetry", stderr="Poetry not found"
        )
        project_path = Path("/test/project")
        result = check_backend_installed(project_path)
        assert result["installed"] is False

    @patch("subprocess.run")
    def test_uses_absolute_project_path(self, mock_run: MagicMock) -> None:
        """Test that absolute paths are used for cross-platform compatibility."""
        mock_run.return_value = MagicMock(
            stdout="OK",
            stderr="",
            returncode=0,
        )
        project_path = Path("/Users/Test User/My Project/RoughCut/roughcut")
        check_backend_installed(project_path)
        # Verify subprocess was called with absolute path
        call_args = mock_run.call_args
        assert "/Users/Test User/My Project/RoughCut/roughcut" in str(call_args)


class TestInstallationDetectionIntegration:
    """Integration tests for full detection flow."""

    @patch("install.check_backend_installed")
    @patch("install.check_poetry_installed")
    @patch("install.check_python_version")
    def test_full_detection_all_installed(
        self,
        mock_python: MagicMock,
        mock_poetry: MagicMock,
        mock_backend: MagicMock,
    ) -> None:
        """Test when all components are installed."""
        from install import run_detection

        mock_python.return_value = {
            "installed": True,
            "version": "3.11.4",
            "meets_requirement": True,
        }
        mock_poetry.return_value = {"installed": True, "version": "2.0.0"}
        mock_backend.return_value = {"installed": True, "error": None}

        result = run_detection(Path("/test"))

        assert result["python"]["installed"] is True
        assert result["poetry"]["installed"] is True
        assert result["backend"]["installed"] is True
        assert result["ready"] is True

    @patch("install.check_backend_installed")
    @patch("install.check_poetry_installed")
    @patch("install.check_python_version")
    def test_full_detection_python_missing(
        self,
        mock_python: MagicMock,
        mock_poetry: MagicMock,
        mock_backend: MagicMock,
    ) -> None:
        """Test when Python is not installed."""
        from install import run_detection

        mock_python.return_value = {
            "installed": False,
            "version": None,
            "meets_requirement": False,
        }
        mock_poetry.return_value = {"installed": False, "version": None}
        mock_backend.return_value = {"installed": False, "error": "Not checked"}

        result = run_detection(Path("/test"))

        assert result["python"]["installed"] is False
        assert result["ready"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
