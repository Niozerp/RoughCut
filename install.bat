@echo off
setlocal EnableDelayedExpansion

echo ============================================
echo     RoughCut Installer for Windows
echo ============================================
echo.

:: Configuration
set "LAUNCHER_NAME=RoughCut.lua"
set "SOURCE_LAUNCHER=%~dp0roughcut\RoughCut.lua"
set "BACKEND_DIR=%~dp0roughcut"

:: Check if running as admin (we don't need admin, but warn if they do)
net session >nul 2>&1
if %errorlevel% == 0 (
    echo [WARNING] Running as Administrator. This is not required.
    echo [WARNING] It's safer to run without admin privileges.
    echo.
    choice /C YN /M "Continue anyway"
    if errorlevel 2 exit /b 1
    echo.
)

:: Check if source files exist first
if not exist "%SOURCE_LAUNCHER%" (
    echo [ERROR] Cannot find RoughCut.lua launcher
    echo [ERROR] Looked in: %SOURCE_LAUNCHER%
    echo.
    echo Make sure you're running install.bat from the extracted RoughCut folder.
    echo This folder should contain: roughcut\, install.bat, README.md
    echo.
    pause
    exit /b 1
)

if not exist "%BACKEND_DIR%" (
    echo [ERROR] Cannot find roughcut\ folder
    echo [ERROR] Looked in: %BACKEND_DIR%
    echo.
    echo Make sure you're running install.bat from the extracted RoughCut folder.
    echo.
    pause
    exit /b 1
)

:: Find DaVinci Resolve Scripts folder
echo [1/4] Looking for DaVinci Resolve installation...
echo.

set "RESOLVE_SCRIPTS="
set "RESOLVE_FOUND=0"

:: First, check if Resolve is installed by looking for the executable
echo [INFO] Checking for DaVinci Resolve installation...

set "RESOLVE_EXE="
for %%p in (
    "C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe"
    "C:\Program Files (x86)\Blackmagic Design\DaVinci Resolve\Resolve.exe"
    "C:\Program Files\Blackmagic Design\DaVinci Resolve Studio\Resolve.exe"
    "C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe"
) do (
    if exist %%p (
        set "RESOLVE_EXE=%%p"
        set "RESOLVE_FOUND=1"
        echo [FOUND] DaVinci Resolve: %%p
        goto :resolve_found
    )
)

:: Check registry for Resolve installation
for /f "tokens=*" %%a in ('reg query "HKLM\SOFTWARE\Blackmagic Design\DaVinci Resolve" /v Path 2^>nul ^| findstr "Path"') do (
    for /f "tokens=2*" %%b in ('echo %%a') do (
        if exist "%%c\Resolve.exe" (
            set "RESOLVE_EXE=%%c\Resolve.exe"
            set "RESOLVE_FOUND=1"
            echo [FOUND] DaVinci Resolve via registry: %%c
            goto :resolve_found
        )
    )
)

:resolve_found
if %RESOLVE_FOUND%==0 (
    echo [WARNING] DaVinci Resolve executable not found!
    echo.
    echo Possible reasons:
    echo   - Resolve is not installed
    echo   - Resolve is installed in a non-standard location
    echo   - This is a portable/folder-based installation
    echo.
    echo We'll try to find the Scripts folder anyway...
    echo.
)

:: Now look for Scripts
echo [INFO] Searching for Resolve Scripts folder...
echo.

:: Check common Windows paths (multiple variations)
echo [INFO] Checking: %%APPDATA%% path...
set "TEST_PATH=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
if exist "%TEST_PATH%" (
    set "RESOLVE_SCRIPTS=%TEST_PATH%"
    echo [FOUND] Scripts folder: %TEST_PATH%
    goto :found_resolve
)

echo [INFO] Checking: %%LOCALAPPDATA%% path...
set "TEST_PATH=%LOCALAPPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
if exist "%TEST_PATH%" (
    set "RESOLVE_SCRIPTS=%TEST_PATH%"
    echo [FOUND] Scripts folder: %TEST_PATH%
    goto :found_resolve
)

echo [INFO] Checking: %%PROGRAMDATA%% path...
set "TEST_PATH=%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
if exist "%TEST_PATH%" (
    set "RESOLVE_SCRIPTS=%TEST_PATH%"
    echo [FOUND] Scripts folder: %TEST_PATH%
    goto :found_resolve
)

:: If Utility folder doesn't exist, check if the Scripts folder exists
:: (we can create Utility if needed)
echo [INFO] Checking for Scripts folder (without Utility subfolder)...

set "TEST_PATH=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts"
if exist "%TEST_PATH%" (
    echo [INFO] Found Scripts folder, creating Utility subfolder...
    mkdir "%TEST_PATH%\Utility" >nul 2>&1
    if exist "%TEST_PATH%\Utility" (
        set "RESOLVE_SCRIPTS=%TEST_PATH%\Utility"
        echo [OK] Created Utility folder: %TEST_PATH%\Utility
        goto :found_resolve
    ) else (
        echo [ERROR] Failed to create Utility folder. Permission denied?
    )
)

set "TEST_PATH=%LOCALAPPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts"
if exist "%TEST_PATH%" (
    echo [INFO] Found Scripts folder, creating Utility subfolder...
    mkdir "%TEST_PATH%\Utility" >nul 2>&1
    if exist "%TEST_PATH%\Utility" (
        set "RESOLVE_SCRIPTS=%TEST_PATH%\Utility"
        echo [OK] Created Utility folder: %TEST_PATH%\Utility
        goto :found_resolve
    ) else (
        echo [ERROR] Failed to create Utility folder. Permission denied?
    )
)

set "TEST_PATH=%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts"
if exist "%TEST_PATH%" (
    echo [INFO] Found Scripts folder, creating Utility subfolder...
    mkdir "%TEST_PATH%\Utility" >nul 2>&1
    if exist "%TEST_PATH%\Utility" (
        set "RESOLVE_SCRIPTS=%TEST_PATH%\Utility"
        echo [OK] Created Utility folder: %TEST_PATH%\Utility
        goto :found_resolve
    ) else (
        echo [ERROR] Failed to create Utility folder. Permission denied?
    )
)

:: Check if Resolve Support folder exists (we can create the whole path)
echo [INFO] Checking for Resolve Support folder...

set "TEST_PATH=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support"
if exist "%TEST_PATH%" (
    echo [INFO] Found Resolve Support folder, creating Scripts\Utility...
    mkdir "%TEST_PATH%\Fusion\Scripts\Utility" >nul 2>&1
    if exist "%TEST_PATH%\Fusion\Scripts\Utility" (
        set "RESOLVE_SCRIPTS=%TEST_PATH%\Fusion\Scripts\Utility"
        echo [OK] Created Scripts\Utility folder: %TEST_PATH%\Fusion\Scripts\Utility
        goto :found_resolve
    ) else (
        echo [ERROR] Failed to create Scripts\Utility folder.
    )
)

:: Check if Resolve is installed via registry for the Support path
for /f "tokens=*" %%a in ('reg query "HKLM\SOFTWARE\Blackmagic Design\DaVinci Resolve" /v Path 2^>nul ^| findstr "Path"') do (
    for /f "tokens=2*" %%b in ('echo %%a') do (
        if exist "%%c\Support\Fusion\Scripts" (
            echo [INFO] Found Resolve via registry, checking/creating Utility folder...
            if not exist "%%c\Support\Fusion\Scripts\Utility" (
                mkdir "%%c\Support\Fusion\Scripts\Utility" >nul 2>&1
            )
            if exist "%%c\Support\Fusion\Scripts\Utility" (
                set "RESOLVE_SCRIPTS=%%c\Support\Fusion\Scripts\Utility"
                echo [FOUND] Scripts folder via registry: !RESOLVE_SCRIPTS!
                goto :found_resolve
            ) else (
                echo [ERROR] Failed to create Utility folder in registry path.
            )
        )
    )
)

:: Not found - ask user
cls
echo ============================================
echo     RoughCut Installer for Windows
echo ============================================
echo.
echo [ERROR] Could not automatically find or create DaVinci Resolve Scripts folder.
echo.
echo Let's figure this out together.
echo.

:: First, ask if Resolve is installed
echo Is DaVinci Resolve installed on this computer?
echo.
echo   1. Yes, it's installed (standard location)
echo   2. Yes, but it's in a custom/portable location
echo   3. No, Resolve is not installed yet
echo   4. I'm not sure / Cancel installation
echo.

choice /C 1234 /M "Select option"
if errorlevel 4 goto :error
if errorlevel 3 (
    echo.
    echo [INFO] You need to install DaVinci Resolve first.
    echo.
    echo Download from: https://www.blackmagicdesign.com/products/davinciresolve/
    echo.
    echo After installing Resolve, run this installer again.
    echo.
    choice /C YN /M "Open download page now"
    if errorlevel 2 goto :wait_exit
    if errorlevel 1 (
        start https://www.blackmagicdesign.com/products/davinciresolve/
        goto :wait_exit
    )
)
if errorlevel 2 goto :custom_location
if errorlevel 1 goto :help_find_location

:help_find_location
cls
echo ============================================
echo     Finding Resolve Scripts Folder
echo ============================================
echo.
echo Let's find your Scripts folder:
echo.
echo Step 1: Open DaVinci Resolve
echo Step 2: Go to: Workspace ^> Scripts ^> Edit...
echo Step 3: Note the folder path that opens
echo.
echo This is your Scripts folder. The file goes in the "Utility" subfolder.
echo.
echo Common locations to check:
echo.
echo Windows (per-user):
echo   %%APPDATA%%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\
echo.
echo Windows (system-wide):
echo   %%PROGRAMDATA%%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\
echo.
echo Tip: Copy one of the paths above, paste in File Explorer address bar,
echo then press Enter to navigate there.
echo.
echo Press any key to open File Explorer and help you find it...

pause >nul

:: Try to open the most likely locations
if exist "%APPDATA%\Blackmagic Design" (
    start explorer "%APPDATA%\Blackmagic Design\DaVinci Resolve"
) else if exist "%PROGRAMDATA%\Blackmagic Design" (
    start explorer "%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve"
) else (
    start explorer "%APPDATA%"
)

goto :ask_for_path

:custom_location
cls
echo ============================================
echo     Custom/Portable Installation
echo ============================================
echo.
echo You have DaVinci Resolve in a custom or portable location.
echo.
echo Please navigate to where Resolve is installed and find:
echo   Resolve\Support\Fusion\Scripts\Utility\
echo.
echo Or if the Utility folder doesn't exist yet:
echo   Resolve\Support\Fusion\Scripts\
echo   (We'll create the Utility folder for you)
echo.
echo Example portable path:
echo   D:\DaVinci Resolve\Support\Fusion\Scripts\Utility\
echo.

:ask_for_path
echo.
echo ============================================
echo IMPORTANT: Path Entry Instructions
echo ============================================
echo.
echo When pasting the path:
echo   - REMOVE any quotes at the beginning and end
echo   - REMOVE any trailing backslash (\) at the end
echo   - Example: C:\Users\You\Scripts\Utility
echo   - NOT: "C:\Users\You\Scripts\Utility\" (no quotes, no trailing \)
echo.
echo Paste the full path to the folder:
echo (Leave blank to cancel)
echo.
set /p "USER_INPUT_PATH=Path: "

:: Trim quotes and spaces from input
set "RESOLVE_SCRIPTS=%USER_INPUT_PATH:"=%"

:: Remove trailing backslash if present (fixes copy command issues)
if "%RESOLVE_SCRIPTS:~-1%"=="\" set "RESOLVE_SCRIPTS=%RESOLVE_SCRIPTS:~0,-1%"

:: Remove trailing spaces
:trim_loop
if "%RESOLVE_SCRIPTS:~-1%"==" " (
    set "RESOLVE_SCRIPTS=%RESOLVE_SCRIPTS:~0,-1%"
    goto trim_loop
)

:: Check if empty
if "%RESOLVE_SCRIPTS%"=="" (
    echo.
    echo Installation cancelled by user.
    goto :error
)

:: Debug output
echo.
echo [DEBUG] You entered: %RESOLVE_SCRIPTS%

:: Check if user gave us the Scripts folder or the Utility folder
if exist "%RESOLVE_SCRIPTS%\RoughCut.lua" (
    echo [INFO] It looks like you already have RoughCut.lua here.
    echo [INFO] Using this location: %RESOLVE_SCRIPTS%
    goto :found_resolve
)

:: If they gave us the Scripts folder (not Utility), check and create Utility
if not exist "%RESOLVE_SCRIPTS%\Utility" (
    if exist "%RESOLVE_SCRIPTS%" (
        echo [INFO] Creating Utility subfolder at: %RESOLVE_SCRIPTS%\Utility
        mkdir "%RESOLVE_SCRIPTS%\Utility"
        if %errorlevel% neq 0 (
            echo [ERROR] Failed to create Utility folder!
            echo [ERROR] Error code: %errorlevel%
            echo.
            echo This might be due to:
            echo   - Permission denied (try running as Administrator)
            echo   - Invalid path (check the path you entered)
            echo   - Disk full or other system error
            echo.
            echo The path you entered was: %RESOLVE_SCRIPTS%
            echo.
            choice /C YN /M "Try again"
            if errorlevel 2 goto :error
            if errorlevel 1 goto :ask_for_path
        )
        if exist "%RESOLVE_SCRIPTS%\Utility" (
            set "RESOLVE_SCRIPTS=%RESOLVE_SCRIPTS%\Utility"
            echo [OK] Created Utility folder: %RESOLVE_SCRIPTS%
        ) else (
            echo [ERROR] Utility folder was not created despite no error!
            choice /C YN /M "Try again"
            if errorlevel 2 goto :error
            if errorlevel 1 goto :ask_for_path
        )
    ) else (
        echo [ERROR] The path does not exist: %RESOLVE_SCRIPTS%
        echo.
        echo Please check:
        echo   - The path is spelled correctly
        echo   - The folders actually exist
        echo   - You have permission to access this location
        echo.
        choice /C YN /M "Try again"
        if errorlevel 2 goto :error
        if errorlevel 1 goto :ask_for_path
    )
) else (
    :: Utility folder already exists
    set "RESOLVE_SCRIPTS=%RESOLVE_SCRIPTS%\Utility"
    echo [OK] Using existing Utility folder: %RESOLVE_SCRIPTS%
)

:: Final verification
if not exist "%RESOLVE_SCRIPTS%" (
    echo [ERROR] Cannot access path: %RESOLVE_SCRIPTS%
    echo.
    choice /C YN /M "Try again"
    if errorlevel 2 goto :error
    if errorlevel 1 goto :ask_for_path
)

:found_resolve
echo.
echo [OK] Resolve Scripts folder: %RESOLVE_SCRIPTS%
echo.

:: Copy launcher and backend folder
echo [2/4] Installing RoughCut launcher and backend...

:: Check if Resolve is running (it might lock the file)
tasklist | findstr /I "Resolve.exe" >nul
if %errorlevel% == 0 (
    echo [WARNING] DaVinci Resolve appears to be running!
    echo [WARNING] Please close Resolve before continuing.
    echo.
    choice /C YC /M "Continue anyway (might fail) or Cancel"
    if errorlevel 2 goto :error
    echo.
)

:: Debug: Show what we're copying where
echo [DEBUG] Copying launcher from: %SOURCE_LAUNCHER%
echo [DEBUG] Copying backend from: %BACKEND_DIR%
echo [DEBUG] Copying to: %RESOLVE_SCRIPTS%

:: Perform the copy and capture result immediately
copy /Y "%SOURCE_LAUNCHER%" "%RESOLVE_SCRIPTS%\" >nul
set "COPY_RESULT=%errorlevel%"

if "%COPY_RESULT%"=="0" (
    echo [OK] RoughCut.lua copied successfully
) else (
    echo.
    echo [ERROR] Failed to copy RoughCut.lua
    echo [ERROR] Copy command returned error code: %COPY_RESULT%
    echo.
    echo Possible causes:
    echo   - DaVinci Resolve is running (close it and try again)
    echo   - Permission denied (run install.bat as Administrator once)
    echo   - Path is incorrect (verify the Utility folder exists)
    echo   - Source file missing: %SOURCE_LAUNCHER%
    echo.
    echo Checking source file:
    if exist "%SOURCE_LAUNCHER%" (
        echo   [OK] Source file found
    ) else (
        echo   [ERROR] Source file NOT found at: %SOURCE_LAUNCHER%
    )
    echo.
    echo Checking target folder:
    if exist "%RESOLVE_SCRIPTS%" (
        echo   [OK] Target folder found
    ) else (
        echo   [ERROR] Target folder NOT found: %RESOLVE_SCRIPTS%
    )
    echo.
    
    :: Special case: Error code 1 might still mean success with xcopy
    :: Let's verify the file actually got copied
    if exist "%RESOLVE_SCRIPTS%\RoughCut.lua" (
        echo.
        echo [INFO] File actually exists at destination despite error code!
        echo [INFO] Installation likely succeeded. Continuing...
        echo.
        goto :copy_success
    )
    
    choice /C YN /M "Try running as Administrator"
    if errorlevel 2 goto :error
    if errorlevel 1 (
        echo.
        echo Please right-click install.bat and select "Run as administrator"
        echo Then try again.
        goto :wait_exit
    )
)

:copy_success
echo [OK] RoughCut.lua installed to Scripts/Utility
echo.

:: Copy the roughcut backend folder
echo [INFO] Copying RoughCut backend folder...
echo [DEBUG] Source: %BACKEND_DIR%
echo [DEBUG] Target: %RESOLVE_SCRIPTS%\roughcut\

:: Use xcopy to copy the entire directory
if exist "%RESOLVE_SCRIPTS%\roughcut\" (
    echo [INFO] Existing roughcut folder found, updating...
    rmdir /S /Q "%RESOLVE_SCRIPTS%\roughcut\" >nul 2>&1
)

xcopy /E /I /Y "%BACKEND_DIR%" "%RESOLVE_SCRIPTS%\roughcut\" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] xcopy returned error code: %errorlevel%
    echo [WARNING] This might be normal. Checking if files exist...
)

