@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%roughcut"
set "ELECTRON_DIR=%BACKEND_DIR%\electron"
set "ROOT_LAUNCHER=%ROOT%launch_roughcut.bat"
set "RESOLVE_SCRIPTS="
set "PYTHON_CMD="

echo ============================================
echo        RoughCut Standalone Installer
echo ============================================
echo.

if not exist "%BACKEND_DIR%\pyproject.toml" (
  echo [ERROR] roughcut\pyproject.toml was not found.
  exit /b 1
)

if not exist "%ELECTRON_DIR%\package.json" (
  echo [ERROR] roughcut\electron\package.json was not found.
  exit /b 1
)

call :find_python
if errorlevel 1 exit /b 1

call :install_python_dependencies
if errorlevel 1 exit /b 1

call :install_electron_dependencies
if errorlevel 1 exit /b 1

call :ensure_spacetime
if errorlevel 1 exit /b 1

call :ensure_rust_toolchain
if errorlevel 1 exit /b 1

call :validate_root_launcher
if errorlevel 1 exit /b 1

call :install_resolve_support

echo.
echo [OK] RoughCut bootstrap complete.
echo [OK] Launcher ready: %ROOT_LAUNCHER%
echo.
echo Launching RoughCut standalone...
start "" "%ROOT_LAUNCHER%"
exit /b 0

:find_python
python --version >nul 2>&1
if %errorlevel% equ 0 (
  set "PYTHON_CMD=python"
  echo [OK] Python found via python
  exit /b 0
)

py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
  set "PYTHON_CMD=py -3"
  echo [OK] Python found via py -3
  exit /b 0
)

echo [ERROR] Python 3.10+ is required.
exit /b 1

:install_python_dependencies
echo.
echo [1/5] Installing Python dependencies...

%PYTHON_CMD% -m pip install --user poetry
if %errorlevel% neq 0 (
  echo [ERROR] Failed to install Poetry.
  exit /b 1
)

pushd "%BACKEND_DIR%"
%PYTHON_CMD% -m poetry install --no-interaction
set "POETRY_RESULT=%errorlevel%"
popd

if %POETRY_RESULT% neq 0 (
  echo [ERROR] Poetry dependency install failed.
  exit /b 1
)

echo [OK] Python backend ready.
exit /b 0

:install_electron_dependencies
echo.
echo [2/5] Installing Electron dependencies...

where npm >nul 2>&1
if %errorlevel% neq 0 (
  echo [ERROR] npm was not found in PATH.
  echo [ERROR] Install Node.js 20+ and rerun install.bat.
  exit /b 1
)

pushd "%ELECTRON_DIR%"
call npm install
if %errorlevel% neq 0 (
  popd
  echo [ERROR] npm install failed.
  exit /b 1
)

call npm run build
set "BUILD_RESULT=%errorlevel%"
popd

if %BUILD_RESULT% neq 0 (
  echo [ERROR] npm run build failed.
  exit /b 1
)

echo [OK] Electron app built.
exit /b 0

:ensure_spacetime
echo.
echo [3/5] Verifying SpacetimeDB CLI...

call :locate_spacetime
if defined SPACETIME_BIN (
  echo [OK] SpacetimeDB CLI found: !SPACETIME_BIN!
  exit /b 0
)

echo [INFO] Installing SpacetimeDB CLI...
powershell -NoProfile -ExecutionPolicy Bypass -Command "iwr https://windows.spacetimedb.com -UseBasicParsing | iex"
if %errorlevel% neq 0 (
  echo [ERROR] SpacetimeDB installer failed.
  exit /b 1
)

call :locate_spacetime
if not defined SPACETIME_BIN (
  echo [WARN] SpacetimeDB CLI installed but was not found in this shell.
  echo [WARN] RoughCut will look for it again at launch time.
  exit /b 0
)

echo [OK] SpacetimeDB CLI ready: !SPACETIME_BIN!
exit /b 0

:ensure_rust_toolchain
echo.
echo [4/5] Verifying Rust toolchain and WebAssembly target...

call :prepend_runtime_path
call :locate_rustup
call :locate_cargo

if not defined RUSTUP_BIN (
  where winget >nul 2>&1
  if %errorlevel% equ 0 (
    echo [INFO] Installing Rust toolchain via winget...
    winget install --id Rustlang.Rustup -e --accept-package-agreements --accept-source-agreements
    if %errorlevel% neq 0 (
      echo [ERROR] Rust toolchain installation failed.
      echo [ERROR] Install rustup from https://rustup.rs/ and rerun install.bat.
      exit /b 1
    )

    call :prepend_runtime_path
    call :locate_rustup
    call :locate_cargo
  ) else (
    echo [ERROR] Rust toolchain not found.
    echo [ERROR] Install rustup from https://rustup.rs/ and rerun install.bat.
    exit /b 1
  )
)

if not defined RUSTUP_BIN (
  echo [ERROR] rustup is still not available after installation.
  echo [ERROR] Restart your shell or install rustup manually from https://rustup.rs/.
  exit /b 1
)

if not defined CARGO_BIN (
  echo [INFO] Initializing the stable Rust toolchain...
  call "!RUSTUP_BIN!" default stable
  if %errorlevel% neq 0 (
    echo [ERROR] Failed to initialize the Rust stable toolchain.
    exit /b 1
  )

  call :prepend_runtime_path
  call :locate_cargo
)

