-- RoughCut Electron Bridge
-- Launches and manages the Electron UI from DaVinci Resolve Lua environment
-- Compatible with DaVinci Resolve's Lua scripting environment
-- Version: 1.1.0 - With Auto-Installation

local electronBridge = {}

local processUtils = require("utils.process")
local protocol = require("utils.protocol")
local logger = require("utils.logger")

-- Module state
local electronProcess = nil
local projectRoot = nil
local isRunning = false
local isInstalling = false
local launchState = "idle"
local lastLaunchError = nil

--- Get the project root directory
-- @return string project root path or nil
local function getProjectRoot()
    if projectRoot then
        return projectRoot
    end
    
    local moduleInfo = debug.getinfo(1, "S")
    if not moduleInfo or not moduleInfo.source then
        return nil
    end
    
    local source = moduleInfo.source
    if source:sub(1, 1) == "@" then
        source = source:sub(2)
    end
    
    source = source:gsub("\\", "/")
    
    -- Go up from roughcut/lua/ui/ to project root
    local dir = source:match("^(.*)/") or "."  -- roughcut/lua/ui
    dir = dir:match("^(.*)/") or "."           -- roughcut/lua
    dir = dir:match("^(.*)/") or "."           -- roughcut
    dir = dir:match("^(.*)/") or "."           -- project root
    
    projectRoot = dir
    return projectRoot
end

--- Check if npm is available
-- Also checks common Node.js installation paths on Windows
-- @return boolean true if npm is found
local function isNpmAvailable()
    -- First try the standard command check
    if processUtils.commandExists("npm") then
        return true
    end
    
    if processUtils.commandExists("npm.cmd") then
        return true
    end
    
    -- On Windows, check common Node.js installation paths
    local isWindows = package.config:sub(1,1) == "\\"
    if isWindows then
        local commonPaths = {
            "C:/Program Files/nodejs/npm.cmd",
            "C:/Program Files (x86)/nodejs/npm.cmd",
            os.getenv("LOCALAPPDATA") .. "/Microsoft/WindowsApps/npm.cmd",
            os.getenv("USERPROFILE") .. "/AppData/Roaming/npm/npm.cmd",
        }
        
        for _, path in ipairs(commonPaths) do
            if path then
                local f = io.open(path, "r")
                if f then
                    f:close()
                    logger.info("Found npm at: " .. path)
                    return true
                end
            end
        end
    end
    
    return false
end

--- Get the npm command path
-- @return string path to npm command or "npm" as fallback
local function getNpmPath()
    -- If standard command works, use it
    if processUtils.commandExists("npm") then
        return "npm"
    end
    
    if processUtils.commandExists("npm.cmd") then
        return "npm.cmd"
    end
    
    -- On Windows, check common Node.js installation paths
    local isWindows = package.config:sub(1,1) == "\\"
    if isWindows then
        local commonPaths = {
            "C:/Program Files/nodejs/npm.cmd",
            "C:/Program Files (x86)/nodejs/npm.cmd",
            os.getenv("LOCALAPPDATA") .. "/Microsoft/WindowsApps/npm.cmd",
            os.getenv("USERPROFILE") .. "/AppData/Roaming/npm/npm.cmd",
        }
        
        for _, path in ipairs(commonPaths) do
            if path then
                local f = io.open(path, "r")
                if f then
                    f:close()
                    return path
                end
            end
        end
    end
    
    -- Fallback
    return "npm"
end

--- Check if Electron dependencies are installed
-- @return boolean true if node_modules exists
local function areDepsInstalled()
    local root = getProjectRoot()
    if not root then
        return false
    end
    
    local nodeModulesPath = root .. "/electron/node_modules"
    local f = io.open(nodeModulesPath .. "/.package-lock.json", "r")
    if f then
        f:close()
        return true
    end
    
    -- Also check for the directory itself
    f = io.open(nodeModulesPath, "r")
    if f then
        f:close()
        return true
    end
    
    return false
end

--- Check if the shipped RoughCut bootstrap entrypoint exists
-- @return boolean true if RoughCut can be launched
function electronBridge.isAvailable()
    local root = getProjectRoot()
    if not root then
        logger.info("Electron not available: could not determine project root")
        return false
    end
    
    -- Check if package.json exists
    local packageJsonPath = root .. "/electron/package.json"
    local f = io.open(packageJsonPath, "r")
    if not f then
        logger.info("Electron not available: package.json not found at " .. packageJsonPath)
        return false
    end
    f:close()

    local bootstrapPath = root .. "/roughcut/scripts/bootstrap_launch.py"
    f = io.open(bootstrapPath, "r")
    if not f then
        logger.info("Electron not available: bootstrap script not found at " .. bootstrapPath)
        return false
    end
    f:close()

    logger.info("Electron is available at: " .. root .. "/electron")
    logger.info("  bootstrap found at: " .. bootstrapPath)
    return true
end

--- Install Electron dependencies (npm install)
-- @param onProgress callback function(status_message) (optional)
-- @return boolean success
function electronBridge.installDependencies(onProgress)
    if isInstalling then
        logger.info("Electron dependency installation already in progress")
        return false
    end
    
    local root = getProjectRoot()
    if not root then
        logger.error("Cannot install: could not determine project root")
        return false
    end
    
    if not isNpmAvailable() then
        logger.error("Cannot install: npm not found in PATH")
        logger.error("Please install Node.js from https://nodejs.org/")
        logger.error("After installation, restart DaVinci Resolve and try again")
        return false
    end
    
    isInstalling = true
    
    if onProgress then
        onProgress("Installing Electron dependencies...")
    end
    
    logger.info("Installing Electron dependencies...")
    logger.info("This may take 2-3 minutes...")
    
    local electronDir = root .. "/electron"
    local npmCmd = getNpmPath()
    
    logger.info("Using npm at: " .. npmCmd)
    
    -- Run npm install with longer timeout (5 minutes)
    local result = processUtils.run({npmCmd, "install"}, electronDir, 300)
    
    isInstalling = false
    
    if not result.success then
        logger.error("npm install failed: " .. tostring(result.error))
        logger.error("stdout: " .. tostring(result.stdout))
        logger.error("stderr: " .. tostring(result.stderr))
        return false
    end
    
    logger.info("Electron dependencies installed successfully!")
    return true
