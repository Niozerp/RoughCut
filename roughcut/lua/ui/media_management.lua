-- RoughCut Media Management Window
-- Dispatcher-safe shell for the media-management route.

local mediaManagement = {}

local okLogger, loggerModule = pcall(require, "utils.logger")
local logger = loggerModule
if not okLogger or not logger then
    logger = {
        info = function(message) print("RoughCut: " .. tostring(message)) end,
        error = function(message) print("RoughCut: " .. tostring(message)) end
    }
end

local runtime = require("ui.runtime")

local WINDOW_CONFIG = {
    id = "RoughCutMediaManagement",
    title = "RoughCut - Media Management",
    geometry = {140, 140, 640, 520}
}

local runtimeRef = nil
local parentWindowRef = nil
local currentWindowRef = nil
local itemsRef = nil
local onReturnToMain = nil
local isDestroying = false

local folderState = {
    music = "Not configured",
    sfx = "Not configured",
    vfx = "Not configured"
}

local function logInfo(message)
    logger.info("RoughCut: Media Management - " .. tostring(message))
end

local function updateText(itemId, value)
    if itemsRef and itemsRef[itemId] then
        pcall(function()
            itemsRef[itemId].Text = value
        end)
    end
end

local function updateFolderLabels()
    updateText("MusicFolderValue", "Music: " .. folderState.music)
    updateText("SfxFolderValue", "SFX: " .. folderState.sfx)
    updateText("VfxFolderValue", "VFX: " .. folderState.vfx)
end

local function setStatus(message)
    updateText("StatusLabel", tostring(message))
    logInfo(message)
end

local function showParentWindow()
    if parentWindowRef then
        pcall(function()
            parentWindowRef:Show()
            parentWindowRef:Raise()
        end)
    end
end

local function returnToMain()
    if isDestroying then
        return
    end

    if currentWindowRef then
        pcall(function()
            currentWindowRef:Hide()
        end)
    end

    showParentWindow()

    if onReturnToMain then
        pcall(onReturnToMain)
    end
end

local function gateAction(message)
    setStatus(message)
end

