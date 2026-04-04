# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///

#!/usr/bin/env python3
"""Installation orchestration script for RoughCut Python backend.

Handles dependency installation, progress reporting, and health checks.
Communicates with Lua frontend via JSON-RPC over stdout.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


# Constants for timeouts (in seconds)
TIMEOUT_PYTHON_CHECK = 5
TIMEOUT_POETRY_CHECK = 5
TIMEOUT_BACKEND_CHECK = 30
TIMEOUT_POETRY_INSTALL = 180  # 3 minutes
TIMEOUT_DEPS_INSTALL = 420  # 7 minutes
MAX_POETRY_RETRIES = 3

# Progress calculation constants
PROGRESS_LINES_PER_PERCENT = 20
PROGRESS_CAP_PERCENT = 95


def parse_version(version_string: str) -> tuple[int, int, int] | None:
    """Parse version string into tuple of (major, minor, patch).
    
    Handles formats like:
    - "Python 3.10.4"
    - "Poetry version 2.0.0"
    - "1.2.3"
    
    Args:
        version_string: String containing version information
        
    Returns:
        Tuple of (major, minor, patch) or None if parsing fails
    """
    # Match version pattern: X.Y.Z
    match = re.search(r'(\d+)\.(\d+)\.(\d+)', version_string)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None


def check_python_version() -> dict[str, Any]:
    """Check if Python 3.10+ is installed and available.
    
    Returns:
        Dict with keys:
        - installed: bool
        - version: str | None
        - meets_requirement: bool
    """
    result = {
        "installed": False,
        "version": None,
        "meets_requirement": False,
    }
    
    try:
        # Try python3 first, then python
        for cmd in ["python3", "python"]:
            try:
                process = subprocess.run(
                    [cmd, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_PYTHON_CHECK,
                )
                if process.returncode == 0:
                    version_str = process.stdout.strip() or process.stderr.strip()
                    version_tuple = parse_version(version_str)
                    
                    if version_tuple:
                        major, minor, patch = version_tuple
                        result["installed"] = True
                        result["version"] = f"{major}.{minor}.{patch}"
                        # Check if meets 3.10+ requirement
                        result["meets_requirement"] = (major > 3) or (major == 3 and minor >= 10)
                    return result
            except FileNotFoundError:
                continue
            except subprocess.TimeoutExpired:
                continue
            except OSError as e:
                # Handle OS-level errors (permissions, etc.)
                result["error"] = f"OS error checking Python: {e}"
                return result
                
    except Exception as e:
        # Catch-all for unexpected errors
        result["error"] = f"Unexpected error checking Python: {e}"
    
    return result


def check_poetry_installed() -> dict[str, Any]:
    """Check if Poetry is installed and get version.
    
    Returns:
        Dict with keys:
        - installed: bool
        - version: str | None
    """
    result = {
        "installed": False,
        "version": None,
    }
    
    try:
        process = subprocess.run(
            ["poetry", "--version"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_POETRY_CHECK,
        )
        if process.returncode == 0:
            version_str = process.stdout.strip()
            version_tuple = parse_version(version_str)
            if version_tuple:
                result["installed"] = True
                result["version"] = f"{version_tuple[0]}.{version_tuple[1]}.{version_tuple[2]}"
    except FileNotFoundError:
        pass  # Poetry not found
    except subprocess.TimeoutExpired:
        result["error"] = "Poetry check timed out"
    except PermissionError as e:
        result["error"] = f"Permission error checking Poetry: {e}"
    except OSError as e:
        result["error"] = f"OS error checking Poetry: {e}"
    
    return result


def check_backend_installed(project_path: Path) -> dict[str, Any]:
    """Check if roughcut backend package is importable via Poetry.
    
    Args:
        project_path: Absolute path to project directory containing pyproject.toml
        
    Returns:
        Dict with keys:
        - installed: bool
        - error: str | None
    """
    result = {
        "installed": False,
        "error": None,
    }
    
    try:
        # Use absolute path for cross-platform compatibility
        abs_path = project_path.resolve()
        
        process = subprocess.run(
            [
                "poetry", "run", "python", "-c",
                "import roughcut; print('OK')"
            ],
            cwd=str(abs_path),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_BACKEND_CHECK,
        )
        
        if process.returncode == 0 and "OK" in process.stdout:
            result["installed"] = True
        else:
            result["error"] = process.stderr.strip() or "Backend package not found"
            
    except FileNotFoundError:
        result["error"] = "Poetry not found - cannot check backend"
    except subprocess.TimeoutExpired:
        result["error"] = f"Backend check timed out after {TIMEOUT_BACKEND_CHECK}s"
    except subprocess.CalledProcessError as e:
        result["error"] = f"Backend check failed: {e.stderr}"
    except PermissionError as e:
        result["error"] = f"Permission error during backend check: {e}"
    except OSError as e:
        result["error"] = f"OS error during backend check: {e}"
    
    return result


def run_detection(project_path: Path) -> dict[str, Any]:
    """Run complete installation detection sequence.
    
    Args:
        project_path: Absolute path to project directory
        
    Returns:
        Complete detection results with all components
    """
    results = {
        "python": check_python_version(),
        "poetry": check_poetry_installed(),
        "backend": {"installed": False, "error": "Not checked"},
        "ready": False,
    }
    
    # Only check backend if Python and Poetry are available
    if results["python"]["installed"] and results["python"]["meets_requirement"]:
        if results["poetry"]["installed"]:
            results["backend"] = check_backend_installed(project_path)
    
    # System is ready only if all components are installed
    results["ready"] = (
        results["python"]["installed"] and
        results["python"]["meets_requirement"] and
        results["poetry"]["installed"] and
        results["backend"]["installed"]
    )
    
    return results


def install_poetry_with_retry(max_retries: int = 3) -> dict[str, Any]:
    """Install Poetry with exponential backoff retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        
    Returns:
        Dict with keys:
        - success: bool
        - error: str | None
        - attempts: int
    """
    result = {
        "success": False,
        "error": None,
        "attempts": 0,
    }
    
    # Installation commands for different platforms
    if sys.platform == "win32":
        install_cmd = [
            "powershell",
            "-Command",
            "(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -",
        ]
    else:
        install_cmd = [
            "bash",
            "-c",
            "curl -sSL https://install.python-poetry.org | python3 -",
        ]
    
    for attempt in range(1, max_retries + 1):
        result["attempts"] = attempt
        
        try:
            send_progress("install_poetry", attempt, max_retries, f"Installing Poetry (attempt {attempt}/{max_retries})...", int((attempt - 1) / max_retries * 100))
            
            process = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_POETRY_INSTALL,
            )
            
            if process.returncode == 0:
                # Verify Poetry is now available
                poetry_check = check_poetry_installed()
                if poetry_check["installed"]:
                    result["success"] = True
                    send_progress("install_poetry", max_retries, max_retries, "Poetry installed successfully", 100)
                    return result
                else:
                    result["error"] = "Poetry installation appeared to succeed but Poetry is not in PATH"
            else:
                result["error"] = f"Poetry installation failed: {process.stderr}"
                
        except subprocess.TimeoutExpired:
            result["error"] = f"Poetry installation timed out (attempt {attempt}, timeout={TIMEOUT_POETRY_INSTALL}s)"
        except PermissionError as e:
            result["error"] = f"Permission error during Poetry install (attempt {attempt}): {e}"
        except OSError as e:
            result["error"] = f"OS error during Poetry install (attempt {attempt}): {e}"
        except subprocess.CalledProcessError as e:
            result["error"] = f"Poetry install process failed (attempt {attempt}): {e}"
        
        # Exponential backoff: 1s, 2s, 4s
        if attempt < max_retries:
            backoff = 2 ** (attempt - 1)
            send_progress("install_poetry", attempt, max_retries, f"Retrying in {backoff}s...", int((attempt - 1) / max_retries * 100))
            time.sleep(backoff)
    
    return result


def install_dependencies(project_path: Path, operation_id: str) -> dict[str, Any]:
    """Install Python dependencies using Poetry.
    
    Args:
        project_path: Absolute path to project directory
        operation_id: Operation ID for progress tracking
        
    Returns:
        Dict with keys:
        - success: bool
        - error: str | None
        - duration_seconds: float
    """
    result = {
        "success": False,
        "error": None,
        "duration_seconds": 0.0,
    }
    
    abs_path = project_path.resolve()
    start_time = time.time()
    
    try:
        send_progress(operation_id, 1, 3, "Installing dependencies...", 0)
        
        # Run poetry install with verbose output for progress tracking
        process = subprocess.Popen(
            ["poetry", "install", "--no-interaction"],
            cwd=str(abs_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line buffered
        )
        
        # Parse output line by line for progress updates
        step_count = 0
        for line in process.stdout:
            line = line.strip()
            step_count += 1
            
            # Send progress every few lines or on significant operations
            if step_count % 5 == 0 or "Installing" in line or "Building" in line:
                percent = min(int(step_count / PROGRESS_LINES_PER_PERCENT * 100), PROGRESS_CAP_PERCENT)
                send_progress(operation_id, 2, 3, line[:50], percent)
        
        process.wait(timeout=TIMEOUT_DEPS_INSTALL)
        
        if process.returncode == 0:
            result["success"] = True
            result["duration_seconds"] = time.time() - start_time
            send_progress(operation_id, 3, 3, "Dependencies installed successfully", 100)
        else:
            result["error"] = f"Poetry install failed with exit code {process.returncode}"
            send_progress(operation_id, 3, 3, "Installation failed", 0)
            
    except subprocess.TimeoutExpired:
        process.kill()
        result["error"] = f"Dependency installation timed out after {TIMEOUT_DEPS_INSTALL}s"
        result["duration_seconds"] = time.time() - start_time
        send_progress(operation_id, 3, 3, "Installation timed out", 0)
    except PermissionError as e:
        result["error"] = f"Permission error during dependency install: {e}"
        result["duration_seconds"] = time.time() - start_time
        send_progress(operation_id, 3, 3, "Permission error", 0)
    except OSError as e:
        result["error"] = f"OS error during dependency install: {e}"
        result["duration_seconds"] = time.time() - start_time
        send_progress(operation_id, 3, 3, "System error", 0)
    except subprocess.CalledProcessError as e:
        result["error"] = f"Poetry install process error: {e}"
        result["duration_seconds"] = time.time() - start_time
        send_progress(operation_id, 3, 3, "Process error", 0)
    
    return result


def run_full_installation(project_path: Path, request_id: str, user_consent: bool = False) -> None:
    """Run complete installation workflow.
    
    Args:
        project_path: Absolute path to project directory
        request_id: JSON-RPC request ID
        user_consent: Whether user has given consent to install Poetry
    """
    operation_id = f"install_{int(time.time())}_{hash(request_id) % 1000:03d}"
    
    send_progress(operation_id, 1, 5, "Checking Python installation...", 5)
    
    # Step 1: Check Python
    python_check = check_python_version()
    if not python_check["installed"]:
        error = {
            "code": -32001,
            "category": "python_not_found",
            "message": "Python 3.10+ is required but not found",
            "suggestion": "Please install Python 3.10 or later from https://python.org",
        }
        send_error(error, request_id)
        return
    
    if not python_check["meets_requirement"]:
        error = {
            "code": -32002,
            "category": "python_version_too_old",
            "message": f"Python {python_check['version']} found, but 3.10+ is required",
            "suggestion": "Please upgrade Python to version 3.10 or later",
        }
        send_error(error, request_id)
        return
    
    send_progress(operation_id, 2, 5, f"Python {python_check['version']} detected", 20)
    
    # Step 2: Check/Install Poetry
    poetry_check = check_poetry_installed()
    if not poetry_check["installed"]:
        if not user_consent:
            error = {
                "code": -32003,
                "category": "poetry_not_installed",
                "message": "Poetry is not installed",
                "suggestion": "User consent required to install Poetry. Set user_consent=true to proceed.",
            }
            send_error(error, request_id)
            return
        
        send_progress(operation_id, 2, 5, "Installing Poetry...", 25)
        poetry_install = install_poetry_with_retry()
        
        if not poetry_install["success"]:
            error = {
                "code": -32004,
                "category": "poetry_install_failed",
                "message": f"Failed to install Poetry after {poetry_install['attempts']} attempts",
                "suggestion": poetry_install["error"] or "Please install Poetry manually from https://python-poetry.org",
            }
            send_error(error, request_id)
            return
    
    send_progress(operation_id, 3, 5, f"Poetry {poetry_check.get('version', 'installed')} ready", 40)
    
    # Step 3: Install dependencies
    send_progress(operation_id, 4, 5, "Installing RoughCut dependencies...", 50)
    dep_result = install_dependencies(project_path, operation_id)
    
    if not dep_result["success"]:
        error = {
            "code": -32005,
            "category": "dependency_install_failed",
            "message": "Failed to install Python dependencies",
            "suggestion": dep_result["error"] or "Check your internet connection and try again",
        }
        send_error(error, request_id)
        return
    
    # Step 4: Verify backend is now available
    send_progress(operation_id, 5, 5, "Verifying installation...", 90)
    backend_check = check_backend_installed(project_path)
    
    if not backend_check["installed"]:
        error = {
            "code": -32006,
            "category": "backend_verification_failed",
            "message": "Installation appeared to succeed but backend is not importable",
            "suggestion": backend_check.get("error") or "Try running 'poetry install' manually in the project directory",
        }
        send_error(error, request_id)
        return
    
    # Success!
    send_result({
        "status": "success",
        "backend_ready": True,
        "python_version": python_check["version"],
        "poetry_version": poetry_check.get("version"),
        "install_duration_seconds": dep_result["duration_seconds"],
    }, request_id)


def handle_install_backend(request_id: str, project_path: Path, params: dict[str, Any]) -> None:
    """Handle install_backend request.
    
    Args:
        request_id: JSON-RPC request ID
        project_path: Absolute path to project directory
        params: Request parameters including user_consent
    """
    user_consent = params.get("user_consent", False)
    run_full_installation(project_path, request_id, user_consent)


def send_json_rpc(message: dict[str, Any], request_id: str | None = None) -> None:
    """Send JSON-RPC message to stdout for Lua to parse.
    
    Args:
        message: Dictionary to send as JSON
        request_id: Optional request ID for correlation
    """
    if request_id:
        message["id"] = request_id
    print(json.dumps(message), flush=True)


def send_progress(
    operation: str,
    current_step: int,
    total_steps: int,
    step_name: str,
    percent: int,
) -> None:
    """Send progress update to Lua frontend.
    
    Args:
        operation: Operation identifier
        current_step: Current step number (1-based)
        total_steps: Total number of steps
        step_name: Human-readable step description
        percent: Completion percentage (0-100)
    """
    send_json_rpc({
        "type": "progress",
        "operation": operation,
        "current_step": current_step,
        "total_steps": total_steps,
        "step_name": step_name,
        "percent": percent,
    })


def send_result(result: dict[str, Any], request_id: str) -> None:
    """Send successful result response.
    
    Args:
        result: Result data dictionary
        request_id: Request ID for correlation
    """
    send_json_rpc({
        "result": result,
        "error": None,
        "id": request_id,
    })


def send_error(error: dict[str, Any], request_id: str) -> None:
    """Send error response.
    
    Args:
        error: Error dictionary with code, category, message, suggestion
        request_id: Request ID for correlation
    """
    send_json_rpc({
        "result": None,
        "error": error,
        "id": request_id,
    })


def handle_detect(request_id: str, project_path: Path) -> None:
    """Handle detect installation status request.
    
    Args:
        request_id: JSON-RPC request ID
        project_path: Absolute path to project directory
    """
    results = run_detection(project_path)
    send_result(results, request_id)


def main() -> int:
    """Main entry point for installation script.
    
    Reads JSON-RPC requests from stdin and writes responses to stdout.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="RoughCut Python backend installation script"
    )
    parser.add_argument(
        "--project-path",
        type=str,
        required=True,
        help="Absolute path to project directory containing pyproject.toml",
    )
    args = parser.parse_args()
    
    project_path = Path(args.project_path).resolve()
    
    # Validate project path exists
    if not project_path.exists():
        error = {
            "code": -32000,
            "category": "invalid_params",
            "message": f"Project path does not exist: {project_path}",
            "suggestion": "Verify the project path is correct and try again",
        }
        send_error(error, "init")
        return 1
    
    # Read and process JSON-RPC requests from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
            
        try:
            request = json.loads(line)
            method = request.get("method")
            request_id = request.get("id", "unknown")
            
            if method == "detect":
                handle_detect(request_id, project_path)
            elif method == "install_backend":
                params = request.get("params", {})
                handle_install_backend(request_id, project_path, params)
            elif method == "ping":
                # Health check response
                send_result({"status": "ok", "backend": "install"}, request_id)
            else:
                # Unknown method
                error = {
                    "code": -32601,
                    "category": "method_not_found",
                    "message": f"Method not found: {method}",
                    "suggestion": "Available methods: detect, install_backend, ping",
                }
                send_error(error, request_id)
                
        except json.JSONDecodeError as e:
            error = {
                "code": -32700,
                "category": "parse_error",
                "message": f"Invalid JSON: {str(e)}",
                "suggestion": "Ensure request is valid JSON",
            }
            send_error(error, "parse_error")
        except (OSError, IOError) as e:
            error = {
                "code": -32603,
                "category": "internal_error",
                "message": f"I/O error: {str(e)}",
                "suggestion": "Check file permissions and disk space",
            }
            send_error(error, request_id if 'request_id' in dir() else "unknown")
        except ValueError as e:
            error = {
                "code": -32603,
                "category": "internal_error",
                "message": f"Value error: {str(e)}",
                "suggestion": "Check input values",
            }
            send_error(error, request_id if 'request_id' in dir() else "unknown")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
