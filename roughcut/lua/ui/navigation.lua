-- RoughCut Navigation Component
-- Defines navigation buttons and handlers for main interface
-- Compatible with DaVinci Resolve's Lua scripting environment

-- Import placeholder windows for navigation
local mediaManagement = require("ui.media_management")
local formatManagement = require("ui.formats_manager")
local roughCutWorkflow = require("ui.rough_cut_workflow")

local navigation = {}

-- Navigation configuration - Story 1.2 AC requires exactly 3 buttons
local NAV_CONFIG = {
    buttons = {
        {
            id = "btnManageMedia",
            label = "Manage Media",
            tooltip = "Configure folders and index your Music, SFX, and VFX assets",
            description = "Set up your Music, SFX, and VFX folders"
        },
        {
            id = "btnManageFormats",
            label = "Manage Formats",
            tooltip = "View and select video format templates for rough cuts",
            description = "Define rough cut templates for your projects"
        },
        {
            id = "btnCreateRoughCut",
            label = "Create Rough Cut",
            tooltip = "Start the AI-powered rough cut generation workflow",
            description = "Select media and format to create rough cuts"
        }
    },
    buttonHeight = 60,
    buttonSpacing = 15
}

-- Navigation state machine states
local NavigationState = {
    HOME = "home",
    MEDIA_MANAGEMENT = "media_management",
    FORMAT_MANAGEMENT = "format_management",
    ROUGH_CUT_WORKFLOW = "rough_cut_workflow"
}

-- Current navigation state
local currentState = NavigationState.HOME
local mainWindowRef = nil
local uiManagerRef = nil
local navigationButtons = {}
local childWindows = {}

-- Create navigation buttons in the main window
-- @param window Main window instance
-- @return boolean success
function navigation.create(window)
    if not window then
        print("RoughCut: Error - Window required for navigation")
        return false
    end
    
    mainWindowRef = window
    navigationButtons = {}
    childWindows = {}
    
    -- Get UI Manager from window for child window creation
    -- Note: We need to get this from the main entry point
    
    -- Add navigation section label
    local okNavLabel = pcall(function()
        window:Add({
            type = "Label",
            text = "What would you like to do?",
            font = { size = 14 },
            alignment = { alignHCenter = true }
        })
    end)
    
    if not okNavLabel then
        print("RoughCut: Warning - Could not add navigation label")
    end
    
    -- Add spacer before buttons
    local okSpacer = pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 10
        })
    end)
    
    -- Create each navigation button
    for i, btnConfig in ipairs(NAV_CONFIG.buttons) do
        local ok, button = pcall(function()
            -- Add description label above button
            window:Add({
                type = "Label",
                text = btnConfig.description,
                font = { size = 10, italic = true },
                alignment = { alignLeft = true }
            })
            
            -- Create the button with hover styling
            local btn = window:Add({
                type = "Button",
                id = btnConfig.id,
                text = btnConfig.label,
                height = NAV_CONFIG.buttonHeight,
                alignment = { alignHCenter = true },
                style = {
                    hoverBackground = { r = 0.3, g = 0.5, b = 0.8 },
                    hoverBorder = { r = 0.4, g = 0.6, b = 0.9, width = 2 }
                }
            })
            
            -- Set tooltip if supported
            pcall(function()
                btn.Tooltip = btnConfig.tooltip
            end)
            
            return btn
        end)
        
        if ok and button then
            -- Store button reference
            navigationButtons[btnConfig.id] = button
            
            -- Attach click handler with error protection
            local okClick = pcall(function()
                button.Clicked = function()
                    -- Wrap navigation handler in pcall for error protection
                    local navOk, navErr = pcall(function()
                        navigation.handleNavigation(btnConfig.id)
                    end)
                    if not navOk then
                        print("RoughCut: Error in navigation handler for " .. btnConfig.label .. ": " .. tostring(navErr))
                    end
                end
            end)
            
            if not okClick then
                print("RoughCut: Warning - Could not attach click handler to " .. btnConfig.label)
            end
            
            -- Add spacing after button (except for last one)
            if i < #NAV_CONFIG.buttons then
                pcall(function()
                    window:Add({
                        type = "Label",
                        text = "",
                        height = NAV_CONFIG.buttonSpacing
                    })
                end)
            end
        else
            print("RoughCut: Error - Failed to create button: " .. btnConfig.label)
        end
    end
    
    return true
end

-- Set UI Manager reference (needed for creating child windows)
-- @param uiManager Resolve UI Manager instance
function navigation.setUIManager(uiManager)
    -- Validate UI Manager parameter
    if not uiManager then
        print("RoughCut: Error - UI Manager cannot be nil")
        return false
    end
    
    -- Verify it has required methods
    local ok, hasAdd = pcall(function()
        return type(uiManager.Add) == "function"
    end)
    
    if not ok or not hasAdd then
        print("RoughCut: Error - Invalid UI Manager (missing Add method)")
        return false
    end
    
    uiManagerRef = uiManager
    return true
end