function mediaManagement.create(uiRuntime, parentWindow)
    if currentWindowRef then
        return currentWindowRef
    end

    if not runtime.isValid(uiRuntime) then
        print("RoughCut: Error - Shared UI runtime required for media management window")
        return nil
    end

    runtimeRef = uiRuntime
    parentWindowRef = parentWindow
    isDestroying = false

    local ui = uiRuntime.ui
    local disp = uiRuntime.disp

    local ok, window = pcall(function()
        return disp:AddWindow({
            ID = WINDOW_CONFIG.id,
            WindowTitle = WINDOW_CONFIG.title,
            Geometry = WINDOW_CONFIG.geometry,

            ui:VGroup{
                ID = "MediaManagementLayout",
                Spacing = 12,
                Weight = 1.0,

                ui:Label{
                    ID = "HeaderLabel",
                    Text = "Manage Media",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 22px; font-weight: bold;"
                },

                ui:Label{
                    ID = "SubtitleLabel",
                    Text = "Dispatcher-safe route shell for folder configuration and indexing.",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 11px;"
                },

                ui:HGroup{
                    ID = "MusicRow",
                    Weight = 0.0,
                    Spacing = 10,
                    ui:Label{
                        ID = "MusicFolderValue",
                        Text = "Music: Not configured",
                        Weight = 1.0
                    },
                    ui:Button{
                        ID = "SelectMusicButton",
                        Text = "Select Music Folder",
                        Weight = 0.0,
                        MinimumSize = {170, 32}
                    }
                },

                ui:HGroup{
                    ID = "SfxRow",
                    Weight = 0.0,
                    Spacing = 10,
                    ui:Label{
                        ID = "SfxFolderValue",
                        Text = "SFX: Not configured",
                        Weight = 1.0
                    },
                    ui:Button{
                        ID = "SelectSfxButton",
                        Text = "Select SFX Folder",
                        Weight = 0.0,
                        MinimumSize = {170, 32}
                    }
                },

                ui:HGroup{
                    ID = "VfxRow",
                    Weight = 0.0,
                    Spacing = 10,
                    ui:Label{
                        ID = "VfxFolderValue",
                        Text = "VFX: Not configured",
                        Weight = 1.0
                    },
                    ui:Button{
                        ID = "SelectVfxButton",
                        Text = "Select VFX Folder",
                        Weight = 0.0,
                        MinimumSize = {170, 32}
                    }
                },

                ui:Label{
                    ID = "GuidanceLabel",
                    Text = "The navigation route is stable. Folder-picker and backend actions are still being migrated off the legacy UI path.",
                    Weight = 0.0,
                    StyleSheet = "font-size: 11px; font-style: italic;"
                },

                ui:HGroup{
                    ID = "ActionRow",
                    Weight = 0.0,
                    Spacing = 10,
                    ui:Button{
                        ID = "SaveButton",
                        Text = "Save",
                        Weight = 1.0,
                        MinimumSize = {0, 34}
                    },
                    ui:Button{
                        ID = "ClearButton",
                        Text = "Clear",
                        Weight = 1.0,
                        MinimumSize = {0, 34}
                    },
                    ui:Button{
                        ID = "ReindexButton",
                        Text = "Re-index",
                        Weight = 1.0,
                        MinimumSize = {0, 34}
                    }
                },

                ui:Label{
                    ID = "StatusLabel",
                    Text = "Route ready. Choose an action or go back to the main menu.",
                    Weight = 1.0,
                    Alignment = {AlignHCenter = true, AlignVCenter = true},
                    StyleSheet = "font-size: 11px;"
                },

                ui:HGroup{
                    ID = "FooterRow",
                    Weight = 0.0,
                    Spacing = 10,
                    ui:Button{
                        ID = "BackButton",
                        Text = "Back to Main Menu",
                        Weight = 0.0,
                        MinimumSize = {170, 34}
                    }
                }
            }
        })
    end)

    if not ok or not window then
        print("RoughCut: Error - Failed to create media management window: " .. tostring(window))
        return nil
    end

    currentWindowRef = window

    local okItems, items = pcall(function()
        return window:GetItems()
    end)
    if okItems then
        itemsRef = items
    end

    function window.On.RoughCutMediaManagement.Close(ev)
        returnToMain()
    end

    function window.On.SelectMusicButton.Clicked(ev)
        gateAction("Music folder picker is temporarily gated while the media-management actions are migrated to dispatcher-safe UI.")
    end

    function window.On.SelectSfxButton.Clicked(ev)
        gateAction("SFX folder picker is temporarily gated while the media-management actions are migrated to dispatcher-safe UI.")
    end

    function window.On.SelectVfxButton.Clicked(ev)
        gateAction("VFX folder picker is temporarily gated while the media-management actions are migrated to dispatcher-safe UI.")
    end

    function window.On.SaveButton.Clicked(ev)
        gateAction("Save is intentionally gated until the backend transport for media folders is migrated off the legacy window stack.")
    end

    function window.On.ClearButton.Clicked(ev)
        folderState.music = "Not configured"
        folderState.sfx = "Not configured"
        folderState.vfx = "Not configured"
        updateFolderLabels()
        gateAction("Cleared the local shell state. Backend clear is still gated in the dispatcher-safe build.")
    end

    function window.On.ReindexButton.Clicked(ev)
        gateAction("Re-index is intentionally gated until the background action layer is migrated to dispatcher-safe UI.")
    end

    function window.On.BackButton.Clicked(ev)
        returnToMain()
    end

    updateFolderLabels()
    setStatus("Route ready. Choose an action or go back to the main menu.")
    return window
end

function mediaManagement.show()
    if not currentWindowRef then
        return false
    end

    updateFolderLabels()
    setStatus("Manage Media opened.")

    local ok = pcall(function()
        currentWindowRef:Show()
        currentWindowRef:Raise()
    end)

    return ok
end

function mediaManagement.hide()
    if not currentWindowRef then
        return false
    end

    local ok = pcall(function()
        currentWindowRef:Hide()
    end)

    return ok
end

function mediaManagement.close()
    if not currentWindowRef then
        return true
    end

    returnToMain()
    return true
end

function mediaManagement.destroy()
    local window = currentWindowRef

    isDestroying = true
    currentWindowRef = nil
    itemsRef = nil
    runtimeRef = nil
    parentWindowRef = nil

    if window then
        pcall(function()
            window:Hide()
            window:Close()
        end)
    end

    isDestroying = false
end

function mediaManagement.setOnReturnToMain(callback)
    onReturnToMain = callback
end

return mediaManagement
