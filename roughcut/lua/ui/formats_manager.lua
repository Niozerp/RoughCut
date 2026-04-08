-- RoughCut Format Management Window
-- Dispatcher-safe shell for browsing rough-cut templates.

local formatManagement = {}

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
    id = "RoughCutFormatManagement",
    title = "RoughCut - Format Management",
    geometry = {160, 160, 640, 520}
}

local TEMPLATES = {
    {
        slug = "social_vertical",
        name = "9:16 Social Vertical",
        description = "Vertical-first cut with room for captions, title cards, and fast transitions.",
        preview = "Aspect: 9:16\nPacing: Fast\nBest for: Shorts, Reels, TikTok"
    },
    {
        slug = "widescreen_story",
        name = "16:9 Story Cut",
        description = "Balanced widescreen cut tuned for narrative pacing and broad platform delivery.",
        preview = "Aspect: 16:9\nPacing: Balanced\nBest for: YouTube, presentations"
    },
    {
        slug = "square_highlight",
        name = "1:1 Highlight",
        description = "Square framing designed for punchy highlight moments and social reposting.",
        preview = "Aspect: 1:1\nPacing: Medium-fast\nBest for: Feed posts, promos"
    }
}

local runtimeRef = nil
local parentWindowRef = nil
local currentWindowRef = nil
local itemsRef = nil
local onReturnToMain = nil
local isDestroying = false
local selectedIndex = 1

local function logInfo(message)
    logger.info("RoughCut: Format Management - " .. tostring(message))
end

local function updateText(itemId, value)
    if itemsRef and itemsRef[itemId] then
        pcall(function()
            itemsRef[itemId].Text = value
        end)
    end
end

local function currentTemplate()
    return TEMPLATES[selectedIndex]
end

local function setStatus(message)
    updateText("StatusLabel", tostring(message))
    logInfo(message)
end

