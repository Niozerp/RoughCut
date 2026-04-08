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

local function closeMainWindow(window, closeWindow)
    local targetWindow = window or windowRef

    if targetWindow then
        pcall(function()
            targetWindow:Hide()
        end)
    end

    if dispRef then
        pcall(function()
            dispRef:ExitLoop()
        end)
    end

    if closeWindow ~= false and targetWindow then
        pcall(function()
            targetWindow:Close()
        end)
    end

    windowRef = nil
    dispRef = nil
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

                uiManager:HGroup{
                    ID = "CloseButtonRow",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},

                    uiManager:Button{
                        ID = "CloseButton",
                        Text = "Close",
                        Weight = 0.0,
                        MinimumSize = {120, 30}
                    }
                },

                uiManager:Label{
                    ID = "Spacer3",
                    Text = "",
                    Weight = 0.0,
                    MinimumSize = {0, 10}
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
    
    local function handleWindowClose()
        print("RoughCut: Main window close requested...")
        closeMainWindow(win, false)
    end

    -- Use Fusion's documented dispatcher event model. Mixing direct widget
    -- callbacks with win.On handlers causes dispatcher startup failures.
    function win.On.RoughCutMainWindow.Close(ev)
        handleWindowClose()
    end

    function win.On.CloseButton.Clicked(ev)
        handleWindowClose()
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
    
    -- Keep the window alive until the user closes it.
    -- Resolve/Fusion Utility scripts need the dispatcher loop to stay open.
    if dispRef then
        local loopOk, loopErr = pcall(function()
            dispRef:RunLoop()
        end)

        if not loopOk then
            print("RoughCut: Error - Dispatcher loop failed: " .. tostring(loopErr))
            return false
        end
    else
        print("RoughCut: Warning - No dispatcher available for main window loop")
    end
    
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
    
    if dispRef then
        local ok = pcall(function()
            dispRef:ExitLoop()
        end)
        if not ok then
            print("RoughCut: Warning - Failed to exit dispatcher loop (may be stuck)")
            success = false
        end
    end

    local ok = pcall(function()
        window:Hide()
    end)
    if not ok then
        print("RoughCut: Warning - Failed to hide window")
        success = false
    end

    local closeOk = pcall(function()
        window:Close()
    end)
    if not closeOk then
        print("RoughCut: Warning - Failed to close window")
        success = false
    end

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
