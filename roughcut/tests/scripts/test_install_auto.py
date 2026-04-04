# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest"]
# ///

"""Tests for auto-installation system (Task 2)."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from install import (
    install_dependencies,
    install_poetry_with_retry,
    run_full_installation,
)


class TestInstallPoetryWithRetry:
    """Tests for Poetry installation with retry logic."""

    @patch("install.check_poetry_installed")
    @patch("subprocess.run")
    @patch("install.send_progress")
    def test_installs_poetry_successfully_first_attempt(
        self,
        mock_send_progress: MagicMock,
        mock_run: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Test successful Poetry installation on first attempt."""
        mock_run.return_value = MagicMock(returncode=0, stdout="Installing Poetry", stderr="")
        # After install, check_poetry_installed should return True on first call
        mock_check.return_value = {"installed": True, "version": "2.0.0"}

        result = install_poetry_with_retry(max_retries=3)

        assert result["success"] is True
        assert result["attempts"] == 1
        assert result["error"] is None

    @patch("install.check_poetry_installed")
    @patch("subprocess.run")
    @patch("install.send_progress")
    def test_retries_on_failure_then_succeeds(
        self,
        mock_send_progress: MagicMock,
        mock_run: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Test retry logic with eventual success."""
        # First two install attempts fail, third succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr="Network error"),
            MagicMock(returncode=1, stderr="Network error"),
            MagicMock(returncode=0, stdout="Installing Poetry"),
        ]
        # Called only after successful install (returncode==0) to verify it worked
        mock_check.return_value = {"installed": True, "version": "2.0.0"}

        result = install_poetry_with_retry(max_retries=3)

        assert result["success"] is True
        assert result["attempts"] == 3
        assert mock_run.call_count == 3

    @patch("install.check_poetry_installed")
    @patch("subprocess.run")
    @patch("install.send_progress")
    @patch("time.sleep")
    def test_exponential_backoff_between_retries(
        self,
        mock_sleep: MagicMock,
        mock_send_progress: MagicMock,
        mock_run: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Test that exponential backoff delays are applied."""
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr="Error"),
            MagicMock(returncode=1, stderr="Error"),
            MagicMock(returncode=1, stderr="Error"),
        ]
        mock_check.return_value = {"installed": False, "version": None}

        result = install_poetry_with_retry(max_retries=3)

        assert result["success"] is False
        assert result["attempts"] == 3
        # Verify exponential backoff: 1s, 2s
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

    @patch("install.check_poetry_installed")
    @patch("subprocess.run")
    @patch("install.send_progress")
    def test_fails_after_max_retries(
        self,
        mock_send_progress: MagicMock,
        mock_run: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Test failure after exhausting all retries."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Persistent network error")
        mock_check.return_value = {"installed": False, "version": None}

        result = install_poetry_with_retry(max_retries=3)

        assert result["success"] is False
        assert result["attempts"] == 3
        assert "network error" in result["error"].lower()

    @patch("install.check_poetry_installed")
    @patch("subprocess.run")
    @patch("install.send_progress")
    def test_handles_timeout(
        self,
        mock_send_progress: MagicMock,
        mock_run: MagicMock,
        mock_check: MagicMock,
    ) -> None:
        """Test handling of timeout during installation."""
        mock_run.side_effect = subprocess.TimeoutExpired("poetry install", 180)
        mock_check.return_value = {"installed": False, "version": None}

        result = install_poetry_with_retry(max_retries=2)

        assert result["success"] is False
        assert "timed out" in result["error"].lower()


