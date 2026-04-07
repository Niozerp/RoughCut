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
    
    -- Set up event handlers using Fusion's expected pattern for RunLoop()
    -- RunLoop requires events organized by type, not by element
    win.On = win.On or {}
    
    -- Window-level events
    win.On.Close = function(ev)
        print("RoughCut: Main window closing...")
        -- Close the window and exit message loop
        pcall(function()
            if windowRef then
                windowRef:Close()
            end
        end)
        if dispRef then
            pcall(function() dispRef:ExitLoop() end)
        end
        -- Clear references
        windowRef = nil
        dispRef = nil
    end
    
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
    
    -- Show the window
    local showOk, _ = pcall(function()
        window:Show()
    end)
    
    if not showOk then
        print("RoughCut: Error - Failed to show main window")
        return false
    end
    
    print("RoughCut: Main window shown")
    
    -- NOTE: We do NOT call disp:RunLoop() here.
    -- RunLoop() blocks the Resolve UI thread and causes 'ontbl' nil errors.
    -- The window persists via Resolve's native window lifecycle.
    
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