end

--- Get the Python bootstrap command used to launch RoughCut
-- @param resolve Resolve API object (optional)
-- @return table with cmd (array), workingDir, and error
local function getElectronCommand(resolve)
    local root = getProjectRoot()
    if not root then
        return { cmd = nil, workingDir = nil, error = "Could not determine project root" }
    end

    local bootstrapScript = root .. "/roughcut/scripts/bootstrap_launch.py"
    local bootstrapFile = io.open(bootstrapScript, "r")
    if not bootstrapFile then
        return {
            cmd = nil,
            workingDir = nil,
            error = "Bootstrap script not found at " .. bootstrapScript
        }
    end
    bootstrapFile:close()

    local pythonCmd = nil
    local pythonArgs = {}
    if processUtils.commandExists("python") then
        pythonCmd = "python"
    elseif processUtils.commandExists("py") then
        pythonCmd = "py"
        pythonArgs = {"-3"}
    else
        return {
            cmd = nil,
            workingDir = nil,
            error = "Python 3.10+ is required before RoughCut can bootstrap itself."
        }
    end

    local cmd = {pythonCmd}
    for _, arg in ipairs(pythonArgs) do
        table.insert(cmd, arg)
    end
    table.insert(cmd, bootstrapScript)
    table.insert(cmd, "--mode")
    table.insert(cmd, "resolve")

    if resolve and resolve.GetProjectManager then
        local ok, projectManager = pcall(function()
            return resolve:GetProjectManager()
        end)
        if ok and projectManager and projectManager.GetCurrentProject then
            local okProject, project = pcall(function()
                return projectManager:GetCurrentProject()
            end)
            if okProject and project and project.GetName then
                local okName, projectName = pcall(function()
                    return project:GetName()
                end)
                if okName and projectName and projectName ~= "" then
                    table.insert(cmd, "--project-name")
                    table.insert(cmd, projectName)
                end
            end
        end
    end

    return {
        cmd = cmd,
        workingDir = root,
        error = nil
    }
end

--- Launch the Electron application
-- @param resolve Resolve API object (optional, for future use)
-- @param onMessage callback for messages from Electron (optional)
-- @return boolean success
function electronBridge.launch(resolve, onMessage)
    if isRunning then
        logger.info("Electron is already running")
        return true
    end
   
    logger.info("Launching RoughCut Electron UI...")
    launchState = "launching"
    lastLaunchError = nil
    
    -- Check if Electron is available
    if not electronBridge.isAvailable() then
        logger.error("Electron app not found or npm not available")
        launchState = "failed"
        lastLaunchError = "Electron app not found or npm not available"
        return false
    end
    
    -- Get launch command
    local launchInfo = getElectronCommand(resolve)
    if launchInfo.error then
        logger.error("Failed to get Electron command: " .. launchInfo.error)
        launchState = "failed"
        lastLaunchError = launchInfo.error
        return false
    end
    
    logger.info("Starting Electron from: " .. launchInfo.workingDir)
    logger.info("Command: " .. table.concat(launchInfo.cmd, " "))

    local result = processUtils.run(launchInfo.cmd, launchInfo.workingDir, 1800)
    if not result.success then
        local combinedOutput = (result.stdout or "") .. "\n" .. (result.stderr or "")
        lastLaunchError = result.error or combinedOutput
        logger.error("RoughCut bootstrap failed before Electron became ready")
        if combinedOutput and combinedOutput ~= "" then
            logger.error(combinedOutput)
        elseif result.error then
            logger.error(result.error)
        end
        launchState = "failed"
        return false
    end

    electronProcess = nil
    isRunning = true
    launchState = "running"

    if result.stdout and result.stdout ~= "" then
        logger.info(result.stdout)
    end
    logger.info("Electron bootstrap completed and the main window survived startup")
    return true
end

--- Check if Electron is running
-- @return boolean
function electronBridge.isRunning()
    return isRunning
end

--- Send a message to Electron (via file or socket)
-- @param message table message to send
-- @return boolean success
function electronBridge.sendMessage(message)
    -- TODO: Implement file-based or socket communication
    -- For MVP, Electron will poll for changes or use a simple HTTP server
    logger.info("Message to Electron: " .. protocol.jsonEncode(message))
    return true
end

--- Close the Electron application
-- @return boolean success
function electronBridge.close()
    if not electronProcess or not electronProcess.handle then
        isRunning = false
        launchState = "idle"
        return true
    end
    
    logger.info("Closing Electron...")
    
    local result = processUtils.close(electronProcess)
    
    electronProcess = nil
    isRunning = false
    launchState = "idle"
    
    return result.success
end

--- Get the project root directory
-- @return string path
function electronBridge.getProjectRoot()
    return getProjectRoot()
end

--- Get installation status
-- @return table with available, depsInstalled, isRunning
function electronBridge.getStatus()
    return {
        available = electronBridge.isAvailable(),
        depsInstalled = areDepsInstalled(),
        isRunning = isRunning,
        isInstalling = isInstalling,
        launchState = launchState,
        lastLaunchError = lastLaunchError,
    }
end

return electronBridge