:: Verify the copy worked
if exist "%RESOLVE_SCRIPTS%\roughcut\lua\roughcut_main.lua" (
    echo [OK] Backend folder copied successfully
) else (
    echo [ERROR] Failed to copy backend folder!
    echo [ERROR] Expected to find: %RESOLVE_SCRIPTS%\roughcut\lua\roughcut_main.lua
    echo.
    echo Please try:
    echo   1. Close DaVinci Resolve completely
    echo   2. Delete any existing roughcut folder in Scripts
    echo   3. Run install.bat again
    echo.
    choice /C YN /M "Continue anyway (will likely fail)"
    if errorlevel 2 goto :error
)
echo.

:: Check Python
echo [3/4] Checking Python installation...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    python3 --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [WARNING] Python not found!
        echo.
        echo RoughCut requires Python 3.10+ for AI features.
        echo.
        echo Would you like to:
        echo   1. Continue anyway (Lua features only, no AI)
        echo   2. Open Python download page
        echo   3. Cancel installation
        echo.
        choice /C 123 /M "Select option"
        if errorlevel 3 goto :error
        if errorlevel 2 (
            start https://www.python.org/downloads/
            echo.
            echo Please install Python 3.10+, then run this installer again.
            goto :wait_exit
        )
        if errorlevel 1 (
            echo.
            echo [INFO] Continuing without Python. AI features will not be available.
            echo [INFO] You can install Python later and the backend will auto-install.
            goto :skip_python
        )
    )
)

