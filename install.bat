@echo off
setlocal EnableDelayedExpansion

:: Create log file for debugging
set "INSTALL_LOG=%TEMP%\roughcut_install.log"
echo RoughCut Install Log - %date% %time% > "%INSTALL_LOG%"
echo ============================================ >> "%INSTALL_LOG%"

echo ============================================
echo     RoughCut Installer for Windows
echo ============================================
echo.
echo [INFO] Log file: %INSTALL_LOG%

:: Configuration
set "LAUNCHER_NAME=RoughCut.lua"
set "SOURCE_LAUNCHER=%~dp0roughcut\RoughCut.lua"
set "BACKEND_DIR=%~dp0roughcut"

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
echo [1/5] Looking for DaVinci Resolve installation...
echo.

set "RESOLVE_SCRIPTS="

:: Check common Windows paths
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

:: Not found - ask user
cls
echo ============================================
echo     RoughCut Installer for Windows
echo ============================================
echo.
echo [ERROR] Could not automatically find or create DaVinci Resolve Scripts folder.
echo.
echo Tip: Copy one of these paths, paste in File Explorer address bar:
echo.
echo %%APPDATA%%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\
echo.
echo Paste the full path to the folder:
set /p "RESOLVE_SCRIPTS=Path: "

if "%RESOLVE_SCRIPTS%"=="" (
    echo.
    echo Installation cancelled by user.
    pause
    exit /b 1
)

:: Remove trailing backslash if present
if "%RESOLVE_SCRIPTS:~-1%"=="\" set "RESOLVE_SCRIPTS=%RESOLVE_SCRIPTS:~0,-1%"

if not exist "%RESOLVE_SCRIPTS%" (
    echo [ERROR] The path does not exist: %RESOLVE_SCRIPTS%
    pause
    exit /b 1
)

:found_resolve
echo.
echo [OK] Resolve Scripts folder: %RESOLVE_SCRIPTS%
echo.

:: Step 2: Build Electron UI FIRST (before copying anything)
echo [2/5] Building Electron UI...
echo.
echo ============================================
echo ELECTRON BUILD DIAGNOSTICS
echo ============================================
echo.

