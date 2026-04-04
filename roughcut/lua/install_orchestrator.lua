-- RoughCut Installation Orchestrator
-- Handles Python backend auto-installation from Lua side
-- Coordinates detection, installation, and UI updates

local installOrchestrator = {}

-- Import modules
local installDialog = require("lua.ui.install_dialog")
local processUtils = require("lua.utils.process")

-- State tracking
local installProcessHandle = nil
local isInstalling = false
local projectPath = nil

-- Generate unique request ID
local function generateRequestId()
    local timestamp = tostring(os.time())
    local random = tostring(math.random(100, 999))
    return "install_" .. timestamp .. "_" .. random
end

-- Check if Python backend is already installed
-- @return table with status information
function installOrchestrator.checkInstallation(projectDir)
    projectPath = projectDir
    
    if not projectPath then
        print("RoughCut: Error - Project path not provided")
        return { ready = false, error = "Project path not provided" }
    end
    
    -- Run detection via install.py
    local detectId = "detect_" .. tostring(os.time())
    local command = {
        "python3",
        "scripts/install.py",
        "--project-path",
        projectPath
    }
    
    -- Try python3 first, then python
    if not processUtils.commandExists("python3") then
        command[1] = "python"
    end
    
    -- Spawn process and send detect request
    local spawnResult = processUtils.spawn(command, projectPath)
    if not spawnResult.handle then
        return { ready = false, error = spawnResult.error or "Failed to start detector" }
    end
    
    -- Send JSON-RPC detect request
    local detectRequest = {
        method = "detect",
        id = detectId
    }
    
    -- Write request to stdin (not directly supported with io.popen in read mode)
    -- Instead, we'll need to use a different approach or run synchronously
    processUtils.close(spawnResult.handle)
    
    -- For now, run synchronously with runPython
    local scriptPath = projectPath .. "/scripts/install.py"
    local result = processUtils.runPython(scriptPath, {"--project-path", projectPath}, projectPath, 30)
    
    -- Parse JSON response from stdout
    if result.success and result.stdout then
        for line in result.stdout:gmatch("[^\n]+") do
            local ok, jsonData = pcall(function()
                -- Simple JSON parsing for result
                if line:find('"ready"%s*:%s*true') then
                    return { ready = true }
                elseif line:find('"ready"%s*:%s*false') then
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
        if installProcessHandle then
            processUtils.kill(installProcessHandle)
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
            installDialog.updateProgress(1, 5, "Checking Python installation...", 10)
            
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
            installDialog.updateProgress(2, 5, "Checking Poetry installation...", 25)
            
            local result = processUtils.run({"poetry", "--version"}, nil, 5)
            
            if not result.success then
                -- Need to install Poetry - requires user consent
                isInstalling = false
                installDialog.showError("Poetry not installed. Please install Poetry first.")
                installDialog.setCancelEnabled(true)
                
                -- Update cancel button to close dialog
                installDialog.setCancelCallback(function()
                    installDialog.close()
                end)
                
                if onError then
                    onError("Poetry not installed")
                end
                return
            end
            
            doInstallStep(3)
            
        elseif step == 3 then
            -- Install dependencies
            installDialog.updateProgress(3, 5, "Installing dependencies...", 50)
            
            -- Run poetry install
            local command = {"poetry", "install", "--no-interaction"}
            installProcessHandle = processUtils.spawn(command, projectPath)
            
            if not installProcessHandle.handle then
                isInstalling = false
                installDialog.showError("Failed to start installation: " .. (installProcessHandle.error or "Unknown error"))
                if onError then
                    onError("Failed to start installation")
                end
                return
            end
            
            -- Read output line by line with cooperative multitasking
            local lineCount = 0
            local function readNextLine()
                if not isInstalling or installDialog.isCancelled() then
                    processUtils.close(installProcessHandle)
                    return
                end
                
                local line = processUtils.readLine(installProcessHandle.handle)
                if line then
                    lineCount = lineCount + 1
                    -- Update progress every few lines
                    if lineCount % 5 == 0 then
                        local percent = math.min(50 + (lineCount / 20) * 45, 95)
                        installDialog.updateProgress(3, 5, line:sub(1, 40), percent)
                    end
                    -- Continue reading
                    -- In real Resolve, we'd use a timer or next idle callback
                    -- For now, we can't easily simulate async in pure Lua
                else
                    -- End of output, close and continue
                    processUtils.close(installProcessHandle)
                    doInstallStep(4)
                end
            end
            
            -- For now, do synchronous read
            local outputLines = {}
            while true do
                local line = processUtils.readLine(installProcessHandle.handle)
                if not line then
                    break
                end
                table.insert(outputLines, line)
            end
            
            processUtils.close(installProcessHandle)
            doInstallStep(4)
            
        elseif step == 4 then
            -- Verify installation
            installDialog.updateProgress(4, 5, "Verifying installation...", 95)
            
            -- Check if backend is now importable
            local verifyCommand = {
                "poetry", "run", "python", "-c",
                "import roughcut; print('OK')"
            }
            local result = processUtils.run(verifyCommand, projectPath, 30)
            
            if not result.success or not result.stdout:find("OK") then
                isInstalling = false
                installDialog.showError("Installation verification failed. Please try again.")
                if onError then
                    onError("Verification failed")
                end
                return
            end
            
            doInstallStep(5)
            
        elseif step == 5 then
            -- Complete
            installDialog.showCompletion()
            isInstalling = false
            
            -- Close dialog after a short delay
            -- In real Resolve, we'd use a timer
            pcall(function()
                os.execute("sleep 2")
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
    if installProcessHandle then
        processUtils.kill(installProcessHandle)
        installProcessHandle = nil
    end
    installDialog.close()
end

-- Get installation status
-- @return table with installation status
function installOrchestrator.getStatus()
    return {
        isInstalling = isInstalling,
        dialogState = installDialog.getState(),
        projectPath = projectPath
    }
end

return installOrchestrator
