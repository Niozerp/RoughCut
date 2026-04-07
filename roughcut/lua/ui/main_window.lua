-- RoughCut Main Window Component
-- Defines the main application window with navigation
-- Compatible with DaVinci Resolve's Lua scripting environment
-- Uses UIDispatcher pattern like install_dialog.lua

local mainWindow = {}

-- Version info for display
local VERSION = "0.3.1"
local BUILD_DATE = "2026-04-05"

-- Window configuration constants
local WINDOW_CONFIG = {
    title = "RoughCut - AI-Powered Rough Cut Generator",
    width = 400,
    height = 500,
    id = "RoughCutMainWindow",
    -- TODO: Get actual screen geometry for multi-monitor support
    -- Currently hardcoded to {100, 100} which may be off-screen on some setups
    geometry = {100, 100, 400, 500}
}

-- Store references for state preservation
local windowRef = nil
local uiManagerRef = nil
local dispRef = nil

-- Create and configure the main window
-- @param uiManager Resolve UI Manager instance
-- @return window table or nil on error
function mainWindow.create(uiManager)
    if not uiManager then
        print("RoughCut: Error - UI Manager required for main window")
        return nil
    end
    
    uiManagerRef = uiManager
    
    -- Check if bmd is available
    if not bmd then
        print("RoughCut: Error - bmd module not available (required for UIDispatcher)")
        return nil
    end
    
    -- Check if UIDispatcher field exists on bmd
    if not bmd.UIDispatcher then
        print("RoughCut: Error - bmd.UIDispatcher not available")
        return nil
    end
    
    -- Create the UIDispatcher - THIS IS REQUIRED!
    local ok, disp = pcall(function()
        return bmd.UIDispatcher(uiManager)
    end)
    
    if not ok or not disp then
        print("RoughCut: Error - Failed to create UIDispatcher: " .. tostring(disp))
        return nil
    end
    
    dispRef = disp
    
    -- Create window using disp:AddWindow() with nested UI layout (same pattern as install_dialog)
    local ok2, win = pcall(function()
        return disp:AddWindow({
            ID = WINDOW_CONFIG.id,
            WindowTitle = WINDOW_CONFIG.title,
            Geometry = WINDOW_CONFIG.geometry,
            
            -- Main vertical layout with all children
            uiManager:VGroup{
                ID = "MainLayout",
                Spacing = 15,
                Weight = 1.0,
                
                -- Header label
                uiManager:Label{
                    ID = "HeaderLabel",
                    Text = "RoughCut",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 24px; font-weight: bold;"
                },
                
                -- Subtitle
                uiManager:Label{
                    ID = "SubtitleLabel",
                    Text = "AI-Powered Rough Cut Generator",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 12px;"
                },
                
                -- Spacer
                uiManager:Label{
                    ID = "Spacer1",
                    Text = "",
                    Weight = 0.0,
                    MinimumSize = {0, 10}
                },
                
                -- Main content area (placeholder for future navigation)
                uiManager:Label{
                    ID = "ContentArea",
                    Text = "RoughCut is ready\n\nNavigation temporarily disabled for UI update",
                    Weight = 1.0,
                    Alignment = {AlignHCenter = true, AlignVCenter = true}
                },
                
                -- Spacer before footer
                uiManager:Label{
                    ID = "Spacer2",
                    Text = "",
                    Weight = 0.0,
                    MinimumSize = {0, 20}
                },
                
                -- Footer with version
                uiManager:Label{
                    ID = "FooterLabel",
                    Text = "v" .. VERSION .. " | " .. BUILD_DATE,
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 10px; color: #666;"
                }
            }
        })
    end)
    
    if not ok2 or not win then
        print("RoughCut: Error - Failed to create main window: " .. tostring(win))
        return nil
    end
    
    windowRef = win
    
    print("RoughCut: Main window created successfully")
    return win
end

-- Show the main window
-- @param window Window object returned from create()
-- @return boolean indicating success
function mainWindow.show(window)
    if not window then
        print("RoughCut: Error - Cannot show main window, not created")
        return false
    end
    
    local ok, _ = pcall(function()
        window:Show()
    end)
    
    if not ok then
        print("RoughCut: Error - Failed to show main window")
        return false
    end
    
    -- NOTE: We do NOT call disp:RunLoop() here because this may be non-blocking
    -- The calling code is responsible for handling the window lifecycle
    
    return true
end

-- Hide the main window
-- @param window Window object returned from create()
-- @return boolean indicating success
function mainWindow.hide(window)
    if not window then
        return false
    end
    
    local ok, _ = pcall(function()
        window:Hide()
    end)
    
    return ok
end

-- Close and destroy the main window
-- @param window Window object returned from create()
-- @return boolean indicating success
function mainWindow.close(window)
    if not window then
        return true
    end
    
    local success = true
    
    -- Exit the dispatcher loop if it was running
    -- Note: ExitLoop may hang if dispatcher is stuck; pcall provides timeout-like protection
    if dispRef then
        local ok = pcall(function()
            dispRef:ExitLoop()
        end)
        if not ok then
            print("RoughCut: Warning - Failed to exit dispatcher loop (may be stuck)")
            -- Force clear reference even if exit failed
            dispRef = nil
            success = false
        end
    end
    
    -- Close the window
    local ok = pcall(function()
        window:Close()
    end)
    if not ok then
        print("RoughCut: Warning - Failed to close window")
        success = false
    end
    
    -- Clear references
    windowRef = nil
    dispRef = nil
    
    return success
end

-- Get the content area for adding navigation buttons
-- @return content area object or nil
function mainWindow.getContentArea()
    if not windowRef then
        return nil
    end
    
    local ok, content = pcall(function()
        return windowRef:FindChild("ContentArea")
    end)
    
    if ok and content then
        return content
    end
    
    return nil
end

-- Update the content area text
-- @param text New text to display
-- @return boolean indicating success
function mainWindow.setContentText(text)
    if not windowRef then
        return false
    end
    
    local ok, _ = pcall(function()
        local content = windowRef:FindChild("ContentArea")
        if content then
            content.Text = text or ""
        end
    end)
    
    return ok
end

return mainWindow
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