class TestInstallDependencies:
    """Tests for dependency installation."""

    @patch("subprocess.Popen")
    @patch("install.send_progress")
    def test_installs_dependencies_successfully(
        self,
        mock_send_progress: MagicMock,
        mock_popen: MagicMock,
    ) -> None:
        """Test successful dependency installation."""
        mock_process = MagicMock()
        mock_process.stdout = iter([
            "Installing dependencies...",
            "Building wheels...",
            "Successfully installed",
        ])
        mock_process.returncode = 0  # Set returncode explicitly
        mock_popen.return_value = mock_process

        project_path = Path("/test/project")
        result = install_dependencies(project_path, "test_op_123")

        assert result["success"] is True
        assert result["error"] is None
        assert result["duration_seconds"] >= 0

    @patch("subprocess.Popen")
    @patch("install.send_progress")
    def test_sends_progress_updates(
        self,
        mock_send_progress: MagicMock,
        mock_popen: MagicMock,
    ) -> None:
        """Test that progress updates are sent during installation."""
        mock_process = MagicMock()
        # Simulate many lines of output
        mock_process.stdout = iter(["Line"] * 25)
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        project_path = Path("/test/project")
        install_dependencies(project_path, "test_op_456")

        # Should have sent multiple progress updates
        assert mock_send_progress.call_count >= 3

    @patch("subprocess.Popen")
    @patch("install.send_progress")
    def test_handles_installation_failure(
        self,
        mock_send_progress: MagicMock,
        mock_popen: MagicMock,
    ) -> None:
        """Test handling of failed dependency installation."""
        mock_process = MagicMock()
        mock_process.stdout = iter(["Error: Failed to build wheel"])
        mock_process.returncode = 1  # Set returncode explicitly
        mock_popen.return_value = mock_process

        project_path = Path("/test/project")
        result = install_dependencies(project_path, "test_op_789")

        assert result["success"] is False
        assert "exit code 1" in result["error"]

    @patch("subprocess.Popen")
    @patch("install.send_progress")
    def test_handles_timeout(
        self,
        mock_send_progress: MagicMock,
        mock_popen: MagicMock,
    ) -> None:
        """Test handling of timeout during dependency installation."""
        mock_process = MagicMock()
        mock_process.stdout = iter(["Installing..."])
        mock_process.wait.side_effect = subprocess.TimeoutExpired("poetry install", 420)
        mock_popen.return_value = mock_process

        project_path = Path("/test/project")
        result = install_dependencies(project_path, "test_op_timeout")

        assert result["success"] is False
        assert "timed out" in result["error"].lower()
        mock_process.kill.assert_called_once()

    @patch("subprocess.Popen")
    @patch("install.send_progress")
    def test_uses_absolute_project_path(
        self,
        mock_send_progress: MagicMock,
        mock_popen: MagicMock,
    ) -> None:
        """Test that absolute paths are used for cross-platform compatibility."""
        mock_process = MagicMock()
        mock_process.stdout = iter(["Done"])
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        project_path = Path("/Users/Test User/My Project/RoughCut/roughcut")
        install_dependencies(project_path, "test_op_path")

        call_args = mock_popen.call_args
        assert "cwd" in call_args.kwargs
        assert "/Users/Test User/My Project/RoughCut/roughcut" in str(call_args.kwargs["cwd"])


