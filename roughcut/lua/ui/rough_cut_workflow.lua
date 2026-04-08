-- RoughCut Rough Cut Workflow Window
-- Dispatcher-safe shell for the rough-cut workflow route.

local roughCutWorkflow = {}

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
    id = "RoughCutWorkflow",
    title = "RoughCut - Create Rough Cut",
    geometry = {180, 180, 700, 560}
}

local FORMAT_OPTIONS = {
    "9:16 Social Vertical",
    "16:9 Story Cut",
    "1:1 Highlight"
}

local runtimeRef = nil
local parentWindowRef = nil
local currentWindowRef = nil
local itemsRef = nil
local onReturnToMain = nil
local isDestroying = false

local workflowState = {
    sessionId = nil,
    selectedFormatIndex = 1,
    mediaSelection = "Media Pool browser gated until its legacy dialog is migrated."
}

local function logInfo(message)
    logger.info("RoughCut: Rough Cut Workflow - " .. tostring(message))
end

local function updateText(itemId, value)
    if itemsRef and itemsRef[itemId] then
        pcall(function()
            itemsRef[itemId].Text = value
        end)
    end
end

local function setStatus(message)
    updateText("StatusLabel", tostring(message))
    logInfo(message)
end

local function updateWorkflowView()
    local currentFormat = FORMAT_OPTIONS[workflowState.selectedFormatIndex]
    updateText("SessionLabel", "Session: " .. tostring(workflowState.sessionId or "not started"))
    updateText("SelectedMediaLabel", "Media: " .. workflowState.mediaSelection)
    updateText("SelectedFormatLabel", "Format: " .. currentFormat)
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

local function initializeSession()
    workflowState.sessionId = "dispatcher-shell-" .. tostring(os.time())
    workflowState.selectedFormatIndex = 1
    workflowState.mediaSelection = "Media Pool browser gated until its legacy dialog is migrated."
end

