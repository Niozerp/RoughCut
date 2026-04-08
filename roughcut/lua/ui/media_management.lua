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

-- Try to load protocol module for backend communication
local okProtocol, protocol = pcall(require, "utils.protocol")
if not okProtocol or not protocol then
    protocol = nil
end

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
local dispRef = nil

local folderState = {
    music = "Not configured",
    sfx = "Not configured",
    vfx = "Not configured"
}

-- Track if folders are saved to backend
local foldersModified = false

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

-- Backend communication functions
local function sendToBackend(method, params, callback)
    if not protocol then
        setStatus("Backend communication not available")
        return false
    end
    
    local ok, result = pcall(function()
        return protocol.sendRequest(method, params, callback)
    end)
    
    if not ok then
        setStatus("Backend communication error: " .. tostring(result))
        return false
    end
    
    return true
end

local function loadFolderConfig()
    setStatus("Loading folder configuration...")
    
    sendToBackend("get_media_folders", {}, function(response)
        if response.error then
            setStatus("Error loading config: " .. tostring(response.error.message))
            return
        end
        
        local result = response.result or response
        
        -- Update folder state from backend
        if result.music_folder and result.music_folder ~= "" then
            folderState.music = result.music_folder
        else
            folderState.music = "Not configured"
        end
        
        if result.sfx_folder and result.sfx_folder ~= "" then
            folderState.sfx = result.sfx_folder
        else
            folderState.sfx = "Not configured"
        end
        
        if result.vfx_folder and result.vfx_folder ~= "" then
            folderState.vfx = result.vfx_folder
        else
            folderState.vfx = "Not configured"
        end
        
        foldersModified = false
        updateFolderLabels()
        setStatus("Folder configuration loaded")
        logInfo("Loaded folder config - Music: " .. folderState.music .. ", SFX: " .. folderState.sfx .. ", VFX: " .. folderState.vfx)
    end)
end

local function saveFolderConfig()
    setStatus("Saving folder configuration...")
    
    local params = {}
    
    -- Only send folders that are configured (not "Not configured")
    if folderState.music ~= "Not configured" then
        params.music_folder = folderState.music
    end
    if folderState.sfx ~= "Not configured" then
        params.sfx_folder = folderState.sfx
    end
    if folderState.vfx ~= "Not configured" then
        params.vfx_folder = folderState.vfx
    end
    
    sendToBackend("save_media_folders", params, function(response)
        if response.error then
            setStatus("Error saving config: " .. tostring(response.error.message))
            logInfo("Save failed: " .. tostring(response.error.message))
            return
        end
        
        local result = response.result or response
        
        if result.success then
            foldersModified = false
            setStatus("Folder configuration saved successfully")
            logInfo("Folder config saved: " .. tostring(result.message))
        else
            setStatus("Save failed: " .. tostring(result.message or "Unknown error"))
            logInfo("Save failed: " .. tostring(result.message))
        end
    end)
end

local function clearFolderConfig()
    setStatus("Clearing folder configuration...")
    
    sendToBackend("clear_media_folders", {}, function(response)
        if response.error then
            setStatus("Error clearing config: " .. tostring(response.error.message))
            logInfo("Clear failed: " .. tostring(response.error.message))
            return
        end
        
        local result = response.result or response
        
        if result.success then
            folderState.music = "Not configured"
            folderState.sfx = "Not configured"
            folderState.vfx = "Not configured"
            foldersModified = false
            updateFolderLabels()
            setStatus("Folder configuration cleared")
            logInfo("Folder config cleared: " .. tostring(result.message))
        else
            setStatus("Clear failed: " .. tostring(result.message or "Unknown error"))
            logInfo("Clear failed: " .. tostring(result.message))
        end
    end)
end