class TestRunFullInstallation:
    """Tests for full installation workflow."""

    @patch("install.check_backend_installed")
    @patch("install.install_dependencies")
    @patch("install.install_poetry_with_retry")
    @patch("install.check_poetry_installed")
    @patch("install.check_python_version")
    @patch("install.send_result")
    @patch("install.send_progress")
    def test_full_installation_success_path(
        self,
        mock_send_progress: MagicMock,
        mock_send_result: MagicMock,
        mock_python: MagicMock,
        mock_poetry_check: MagicMock,
        mock_poetry_install: MagicMock,
        mock_deps: MagicMock,
        mock_backend: MagicMock,
    ) -> None:
        """Test successful full installation flow."""
        mock_python.return_value = {
            "installed": True,
            "version": "3.11.4",
            "meets_requirement": True,
        }
        mock_poetry_check.return_value = {"installed": True, "version": "2.0.0"}
        mock_deps.return_value = {"success": True, "error": None, "duration_seconds": 120.0}
        mock_backend.return_value = {"installed": True, "error": None}

        project_path = Path("/test/project")
        run_full_installation(project_path, "req_123", user_consent=True)

        mock_send_result.assert_called_once()
        result_data = mock_send_result.call_args[0][0]
        assert result_data["status"] == "success"
        assert result_data["backend_ready"] is True

    @patch("install.send_error")
    @patch("install.send_progress")
    @patch("install.check_python_version")
    def test_fails_when_python_not_found(
        self,
        mock_python: MagicMock,
        mock_send_progress: MagicMock,
        mock_send_error: MagicMock,
    ) -> None:
        """Test failure when Python is not installed."""
        mock_python.return_value = {
            "installed": False,
            "version": None,
            "meets_requirement": False,
        }

        project_path = Path("/test/project")
        run_full_installation(project_path, "req_456", user_consent=True)

        mock_send_error.assert_called_once()
        error_data = mock_send_error.call_args[0][0]
        assert error_data["category"] == "python_not_found"

    @patch("install.send_error")
    @patch("install.send_progress")
    @patch("install.check_python_version")
    def test_fails_when_python_version_too_old(
        self,
        mock_python: MagicMock,
        mock_send_progress: MagicMock,
        mock_send_error: MagicMock,
    ) -> None:
        """Test failure when Python version is < 3.10."""
        mock_python.return_value = {
            "installed": True,
            "version": "3.9.7",
            "meets_requirement": False,
        }

        project_path = Path("/test/project")
        run_full_installation(project_path, "req_789", user_consent=True)

        mock_send_error.assert_called_once()
        error_data = mock_send_error.call_args[0][0]
        assert error_data["category"] == "python_version_too_old"
        assert "3.9.7" in error_data["message"]

    @patch("install.send_error")
    @patch("install.check_poetry_installed")
    @patch("install.check_python_version")
    @patch("install.send_progress")
    def test_requires_consent_for_poetry_install(
        self,
        mock_send_progress: MagicMock,
        mock_python: MagicMock,
        mock_poetry_check: MagicMock,
        mock_send_error: MagicMock,
    ) -> None:
        """Test that Poetry installation requires user consent."""
        mock_python.return_value = {
            "installed": True,
            "version": "3.11.4",
            "meets_requirement": True,
        }
        mock_poetry_check.return_value = {"installed": False, "version": None}

        project_path = Path("/test/project")
        run_full_installation(project_path, "req_no_consent", user_consent=False)

        mock_send_error.assert_called_once()
        error_data = mock_send_error.call_args[0][0]
        assert error_data["category"] == "poetry_not_installed"
        assert "consent" in error_data["suggestion"].lower()

    @patch("install.send_error")
    @patch("install.install_poetry_with_retry")
    @patch("install.check_poetry_installed")
    @patch("install.check_python_version")
    @patch("install.send_progress")
    def test_fails_when_poetry_install_fails(
        self,
        mock_send_progress: MagicMock,
        mock_python: MagicMock,
        mock_poetry_check: MagicMock,
        mock_poetry_install: MagicMock,
        mock_send_error: MagicMock,
    ) -> None:
        """Test failure when Poetry installation fails."""
        mock_python.return_value = {
            "installed": True,
            "version": "3.11.4",
            "meets_requirement": True,
        }
        mock_poetry_check.return_value = {"installed": False, "version": None}
        mock_poetry_install.return_value = {
            "success": False,
            "error": "Network unreachable",
            "attempts": 3,
        }

        project_path = Path("/test/project")
        run_full_installation(project_path, "req_poetry_fail", user_consent=True)

        mock_send_error.assert_called_once()
        error_data = mock_send_error.call_args[0][0]
        assert error_data["category"] == "poetry_install_failed"

    @patch("install.send_error")
    @patch("install.install_dependencies")
    @patch("install.check_poetry_installed")
    @patch("install.check_python_version")
    @patch("install.send_progress")
    def test_fails_when_dependencies_fail(
        self,
        mock_send_progress: MagicMock,
        mock_python: MagicMock,
        mock_poetry_check: MagicMock,
        mock_deps: MagicMock,
        mock_send_error: MagicMock,
    ) -> None:
        """Test failure when dependency installation fails."""
        mock_python.return_value = {
            "installed": True,
            "version": "3.11.4",
            "meets_requirement": True,
        }
        mock_poetry_check.return_value = {"installed": True, "version": "2.0.0"}
        mock_deps.return_value = {"success": False, "error": "Network error", "duration_seconds": 0}

        project_path = Path("/test/project")
        run_full_installation(project_path, "req_deps_fail", user_consent=True)

        mock_send_error.assert_called_once()
        error_data = mock_send_error.call_args[0][0]
        assert error_data["category"] == "dependency_install_failed"

    @patch("install.send_error")
    @patch("install.check_backend_installed")
    @patch("install.install_dependencies")
    @patch("install.check_poetry_installed")
    @patch("install.check_python_version")
    @patch("install.send_progress")
    def test_fails_when_backend_verification_fails(
        self,
        mock_send_progress: MagicMock,
        mock_python: MagicMock,
        mock_poetry_check: MagicMock,
        mock_deps: MagicMock,
        mock_backend: MagicMock,
        mock_send_error: MagicMock,
    ) -> None:
        """Test failure when backend verification after install fails."""
        mock_python.return_value = {
            "installed": True,
            "version": "3.11.4",
            "meets_requirement": True,
        }
        mock_poetry_check.return_value = {"installed": True, "version": "2.0.0"}
        mock_deps.return_value = {"success": True, "error": None, "duration_seconds": 60.0}
        mock_backend.return_value = {"installed": False, "error": "Import error"}

        project_path = Path("/test/project")
        run_full_installation(project_path, "req_verify_fail", user_consent=True)

        mock_send_error.assert_called_once()
        error_data = mock_send_error.call_args[0][0]
        assert error_data["category"] == "backend_verification_failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