for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
echo [OK] Found Python %PYTHON_VERSION%

:: Check Poetry
echo.
echo [4/4] Checking Poetry package manager...

poetry --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Poetry not found. Installing automatically...
    echo.
    
    :: Install Poetry
    powershell -Command "(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -" 2>nul
    
    if %errorlevel% neq 0 (
        echo [WARNING] Automatic Poetry installation failed.
        echo.
        echo The RoughCut Lua script will attempt to install dependencies
        echo on first run. Just click "Yes" when prompted.
        echo.
        echo Or install manually:
        echo   1. Open PowerShell as Administrator
        echo   2. Run: (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
        echo   3. Close and reopen this installer
        echo.
        goto :skip_poetry
    )
    
    :: Refresh PATH
    call :refresh_path
    
    poetry --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [WARNING] Poetry installed but not in PATH.
        echo [INFO] Please restart this installer, or let auto-install handle it.
        goto :skip_poetry
    )
    
    for /f "tokens=3" %%a in ('poetry --version 2^>^&1') do set POETRY_VERSION=%%a
    echo [OK] Poetry %POETRY_VERSION% installed
) else (
    for /f "tokens=3" %%a in ('poetry --version 2^>^&1') do set POETRY_VERSION=%%a
    echo [OK] Poetry %POETRY_VERSION% found
)

