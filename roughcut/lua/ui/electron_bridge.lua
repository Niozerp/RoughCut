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

--- Check if Electron app exists
-- @return boolean true if electron app exists
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
    
    -- Check if npm is available
    if not isNpmAvailable() then
        logger.info("Electron not available: npm not found in PATH")
        logger.info("  Node.js may not be installed or not in system PATH")
        logger.info("  Download from: https://nodejs.org/")
        return false
    end
    
    local npmPath = getNpmPath()
    logger.info("Electron is available at: " .. root .. "/electron")
    logger.info("  npm found at: " .. npmPath)
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

--- Get the path to run Electron
-- @return table with cmd (array), workingDir, and error
local function getElectronCommand()
    local root = getProjectRoot()
    if not root then
        return { cmd = nil, workingDir = nil, error = "Could not determine project root" }
    end
    
    local electronDir = root .. "/electron"
    
    -- Check for npm
    if not isNpmAvailable() then
        return { cmd = nil, workingDir = nil, error = "npm not found in PATH. Please install Node.js." }
    end
    
    local npmCmd = getNpmPath()
    
    -- Check if dependencies are installed
    if not areDepsInstalled() then
        return { cmd = nil, workingDir = nil, error = "Dependencies not installed. Run installDependencies() first." }
    end
    
    -- Build the command: npm run dev
    return {
        cmd = { npmCmd, "run", "dev" },
        workingDir = electronDir,
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
    
    -- Check if Electron is available
    if not electronBridge.isAvailable() then
        logger.error("Electron app not found or npm not available")
        return false
    end
    
    -- Auto-install dependencies if needed
    if not areDepsInstalled() then
        logger.info("Electron dependencies not found, installing...")
        local installed = electronBridge.installDependencies()
        if not installed then
            logger.error("Failed to install Electron dependencies")
            return false
        end
    end
    
    -- Get launch command
    local launchInfo = getElectronCommand()
    if launchInfo.error then
        logger.error("Failed to get Electron command: " .. launchInfo.error)
        return false
    end
    
    logger.info("Starting Electron from: " .. launchInfo.workingDir)
    logger.info("Command: " .. table.concat(launchInfo.cmd, " "))
    
    -- Spawn the Electron process
    -- Note: We use spawn instead of run because Electron is a long-running GUI app
    local result = processUtils.spawn(launchInfo.cmd, launchInfo.workingDir)
    
    if result.error then
        logger.error("Failed to spawn Electron: " .. result.error)
        return false
    end
    
    electronProcess = result
    isRunning = true
    
    logger.info("Electron process started")
    
    -- Give Electron a moment to start, then report success
    -- We don't wait for it to finish since it's a GUI app
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
        return true
    end
    
    logger.info("Closing Electron...")
    
    local result = processUtils.close(electronProcess)
    
    electronProcess = nil
    isRunning = false
    
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
        isInstalling = isInstalling
    }
end

return electronBridge
