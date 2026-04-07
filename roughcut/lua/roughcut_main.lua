-- RoughCut Main Module
-- Compatible with DaVinci Resolve's Lua scripting environment
-- Version: 0.3.1 - DEBUG BUILD
-- This module is loaded by RoughCut.lua launcher

print("[RoughCut] roughcut_main.lua loaded - version 0.3.1")

-- Import UI modules - paths are already set up by the launcher
local mainWindow = require("ui.main_window")
local installDialog = require("ui.install_dialog")
local installOrchestrator = require("install_orchestrator")
local config = require("utils.config")
local logger = require("utils.logger")

-- Initialize config and logging
config.init()
logger.init()

-- State tracking
local installationInProgress = false

-- Determine project path from module location
local function getProjectPath()
    -- Get the directory of this module
    local moduleInfo = debug.getinfo(1, "S")
    if not moduleInfo or not moduleInfo.source then
        return nil
    end
    
    local source = moduleInfo.source
    if source:sub(1, 1) == "@" then
        source = source:sub(2)
    end
    
    -- Normalize path
    source = source:gsub("\\", "/")
    
    -- Get directory containing this file (should be .../roughcut/lua/)
    local dir = source:match("^(.*)/") or "."
    
    -- Go up one level to get the project root (parent of lua/)
    local projectRoot = dir:gsub("/[^/]+$", "")
    
    return projectRoot
end

local projectPath = getProjectPath()

-- Check if installation is needed
local function checkInstallationNeeded()
    -- First check config
    if config.isBackendInstalled() then
        logger.info("Backend already installed according to config")
        return false
    end
    
    -- Check if installation was cancelled previously
    local cfg = config.read()
    if cfg.installation_cancelled then
        logger.info("Installation was previously cancelled, will retry")
        return true
    end
    
    return true
end

-- Launch main window (separate from install flow)
local function launchMainWindow(uiManager)
    -- Step 1: Create main window
    local window = mainWindow.create(uiManager)
    
    if not window then
        print("RoughCut: Error - Failed to create main window")
        logger.error("Failed to create main window")
        return false
    end
    
    -- NOTE: Navigation temporarily disabled - will be restored in future update
    -- Future Step 2: Set UI Manager for navigation
    -- Future Step 3: Add navigation buttons
    
    -- Step 2: Show the window
    -- Record launch time before entering the UI loop, since show() now blocks
    -- until the user closes the main window.
    config.updateLastRun()
    logger.info("Main window entering UI loop")

    local showSuccess = mainWindow.show(window)
    
    if not showSuccess then
        print("RoughCut: Error - Failed to show main window")
        logger.error("Failed to show main window")
        return false
    end

    logger.info("Main window closed")
    print("[RoughCut] Main window closed")
    return true
end

-- Launch RoughCut main interface
-- Creates window, adds navigation, and displays to user
-- @param resolve The Resolve API object (passed from launcher)
local function launchRoughCut(resolve)
    print("[RoughCut] launchRoughCut() called")
    
    -- Step 1: Validate Resolve API was passed
    if not resolve then
        print("[RoughCut Error] Resolve object not provided")
        logger.error("Resolve object not provided to launch function")
        return false
    end
    
    -- Step 2: Get UI Manager from global fu object
    if not fu then
        print("[RoughCut Error] Fusion global object 'fu' not available")
        logger.error("Fusion global object 'fu' not available - cannot access UI Manager")
        return false
    end
    
    local ok_ui, uiManager = pcall(function() return fu.UIManager end)
    
    if not ok_ui or not uiManager then
        print("[RoughCut Error] Could not access UI Manager via fu.UIManager")
        logger.error("Could not access UI Manager - fu.UIManager unavailable or nil")
        return false
    end
    
    -- Step 3: Check installation
    logger.info("Project path: " .. projectPath)
    
    if checkInstallationNeeded() then
        -- Guard against concurrent installation attempts
        if installationInProgress then
            logger.warning("Installation already in progress, not starting another")
            return false
        end
        
        installationInProgress = true
        logger.info("Installation required, starting setup...")
        
        -- Start installation
        local installStarted = installOrchestrator.startInstallation(
            uiManager,
            projectPath,
            function(status)
                -- On complete
                installationInProgress = false
                if status.success then
                    logger.info("Installation completed successfully")
                    config.markInstalled()
                    -- Continue to main window
                    local launched = launchMainWindow(uiManager)
                    if not launched then
                        logger.error("Main window failed to launch after installation")
                        pcall(function()
                            uiManager:ShowMessageBox(
                                "RoughCut installed successfully, but the main UI could not be opened.\n\nPlease check the Resolve console for details.",
                                "RoughCut Launch Error",
                                "OK"
                            )
                        end)
                    end
                end
            end,
            function(error)
                -- On error
                installationInProgress = false
                logger.error("Installation failed: " .. tostring(error))
                -- Show error dialog
                pcall(function()
                    uiManager:ShowMessageBox(
                        "Installation Error\n\n" .. tostring(error) .. "\n\nPlease check the logs at:\n" .. logger.getLogPath(),
                        "RoughCut Installation",
                        "OK"
                    )
                end)
            end
        )
        
        if not installStarted then
            logger.error("Failed to start installation")
            return false
        end
        
        -- Don't launch main window yet - wait for installation
        return true
    else
        -- No installation needed, launch main window directly
        return launchMainWindow(uiManager)
    end
end

-- Export the launch function for the launcher to call
-- The launcher handles Resolve API access, we just need to be called
return {
    launch = launchRoughCut
}
