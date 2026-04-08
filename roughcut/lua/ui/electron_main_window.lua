-- RoughCut Electron Main Window
-- Launches the Electron UI as a replacement for Resolve's built-in UIManager
-- Compatible with DaVinci Resolve's Lua scripting environment
-- Version: 1.0.0

local electronMainWindow = {}

local electronBridge = require("ui.electron_bridge")
local navigation = require("ui.navigation")
local logger = require("utils.logger")

local VERSION = "1.0.0-electron"
local BUILD_DATE = "2026-04-08"

local windowRef = nil
local runtimeRef = nil
local onCloseCallback = nil
local closeCallbackInvoked = false

--- Invoke the close callback if not already invoked
local function invokeCloseCallback()
    if closeCallbackInvoked then
        return
    end
    
    closeCallbackInvoked = true
    if onCloseCallback then
        pcall(onCloseCallback)
    end
end

--- Close the Electron window and cleanup
-- @param window window reference (optional)
-- @param closeWindow boolean whether to close the window (optional)
local function closeMainWindow(window, closeWindow)
    invokeCloseCallback()
    
    -- Close Electron process
    electronBridge.close()
    
    windowRef = nil
    runtimeRef = nil
    onCloseCallback = nil
    closeCallbackInvoked = false
    
    logger.info("Electron main window closed")
end

--- Create and launch the Electron main window
-- @param uiRuntime table with ui and disp references (kept for compatibility)
-- @return window reference or nil on error
function electronMainWindow.create(uiRuntime)
    logger.info("Creating Electron main window...")
    
    -- Store runtime reference
    runtimeRef = uiRuntime
    onCloseCallback = nil
    closeCallbackInvoked = false
    
    -- Launch Electron
    local success = electronBridge.launch()
    if not success then
        logger.error("Failed to launch Electron window")
        return nil
    end
    
    -- Create a virtual window reference
    -- Since Electron runs externally, we return a stub object
    windowRef = {
        _type = "electron_window",
        _version = VERSION,
        _electron = true,
        Show = function() end,  -- No-op, Electron is already visible
        Hide = function() end,  -- No-op
        Close = function() closeMainWindow() end,
    }
    
    logger.info("Electron main window created successfully")
    return windowRef
end

--- Close the main window
-- @param window window reference (optional)
function electronMainWindow.close(window)
    closeMainWindow(window, true)
end

--- Set callback for window close event
-- @param callback function to call on close
function electronMainWindow.setOnClose(callback)
    onCloseCallback = callback
end

--- Check if window is visible (Electron is always visible once launched)
-- @param window window reference
-- @return boolean
function electronMainWindow.isVisible(window)
    return electronBridge.isRunning()
end

--- Show the window (no-op for Electron, it's already visible)
-- @param window window reference
function electronMainWindow.show(window)
    -- Electron is already visible
end

--- Get window configuration
-- @return table with window settings
function electronMainWindow.getConfig()
    return {
        title = "RoughCut - AI-Powered Rough Cut Generator",
        width = 1400,
        height = 900,
        id = "RoughCutElectronWindow",
        version = VERSION,
        buildDate = BUILD_DATE,
        type = "electron"
    }
end

--- Check if Electron mode is available
-- @return boolean
function electronMainWindow.isAvailable()
    return electronBridge.getProjectRoot() ~= nil
end

return electronMainWindow
