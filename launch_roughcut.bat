@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
set "BOOTSTRAP=%ROOT%roughcut\scripts\bootstrap_launch.py"
set "PYTHON_CMD="

if not exist "%BOOTSTRAP%" (
  echo [ERROR] RoughCut bootstrap script was not found at:
  echo [ERROR]   %BOOTSTRAP%
  pause
  exit /b 1
)

python --version >nul 2>&1
if %errorlevel% equ 0 (
  set "PYTHON_CMD=python"
) else (
  py -3 --version >nul 2>&1
  if %errorlevel% equ 0 (
    set "PYTHON_CMD=py -3"
  )
)

if not defined PYTHON_CMD (
  echo [ERROR] Python 3.10+ is required before RoughCut can bootstrap itself.
  pause
  exit /b 1
)

cd /d "%ROOT%"
echo [INFO] Running RoughCut prelaunch bootstrap...
call %PYTHON_CMD% "%BOOTSTRAP%" --mode standalone
set "EXIT_CODE=%errorlevel%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERROR] RoughCut failed before the GUI could start.
  echo [ERROR] Review the messages above, then press any key to close this window.
  pause >nul
)

exit /b %EXIT_CODE%