local function triggerReindex()
    setStatus("Starting media re-index...")
    
    sendToBackend("trigger_reindex", {}, function(response)
        if response.error then
            setStatus("Re-index failed: " .. tostring(response.error.message))
            logInfo("Re-index failed: " .. tostring(response.error.message))
            return
        end
        
        local result = response.result or response
        
        if result.success then
            local stats = result.result or {}
            local msg = string.format(
                "Re-index complete - New: %d, Modified: %d, Deleted: %d",
                stats.new_count or 0,
                stats.modified_count or 0,
                stats.deleted_count or 0
            )
            setStatus(msg)
            logInfo(msg)
        else
            setStatus("Re-index failed: " .. tostring(result.message or "Unknown error"))
            logInfo("Re-index failed: " .. tostring(result.message))
        end
    end)
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
    dispRef = uiRuntime.disp

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
                    Text = "Select folders for Music, SFX, and VFX assets. Click Save to store configuration, then Re-index to scan for media files.",
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

    local function selectFolder(folderType, title)
        logInfo("Opening folder picker for " .. folderType)
        
        -- Get fusion object from global context
        local fu = _G.fu or _G.fusion
        if not fu then
            gateAction("Error: Fusion not available")
            logInfo("ERROR: fusion object not available!")
            return
        end
        
        -- Try to find RequestDir function
        -- It may be on fu object itself, or as a global function
        logInfo("Looking for RequestDir function...")
        
        local requestDirFunc = nil
        
        -- Try fu:RequestDir (method on fusion object)
        if type(fu.RequestDir) == "function" then
            requestDirFunc = function(t, defaultPath) return fu:RequestDir(t, defaultPath) end
            logInfo("Found fu:RequestDir")
        -- Try fu.RequestDir (function field on fusion)
        elseif type(fu.RequestDir) ~= "nil" then
            logInfo("fu.RequestDir exists but is not a function, type: " .. type(fu.RequestDir))
        end
        
        -- Try global RequestDir if not found on fu
        if not requestDirFunc and type(_G.RequestDir) == "function" then
            requestDirFunc = function(t, defaultPath) return _G.RequestDir(t, defaultPath) end
            logInfo("Found global RequestDir")
        end
        
        -- Try bmd.RequestDir if available
        if not requestDirFunc and _G.bmd and type(_G.bmd.RequestDir) == "function" then
            requestDirFunc = function(t, defaultPath) return _G.bmd.RequestDir(t, defaultPath) end
            logInfo("Found bmd.RequestDir")
        end
        
        if not requestDirFunc then
            -- Log what we found for debugging
            logInfo("fu type: " .. type(fu))
            logInfo("fu.RequestDir type: " .. type(fu.RequestDir))
            logInfo("_G.RequestDir type: " .. type(_G.RequestDir))
            if _G.bmd then
                logInfo("bmd.RequestDir type: " .. type(_G.bmd.RequestDir))
            else
                logInfo("bmd is nil")
            end
            
            gateAction("Folder picker not available in this Resolve version")
            logInfo("ERROR: No RequestDir function found!")
            return
        end
        
        logInfo("Calling RequestDir...")
        
        local ok, result = pcall(function()
            return requestDirFunc(title, "")
        end)

        logInfo("RequestDir pcall ok: " .. tostring(ok) .. ", result type: " .. type(result) .. ", value: " .. tostring(result))

        if ok then
            if result and result ~= "" then
                folderState[folderType] = result
                foldersModified = true
                updateFolderLabels()
                setStatus(folderType .. " folder set to: " .. result)
                logInfo(folderType .. " folder selected: " .. result)
            else
                setStatus(folderType .. " folder selection cancelled")
                logInfo(folderType .. " folder selection cancelled (empty result)")
            end
        else
            setStatus("Error selecting folder: " .. tostring(result))
            logInfo("ERROR in RequestDir: " .. tostring(result))
        end
    end

    function window.On.SelectMusicButton.Clicked(ev)
        selectFolder("music", "Select Music Folder")
    end

    function window.On.SelectSfxButton.Clicked(ev)
        selectFolder("sfx", "Select SFX Folder")
    end

    function window.On.SelectVfxButton.Clicked(ev)
        selectFolder("vfx", "Select VFX Folder")
    end

    function window.On.SaveButton.Clicked(ev)
        saveFolderConfig()
    end

    function window.On.ClearButton.Clicked(ev)
        clearFolderConfig()
    end

    function window.On.ReindexButton.Clicked(ev)
        triggerReindex()
    end

    function window.On.BackButton.Clicked(ev)
        returnToMain()
    end

    updateFolderLabels()
    setStatus("Route ready. Choose an action or go back to the main menu.")
    
    -- Load existing folder configuration from backend
    loadFolderConfig()
    
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
    dispRef = nil

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
