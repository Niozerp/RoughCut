-- RoughCut Navigation Controller
-- Binds dispatcher-managed home screen buttons to child windows.

local mediaManagement = require("ui.media_management")
local formatManagement = require("ui.formats_manager")
local roughCutWorkflow = require("ui.rough_cut_workflow")
local logger = require("utils.logger")

local navigation = {}

local NAV_CONFIG = {
    buttons = {
        {
            id = "btnManageMedia",
            label = "Manage Media",
            tooltip = "Configure folders and index your Music, SFX, and VFX assets",
            key = "media",
            state = "media_management",
            module = mediaManagement
        },
        {
            id = "btnManageFormats",
            label = "Manage Formats",
            tooltip = "View and select video format templates for rough cuts",
            key = "format",
            state = "format_management",
            module = formatManagement
        },
        {
            id = "btnCreateRoughCut",
            label = "Create Rough Cut",
            tooltip = "Start the AI-powered rough cut generation workflow",
            key = "workflow",
            state = "rough_cut_workflow",
            module = roughCutWorkflow
        }
    }
}

local NavigationState = {
    HOME = "home",
    MEDIA_MANAGEMENT = "media_management",
    FORMAT_MANAGEMENT = "format_management",
    ROUGH_CUT_WORKFLOW = "rough_cut_workflow"
}

local currentState = NavigationState.HOME
local mainWindowRef = nil
local runtimeRef = nil
local navigationButtons = {}
local childWindows = {}

local function logNavigation(message)
    local formatted = "RoughCut: Navigation - " .. tostring(message)
    print(formatted)
    logger.info(formatted)
end

local function getButtonConfig(buttonId)
    for _, buttonConfig in ipairs(NAV_CONFIG.buttons) do
        if buttonConfig.id == buttonId then
            return buttonConfig
        end
    end

    return nil
end

local function ensureWindowItems(window)
    local ok, items = pcall(function()
        return window:GetItems()
    end)

    if ok and items then
        return items
    end

    return {}
end

local function showMainWindow()
    if not mainWindowRef then
        return false
    end

    local ok = pcall(function()
        mainWindowRef:Show()
        mainWindowRef:Raise()
    end)

    return ok
end

local function hideMainWindow()
    if not mainWindowRef then
        return false
    end

    local ok = pcall(function()
        mainWindowRef:Hide()
    end)

    return ok
end

local function attachReturnCallbacks()
    mediaManagement.setOnReturnToMain(function()
        currentState = NavigationState.HOME
        showMainWindow()
        logNavigation("returned from Manage Media")
    end)

    formatManagement.setOnReturnToMain(function()
        currentState = NavigationState.HOME
        showMainWindow()
        logNavigation("returned from Manage Formats")
    end)

    roughCutWorkflow.setOnReturnToMain(function()
        currentState = NavigationState.HOME
        showMainWindow()
        logNavigation("returned from Create Rough Cut")
    end)
end

local function createChildWindow(buttonConfig)
    local ok, childWindow = pcall(function()
        return buttonConfig.module.create(runtimeRef, mainWindowRef)
    end)

    if not ok or not childWindow then
        logNavigation("route creation failed for " .. buttonConfig.label .. ": " .. tostring(childWindow))
        return nil
    end

    childWindows[buttonConfig.key] = childWindow
    return childWindow
end

local function showChildWindow(buttonConfig)
    local ok, shown = pcall(function()
        return buttonConfig.module.show()
    end)

    if not ok then
        logNavigation("route show failed for " .. buttonConfig.label .. ": " .. tostring(shown))
        return false
    end

    return shown == true
end

local function bindButtonHandler(window, buttonConfig)
    local ok, err = pcall(function()
        window.On[buttonConfig.id].Clicked = function(ev)
            local navOk, navErr = pcall(function()
                navigation.handleNavigation(buttonConfig.id)
            end)

            if not navOk then
                logNavigation("handler failed for " .. buttonConfig.label .. ": " .. tostring(navErr))
                navigation.returnToMain()
            end
        end
    end)

    if not ok then
        logNavigation("failed to bind " .. buttonConfig.label .. ": " .. tostring(err))
        return false
    end

    return true
end

function navigation.getButtonConfigs()
    return NAV_CONFIG.buttons
end

function navigation.bind(window, uiRuntime)
    if not window then
        print("RoughCut: Error - Window required for navigation")
        return false
    end

    if not uiRuntime or not uiRuntime.ui or not uiRuntime.disp then
        print("RoughCut: Error - Shared UI runtime required for navigation binding")
        return false
    end

    runtimeRef = uiRuntime
    mainWindowRef = window
    currentState = NavigationState.HOME
    navigationButtons = ensureWindowItems(window)
    childWindows = {}

    attachReturnCallbacks()

    for _, buttonConfig in ipairs(NAV_CONFIG.buttons) do
        local button = navigationButtons[buttonConfig.id]
        if not button then
            print("RoughCut: Error - Main window missing navigation button: " .. buttonConfig.id)
            return false
        end

        pcall(function()
            button.ToolTip = buttonConfig.tooltip
        end)
        pcall(function()
            button.Tooltip = buttonConfig.tooltip
        end)

        if not bindButtonHandler(window, buttonConfig) then
            return false
        end
    end

    logNavigation("home buttons bound")
    return true
end

function navigation.create(window)
    return navigation.bind(window, runtimeRef)
end

function navigation.handleNavigation(buttonId)
    if not runtimeRef then
        print("RoughCut: Error - Shared UI runtime not set for navigation")
        return
    end

    local buttonConfig = getButtonConfig(buttonId)
    if not buttonConfig then
        print("RoughCut: Error - Unknown navigation button: " .. tostring(buttonId))
        return
    end

    logNavigation("opening " .. buttonConfig.label)

    local childWindow = childWindows[buttonConfig.key]
    if not childWindow then
        childWindow = createChildWindow(buttonConfig)
    end

    if not childWindow then
        showMainWindow()
        currentState = NavigationState.HOME
        return
    end

    if not hideMainWindow() then
        logNavigation("main window hide failed before opening " .. buttonConfig.label)
    end

    if not showChildWindow(buttonConfig) then
        showMainWindow()
        currentState = NavigationState.HOME
        logNavigation("returned to home after failed route: " .. buttonConfig.label)
        return
    end

    currentState = buttonConfig.state
    logNavigation("route active: " .. tostring(currentState))
end

function navigation.returnToMain()
    logNavigation("returning to main menu")

    pcall(function() mediaManagement.hide() end)
    pcall(function() formatManagement.hide() end)
    pcall(function() roughCutWorkflow.hide() end)
    showMainWindow()

    currentState = NavigationState.HOME
end

function navigation.getCurrentState()
    return currentState
end

function navigation.isHome()
    return currentState == NavigationState.HOME
end

function navigation.isMainScreen()
    return currentState == NavigationState.HOME
end

function navigation.getCurrentScreen()
    return currentState
end

function navigation.reset()
    currentState = NavigationState.HOME
    navigationButtons = {}
    childWindows = {}
    mainWindowRef = nil
    runtimeRef = nil
end

function navigation.destroy()
    logNavigation("destroying navigation state")
    mediaManagement.destroy()
    formatManagement.destroy()
    roughCutWorkflow.destroy()
    childWindows = {}
    navigation.reset()
end

return navigation