if exist "%~dp0roughcut\electron\package.json" (
    echo [DIAGNOSTIC] Found Electron app at: %~dp0roughcut\electron\
    echo.
    
    :: DIAGNOSTIC: Check what's in electron folder before build
    echo [DIAGNOSTIC] Contents of %~dp0roughcut\electron\ before build:
    dir /b "%~dp0roughcut\electron\" 2>nul | findstr /v "node_modules" || echo   (empty or no access)
    echo.
    
    :: DIAGNOSTIC: Check if dist exists before build
    if exist "%~dp0roughcut\electron\dist" (
        echo [DIAGNOSTIC] dist\ folder EXISTS before build
        dir /b "%~dp0roughcut\electron\dist\" 2>nul || echo   (folder exists but empty)
        echo.
    ) else (
        echo [DIAGNOSTIC] dist\ folder does NOT exist yet (expected)
        echo.
    )
    
    :: Check for npm
    echo [DIAGNOSTIC] Checking for npm...
    where npm >nul 2>&1
    if %errorlevel% neq 0 (
        where npm.cmd >nul 2>&1
        if %errorlevel% neq 0 (
            echo [WARNING] Node.js/npm not found in PATH!
            echo [WARNING] Electron UI will be copied but may not work.
            echo [INFO] Install Node.js from https://nodejs.org/
            echo.
            goto :skip_electron_build
        )
    )
    echo [DIAGNOSTIC] npm found in PATH
echo.
    
    :: Check if dist/main.js already exists
    if exist "%~dp0roughcut\electron\dist\main.js" (
        echo [DIAGNOSTIC] dist\main.js already exists - skipping npm install/build
        echo [INFO] Skipping rebuild. Delete dist\ folder to force rebuild.
        echo.
        goto :electron_built
    )
    
    :: Install dependencies
    echo [INFO] Installing Electron dependencies (npm install)...
    echo [INFO] This may take 2-3 minutes on first run...
    echo [INFO] You will see npm output below...
    echo.
    
    cd /d "%~dp0roughcut\electron"
    
    :: Run npm install - output shown on screen
    call npm install
    set "NPM_INSTALL_ERROR=%errorlevel%"
    
    if %NPM_INSTALL_ERROR% neq 0 (
        echo.
        echo [ERROR] npm install FAILED with exit code %NPM_INSTALL_ERROR%!
        echo.
        pause
        goto :skip_electron_build
    ) else (
        echo.
        echo [OK] npm install completed successfully
        echo.
    )
    
    :: Build the app
    echo [INFO] Building Electron app (npm run build)...
    echo [INFO] This may take 1-2 minutes...
    echo [INFO] You will see build output below...
    echo.
    
    :: Run npm build - output shown on screen
    call npm run build
    set "NPM_BUILD_ERROR=%errorlevel%"
    
    if %NPM_BUILD_ERROR% neq 0 (
        echo.
        echo [ERROR] npm run build FAILED with exit code %NPM_BUILD_ERROR%!
        echo.
        pause
        goto :skip_electron_build
    ) else (
        echo.
        echo [OK] npm run build completed successfully
        echo.
    )
    
    :: DIAGNOSTIC: Check dist folder after build
    echo ============================================
    echo [DIAGNOSTIC] Checking build output...
    echo ============================================
    if exist "%~dp0roughcut\electron\dist" (
        echo [DIAGNOSTIC] dist\ folder was created
        echo.
        echo [DIAGNOSTIC] Contents of dist\ folder:
        dir /s /b "%~dp0roughcut\electron\dist\" 2>nul
        echo.
    ) else (
        echo [DIAGNOSTIC] ERROR: dist\ folder was NOT created!
        echo.
    )
    
    :: Verify dist/main.js was created
    if not exist "%~dp0roughcut\electron\dist\main.js" (
        echo [WARNING] Build completed but dist\main.js not found!
        echo [WARNING] Build process may have failed silently.
        echo.
        echo [DIAGNOSTIC] Listing ALL files in electron folder:
        dir /s /b "%~dp0roughcut\electron\" 2>nul | findstr /v "node_modules"
        echo.
        pause
        goto :skip_electron_build
    ) else (
        echo [OK] Verified: dist\main.js exists
        echo.
    )
    
    :electron_built
    echo [OK] Electron UI ready
    echo.
) else (
    echo [INFO] No Electron app found at: %~dp0roughcut\electron\
    echo [INFO] Skipping Electron build.
    echo.
)

:skip_electron_build

:: Step 3: Copy files to Resolve
echo [3/5] Installing RoughCut to DaVinci Resolve...
echo.

:: Check if Resolve is running
tasklist | findstr /I "Resolve.exe" >nul
if %errorlevel% == 0 (
    echo [WARNING] DaVinci Resolve appears to be running!
    echo [WARNING] Please close Resolve before continuing.
    echo.
    choice /C YC /M "Continue anyway (might fail) or Cancel"
    if errorlevel 2 exit /b 1
    echo.
)

:: Copy launcher
echo [INFO] Copying RoughCut.lua...
copy /Y "%SOURCE_LAUNCHER%" "%RESOLVE_SCRIPTS%\" >nul
if %errorlevel% neq 0 (
    echo [ERROR] Failed to copy RoughCut.lua
    echo [ERROR] Make sure Resolve is closed and you have permissions.
    echo.
    pause
    exit /b 1
)
echo [OK] RoughCut.lua installed
echo.

:: Copy roughcut folder
echo [INFO] Copying roughcut\ folder (this includes Electron UI if built)...
if exist "%RESOLVE_SCRIPTS%\roughcut\" (
    echo [INFO] Removing existing roughcut folder...
    rmdir /S /Q "%RESOLVE_SCRIPTS%\roughcut\" >nul 2>&1
)

echo [DIAGNOSTIC] Source: %~dp0roughcut\
echo [DIAGNOSTIC] Target: %RESOLVE_SCRIPTS%\roughcut\
echo.

xcopy /E /I /Y "%~dp0roughcut\" "%RESOLVE_SCRIPTS%\roughcut\"
set "XCOPY_RESULT=%errorlevel%"