function roughCutWorkflow.create(uiRuntime, parentWindow)
    if currentWindowRef then
        return currentWindowRef
    end

    if not runtime.isValid(uiRuntime) then
        print("RoughCut: Error - Shared UI runtime required for rough cut workflow window")
        return nil
    end

    runtimeRef = uiRuntime
    parentWindowRef = parentWindow
    isDestroying = false
    initializeSession()

    local ui = uiRuntime.ui
    local disp = uiRuntime.disp

    local ok, window = pcall(function()
        return disp:AddWindow({
            ID = WINDOW_CONFIG.id,
            WindowTitle = WINDOW_CONFIG.title,
            Geometry = WINDOW_CONFIG.geometry,

            ui:VGroup{
                ID = "WorkflowLayout",
                Spacing = 12,
                Weight = 1.0,

                ui:Label{
                    ID = "HeaderLabel",
                    Text = "Create Rough Cut",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 22px; font-weight: bold;"
                },

                ui:Label{
                    ID = "SubtitleLabel",
                    Text = "Stable workflow shell while the media browser and generator are migrated to dispatcher-safe UI.",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 11px;"
                },

                ui:Label{
                    ID = "SessionLabel",
                    Text = "",
                    Weight = 0.0,
                    StyleSheet = "font-size: 11px; font-style: italic;"
                },

                ui:Label{
                    ID = "StepOneLabel",
                    Text = "Step 1: Source Media",
                    Weight = 0.0,
                    StyleSheet = "font-size: 13px; font-weight: bold;"
                },
                ui:Label{
                    ID = "SelectedMediaLabel",
                    Text = "",
                    Weight = 0.0,
                    StyleSheet = "font-size: 11px;"
                },
                ui:Button{
                    ID = "BrowseMediaButton",
                    Text = "Browse Media Pool",
                    Weight = 0.0,
                    MinimumSize = {220, 36}
                },

                ui:Label{
                    ID = "StepTwoLabel",
                    Text = "Step 2: Format Template",
                    Weight = 0.0,
                    StyleSheet = "font-size: 13px; font-weight: bold;"
                },
                ui:Label{
                    ID = "SelectedFormatLabel",
                    Text = "",
                    Weight = 0.0,
                    StyleSheet = "font-size: 11px;"
                },
                ui:HGroup{
                    ID = "FormatRow",
                    Weight = 0.0,
                    Spacing = 10,
                    ui:Button{
                        ID = "CycleFormatButton",
                        Text = "Next Format",
                        Weight = 0.0,
                        MinimumSize = {150, 34}
                    },
                    ui:Button{
                        ID = "PreviewSelectionButton",
                        Text = "Preview Selection",
                        Weight = 0.0,
                        MinimumSize = {170, 34}
                    }
                },

                ui:Label{
                    ID = "StepThreeLabel",
                    Text = "Step 3: Generate",
                    Weight = 0.0,
                    StyleSheet = "font-size: 13px; font-weight: bold;"
                },
                ui:Button{
                    ID = "GenerateRoughCutButton",
                    Text = "Generate Rough Cut",
                    Weight = 0.0,
                    MinimumSize = {220, 36}
                },

                ui:Label{
                    ID = "StatusLabel",
                    Text = "Route ready. Work through the shell or return to the main menu.",
                    Weight = 1.0,
                    Alignment = {AlignHCenter = true, AlignVCenter = true},
                    StyleSheet = "font-size: 11px;"
                },

                ui:Button{
                    ID = "BackButton",
                    Text = "Back to Main Menu",
                    Weight = 0.0,
                    MinimumSize = {180, 34}
                }
            }
        })
    end)

    if not ok or not window then
        print("RoughCut: Error - Failed to create rough cut workflow window: " .. tostring(window))
        return nil
    end

    currentWindowRef = window

    local okItems, items = pcall(function()
        return window:GetItems()
    end)
    if okItems then
        itemsRef = items
    end

    function window.On.RoughCutWorkflow.Close(ev)
        returnToMain()
    end

    function window.On.BrowseMediaButton.Clicked(ev)
        setStatus("Media Browser is intentionally gated because it still relies on a legacy non-dispatcher dialog.")
    end

    function window.On.CycleFormatButton.Clicked(ev)
        workflowState.selectedFormatIndex = workflowState.selectedFormatIndex + 1
        if workflowState.selectedFormatIndex > #FORMAT_OPTIONS then
            workflowState.selectedFormatIndex = 1
        end
        updateWorkflowView()
        setStatus("Selected format shell: " .. FORMAT_OPTIONS[workflowState.selectedFormatIndex] .. ".")
    end

    function window.On.PreviewSelectionButton.Clicked(ev)
        updateWorkflowView()
        setStatus("Preview shell ready. Detailed backend preview is still gated while the workflow route is migrated.")
    end

    function window.On.GenerateRoughCutButton.Clicked(ev)
        setStatus("Rough cut generation is intentionally gated until the backend action layer is migrated to dispatcher-safe UI.")
    end

    function window.On.BackButton.Clicked(ev)
        returnToMain()
    end

    updateWorkflowView()
    setStatus("Route ready. Work through the shell or return to the main menu.")
    return window
end

function roughCutWorkflow.show()
    if not currentWindowRef then
        return false
    end

    updateWorkflowView()
    setStatus("Create Rough Cut opened.")

    local ok = pcall(function()
        currentWindowRef:Show()
        currentWindowRef:Raise()
    end)

    return ok
end

function roughCutWorkflow.hide()
    if not currentWindowRef then
        return false
    end

    local ok = pcall(function()
        currentWindowRef:Hide()
    end)

    return ok
end

function roughCutWorkflow.close()
    if not currentWindowRef then
        return true
    end

    returnToMain()
    return true
end

function roughCutWorkflow.destroy()
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

function roughCutWorkflow.setOnReturnToMain(callback)
    onReturnToMain = callback
end

return roughCutWorkflow