:: Install Python dependencies
echo.
echo Installing RoughCut Python backend...
echo (This may take a few minutes on first run)
echo.

cd /d "%BACKEND_DIR%"
poetry install --no-interaction

if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Backend installation had issues.
    echo [INFO] The Lua script will retry on first run.
    echo.
) else (
    echo [OK] Python backend installed successfully
)

:skip_poetry
:skip_python

:: Success!
:: Verify the files actually exist at the destination
if not exist "%RESOLVE_SCRIPTS%\RoughCut.lua" (
    echo [ERROR] Installation verification failed!
    echo [ERROR] Launcher not found at: %RESOLVE_SCRIPTS%\RoughCut.lua
    echo.
    echo The copy reported success but the file is not in place.
    echo This might be a permissions issue.
    echo.
    goto :error
)

if not exist "%RESOLVE_SCRIPTS%\roughcut\lua\roughcut_main.lua" (
    echo [ERROR] Installation verification failed!
    echo [ERROR] Backend not found at: %RESOLVE_SCRIPTS%\roughcut\lua\roughcut_main.lua
    echo.
    echo The folder copy may have failed.
    echo.
    goto :error
)

cls
echo ============================================
echo     RoughCut Installation Complete!
echo ============================================
echo.
echo [✓] RoughCut.lua installed to: %RESOLVE_SCRIPTS%
echo [✓] Backend folder installed: %RESOLVE_SCRIPTS%\roughcut\
echo [✓] Files verified at destination
echo [✓] Python backend ready (or will auto-install)
echo.
echo NEXT STEPS:
echo -----------
echo 1. RESTART DaVinci Resolve (if it's open)
echo 2. Go to: Workspace ^> Scripts ^> Utility ^> RoughCut
echo 3. The RoughCut window should appear!
echo.
echo TROUBLESHOOTING:
echo ----------------
echo - If script doesn't appear: Restart Resolve completely
echo - If backend fails: It will auto-install when you run RoughCut
echo - For help: See README.md in the roughcut folder
echo.

choice /C YN /M "Would you like to launch DaVinci Resolve now"
if errorlevel 2 goto :done
if errorlevel 1 (
    :: Try to find and launch Resolve
    if exist "C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe" (
        start "" "C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe"
    ) else if exist "C:\Program Files (x86)\Blackmagic Design\DaVinci Resolve\Resolve.exe" (
        start "" "C:\Program Files (x86)\Blackmagic Design\DaVinci Resolve\Resolve.exe"
    ) else (
        echo Could not auto-find Resolve. Please launch it manually.
    )
)

:done
echo.
echo Installation complete! Enjoy using RoughCut! 🎬
echo.
echo Installation location: %RESOLVE_SCRIPTS%
echo.
pause
goto :eof

:error
echo.
echo ============================================
echo     Installation Failed or Cancelled
echo ============================================
echo.
echo Please check the error messages above.
echo.
echo For detailed help, see: install-guide.md
echo.
echo Press any key to exit...
pause >nul
exit /b 1

:wait_exit
echo.
echo Press any key to exit...
pause >nul
exit /b 0

:refresh_path
:: Refresh environment variables without restarting
for /f "tokens=*" %%a in ('path') do set "PATH=%%a"
for /f "skip=2 tokens=3*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do (
    set "USER_PATH=%%a %%b"
    setx PATH "%%a %%b" >nul 2>&1
)
if not "%USER_PATH%"=="" set "PATH=%PATH%;%USER_PATH%"
goto :eof