if %XCOPY_RESULT% neq 0 (
    echo.
    echo [WARNING] xcopy returned error code: %XCOPY_RESULT%
    echo [WARNING] Checking if files exist anyway...
    echo.
)

:: Verify the copy worked
echo [DIAGNOSTIC] Verifying copy...
if exist "%RESOLVE_SCRIPTS%\roughcut\lua\roughcut_main.lua" (
    echo [OK] roughcut\lua\roughcut_main.lua found at destination
) else (
    echo [ERROR] roughcut\lua\roughcut_main.lua NOT found!
)

:: DIAGNOSTIC: Check if dist was copied
echo.
echo [DIAGNOSTIC] Checking if Electron dist\ was copied...
if exist "%RESOLVE_SCRIPTS%\roughcut\electron\dist" (
    echo [OK] electron\dist\ folder exists at destination
    echo [DIAGNOSTIC] Contents:
    dir /b "%RESOLVE_SCRIPTS%\roughcut\electron\dist\" 2>nul || echo (empty)
) else (
    echo [WARNING] electron\dist\ folder NOT found at destination!
    echo [WARNING] Electron UI will not work.
)

if exist "%RESOLVE_SCRIPTS%\roughcut\electron\dist\main.js" (
    echo [OK] electron\dist\main.js exists at destination - Electron ready!
) else (
    echo [ERROR] electron\dist\main.js NOT found at destination!
    echo [ERROR] Electron UI will fail to launch.
)

echo.

:: Step 4: Check Python
echo [4/5] Checking Python installation...
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    python3 --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [WARNING] Python not found!
        echo [INFO] RoughCut will use Lua features only (no AI).
        echo [INFO] Install Python 3.10+ for full functionality.
        echo.
    ) else (
        for /f "tokens=2" %%a in ('python3 --version 2^>^&1') do echo [OK] Found Python %%a
    )
) else (
    for /f "tokens=2" %%a in ('python --version 2^>^&1') do echo [OK] Found Python %%a
)

:: Step 5: Summary
echo.
echo ============================================
echo     RoughCut Installation Complete!
echo ============================================
echo.
echo [✓] RoughCut.lua installed to: %RESOLVE_SCRIPTS%
echo [✓] Backend folder: %RESOLVE_SCRIPTS%\roughcut\
if exist "%RESOLVE_SCRIPTS%\roughcut\electron\dist\main.js" (
    echo [✓] Electron UI built and installed correctly
) else (
    echo [✗] Electron UI NOT installed correctly - will fail on launch
    if exist "%~dp0roughcut\electron\dist\main.js" (
        echo [INFO] Build succeeded in source but copy failed
    ) else (
        echo [INFO] Build may have failed or was skipped
    )
)
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
echo - For help: See README.md in the roughcut folder
echo.
echo ============================================
echo DIAGNOSTIC INFO FOR DEBUGGING:
echo ============================================
echo Source roughcut\electron\dist\main.js: %~dp0roughcut\electron\dist\main.js
echo Dest   roughcut\electron\dist\main.js: %RESOLVE_SCRIPTS%\roughcut\electron\dist\main.js
echo.
echo Source exists: 
if exist "%~dp0roughcut\electron\dist\main.js" (echo YES) else (echo NO)
echo Dest   exists: 
if exist "%RESOLVE_SCRIPTS%\roughcut\electron\dist\main.js" (echo YES) else (echo NO)
echo ============================================
echo.

choice /C YN /M "Launch DaVinci Resolve now"
if errorlevel 2 goto :done
if errorlevel 1 (
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
echo Installation complete
echo.
echo Location: %RESOLVE_SCRIPTS%
echo.
echo Debug log: %INSTALL_LOG%
echo.

:end_of_script
echo.
echo ============================================
echo PRESS ANY KEY TO EXIT
echo ============================================
echo.
set /p "EXITCONFIRM=Press Enter to exit..."
exit /b 0

:error
echo.
echo ============================================
echo     Installation Failed
echo ============================================
echo.
echo Please check the error messages above.
echo.
echo Debug log: %INSTALL_LOG%
echo.
goto :end_of_script
