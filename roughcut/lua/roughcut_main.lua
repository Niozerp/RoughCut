-- RoughCut Main Module
-- Compatible with DaVinci Resolve's Lua scripting environment
-- Version: 0.3.1 - DEBUG BUILD
-- This module is loaded by RoughCut.lua launcher

print("[RoughCut] roughcut_main.lua loaded - version 0.3.1")

local mainWindow = require("ui.main_window")
local navigation = require("ui.navigation")
local uiRuntime = require("ui.runtime")
local installOrchestrator = require("install_orchestrator")
local config = require("utils.config")
local logger = require("utils.logger")

config.init()
logger.init()

local installationInProgress = false

local function getProjectPath()
    local moduleInfo = debug.getinfo(1, "S")
    if not moduleInfo or not moduleInfo.source then
        return nil
    end

    local source = moduleInfo.source
    if source:sub(1, 1) == "@" then
        source = source:sub(2)
    end

    source = source:gsub("\\", "/")

    local dir = source:match("^(.*)/") or "."
    local projectRoot = dir:gsub("/[^/]+$", "")

    return projectRoot
end

local projectPath = getProjectPath()

local function logStartupPhase(message)
    local formatted = "RoughCut: Startup - " .. tostring(message)
    print(formatted)
    logger.info(formatted)
end

local function getBackendState()
    local cfg = config.read()
    local orchestratorState = installOrchestrator.getBackendState(projectPath)
    local configInstalled = config.isBackendInstalled()

    return {
        config_installed = configInstalled,
        global_installed = orchestratorState.global_installed,
        installation_cancelled = cfg.installation_cancelled == true,
        source_dir = orchestratorState.source_dir,
        installed = configInstalled or orchestratorState.global_installed,
        needs_install = not (configInstalled or orchestratorState.global_installed),
    }
end

local function launchMainWindow(uiManager)
    navigation.reset()
    logStartupPhase("creating shared navigation runtime")

    local runtimeContext = uiRuntime.create(uiManager)
    if not runtimeContext then
        print("RoughCut: Error - Failed to create shared navigation runtime")
        logger.error("Failed to create shared navigation runtime")
        return false
    end

    logStartupPhase("shared navigation runtime created")
    logStartupPhase("preparing home screen")

    local window = mainWindow.create(runtimeContext)
    if not window then
        print("RoughCut: Error - Failed to create main window")
        logger.error("Failed to create main window")
        return false
    end

    logStartupPhase("home window created")

    local navBound = navigation.bind(window, runtimeContext)
    if not navBound then
        print("RoughCut: Error - Failed to bind navigation")
        logger.error("Failed to bind navigation to main window")
        mainWindow.close(window)
        return false
    end

    mainWindow.setOnClose(function()
        navigation.destroy()
    end)

    logStartupPhase("home screen bound")

    config.updateLastRun()
    logStartupPhase("entering main window RunLoop")
    logger.info("Main window entering UI loop")

    local showSuccess = mainWindow.show(window)
    if not showSuccess then
        print("RoughCut: Error - Failed to show main window")
        logger.error("Failed to show main window")
        return false
    end

    logStartupPhase("main window closed")
    print("[RoughCut] Main window closed")
    return true
end

local function launchRoughCut(resolve)
    print("[RoughCut] launchRoughCut() called")
    logStartupPhase("launcher handoff received")

    if not resolve then
        print("[RoughCut Error] Resolve object not provided")
        logger.error("Resolve object not provided to launch function")
        return false
    end

    if not fu then
        print("[RoughCut Error] Fusion global object 'fu' not available")
        logger.error("Fusion global object 'fu' not available - cannot access UI Manager")
        return false
    end

    local okUi, uiManager = pcall(function()
        return fu.UIManager
    end)

    if not okUi or not uiManager then
        print("[RoughCut Error] Could not access UI Manager via fu.UIManager")
        logger.error("Could not access UI Manager - fu.UIManager unavailable or nil")
        return false
    end

    logStartupPhase("Fusion UI manager acquired")
    logger.info("Project path: " .. tostring(projectPath))

    local backendState = getBackendState()
    logger.info(
        "Backend state - config: " .. tostring(backendState.config_installed) ..
        ", global: " .. tostring(backendState.global_installed) ..
        ", needs_install: " .. tostring(backendState.needs_install)
    )

    if backendState.global_installed and not backendState.config_installed then
        logStartupPhase("global backend detected, syncing local config")
        logger.info("Global backend detected - marking local config as installed")
        config.markInstalled()
        backendState.config_installed = true
        backendState.installed = true
        backendState.needs_install = false
    end

    if not backendState.needs_install then
        logStartupPhase("backend ready, skipping install UI")
        return launchMainWindow(uiManager)
    end

    if installationInProgress then
        logger.warning("Installation already in progress, not starting another")
        return false
    end

    installationInProgress = true
    logStartupPhase("backend missing, starting install flow")
    logger.info("Installation required, starting setup...")

    local installResult = installOrchestrator.startInstallation(uiManager, projectPath)
    installationInProgress = false

    if not installResult.success then
        if installResult.cancelled then
            config.markCancelled()
            logger.info("Installation cancelled by user")
            return false
        end

        logStartupPhase("install flow failed")
        logger.error("Installation failed: " .. tostring(installResult.error))
        pcall(function()
            uiManager:ShowMessageBox(
                "Installation Error\n\n" .. tostring(installResult.error) .. "\n\nPlease check the logs at:\n" .. logger.getLogPath(),
                "RoughCut Installation",
                "OK"
            )
        end)
        return false
    end

    logStartupPhase("install flow completed, launching home screen")
    logger.info("Installation completed successfully")
    config.markInstalled()

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

    return launched
end

return {
    launch = launchRoughCut
}
