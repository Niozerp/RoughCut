-- RoughCut Installation Orchestrator
-- Handles Python backend auto-installation from Lua side
-- Coordinates detection, installation, and UI updates

local installOrchestrator = {}

-- Import modules
local installDialog = require("ui.install_dialog")
local processUtils = require("utils.process")

-- State tracking
local installProcessHandle = nil
local isInstalling = false
local projectPath = nil
local requestIdCounter = 0

-- Reset all module-level state
local function resetState()
    installProcessHandle = nil
    isInstalling = false
    projectPath = nil
    requestIdCounter = 0
end

-- Initialize random seed once
math.randomseed(os.time())

-- Generate unique request ID
local function generateRequestId()
    requestIdCounter = requestIdCounter + 1
    local timestamp = tostring(os.time())
    local random = tostring(math.random(100, 999))
    return "install_" .. timestamp .. "_" .. random .. "_" .. tostring(requestIdCounter)
end

-- Check if roughcut Python package is installed system-wide
-- @return boolean true if roughcut is installed globally
local function isRoughcutInstalledGlobally()
    local GLOBAL_VERIFY_MARKER = "INSTALLED"
    
    -- Try importing roughcut with the system's default Python
    local checkCmd = {"python", "-c", "import roughcut; print('" .. GLOBAL_VERIFY_MARKER .. "')"}
    local result = processUtils.run(checkCmd, nil, 5)
    if result.success and result.stdout and #result.stdout > 0 and result.stdout:find(GLOBAL_VERIFY_MARKER) then
        return true
    end
    
    -- Try with python3
    checkCmd = {"python3", "-c", "import roughcut; print('" .. GLOBAL_VERIFY_MARKER .. "')"}
    result = processUtils.run(checkCmd, nil, 5)
    return result.success and result.stdout and #result.stdout > 0 and result.stdout:find(GLOBAL_VERIFY_MARKER)
end