local function updateTemplateView()
    local template = currentTemplate()
    if not template then
        return
    end

    updateText("TemplateCountLabel", "Template " .. tostring(selectedIndex) .. " of " .. tostring(#TEMPLATES))
    updateText("TemplateNameLabel", template.name)
    updateText("TemplateSlugLabel", "Slug: " .. template.slug)
    updateText("TemplateDescriptionLabel", template.description)
    updateText("PreviewLabel", template.preview)
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

function formatManagement.create(uiRuntime, parentWindow)
    if currentWindowRef then
        return currentWindowRef
    end

    if not runtime.isValid(uiRuntime) then
        print("RoughCut: Error - Shared UI runtime required for format management window")
        return nil
    end

    runtimeRef = uiRuntime
    parentWindowRef = parentWindow
    selectedIndex = 1
    isDestroying = false

    local ui = uiRuntime.ui
    local disp = uiRuntime.disp

    local ok, window = pcall(function()
        return disp:AddWindow({
            ID = WINDOW_CONFIG.id,
            WindowTitle = WINDOW_CONFIG.title,
            Geometry = WINDOW_CONFIG.geometry,

            ui:VGroup{
                ID = "FormatManagementLayout",
                Spacing = 12,
                Weight = 1.0,

                ui:Label{
                    ID = "HeaderLabel",
                    Text = "Manage Formats",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 22px; font-weight: bold;"
                },

                ui:Label{
                    ID = "SubtitleLabel",
                    Text = "Stable template browser shell while the legacy dynamic window stack is retired.",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 11px;"
                },

                ui:Label{
                    ID = "TemplateCountLabel",
                    Text = "Template 1 of 3",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 11px; font-style: italic;"
                },

                ui:Label{
                    ID = "TemplateNameLabel",
                    Text = "",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 18px; font-weight: bold;"
                },

                ui:Label{
                    ID = "TemplateSlugLabel",
                    Text = "",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
                    StyleSheet = "font-size: 11px;"
                },

                ui:Label{
                    ID = "TemplateDescriptionLabel",
                    Text = "",
                    Weight = 0.0,
                    StyleSheet = "font-size: 12px;"
                },

                ui:Label{
                    ID = "PreviewHeaderLabel",
                    Text = "Preview",
                    Weight = 0.0,
                    StyleSheet = "font-size: 13px; font-weight: bold;"
                },

                ui:Label{
                    ID = "PreviewLabel",
                    Text = "",
                    Weight = 1.0,
                    StyleSheet = "font-size: 11px;"
                },

                ui:HGroup{
                    ID = "BrowseRow",
                    Weight = 0.0,
                    Spacing = 10,
                    ui:Button{
                        ID = "PreviousTemplateButton",
                        Text = "Previous",
                        Weight = 1.0,
                        MinimumSize = {0, 34}
                    },
                    ui:Button{
                        ID = "NextTemplateButton",
                        Text = "Next",
                        Weight = 1.0,
                        MinimumSize = {0, 34}
                    },
                    ui:Button{
                        ID = "RefreshTemplatesButton",
                        Text = "Refresh",
                        Weight = 1.0,
                        MinimumSize = {0, 34}
                    }
                },

                ui:HGroup{
                    ID = "ActionRow",
                    Weight = 0.0,
                    Spacing = 10,
                    ui:Button{
                        ID = "PreviewTemplateButton",
                        Text = "Use Preview",
                        Weight = 1.0,
                        MinimumSize = {0, 34}
                    },
                    ui:Button{
                        ID = "UseTemplateButton",
                        Text = "Select Template",
                        Weight = 1.0,
                        MinimumSize = {0, 34}
                    }
                },

                ui:Label{
                    ID = "StatusLabel",
                    Text = "Route ready. Browse templates or return to the main menu.",
                    Weight = 0.0,
                    Alignment = {AlignHCenter = true},
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
        print("RoughCut: Error - Failed to create format management window: " .. tostring(window))
        return nil
    end

    currentWindowRef = window

    local okItems, items = pcall(function()
        return window:GetItems()
    end)
    if okItems then
        itemsRef = items
    end

    function window.On.RoughCutFormatManagement.Close(ev)
        returnToMain()
    end

    function window.On.PreviousTemplateButton.Clicked(ev)
        selectedIndex = selectedIndex - 1
        if selectedIndex < 1 then
            selectedIndex = #TEMPLATES
        end
        updateTemplateView()
        setStatus("Showing template " .. tostring(selectedIndex) .. " of " .. tostring(#TEMPLATES) .. ".")
    end

    function window.On.NextTemplateButton.Clicked(ev)
        selectedIndex = selectedIndex + 1
        if selectedIndex > #TEMPLATES then
            selectedIndex = 1
        end
        updateTemplateView()
        setStatus("Showing template " .. tostring(selectedIndex) .. " of " .. tostring(#TEMPLATES) .. ".")
    end

    function window.On.RefreshTemplatesButton.Clicked(ev)
        updateTemplateView()
        setStatus("Template browser refreshed from the dispatcher-safe local catalog.")
    end

    function window.On.PreviewTemplateButton.Clicked(ev)
        local template = currentTemplate()
        setStatus("Preview ready for " .. template.name .. ". The detailed backend preview is still gated while the legacy window stack is retired.")
    end

    function window.On.UseTemplateButton.Clicked(ev)
        local template = currentTemplate()
        setStatus("Selected " .. template.name .. " in the dispatcher-safe shell. Downstream workflow hookup is still pending.")
    end

    function window.On.BackButton.Clicked(ev)
        returnToMain()
    end

    updateTemplateView()
    setStatus("Route ready. Browse templates or return to the main menu.")
    return window
end

function formatManagement.show()
    if not currentWindowRef then
        return false
    end

    updateTemplateView()
    setStatus("Manage Formats opened.")

    local ok = pcall(function()
        currentWindowRef:Show()
        currentWindowRef:Raise()
    end)

    return ok
end

function formatManagement.hide()
    if not currentWindowRef then
        return false
    end

    local ok = pcall(function()
        currentWindowRef:Hide()
    end)

    return ok
end

function formatManagement.close()
    if not currentWindowRef then
        return true
    end

    returnToMain()
    return true
end

function formatManagement.destroy()
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

function formatManagement.setOnReturnToMain(callback)
    onReturnToMain = callback
end

return formatManagement
