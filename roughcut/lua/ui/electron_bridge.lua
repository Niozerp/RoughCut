-- RoughCut Electron Bridge
-- Launches and manages the Electron UI from DaVinci Resolve Lua environment
-- Compatible with DaVinci Resolve's Lua scripting environment
-- Version: 1.0.0

local electronBridge = {}

local processUtils = require("utils.process")
local protocol = require("utils.protocol")
local logger = require("utils.logger")

-- Module state
local electronProcess = nil
local projectRoot = nil
local isRunning = false

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

--- Check if Electron app is built
-- @return boolean true if electron app exists
local function isElectronBuilt()
    local root = getProjectRoot()
    if not root then
        return false
    end
    
    -- Check for the built Electron app
    -- On Windows, check for the .exe in dist or node_modules/.bin
    local electronDistPath = root .. "/roughcut-electron/dist"
    local packageJsonPath = root .. "/roughcut-electron/package.json"
    
    -- Check if package.json exists
    local f = io.open(packageJsonPath, "r")
    if f then
        f:close()
        return true
    end
    
    return false
end

--- Get the path to run Electron
-- @return table with cmd (array), workingDir, and error
local function getElectronCommand()
    local root = getProjectRoot()
    if not root then
        return { cmd = nil, workingDir = nil, error = "Could not determine project root" }
    end
    
    local electronDir = root .. "/roughcut-electron"
    
    -- Check for npm/node
    local npmCmd = "npm"
    if processUtils.commandExists("npm") then
        npmCmd = "npm"
    elseif processUtils.commandExists("npm.cmd") then
        npmCmd = "npm.cmd"
    else
        return { cmd = nil, workingDir = nil, error = "npm not found in PATH" }
    end
    
    -- Build the command: npm run dev
    -- This will build and launch the Electron app
    return {
        cmd = { npmCmd, "run", "dev" },
        workingDir = electronDir,
        error = nil
    }
end

--- Launch the Electron application
-- @param resolve Resolve API object
-- @param onMessage callback for messages from Electron (optional)
-- @return boolean success
function electronBridge.launch(resolve, onMessage)
    if isRunning then
        logger.info("Electron is already running")
        return true
    end
    
    logger.info("Launching RoughCut Electron UI...")
    
    -- Check if Electron is available
    if not isElectronBuilt() then
        logger.error("Electron app not found at roughcut-electron/")
        return false
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
    -- We don't wait for it to complete
    local result = processUtils.spawn(launchInfo.cmd, launchInfo.workingDir)
    
    if result.error then
        logger.error("Failed to spawn Electron: " .. result.error)
        return false
    end
    
    electronProcess = result
    isRunning = true
    
    logger.info("Electron process started")
    
    -- Since Electron is a GUI app, we can't easily read its output via io.popen
    -- Instead, we'll use a file-based or socket-based protocol for communication
    -- For now, just report success
    
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

return electronBridge