if not defined CARGO_BIN (
  echo [ERROR] cargo is not available.
  echo [ERROR] Make sure %%USERPROFILE%%\.cargo\bin is on PATH and rerun install.bat.
  exit /b 1
)

call "!RUSTUP_BIN!" target list --installed | findstr /x /c:"wasm32-unknown-unknown" >nul
if %errorlevel% neq 0 (
  echo [INFO] Installing Rust target wasm32-unknown-unknown...
  call "!RUSTUP_BIN!" target add wasm32-unknown-unknown
  if %errorlevel% neq 0 (
    echo [ERROR] Failed to install the wasm32-unknown-unknown target.
    exit /b 1
  )
)

echo [OK] Rust toolchain ready: !CARGO_BIN!
echo [OK] WebAssembly target ready: wasm32-unknown-unknown
exit /b 0

:prepend_runtime_path
set "PATH=%USERPROFILE%\.cargo\bin;%USERPROFILE%\.local\bin;%LOCALAPPDATA%\SpacetimeDB;%APPDATA%\SpacetimeDB;%LOCALAPPDATA%\SpacetimeDB\bin;%APPDATA%\SpacetimeDB\bin;%PATH%"
exit /b 0

:locate_spacetime
set "SPACETIME_BIN="
for %%P in (
  "%LOCALAPPDATA%\SpacetimeDB\spacetime.exe"
  "%APPDATA%\SpacetimeDB\spacetime.exe"
  "%USERPROFILE%\.local\bin\spacetime.exe"
  "%LOCALAPPDATA%\SpacetimeDB\bin\spacetime.exe"
  "%APPDATA%\SpacetimeDB\bin\spacetime.exe"
  "%BACKEND_DIR%\bin\spacetime.exe"
) do (
  if not defined SPACETIME_BIN (
    if exist "%%~fP" set "SPACETIME_BIN=%%~fP"
  )
)

if not defined SPACETIME_BIN (
  where spacetime >nul 2>&1
  if %errorlevel% equ 0 (
    for /f "usebackq delims=" %%P in (`where spacetime`) do (
      if not defined SPACETIME_BIN set "SPACETIME_BIN=%%P"
    )
  )
)
exit /b 0

:locate_rustup
set "RUSTUP_BIN="
for %%P in (
  "%USERPROFILE%\.cargo\bin\rustup.exe"
) do (
  if not defined RUSTUP_BIN (
    if exist "%%~fP" set "RUSTUP_BIN=%%~fP"
  )
)

if not defined RUSTUP_BIN (
  where rustup >nul 2>&1
  if %errorlevel% equ 0 (
    for /f "usebackq delims=" %%P in (`where rustup`) do (
      if not defined RUSTUP_BIN set "RUSTUP_BIN=%%P"
    )
  )
)
exit /b 0

:locate_cargo
set "CARGO_BIN="
for %%P in (
  "%USERPROFILE%\.cargo\bin\cargo.exe"
) do (
  if not defined CARGO_BIN (
    if exist "%%~fP" set "CARGO_BIN=%%~fP"
  )
)

if not defined CARGO_BIN (
  where cargo >nul 2>&1
  if %errorlevel% equ 0 (
    for /f "usebackq delims=" %%P in (`where cargo`) do (
      if not defined CARGO_BIN set "CARGO_BIN=%%P"
    )
  )
)
exit /b 0

:validate_root_launcher
echo.
echo [5/5] Validating standalone launcher...

if not exist "%ROOT_LAUNCHER%" (
  echo [ERROR] %ROOT_LAUNCHER% was not found.
  exit /b 1
)

if not exist "%BACKEND_DIR%\scripts\bootstrap_launch.py" (
  echo [ERROR] roughcut\scripts\bootstrap_launch.py was not found.
  exit /b 1
)

echo [OK] Standalone launcher ready.
exit /b 0

:install_resolve_support
echo.
echo [INFO] Checking for DaVinci Resolve scripts folder...

for %%P in (
  "%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
  "%LOCALAPPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
  "%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
) do (
  if not defined RESOLVE_SCRIPTS if exist "%%~fP" set "RESOLVE_SCRIPTS=%%~fP"
)

if not defined RESOLVE_SCRIPTS (
  echo [INFO] Resolve scripts folder not found. Skipping Resolve menu installation.
  exit /b 0
)

echo [INFO] Installing Resolve launcher to: %RESOLVE_SCRIPTS%
copy /Y "%BACKEND_DIR%\RoughCut.lua" "%RESOLVE_SCRIPTS%\" >nul
if %errorlevel% neq 0 (
  echo [WARN] Could not copy RoughCut.lua into the Resolve scripts folder.
  exit /b 0
)

if exist "%RESOLVE_SCRIPTS%\roughcut" rmdir /S /Q "%RESOLVE_SCRIPTS%\roughcut"
xcopy /E /I /Y "%BACKEND_DIR%" "%RESOLVE_SCRIPTS%\roughcut" >nul
if %errorlevel% neq 0 (
  echo [WARN] Could not copy roughcut\ into the Resolve scripts folder.
  exit /b 0
)

echo [OK] Resolve menu support installed.
exit /b 0
