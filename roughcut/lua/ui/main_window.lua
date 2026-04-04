-- RoughCut Main Window Component
-- Defines the main application window with navigation
-- Compatible with DaVinci Resolve's Lua scripting environment

local mainWindow = {}

-- Version info for display
local VERSION = "0.2.0"
local BUILD_DATE = "2026-04-03"

-- Window configuration constants
-- Dimensions validated to fit within typical Resolve workspace
local WINDOW_CONFIG = {
    title = "RoughCut - AI-Powered Rough Cut Generator",
    width = 400,
    height = 500,
    id = "RoughCutMainWindow",
    maxWidthRatio = 0.8,  -- 80% of display width
    maxHeightRatio = 0.8  -- 80% of display height
}

-- Store references for state preservation
local windowRef = nil
local uiManagerRef = nil
local footerLabelRef = nil

-- Validate and adjust window dimensions for display size
local function getValidatedDimensions()
    local width = WINDOW_CONFIG.width
    local height = WINDOW_CONFIG.height
    
    -- Try to get display size (best effort - may not work in all Resolve versions)
    pcall(function()
        local ok, resolve = pcall(function() return Resolve() end)
        if ok and resolve then
            local ok_mgr, projectManager = pcall(function() return resolve:GetProjectManager() end)
            if ok_mgr and projectManager then
                local ok_proj, currentProject = pcall(function() return projectManager:GetCurrentProject() end)
                if ok_proj and currentProject then
                    -- Use project settings as proxy for workspace awareness
                    -- Conservative defaults that work across screen sizes
                    local maxWidth = 1920 * WINDOW_CONFIG.maxWidthRatio
                    local maxHeight = 1080 * WINDOW_CONFIG.maxHeightRatio
                    
                    if width > maxWidth then
                        width = math.floor(maxWidth)
                    end
                    if height > maxHeight then
                        height = math.floor(maxHeight)
                    end
                end
            end
        end
    end)
    
    return width, height
end

-- Create and configure the main window
-- @param uiManager Resolve UI Manager instance
-- @return window table or nil on error
function mainWindow.create(uiManager)
    if not uiManager then
        print("RoughCut: Error - UI Manager required for main window")
        return nil
    end
    
    uiManagerRef = uiManager
    
    -- Get validated dimensions
    local width, height = getValidatedDimensions()
    
    -- Use pcall to handle any Resolve API errors
    local ok, window = pcall(function()
        return uiManager:Add({
            type = "Window",
            id = WINDOW_CONFIG.id,
            title = WINDOW_CONFIG.title,
            width = width,
            height = height,
            spacing = 20,
            padding = 20
        })
    end)
    
    if not ok or not window then
        print("RoughCut: Error - Failed to create main window")
        return nil
    end
    
    windowRef = window
    
    -- Add window header/title label
    local okHeader, headerLabel = pcall(function()
        return window:Add({
            type = "Label",
            text = "RoughCut",
            font = { size = 24, bold = true },
            alignment = { alignHCenter = true }
        })
    end)
    
    if not okHeader then
        print("RoughCut: Warning - Could not add header label")
    end
    
    -- Add subtitle
    local okSubtitle, subtitleLabel = pcall(function()
        return window:Add({
            type = "Label",
            text = "AI-Powered Rough Cut Generator",
            font = { size = 12 },
            alignment = { alignHCenter = true }
        })
    end)
    
    if not okSubtitle then
        print("RoughCut: Warning - Could not add subtitle label")
    end
    
    -- Add separator line (using empty label as spacer)
    local okSpacer = pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 10
        })
    end)
    
    if not okSpacer then
        print("RoughCut: Warning - Could not add spacer")
    end
    
    -- Add footer with version and status
    local okFooter = pcall(function()
        -- Spacer before footer
        window:Add({
            type = "Label",
            text = "",
            height = 20
        })
        
        -- Footer container with border-like appearance using labels
        local footerText = "Version " .. VERSION .. " • Ready"
        footerLabelRef = window:Add({
            type = "Label",
            id = "footerStatusLabel",
            text = footerText,
            font = { size = 10, italic = true },
            alignment = { alignHCenter = true }
        })
        
        return footerLabelRef
    end)
    
    if not okFooter then
        print("RoughCut: Warning - Could not add footer")
    end
    
    return window
end

-- Show the main window
-- @param window Window instance created by mainWindow.create()
-- @return boolean success
function mainWindow.show(window)
    if not window then
        print("RoughCut: Error - No window to show")
        return false
    end
    
    local ok = pcall(function()
        window:Show()
    end)
    
    if not ok then
        print("RoughCut: Error - Failed to show main window")
        return false
    end
    
    return true
end

-- Hide the main window
-- @param window Window instance
-- @return boolean success
function mainWindow.hide(window)
    if not window then
        print("RoughCut: Error - No window to hide")
        return false
    end
    
    local ok = pcall(function()
        window:Hide()
    end)
    
    if not ok then
        print("RoughCut: Error - Failed to hide main window")
        return false
    end
    
    return true
end

-- Close and destroy the main window
-- @param window Window instance
-- @return boolean success
function mainWindow.close(window)
    if not window then
        print("RoughCut: Error - No window to close")
        return false
    end
    
    local ok = pcall(function()
        window:Close()
    end)
    
    if not ok then
        print("RoughCut: Error - Failed to close main window")
        return false
    end
    
    windowRef = nil
    return true
end

-- Update footer status text
-- @param statusText New status text to display
-- @return boolean success
function mainWindow.updateStatus(statusText)
    if not footerLabelRef then
        return false
    end
    
    local ok = pcall(function()
        footerLabelRef.Text = "Version " .. VERSION .. " • " .. statusText
    end)
    
    return ok
end

-- Get the window reference (for state preservation)
-- @return window reference or nil
function mainWindow.getWindow()
    return windowRef
end

-- Get UI Manager reference
-- @return uiManager reference or nil
function mainWindow.getUIManager()
    return uiManagerRef
end

return mainWindow