-- Find pyproject.toml in common locations
-- Searches common locations including git repo and environment variable
-- @return string|nil path to directory containing pyproject.toml, or nil if not found
local function findPyprojectToml()
    print("RoughCut: Searching for pyproject.toml...")
    
    -- Helper to validate that a pyproject.toml belongs to roughcut project
    local function validateRoughcutToml(path)
        local f = io.open(path, "r")
        if not f then
            return false
        end
        
        local content = f:read("*a")
        f:close()
        
        -- Check for roughcut-specific content (name field or roughcut in content)
        if content and content:find('name%s*=%s*["\']roughcut["\']') then
            return true
        end
        if content and content:find('roughcut') then
            return true
        end
        return false
    end
    
    -- Helper to detect git repo root
    local function findGitRoot(startPath)
        local current = startPath
        for i = 1, 5 do  -- Limit depth
            local gitPath = current .. "/.git"
            local f = io.open(gitPath, "r")
            if f then
                f:close()
                return current
            end
            -- Go up one directory
            local parent = current:match("^(.*)[/\\][^/\\]+$")
            if not parent or parent == current then
                break
            end
            current = parent
        end
        return nil
    end
    
    local paths = {}
    
    -- Add project path and parents
    if projectPath then
        table.insert(paths, projectPath .. "/pyproject.toml")
        table.insert(paths, projectPath .. "/../pyproject.toml")
        table.insert(paths, projectPath .. "/../../pyproject.toml")
        table.insert(paths, projectPath .. "/../../../pyproject.toml")
        
        -- Try with forward slashes converted
        local pathFwd = projectPath:gsub("\\", "/")
        table.insert(paths, pathFwd .. "/pyproject.toml")
        table.insert(paths, pathFwd .. "/../../pyproject.toml")
    end
    
    -- Try to detect git repo root
    if projectPath then
        local gitRoot = findGitRoot(projectPath)
        if gitRoot then
            table.insert(paths, gitRoot .. "/roughcut/pyproject.toml")
            table.insert(paths, gitRoot .. "/pyproject.toml")
        end
    end
    
    -- Environment variable
    if os.getenv("ROUGHCUT_SOURCE_PATH") then
        table.insert(paths, os.getenv("ROUGHCUT_SOURCE_PATH") .. "/pyproject.toml")
    end
    
    for i, path in ipairs(paths) do
        print("RoughCut: Checking path " .. i .. ": " .. path)
        
        -- Use io.open for file existence check (more reliable than python)
        local f = io.open(path, "r")
        if f then
            f:close()
            -- Validate it belongs to roughcut
            if validateRoughcutToml(path) then
                print("RoughCut: FOUND roughcut pyproject.toml at: " .. path)
                -- Return the directory (handle both forward and backward slashes)
                local dir = path:gsub("[/\\][^/\\]+$", "")
                print("RoughCut: Source directory: " .. dir)
                return dir
            else
                print("RoughCut: Found pyproject.toml but not a roughcut project: " .. path)
            end
        else
            print("RoughCut: Not found at: " .. path)
        end
    end
    
    print("RoughCut: pyproject.toml not found in any of " .. #paths .. " locations")
    return nil
end

-- Verification constants
local VERIFY_OK = "OK"

-- Deploy Lua plugin files to Resolve Scripts folder
-- @param projectDir Absolute path to project directory
-- @return boolean success, string error
local function deployLuaPlugin(projectDir)
    -- Validate input first (Fix #1, #8)
    if not projectDir or projectDir == "" then
        print("RoughCut: ERROR - projectDir is nil or empty")
        return false, "projectDir is required and cannot be empty"
    end
    
    print("RoughCut: Deploying Lua plugin from: " .. tostring(projectDir))
    
    local deployScript = projectDir .. "/scripts/deploy.py"
    
    print("RoughCut: Checking for deploy script at: " .. deployScript)
    
    -- Check if deploy script exists
    -- Use single quotes for Python string to avoid shell escaping issues (Fix #2)
    local checkCmd = {"python", "-c", "import os; print('" .. VERIFY_OK .. "' if os.path.exists('" .. deployScript .. "') else 'MISSING')"}
    print("RoughCut: Running deploy script check: " .. table.concat(checkCmd, " "))
    local checkResult = processUtils.run(checkCmd, nil, 5)
    print("RoughCut: Deploy script check result - success: " .. tostring(checkResult.success) .. ", stdout: " .. tostring(checkResult.stdout or "nil"))
    
    local pythonFound = false
    if checkResult.success and checkResult.stdout and checkResult.stdout:find(VERIFY_OK) then
        pythonFound = true
    else
        -- Try python3
        checkCmd[1] = "python3"
        print("RoughCut: Retrying with python3...")
        checkResult = processUtils.run(checkCmd, nil, 5)
        print("RoughCut: Python3 check result - success: " .. tostring(checkResult.success) .. ", stdout: " .. tostring(checkResult.stdout or "nil"))
        
        if checkResult.success and checkResult.stdout and checkResult.stdout:find(VERIFY_OK) then
            pythonFound = true
        end
    end
    
    if not pythonFound then
        local errorMsg = "Deploy script not found at: " .. deployScript
        if not checkResult.success then
            errorMsg = errorMsg .. " (Python command failed: " .. tostring(checkResult.error or "unknown error") .. ")"
        end
        print("RoughCut: ERROR - " .. errorMsg)
        return false, errorMsg
    end
    
    print("RoughCut: Deploy script found, executing...")
    
    -- Run deploy script with --force to handle already-installed case
    -- Note: --force is intentional for auto-install; overwrites existing without prompt (Fix #7)
    local deployResult = processUtils.runPython(deployScript, {"--project-path", projectDir, "--force"}, projectDir, 60)
    
    print("RoughCut: Deploy result - success: " .. tostring(deployResult.success))
    print("RoughCut: Deploy result - exitCode: " .. tostring(deployResult.exitCode or "nil"))
    print("RoughCut: Deploy result - stdout: " .. tostring(deployResult.stdout or "nil"))
    print("RoughCut: Deploy result - stderr: " .. tostring(deployResult.stderr or "nil"))
    
    -- Check for errors even on apparent success (Fix #4)
    if deployResult.stderr and deployResult.stderr:find("[Ee]rror") then
        print("RoughCut: WARNING - stderr contains error indicators")
    end
    
    -- Validate exitCode explicitly (Fix #5, #10)
    local validSuccess = deployResult.success
    if deployResult.exitCode ~= nil and deployResult.exitCode ~= 0 then
        validSuccess = false
    end
    
    if not validSuccess then
        return false, "Deployment failed: " .. (deployResult.stderr or deployResult.stdout or "Unknown error")
    end
    
    print("RoughCut: Deployment completed successfully")
    return true, nil
end

-- Check if Python backend is already installed
-- @return table with status information
function installOrchestrator.checkInstallation(projectDir)
    projectPath = projectDir
    
    if not projectPath then
        print("RoughCut: Error - Project path not provided")
        return { ready = false, error = "Project path not provided" }
    end
    
    -- First check if roughcut is globally installed
    if isRoughcutInstalledGlobally() then
        return { ready = true, global = true }
    end
    
    -- Find where pyproject.toml is located
    local sourceDir = findPyprojectToml()
    if not sourceDir then
        return { 
            ready = false, 
            error = "pyproject.toml not found. Set ROUGHCUT_SOURCE_PATH environment variable to the source directory."
        }
    end
    
    -- Run detection via install.py from the source directory
    local detectId = "detect_" .. tostring(os.time())
    local command = {
        "python3",
        "scripts/install.py",
        "--project-path",
        sourceDir
    }
    
    -- Try python3 first, then python
    if not processUtils.commandExists("python3") then
        command[1] = "python"
    end
    
    -- For now, run synchronously with runPython (removed unnecessary spawn/close)
    local scriptPath = sourceDir .. "/scripts/install.py"
    local result = processUtils.runPython(scriptPath, {"--project-path", sourceDir}, sourceDir, 30)
    
    -- Parse JSON response from stdout using simple parsing
    if result.success and result.stdout then
        for line in result.stdout:gmatch("[^\r\n]+") do
            -- Look for JSON objects with "result" field containing "ready"
            local ok, jsonData = pcall(function()
                -- Try to extract ready field from various JSON formats
                local ready = line:match('"ready"%s*:%s*(true)')
                if ready then
                    return { ready = true }
                end
                local notReady = line:match('"ready"%s*:%s*(false)')
                if notReady then
                    return { ready = false }
                end
                -- Also check for result objects
                local resultReady = line:match('"result".-"ready"%s*:%s*(true)')
                if resultReady then
                    return { ready = true }
                end
                local resultNotReady = line:match('"result".-"ready"%s*:%s*(false)')
                if resultNotReady then
                    return { ready = false }
                end
                return nil
            end)
            
            if ok and jsonData then
                return jsonData
            end
        end
    end
    
    -- If we can't parse, assume not ready
    return { ready = false, error = "Could not verify installation status" }
end

-- Start the installation process
-- @param uiManager Resolve UI Manager
-- @param projectDir Absolute path to project directory
-- @param onComplete Callback function(status) called when installation completes
-- @param onError Callback function(error) called on error
-- @return boolean indicating if installation was started
function installOrchestrator.startInstallation(uiManager, projectDir, onComplete, onError)
    -- Reset state at the start of each installation
    resetState()
    
    if isInstalling then
        print("RoughCut: Installation already in progress")
        return false
    end
    
    projectPath = projectDir
    isInstalling = true
    
    -- Create and show install dialog
    local dialog = installDialog.create(uiManager)
    if not dialog then
        isInstalling = false
        if onError then
            onError("Failed to create installation dialog")
        end
        return false
    end
    
    installDialog.show()
    
    -- Set up cancel callback
    installDialog.setCancelCallback(function()
        print("RoughCut: Cancelling installation...")
        if installProcessHandle and installProcessHandle.handle then
            processUtils.kill(installProcessHandle.handle)
            installProcessHandle = nil
        end
        isInstalling = false
        installDialog.close()
    end)
    
    -- Start installation in background
    local installId = generateRequestId()
    
    -- For Resolve Lua, we'll need to use a cooperative approach
    -- since we can't easily run async operations
    local function doInstallStep(step)
        if not isInstalling or installDialog.isCancelled() then
            return
        end
        
        if step == 1 then
            -- Check Python
            installDialog.updateProgress(1, 6, "Checking Python installation...", 10)
            
            local result = processUtils.run({"python3", "--version"}, nil, 5)
            if not result.success then
                result = processUtils.run({"python", "--version"}, nil, 5)
            end
            
            if not result.success then
                isInstalling = false
                installDialog.showError("Python not found. Please install Python 3.10 or later.")
                if onError then
                    onError("Python not found")
                end
                return
            end
            
            -- Continue to next step
            doInstallStep(2)
            
        elseif step == 2 then
            -- Check Poetry
            installDialog.updateProgress(2, 6, "Checking Poetry installation...", 25)
            print("RoughCut: Checking for Poetry...")
            
            -- Try multiple Poetry detection strategies
            local poetryCmd = nil
            local poetryTried = {}
            
            -- Strategy 1: Try "poetry" in PATH
            print("RoughCut: Trying 'poetry' command...")
            table.insert(poetryTried, "poetry")
            local result = processUtils.run({"poetry", "--version"}, nil, 5)
            if result.success then
                print("RoughCut: Poetry found in PATH")
                poetryCmd = "poetry"
            else
                print("RoughCut: 'poetry' not found in PATH, error: " .. tostring(result.error or "none"))
            end
            
            -- Strategy 2: Try common Windows paths
            if not poetryCmd then
                local localAppData = os.getenv("LOCALAPPDATA")
                local username = os.getenv("USERNAME") or "User"
                
                local commonPaths = {
                    "C:\\Python310\\Scripts\\poetry",
                    "C:\\Python311\\Scripts\\poetry",
                    "C:\\Python312\\Scripts\\poetry",
                }
                
                -- Add user-specific paths only if env vars are set
                if username then
                    table.insert(commonPaths, "C:\\Users\\" .. username .. "\\AppData\\Roaming\\Python\\Python310\\Scripts\\poetry")
                    table.insert(commonPaths, "C:\\Users\\" .. username .. "\\AppData\\Roaming\\Python\\Python311\\Scripts\\poetry")
                    table.insert(commonPaths, "C:\\Users\\" .. username .. "\\AppData\\Roaming\\Python\\Python312\\Scripts\\poetry")
                end
                
                if localAppData then
                    table.insert(commonPaths, localAppData .. "\\Programs\\Python\\Python310\\Scripts\\poetry")
                    table.insert(commonPaths, localAppData .. "\\Programs\\Python\\Python311\\Scripts\\poetry")
                    table.insert(commonPaths, localAppData .. "\\Programs\\Python\\Python312\\Scripts\\poetry")
                end
                
                for _, path in ipairs(commonPaths) do
                    if path then
                        print("RoughCut: Trying Poetry at: " .. path)
                        table.insert(poetryTried, path)
                        result = processUtils.run({path, "--version"}, nil, 5)
                        if result.success then
                            print("RoughCut: Poetry found at: " .. path)
                            poetryCmd = path
                            break
                        end
                    end
                end
            end
            
            -- Strategy 3: Try "poetry.exe"
            if not poetryCmd then
                print("RoughCut: Trying 'poetry.exe'...")
                table.insert(poetryTried, "poetry.exe")
                result = processUtils.run({"poetry.exe", "--version"}, nil, 5)
                if result.success then
                    print("RoughCut: Poetry found as poetry.exe")
                    poetryCmd = "poetry.exe"
                end
            end
            
            if not poetryCmd then
                -- Need to install Poetry - requires user consent
                isInstalling = false
                local triedList = table.concat(poetryTried, ", ")
                print("RoughCut: ERROR - Poetry not found. Tried: " .. triedList)
                -- Escape paths in error message to prevent injection
                local safeTriedList = triedList:gsub("[&<>\"']", function(c) 
                    return "&#" .. string.byte(c) .. ";" 
                end)
                installDialog.showError("Poetry not found in PATH. Install with: pip install poetry\n\nTried: " .. safeTriedList)
                installDialog.setCancelEnabled(true)
                
                -- Update cancel button to close dialog
                installDialog.setCancelCallback(function()
                    installDialog.close()
                end)
                
                if onError then
                    onError("Poetry not installed - tried: " .. triedList)
                end
                return
            end
            
            -- Store poetry command for later use
            installOrchestrator._poetryCmd = poetryCmd
            print("RoughCut: Using Poetry command: " .. poetryCmd)
            
            doInstallStep(3)
            
        elseif step == 3 then
            -- Install dependencies
            installDialog.updateProgress(3, 6, "Installing dependencies...", 50)
            
            -- First, check if roughcut is already installed globally
            print("RoughCut: Checking if roughcut is already installed globally...")
            if isRoughcutInstalledGlobally() then
                print("RoughCut: Python backend already installed globally - skipping local installation")
                installDialog.updateProgress(3, 6, "Python backend already installed globally", 95)
                -- Skip to verification step
                doInstallStep(4)
                return
            end
            
            -- Get the Poetry command we found earlier
            local poetryCmd = installOrchestrator._poetryCmd or "poetry"
            
            -- Find pyproject.toml in source directory
            local sourceDir = findPyprojectToml()
            if not sourceDir then
                isInstalling = false
                print("RoughCut: ERROR - pyproject.toml not found in any location")
                local sourcePath = os.getenv("ROUGHCUT_SOURCE_PATH") or "<source_directory>"
                local errorMsg = "Python backend not found.\n\n" ..
                                 "pyproject.toml not found in any of these locations:\n" ..
                                 "  - Current project path: " .. tostring(projectPath) .. "/pyproject.toml\n" ..
                                 "  - Parent directories (looking for git repo)\n" ..
                                 "  - ROUGHCUT_SOURCE_PATH environment variable\n\n" ..
                                 "To fix:\n" ..
                                 "1. Install from the source directory: cd " .. sourcePath .. " && poetry install\n" ..
                                 "2. OR set ROUGHCUT_SOURCE_PATH to the source directory containing pyproject.toml"
                installDialog.showError(errorMsg)
                if onError then
                    onError("pyproject.toml not found in any location")
                end
                return
            end
            
            -- Store source directory for later steps
            installOrchestrator._sourceDir = sourceDir
            
            print("RoughCut: Found pyproject.toml in: " .. sourceDir)
            -- Safely truncate sourceDir for display (with nil check)
            local displayDir = sourceDir
            if displayDir and #displayDir > 30 then
                displayDir = "..." .. displayDir:sub(-30)
            end
            installDialog.updateProgress(3, 6, "Found source at: " .. (displayDir or "unknown"), 55)
            
            -- Run poetry install from the source directory
            local command = {poetryCmd, "install", "--no-interaction"}
            print("RoughCut: Running command: " .. table.concat(command, " "))
            print("RoughCut: Working directory: " .. sourceDir)
            
            installProcessHandle = processUtils.spawn(command, sourceDir)
            
            print("RoughCut: Spawn result - handle exists: " .. tostring(installProcessHandle.handle ~= nil))
            print("RoughCut: Spawn result - error: " .. tostring(installProcessHandle.error or "none"))
            
            if not installProcessHandle.handle then
                isInstalling = false
                local errorMsg = "Could not start poetry process: " .. tostring(installProcessHandle.error or "Unknown error")
                print("RoughCut: ERROR - " .. errorMsg)
                installDialog.showError(errorMsg .. "\n\nPoetry command tried: " .. poetryCmd)
                if onError then
                    onError(errorMsg)
                end
                return
            end
            
            if not isInstalling or installDialog.isCancelled() then
                if installProcessHandle and installProcessHandle.handle then
                    processUtils.close(installProcessHandle.handle)
                end
                return
            end
            
            -- Synchronous reading is used below, this async function is not used
            -- Keeping for future async implementation but marked as unused
            local function readNextLine_unused()
                if not isInstalling or installDialog.isCancelled() then
                    if installProcessHandle and installProcessHandle.handle then
                        processUtils.close(installProcessHandle.handle)
                    end
                    return
                end
                
                if not installProcessHandle or not installProcessHandle.handle then
                    return
                end
                
                local line = processUtils.readLine(installProcessHandle.handle)
                if line then
                    lineCount = lineCount + 1
                    -- Update progress every few lines
                    if lineCount % 5 == 0 then
                        local percent = math.min(50 + (lineCount / 20) * 45, 95)
                        installDialog.updateProgress(3, 6, line:sub(1, 40), percent)
                    end
                    -- Continue reading
                    -- In real Resolve, we'd use a timer or next idle callback
                    -- For now, we can't easily simulate async in pure Lua
                else
                    -- End of output, close and continue
                    if installProcessHandle and installProcessHandle.handle then
                        processUtils.close(installProcessHandle.handle)
                    end
                    doInstallStep(4)
                end
            end
            
            -- For now, do synchronous read
            local outputLines = {}
            local lineCount = 0
            print("RoughCut: Reading poetry install output...")
            while true do
                local line = processUtils.readLine(installProcessHandle.handle)
                if not line then
                    print("RoughCut: End of output reached (line count: " .. lineCount .. ")")
                    break
                end
                lineCount = lineCount + 1
                table.insert(outputLines, line)
                if lineCount <= 10 then
                    print("RoughCut: Output line " .. lineCount .. ": " .. line:sub(1, 100))
                elseif lineCount == 11 then
                    print("RoughCut: ... (more output lines)")
                end
            end
            
            -- Check exit code!
            print("RoughCut: Closing process handle and checking exit code...")
            local closeResult = nil
            if installProcessHandle and installProcessHandle.handle then
                closeResult = processUtils.close(installProcessHandle.handle)
            else
                closeResult = { success = false, exitCode = -1, error = "Invalid process handle" }
            end
            
            -- Ensure closeResult has required fields
            if not closeResult then
                closeResult = { success = false, exitCode = -1, error = "Close returned nil" }
            end
            
            print("RoughCut: Exit code: " .. tostring(closeResult.exitCode))
            print("RoughCut: Success: " .. tostring(closeResult.success))
            
            -- Use closeResult.success for decision making
            if not closeResult.success then
                -- Show error with output
                local outputText = table.concat(outputLines, "\n")
                local errorMsg = "poetry install failed with exit code " .. tostring(closeResult.exitCode or "unknown")
                print("RoughCut: ERROR - " .. errorMsg)
                print("RoughCut: Full output:\n" .. outputText)
                
                isInstalling = false
                local userErrorMsg = "Installation failed (exit code " .. tostring(closeResult.exitCode or "unknown") .. ").\n\n"
                if closeResult.exitCode == -1 then
                    userErrorMsg = userErrorMsg .. "Exit code -1 means the process couldn't start.\n" ..
                                   "Poetry may not be installed or not in PATH.\n" ..
                                   "Poetry command used: " .. poetryCmd
                elseif outputText == "" then
                    userErrorMsg = userErrorMsg .. "No output captured - process may have failed to start."
                else
                    userErrorMsg = userErrorMsg .. "Check the console logs for full output."
                end
                
                installDialog.showError(userErrorMsg)
                if onError then onError(errorMsg) end
                return
            end
            
            print("RoughCut: poetry install completed successfully")
            doInstallStep(4)
            
        elseif step == 4 then
            -- Verify installation
            installDialog.updateProgress(4, 6, "Verifying installation...", 95)
            print("RoughCut: Verifying installation...")
            
            -- Check if roughcut is globally installed (fast path)
            if isRoughcutInstalledGlobally() then
                print("RoughCut: Verified - roughcut is installed globally")
                doInstallStep(5)
                return
            end
            
            -- Check if backend is now importable via poetry run
            local poetryCmd = installOrchestrator._poetryCmd or "poetry"
            local verifyCommand = {
                poetryCmd, "run", "python", "-c",
                "import roughcut; print('" .. VERIFY_OK .. "')"
            }
            -- Use the source directory we found earlier, or fall back to finding it
            local sourceDir = installOrchestrator._sourceDir or findPyprojectToml()
            if not sourceDir then
                sourceDir = projectPath  -- Last resort fallback
            end
            print("RoughCut: Running verification command from: " .. sourceDir)
            print("RoughCut: Command: " .. table.concat(verifyCommand, " "))
            local result = processUtils.run(verifyCommand, sourceDir, 30)
            
            -- Validate exitCode exists (Fix #5)
            local exitCode = result.exitCode
            if exitCode == nil then
                -- Try to derive from success flag
                exitCode = result.success and 0 or -1
            end
            
            print("RoughCut: Verification result - success: " .. tostring(result.success))
            print("RoughCut: Verification result - exitCode: " .. tostring(exitCode))
            print("RoughCut: Verification result - stdout: " .. tostring(result.stdout or "nil"))
            print("RoughCut: Verification result - stderr: " .. tostring(result.stderr or "nil"))
            
            -- Verification passes if command succeeded (exit code 0)
            -- stdout check is secondary - io.popen on Windows can have empty stdout even on success
            -- Fix #10: Use exitCode for primary validation
            local verified = (exitCode == 0)
            
            -- Fix #6: Handle empty stdout properly - check length > 0 before find()
            if not verified and result.stdout and #result.stdout > 0 and result.stdout:find(VERIFY_OK) then
                verified = true
            end
            
            if not verified then
                isInstalling = false
                print("RoughCut: ERROR - Installation verification failed")
                installDialog.showError("Installation verification failed. Please try again.")
                if onError then
                    onError("Verification failed")
                end
                return
            end
            
            print("RoughCut: Installation verified successfully")
            doInstallStep(5)
            
        elseif step == 5 then
            -- Deploy Lua plugin files
            installDialog.updateProgress(5, 6, "Deploying plugin files to Resolve...", 95)
            
            -- Use the source directory we found earlier, or fall back to projectPath
            local sourceDir = installOrchestrator._sourceDir or findPyprojectToml() or projectPath
            local deploySuccess, deployError = deployLuaPlugin(sourceDir)
            if not deploySuccess then
                isInstalling = false
                installDialog.showError("Failed to deploy plugin: " .. tostring(deployError))
                if onError then
                    onError(deployError)
                end
                return
            end
            
            doInstallStep(6)
            
        elseif step == 6 then
            -- Complete
            installDialog.showCompletion()
            isInstalling = false
            
            -- Close dialog after a short delay
            -- Use Windows-compatible timeout (timeout command on Windows, sleep on Unix)
            pcall(function()
                if package.config:sub(1,1) == "\\" then
                    -- Windows
                    os.execute("timeout /t 2 >nul 2>&1")
                else
                    -- Unix/Linux/Mac
                    os.execute("sleep 2")
                end
                installDialog.close()
            end)
            
            if onComplete then
                onComplete({ success = true })
            end
        end
    end
    
    -- Start installation
    doInstallStep(1)
    
    return true
end

-- Check if installation is in progress
-- @return boolean
function installOrchestrator.isInstalling()
    return isInstalling
end

-- Cancel ongoing installation
function installOrchestrator.cancelInstallation()
    isInstalling = false
    if installProcessHandle and installProcessHandle.handle then
        processUtils.kill(installProcessHandle.handle)
        installProcessHandle = nil
    end
    installDialog.close()
end

-- Get installation status
-- @return table with installation status
-- NOTE: This function may race with ongoing installation operations.
-- The state returned reflects a snapshot that may be stale immediately.
-- For accurate state during installation, use isInstalling() checks before operations.
function installOrchestrator.getStatus()
    return {
        isInstalling = isInstalling,
        dialogState = installDialog.getState(),
        projectPath = projectPath
    }
end

return installOrchestrator
