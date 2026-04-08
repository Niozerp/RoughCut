-- RoughCut Main Window Component
-- Defines the main application window with navigation
-- Compatible with DaVinci Resolve's Lua scripting environment

local mainWindow = {}

local VERSION = "0.3.1"
local BUILD_DATE = "2026-04-05"

local WINDOW_CONFIG = {
    title = "RoughCut - AI-Powered Rough Cut Generator",
    width = 400,
    height = 500,
    id = "RoughCutMainWindow",
    geometry = {100, 100, 400, 500}
}

local windowRef = nil
local runtimeRef = nil
local dispRef = nil
local onCloseCallback = nil
local closeCallbackInvoked = false

local HOME_BUTTONS = {
    {
        id = "btnManageMedia",
        label = "Manage Media",
        description = "Set up your Music, SFX, and VFX folders",
        tooltip = "Configure folders and index your Music, SFX, and VFX assets"
    },
    {
        id = "btnManageFormats",
        label = "Manage Formats",
        description = "Define rough cut templates for your projects",
        tooltip = "View and select video format templates for rough cuts"
    },
    {
        id = "btnCreateRoughCut",
        label = "Create Rough Cut",
        description = "Select media and format to create rough cuts",
        tooltip = "Start the AI-powered rough cut generation workflow"
    }
}

local function invokeCloseCallback()
    if closeCallbackInvoked then
        return
    end

    closeCallbackInvoked = true
    if onCloseCallback then
        pcall(onCloseCallback)
    end
end

local function closeMainWindow(window, closeWindow)
    local targetWindow = window or windowRef

    invokeCloseCallback()

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
    runtimeRef = nil
    dispRef = nil
    onCloseCallback = nil
    closeCallbackInvoked = false
end

function mainWindow.create(uiRuntime)
    if not uiRuntime or not uiRuntime.ui or not uiRuntime.disp then
        print("RoughCut: Error - Shared UI runtime required for main window")
        return nil
    end

    local uiManager = uiRuntime.ui

    runtimeRef = uiRuntime
    dispRef = uiRuntime.disp
    onCloseCallback = nil
    closeCallbackInvoked = false

    local ok, win = pcall(function()
        return dispRef:AddWindow({
            ID = WINDOW_CONFIG.id,
            WindowTitle = WINDOW_CONFIG.title,
            Geometry = WINDOW_CONFIG.geometry,

            uiManager:VGroup{
                ID = "MainLayout",
                Spacing = 15,
                Weight = 1.0,

                uiManager:Label{
                    ID = "HeaderLabel",
                    Text = "RoughCut",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 24px; font-weight: bold;"
                },

                uiManager:Label{
                    ID = "SubtitleLabel",
                    Text = "AI-Powered Rough Cut Generator",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 12px;"
                },

                uiManager:Label{
                    ID = "Spacer1",
                    Text = "",
                    Weight = 0.0,
                    MinimumSize = {0, 10}
                },

                uiManager:Label{
                    ID = "NavigationIntroLabel",
                    Text = "What would you like to do?",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 14px; font-weight: bold;"
                },

                uiManager:VGroup{
                    ID = "HomeSection",
                    Weight = 1.0,
                    Spacing = 12,

                    uiManager:Label{
                        ID = "ManageMediaDescription",
                        Text = HOME_BUTTONS[1].description,
                        Weight = 0.0,
                        StyleSheet = "font-size: 11px; font-style: italic;"
                    },
                    uiManager:Button{
                        ID = HOME_BUTTONS[1].id,
                        Text = HOME_BUTTONS[1].label,
                        Weight = 0.0,
                        MinimumSize = {0, 42}
                    },

                    uiManager:Label{
                        ID = "ManageFormatsDescription",
                        Text = HOME_BUTTONS[2].description,
                        Weight = 0.0,
                        StyleSheet = "font-size: 11px; font-style: italic;"
                    },
                    uiManager:Button{
                        ID = HOME_BUTTONS[2].id,
                        Text = HOME_BUTTONS[2].label,
                        Weight = 0.0,
                        MinimumSize = {0, 42}
                    },

                    uiManager:Label{
                        ID = "CreateRoughCutDescription",
                        Text = HOME_BUTTONS[3].description,
                        Weight = 0.0,
                        StyleSheet = "font-size: 11px; font-style: italic;"
                    },
                    uiManager:Button{
                        ID = HOME_BUTTONS[3].id,
                        Text = HOME_BUTTONS[3].label,
                        Weight = 0.0,
                        MinimumSize = {0, 42}
                    },

                    uiManager:Label{
                        ID = "StatusLabel",
                        Text = "Choose an action to get started.",
                        Weight = 1.0,
                        Alignment = {AlignHCenter = true, AlignVCenter = true},
                        StyleSheet = "font-size: 11px;"
                    }
                },

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

    if not ok or not win then
        print("RoughCut: Error - Failed to create main window: " .. tostring(win))
        return nil
    end

    windowRef = win

    local okItems, items = pcall(function()
        return win:GetItems()
    end)

    if okItems and items then
        for _, button in ipairs(HOME_BUTTONS) do
            local item = items[button.id]
            if item then
                pcall(function()
                    item.ToolTip = button.tooltip
                end)
                pcall(function()
                    item.Tooltip = button.tooltip
                end)
            end
        end
    end

    local function handleWindowClose()
        print("RoughCut: Main window close requested...")
        closeMainWindow(win, false)
    end

    function win.On.RoughCutMainWindow.Close(ev)
        handleWindowClose()
    end

    function win.On.CloseButton.Clicked(ev)
        handleWindowClose()
    end

    print("RoughCut: Main window created successfully")
    return win
end

function mainWindow.setOnClose(callback)
    onCloseCallback = callback
    closeCallbackInvoked = false
end

function mainWindow.show(window)
    if not window then
        print("RoughCut: Error - Cannot show main window, not created")
        return false
    end

    local showOk = pcall(function()
        window:Show()
        window:Raise()
    end)

    if not showOk then
        print("RoughCut: Error - Failed to show main window")
        return false
    end

    print("RoughCut: Main window shown")

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

function mainWindow.hide(window)
    if not window then
        return false
    end

    local ok = pcall(function()
        window:Hide()
    end)

    return ok
end

function mainWindow.close(window)
    if not window then
        return true
    end

    local ok = pcall(function()
        closeMainWindow(window, true)
    end)

    if not ok then
        print("RoughCut: Warning - Failed to close window")
    end

    return ok
end

function mainWindow.getContentArea()
    if not windowRef then
        return nil
    end

    local ok, content = pcall(function()
        return windowRef:FindChild("HomeSection")
    end)

    if ok and content then
        return content
    end

    return nil
end

function mainWindow.setContentText(text)
    if not windowRef then
        return false
    end

    local ok = pcall(function()
        local content = windowRef:FindChild("StatusLabel")
        if content then
            content.Text = text or ""
        end
    end)

    return ok
end

return mainWindow