-- Safely show a child window with error handling
-- @param childWindow Window instance
-- @param showFunc Function to call to show the window
-- @return boolean success
local function safelyShowChildWindow(childWindow, showFunc)
    if not childWindow then
        print("RoughCut: Error - Cannot show nil child window")
        return false
    end
    
    local ok, err = pcall(showFunc)
    if not ok then
        print("RoughCut: Error - Failed to show child window: " .. tostring(err))
        return false
    end
    
    return true
end

-- Handle navigation button clicks
-- @param buttonId ID of the clicked button
function navigation.handleNavigation(buttonId)
    if not uiManagerRef then
        print("RoughCut: Error - UI Manager not set for navigation")
        return
    end
    
    local buttonConfig = nil
    
    -- Find button configuration
    for _, btn in ipairs(NAV_CONFIG.buttons) do
        if btn.id == buttonId then
            buttonConfig = btn
            break
        end
    end
    
    if not buttonConfig then
        print("RoughCut: Error - Unknown navigation button: " .. tostring(buttonId))
        return
    end
    
    print("RoughCut: Navigating to " .. buttonConfig.label)
    
    -- Create child window first (before hiding main window)
    local childWindow = nil
    local createOk, createErr = pcall(function()
        if buttonId == "btnManageMedia" then
            if not childWindows.media then
                childWindows.media = mediaManagement.create(uiManagerRef, mainWindowRef)
            end
            childWindow = childWindows.media
            if childWindow then
                currentState = NavigationState.MEDIA_MANAGEMENT
            end
            
        elseif buttonId == "btnManageFormats" then
            if not childWindows.format then
                childWindows.format = formatManagement.create(uiManagerRef, mainWindowRef)
            end
            childWindow = childWindows.format
            if childWindow then
                currentState = NavigationState.FORMAT_MANAGEMENT
            end
            
        elseif buttonId == "btnCreateRoughCut" then
            if not childWindows.workflow then
                childWindows.workflow = roughCutWorkflow.create(uiManagerRef, mainWindowRef)
            end
            childWindow = childWindows.workflow
            if childWindow then
                currentState = NavigationState.ROUGH_CUT_WORKFLOW
            end
        end
    end)
    
    -- Only proceed if child window was created successfully
    if not createOk then
        print("RoughCut: Error - Failed to create child window: " .. tostring(createErr))
        return
    end
    
    if not childWindow then
        print("RoughCut: Error - Child window creation returned nil for " .. buttonConfig.label)
        return
    end
    
    -- Now safe to hide main window and show child with error handling
    -- Hide main window first
    local hideOk = pcall(function()
        if mainWindowRef then
            mainWindowRef:Hide()
        end
    end)
    
    if not hideOk then
        print("RoughCut: Warning - Could not hide main window")
    end
    
    -- Show the appropriate child window with error handling
    local showSuccess = false
    if buttonId == "btnManageMedia" then
        showSuccess = safelyShowChildWindow(childWindow, function() mediaManagement.show() end)
    elseif buttonId == "btnManageFormats" then
        showSuccess = safelyShowChildWindow(childWindow, function() formatManagement.show() end)
    elseif buttonId == "btnCreateRoughCut" then
        showSuccess = safelyShowChildWindow(childWindow, function() roughCutWorkflow.show() end)
    end
    
    -- If showing failed, recover by showing main window again
    if not showSuccess then
        print("RoughCut: Error - Failed to show child window, returning to main menu")
        pcall(function()
            if mainWindowRef then
                mainWindowRef:Show()
            end
        end)
        currentState = NavigationState.HOME
    end
end

-- Return to main navigation screen (called from child windows)
function navigation.returnToMain()
    print("RoughCut: Returning to main menu")
    
    local ok = pcall(function()
        -- Hide any visible child windows
        if childWindows.media then
            pcall(function() childWindows.media:Hide() end)
        end
        if childWindows.format then
            pcall(function() childWindows.format:Hide() end)
        end
        if childWindows.workflow then
            pcall(function() childWindows.workflow:Hide() end)
        end
        
        -- Show main window
        if mainWindowRef then
            mainWindowRef:Show()
        end
        
        currentState = NavigationState.HOME
    end)
    
    if not ok then
        print("RoughCut: Error - Failed to return to main menu")
    end
end

-- Get current navigation state
-- @return string current screen ID
function navigation.getCurrentState()
    return currentState
end

-- Check if we're on the home screen
-- @return boolean
function navigation.isHome()
    return currentState == NavigationState.HOME
end

-- Check if we're on the main screen (alias for isHome)
-- @return boolean
function navigation.isMainScreen()
    return currentState == NavigationState.HOME
end

-- Get current navigation screen (alias for getCurrentState)
-- @return string current screen ID
function navigation.getCurrentScreen()
    return currentState
end

-- Reset navigation state (useful for window reopening)
function navigation.reset()
    currentState = NavigationState.HOME
    navigationButtons = {}
    childWindows = {}
    mainWindowRef = nil
    uiManagerRef = nil
end

-- Clean up all windows
function navigation.destroy()
    -- Destroy child windows
    if childWindows.media then
        pcall(function() childWindows.media:Close() end)
    end
    if childWindows.format then
        pcall(function() childWindows.format:Close() end)
    end
    if childWindows.workflow then
        pcall(function() childWindows.workflow:Close() end)
    end
    childWindows = {}
    navigation.reset()
end

return navigation
