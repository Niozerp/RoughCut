-- RoughCut Main Entry Point
-- Compatible with DaVinci Resolve's Lua scripting environment
-- Version: 0.2.0

-- Import UI modules
local mainWindow = require("ui.main_window")
local navigation = require("ui.navigation")
local installDialog = require("ui.install_dialog")
local installOrchestrator = require("install_orchestrator")
local config = require("utils.config")
local logger = require("utils.logger")

-- Initialize config and logging
config.init()
logger.init()

-- State tracking
local installationInProgress = false

-- Get project path from script location
local function getProjectPath()
    local scriptDir = debug.getinfo(1, "S").source
    if scriptDir:sub(1, 1) == "@" then
        scriptDir = scriptDir:sub(2)
    end
    -- Handle both forward slashes and backslashes (Windows compatibility)
    scriptDir = scriptDir:gsub("\\", "/")
    -- Get parent directory of lua/ directory
    local projectPath = scriptDir:gsub("/lua/roughcut%.lua", "")
    return projectPath
end

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

-- Launch RoughCut main interface
-- Creates window, adds navigation, and displays to user
local function launchRoughCut()
    -- Step 1: Access Resolve API with error handling
    local ok, resolve = pcall(function() return Resolve() end)
    
    if not ok or not resolve then
        print("RoughCut: Error - Could not access Resolve API")
        logger.error("Could not access Resolve API")
        return false
    end
    
    -- Step 2: Get UI Manager
    local ok_ui, uiManager = pcall(function() return resolve:GetUIManager() end)
    
    if not ok_ui or not uiManager then
        print("RoughCut: Error - Could not access UI Manager")
        logger.error("Could not access UI Manager")
        return false
    end
    
    -- Step 3: Check installation
    local projectPath = getProjectPath()
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
                    launchMainWindow(uiManager)
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

-- Launch main window (separate from install flow)
local function launchMainWindow(uiManager)
    -- Step 1: Create main window
    local window = mainWindow.create(uiManager)
    
    if not window then
        print("RoughCut: Error - Failed to create main window")
        logger.error("Failed to create main window")
        return false
    end
    
    -- Step 2: Set UI Manager for navigation (needed for child windows)
    navigation.setUIManager(uiManager)
    
    -- Step 3: Add navigation buttons
    local navSuccess = navigation.create(window)
    
    if not navSuccess then
        print("RoughCut: Error - Failed to create navigation")
        logger.error("Failed to create navigation")
        return false
    end
    
    -- Step 4: Show the window
    local showSuccess = mainWindow.show(window)
    
    if not showSuccess then
        print("RoughCut: Error - Failed to show main window")
        logger.error("Failed to show main window")
        return false
    end
    
    -- Update last run timestamp
    config.updateLastRun()
    logger.info("Main window launched successfully")
    
    print("RoughCut: Main window launched successfully")
    return true
end

-- Main entry point when script is run from Resolve menu
logger.info("RoughCut starting...")
local success = launchRoughCut()

if not success then
    -- Fallback: Show error dialog
    -- Protect against Resolve API failures - use multiple fallback levels
    local function showErrorFallback(message)
        -- Level 1: Try Resolve message box
        local ok, resolve = pcall(function() return Resolve() end)
        if ok and resolve then
            local ok_ui, uiManager = pcall(function() return resolve:GetUIManager() end)
            if ok_ui and uiManager then
                local ok_msg = pcall(function()
                    uiManager:ShowMessageBox(
                        message,
                        "RoughCut Error",
                        "OK"
                    )
                end)
                if ok_msg then return end
            end
        end
        
        -- Level 2: Print to console
        print("RoughCut Error: " .. message)
        
        -- Level 3: Try logging
        pcall(function()
            logger.error("Launch failed: " .. message)
        end)
    end
    
    showErrorFallback(
        "RoughCut encountered an error launching.\n\n" ..
        "Please check the Resolve console and logs for details.\n\n" ..
        "Log location: " .. tostring(logger.getLogPath())
    )
end
