-- RoughCut Media Management Window
-- Media folder configuration for Epic 2
-- Compatible with DaVinci Resolve's Lua scripting environment
-- Version: 1.0.0

local mediaManagement = {}

-- Window configuration
local WINDOW_CONFIG = {
    id = "RoughCutMediaManagement",
    title = "RoughCut - Media Management",
    width = 600,
    height = 500
}

-- Reference to parent window for navigation
local parentWindowRef = nil
local currentWindowRef = nil
local uiManagerRef = nil

-- UI element references
local musicFolderLabelRef = nil
local sfxFolderLabelRef = nil
local vfxFolderLabelRef = nil
local statusLabelRef = nil
local errorLabelRef = nil

-- Current configuration state
local currentConfig = {
    musicFolder = "",
    sfxFolder = "",
    vfxFolder = "",
    configured = false,
    lastUpdated = nil
}

-- Create the media management window
-- @param uiManager Resolve UI Manager instance
-- @param parentWindow Reference to main window for navigation back
-- @return window table or nil on error
function mediaManagement.create(uiManager, parentWindow)
    if not uiManager then
        print("RoughCut: Error - UI Manager required for media management window")
        return nil
    end
    
    uiManagerRef = uiManager
    parentWindowRef = parentWindow
    
    -- Create window with error handling
    local ok, window = pcall(function()
        return uiManager:Add({
            type = "Window",
            id = WINDOW_CONFIG.id,
            title = WINDOW_CONFIG.title,
            width = WINDOW_CONFIG.width,
            height = WINDOW_CONFIG.height,
            spacing = 15,
            padding = 20
        })
    end)
    
    if not ok or not window then
        print("RoughCut: Error - Failed to create media management window")
        return nil
    end
    
    currentWindowRef = window
    
    -- Add header
    local okHeader = pcall(function()
        window:Add({
            type = "Label",
            text = "Media Folder Configuration",
            font = { size = 20, bold = true },
            alignment = { alignHCenter = true }
        })
    end)
    
    if not okHeader then
        print("RoughCut: Warning - Could not add header to media management window")
    end
    
    -- Add subtitle
    pcall(function()
        window:Add({
            type = "Label",
            text = "Configure parent folders for your media assets",
            font = { size = 10, italic = true },
            alignment = { alignHCenter = true }
        })
    end)
    
    -- Add spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 10
        })
    end)
    
    -- Status indicator
    local okStatus = pcall(function()
        statusLabelRef = window:Add({
            type = "Label",
            id = "statusLabel",
            text = "Status: Not configured",
            font = { size = 12, bold = true },
            alignment = { alignHCenter = true }
        })
    end)
    
    if not okStatus then
        print("RoughCut: Warning - Could not add status label")
    end
    
    -- Add spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 20
        })
    end)
    
    -- Music Folder Section
    createFolderSection(window, "Music", "musicFolder", "Select Music Folder")
    
    -- Add spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 15
        })
    end)
    
    -- SFX Folder Section
    createFolderSection(window, "SFX", "sfxFolder", "Select SFX Folder")
    
    -- Add spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 15
        })
    end)
    
    -- VFX Folder Section
    createFolderSection(window, "VFX", "vfxFolder", "Select VFX Folder")
    
    -- Add spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 20
        })
    end)
    
    -- Error message label (hidden by default)
    local okError = pcall(function()
        errorLabelRef = window:Add({
            type = "Label",
            id = "errorLabel",
            text = "",
            font = { size = 10, color = { r = 1, g = 0, b = 0 } },
            alignment = { alignHCenter = true },
            visible = false
        })
    end)
    
    -- Add spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 15
        })
    end)
    
    -- Save Configuration button
    local okSaveBtn = pcall(function()
        local saveBtn = window:Add({
            type = "Button",
            id = "saveButton",
            text = "Save Configuration",
            height = 45,
            style = {
                background = { r = 0.2, g = 0.6, b = 0.3 },
                hoverBackground = { r = 0.25, g = 0.7, b = 0.35 }
            }
        })
        
        saveBtn.Clicked = function()
            mediaManagement.handleSave()
        end
        
        return saveBtn
    end)
    
    if not okSaveBtn then
        print("RoughCut: Warning - Could not add save button")
    end
    
    -- Small spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 10
        })
    end)
    
    -- Clear Configuration button
    local okClearBtn = pcall(function()
        local clearBtn = window:Add({
            type = "Button",
            id = "clearButton",
            text = "Clear Configuration",
            height = 35,
            style = {
                background = { r = 0.6, g = 0.2, b = 0.2 },
                hoverBackground = { r = 0.7, g = 0.25, b = 0.25 }
            }
        })
        
        clearBtn.Clicked = function()
            mediaManagement.handleClear()
        end
        
        return clearBtn
    end)
    
    if not okClearBtn then
        print("RoughCut: Warning - Could not add clear button")
    end
    
    -- Small spacer
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 10
        })
    end)
    
    -- Re-index Media button
    local okReindexBtn = pcall(function()
        local reindexBtn = window:Add({
            type = "Button",
            id = "reindexButton",
            text = "Re-index Media Library",
            height = 40,
            style = {
                background = { r = 0.3, g = 0.4, b = 0.8 },
                hoverBackground = { r = 0.35, g = 0.45, b = 0.9 }
            }
        })
        
        reindexBtn.Clicked = function()
            mediaManagement.handleReindex()
        end
        
        return reindexBtn
    end)
    
    if not okReindexBtn then
        print("RoughCut: Warning - Could not add re-index button")
    end
    
    -- Add spacer before back button
    pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 20
        })
    end)
    
    -- "Back to Main" button
    local okBackButton = pcall(function()
        window:Add({
            type = "Label",
            text = "",
            height = 10
        })
        
        local backBtn = window:Add({
            type = "Button",
            id = "btnBackToMain",
            text = "← Back to Main Menu",
            height = 40,
            alignment = { alignHCenter = true }
        })
        
        if backBtn then
            backBtn.Clicked = function()
                mediaManagement.close()
            end
        end
        
        return backBtn
    end)
    
    if not okBackButton then
        print("RoughCut: Warning - Could not add back button to media management window")
    end
    
    return window
end

-- Create a folder section UI component
-- @param window Parent window
-- @param category Category name (Music, SFX, VFX)
-- @param configKey Key in currentConfig for this folder
-- @param buttonText Text for the select button
function createFolderSection(window, category, configKey, buttonText)
    -- Category label
    pcall(function()
        window:Add({
            type = "Label",
            text = category .. " Folder:",
            font = { size = 12, bold = true },
            alignment = { alignLeft = true }
        })
    end)
    
    -- Current path label
    local pathLabel = nil
    local okPathLabel = pcall(function()
        local initialText = "Not configured"
        if currentConfig[configKey] and currentConfig[configKey] ~= "" then
            initialText = currentConfig[configKey]
        end
        
        pathLabel = window:Add({
            type = "Label",
            id = "pathLabel" .. category,
            text = initialText,
            font = { size = 9, italic = true, color = { r = 0.5, g = 0.5, b = 0.5 } },
            alignment = { alignLeft = true }
        })
        
        -- Store reference for updates
        if category == "Music" then
            musicFolderLabelRef = pathLabel
        elseif category == "SFX" then
            sfxFolderLabelRef = pathLabel
        elseif category == "VFX" then
            vfxFolderLabelRef = pathLabel
        end
    end)
    
    if not okPathLabel then
        print("RoughCut: Warning - Could not add path label for " .. category)
    end
    
    -- Select folder button
    local okSelectBtn = pcall(function()
        local selectBtn = window:Add({
            type = "Button",
            id = "btnSelect" .. category,
            text = buttonText,
            height = 35,
            style = {
                background = { r = 0.2, g = 0.5, b = 0.8 },
                hoverBackground = { r = 0.25, g = 0.6, b = 0.9 }
            }
        })
        
        selectBtn.Clicked = function()
            mediaManagement.handleSelectFolder(category, configKey)
        end
        
        return selectBtn
    end)
    
    if not okSelectBtn then
        print("RoughCut: Warning - Could not add select button for " .. category)
    end
end

-- Show the media management window
-- @param uiManager Resolve UI Manager instance
-- @param parentWindow Parent window to return to
function mediaManagement.show(uiManager, parentWindow)
    if not uiManager then
        print("RoughCut: Error - UI Manager required")
        return false
    end
    
    uiManagerRef = uiManager
    parentWindowRef = parentWindow
    
    -- Create window if it doesn't exist
    if not currentWindowRef then
        mediaManagement.create(uiManager, parentWindow)
    end
    
    if not currentWindowRef then
        print("RoughCut: Error - Failed to create media management window")
        return false
    end
    
    -- Load current configuration
    mediaManagement.loadConfig()
    
    -- Show window and hide parent
    local success = pcall(function()
        currentWindowRef:Show()
        if parentWindow then
            parentWindow:Hide()
        end
    end)
    
    if not success then
        print("RoughCut: Error - Failed to show media management window")
        return false
    end
    
    return true
end

-- Hide the media management window
-- @return boolean success
function mediaManagement.hide()
    if not currentWindowRef then
        return false
    end
    
    local ok = pcall(function()
        currentWindowRef:Hide()
    end)
    
    return ok
end

-- Close the media management window and return to main
-- @return boolean success
function mediaManagement.close()
    print("RoughCut: Closing media management window")
    
    local ok = pcall(function()
        -- Hide current window
        if currentWindowRef then
            currentWindowRef:Hide()
        end
        
        -- Show parent window if available and valid
        if parentWindowRef and parentWindowRef.Show then
            parentWindowRef:Show()
        end
        
        -- Clear reference to indicate window is closed
        currentWindowRef = nil
    end)
    
    if not ok then
        print("RoughCut: Error - Failed to close media management window properly")
    end
    
    return ok
end

-- Clean up resources
function mediaManagement.destroy()
    if currentWindowRef then
        pcall(function()
            currentWindowRef:Close()
        end)
        currentWindowRef = nil
    end
    parentWindowRef = nil
    uiManagerRef = nil
    musicFolderLabelRef = nil
    sfxFolderLabelRef = nil
    vfxFolderLabelRef = nil
    statusLabelRef = nil
    errorLabelRef = nil
    
    -- Clean up any pending requests to prevent memory leaks
    if _G._pending_requests then
        _G._pending_requests = {}
    end
end

-- Request counter for unique IDs
local requestCounter = 0

-- Pending requests storage
_G._pending_requests = {}

-- Generate unique request ID
local function generateRequestId()
    requestCounter = requestCounter + 1
    return "req_" .. tostring(os.time()) .. "_" .. tostring(requestCounter)
end

-- Wait for response with timeout
-- @param requestId The request ID to wait for
-- @param timeoutSeconds Maximum time to wait (default: 5)
-- @return response or nil if timeout
local function waitForResponse(requestId, timeoutSeconds)
    timeoutSeconds = timeoutSeconds or 5
    local startTime = os.time()
    
    -- Poll for response with timeout
    while (os.time() - startTime) < timeoutSeconds do
        if _G._pending_requests[requestId] and _G._pending_requests[requestId].response then
            local response = _G._pending_requests[requestId].response
            _G._pending_requests[requestId] = nil  -- Clean up
            return response
        end
        -- Small delay to prevent tight loop
        -- In DaVinci Resolve Lua, we can't really sleep, but we can yield
        -- by doing a minimal operation
        local dummy = os.time()
    end
    
    -- Timeout reached
    _G._pending_requests[requestId] = nil  -- Clean up
    print("RoughCut: Timeout waiting for backend response (request: " .. requestId .. ")")
    return nil
end

-- Load current configuration from backend
function mediaManagement.loadConfig()
    local requestId = generateRequestId()
    _G._pending_requests[requestId] = {timestamp = os.time()}
    
    local success, result = pcall(function()
        local request = {
            method = "get_media_folders",
            params = {},
            id = requestId
        }
        
        local requestJson = json.encode(request)
        print("RC_JSONRPC:" .. requestJson)
        
        -- Wait for response with timeout
        local response = waitForResponse(requestId, 5)
        
        if not response then
            print("RoughCut: Error loading media config - timeout or no response")
            return nil
        end
        
        if response.error then
            print("RoughCut: Error loading media config: " .. tostring(response.error.message))
            return nil
        end
        
        return response.result
    end)
    
    if success and result then
        currentConfig = {
            musicFolder = result.music_folder or "",
            sfxFolder = result.sfx_folder or "",
            vfxFolder = result.vfx_folder or "",
            configured = result.configured or false,
            lastUpdated = result.last_updated
        }
    else
        -- Default to not configured if load fails
        currentConfig = {
            musicFolder = "",
            sfxFolder = "",
            vfxFolder = "",
            configured = false,
            lastUpdated = nil
        }
        
        -- Show error to user if loading failed
        if not success then
            mediaManagement.showError("Failed to load configuration - backend timeout")
        end
    end
    
    -- Update UI labels with loaded values
    mediaManagement.updateFolderLabels()
    mediaManagement.updateStatusDisplay()
end

-- Update folder path labels
function mediaManagement.updateFolderLabels()
    local function updateLabel(labelRef, path)
        if labelRef then
            pcall(function()
                if path and #path > 0 then
                    labelRef.Text = path
                    labelRef.Font = { size = 9, italic = false, color = { r = 0.2, g = 0.6, b = 0.2 } }
                else
                    labelRef.Text = "Not configured"
                    labelRef.Font = { size = 9, italic = true, color = { r = 0.5, g = 0.5, b = 0.5 } }
                end
            end)
        end
    end
    
    updateLabel(musicFolderLabelRef, currentConfig.musicFolder)
    updateLabel(sfxFolderLabelRef, currentConfig.sfxFolder)
    updateLabel(vfxFolderLabelRef, currentConfig.vfxFolder)
end

-- Update the status label based on current config
function mediaManagement.updateStatusDisplay()
    if not statusLabelRef then
        return
    end
    
    local success = pcall(function()
        if currentConfig.configured then
            statusLabelRef.Text = "Status: ✓ Configured"
            statusLabelRef.Font = { size = 12, bold = true, color = { r = 0, g = 0.7, b = 0 } }
        else
            statusLabelRef.Text = "Status: Not configured"
            statusLabelRef.Font = { size = 12, bold = true, color = { r = 0.7, g = 0.5, b = 0 } }
        end
    end)
    
    if not success then
        print("RoughCut: Warning - Could not update status display")
    end
end

-- Handle folder selection button click
-- @param category Category name (Music, SFX, VFX)
-- @param configKey Key in currentConfig for this folder
function mediaManagement.handleSelectFolder(category, configKey)
    mediaManagement.showError("")
    
    -- Show folder browser dialog
    if uiManagerRef then
        local success, result = pcall(function()
            -- Resolve doesn't have a native folder browser in all versions
            -- We'll simulate this with a request to Python backend
            -- In a real implementation, this would open a native file dialog
            
            -- For now, we'll use a LineEdit dialog to get the path
            -- This is a workaround for environments without native folder dialogs
            local dialog = uiManagerRef:Add({
                type = "Window",
                id = "FolderSelectDialog",
                title = "Enter " .. category .. " Folder Path",
                width = 500,
                height = 150
            })
            
            dialog:Add({
                type = "Label",
                text = "Please enter the absolute path to your " .. category .. " folder:",
                font = { size = 11 }
            })
            
            local pathInput = dialog:Add({
                type = "LineEdit",
                id = "pathInput",
                placeholder = "/path/to/" .. category:lower() .. "/folder",
                height = 30
            })
            
            -- Pre-fill with current value if any
            if currentConfig[configKey] and currentConfig[configKey] ~= "" then
                pathInput.Text = currentConfig[configKey]
            end
            
            dialog:Add({
                type = "Label",
                text = "",
                height = 10
            })
            
            local confirmBtn = dialog:Add({
                type = "Button",
                text = "Confirm",
                height = 35,
                style = {
                    background = { r = 0.2, g = 0.6, b = 0.3 }
                }
            })
            
            confirmBtn.Clicked = function()
                local path = pathInput.Text or ""
                if path and #path > 0 then
                    -- Validate the path
                    mediaManagement.validateAndSetFolder(category, configKey, path)
                end
                dialog:Hide()
            end
            
            local cancelBtn = dialog:Add({
                type = "Button",
                text = "Cancel",
                height = 35,
                style = {
                    background = { r = 0.6, g = 0.2, b = 0.2 }
                }
            })
            
            cancelBtn.Clicked = function()
                dialog:Hide()
            end
            
            dialog:Show()
        end)
        
        if not success then
            print("RoughCut: Error showing folder dialog: " .. tostring(result))
            mediaManagement.showError("Could not open folder selection dialog")
        end
    else
        mediaManagement.showError("UI Manager not available")
    end
end

-- Validate and set a folder path
-- @param category Category name
-- @param configKey Key in currentConfig
-- @param path Folder path to validate and set
function mediaManagement.validateAndSetFolder(category, configKey, path)
    -- Clear previous error
    mediaManagement.showError("")
    
    local requestId = generateRequestId()
    _G._pending_requests[requestId] = {timestamp = os.time()}
    
    -- Call backend to validate the path
    local success, result = pcall(function()
        local request = {
            method = "validate_folder_path",
            params = {
                path = path,
                category = category:lower()
            },
            id = requestId
        }
        
        local requestJson = json.encode(request)
        print("RC_JSONRPC:" .. requestJson)
        
        -- Wait for response with timeout
        local response = waitForResponse(requestId, 5)
        
        if not response then
            return {
                valid = false,
                error = "Backend timeout - no response received"
            }
        end
        
        if response.error then
            return {
                valid = false,
                error = response.error.message or "Validation failed"
            }
        end
        
        return response.result
    end)
    
    if success and result then
        if result.valid then
            -- Update local config with validated path
            currentConfig[configKey] = result.absolute_path or path
            mediaManagement.updateFolderLabels()
            mediaManagement.showError(category .. " folder set: " .. currentConfig[configKey], true)
        else
            mediaManagement.showError(category .. ": " .. (result.error or "Invalid path"))
        end
    else
        -- If validation call fails, still allow the path but warn
        currentConfig[configKey] = path
        mediaManagement.updateFolderLabels()
        print("RoughCut: Warning - Path validation failed, using path anyway: " .. path)
    end
end

-- Handle save button click
function mediaManagement.handleSave()
    mediaManagement.showError("")
    
    local requestId = generateRequestId()
    _G._pending_requests[requestId] = {timestamp = os.time()}
    
    -- Call Python backend to save configuration
    local success, result = pcall(function()
        local request = {
            method = "save_media_folders",
            params = {
                music_folder = currentConfig.musicFolder ~= "" and currentConfig.musicFolder or nil,
                sfx_folder = currentConfig.sfxFolder ~= "" and currentConfig.sfxFolder or nil,
                vfx_folder = currentConfig.vfxFolder ~= "" and currentConfig.vfxFolder or nil
            },
            id = requestId
        }
        
        local requestJson = json.encode(request)
        print("RC_JSONRPC:" .. requestJson)
        
        -- Wait for response with timeout
        local response = waitForResponse(requestId, 5)
        
        if not response then
            return {
                success = false,
                message = "Backend timeout - no response received"
            }
        end
        
        if response.error then
            return {
                success = false,
                message = response.error.message or "Save failed",
                details = response.error.details
            }
        end
        
        return response.result
    end)
    
    if success and result then
        if result.success then
            currentConfig.configured = true
            mediaManagement.updateStatusDisplay()
            mediaManagement.showError("Configuration saved successfully", true)
            
            -- Show success dialog if UI manager supports it
            if uiManagerRef then
                pcall(function()
                    uiManagerRef:ShowMessageDialog(
                        "Configuration Saved",
                        "Your media folder configuration has been saved successfully.",
                        "OK"
                    )
                end)
            end
        else
            local errorMsg = result.message or "Failed to save"
            
            -- Add details if available
            if result.details then
                for category, error in pairs(result.details) do
                    errorMsg = errorMsg .. "\n" .. category .. ": " .. error
                end
            end
            
            mediaManagement.showError(errorMsg)
        end
    else
        mediaManagement.showError("Failed to communicate with backend: " .. tostring(result))
    end
end

-- Handle clear button click
function mediaManagement.handleClear()
    local requestId = generateRequestId()
    _G._pending_requests[requestId] = {timestamp = os.time()}
    
    -- Call Python backend to clear configuration
    local success, result = pcall(function()
        local request = {
            method = "clear_media_folders",
            params = {},
            id = requestId
        }
        
        local requestJson = json.encode(request)
        print("RC_JSONRPC:" .. requestJson)
        
        -- Wait for response with timeout
        local response = waitForResponse(requestId, 5)
        
        if not response then
            return false, "Backend timeout - no response received"
        end
        
        if response.error then
            return false, response.error.message or "Clear failed"
        end
        
        return true, response.result and response.result.message or "Configuration cleared"
    end)
    
    if success then
        local ok, message = result
        if ok then
            -- Reset local config
            currentConfig = {
                musicFolder = "",
                sfxFolder = "",
                vfxFolder = "",
                configured = false,
                lastUpdated = nil
            }
            
            mediaManagement.updateFolderLabels()
            mediaManagement.updateStatusDisplay()
            mediaManagement.showError("Configuration cleared", true)
        else
            mediaManagement.showError("Failed to clear: " .. tostring(message))
        end
    else
        mediaManagement.showError("Failed to communicate with backend: " .. tostring(result))
    end
end

-- Show error or success message
-- @param message Message to display (empty to hide)
-- @param isSuccess If true, show as success (green), else error (red)
function mediaManagement.showError(message, isSuccess)
    if not errorLabelRef then
        return
    end
    
    local success = pcall(function()
        if not message or message == "" then
            errorLabelRef.Visible = false
            errorLabelRef.Text = ""
        else
            errorLabelRef.Visible = true
            errorLabelRef.Text = message
            
            if isSuccess then
                errorLabelRef.Font = { size = 10, color = { r = 0, g = 0.7, b = 0 } }
            else
                errorLabelRef.Font = { size = 10, color = { r = 1, g = 0, b = 0 } }
            end
        end
    end)
    
    if not success then
        print("RoughCut: Warning - Could not show error message")
    end
end

-- Show re-index confirmation dialog
-- @return boolean true if user confirmed
function mediaManagement.showReindexConfirmation()
    if not uiManagerRef then
        return false
    end
    
    local confirmed = false
    
    local success = pcall(function()
        local dialog = uiManagerRef:Add({
            type = "Window",
            id = "ReindexConfirmationDialog",
            title = "Confirm Re-indexing",
            width = 450,
            height = 280,
            modal = true
        })
        
        if not dialog then
            return
        end
        
        -- Message
        dialog:Add({
            type = "Label",
            text = "Re-indexing will scan all configured folders and may take several minutes for large libraries.",
            wordWrap = true,
            font = { size = 11 }
        })
        
        dialog:Add({
            type = "Label",
            text = "",
            height = 10
        })
        
        -- What it will do
        dialog:Add({
            type = "Label",
            text = "This will:",
            font = { size = 11, bold = true }
        })
        
        dialog:Add({
            type = "Label",
            text = "  • Scan all Music, SFX, and VFX folders",
            font = { size = 10 }
        })
        
        dialog:Add({
            type = "Label",
            text = "  • Detect new, moved, and deleted files",
            font = { size = 10 }
        })
        
        dialog:Add({
            type = "Label",
            text = "  • Update the asset database",
            font = { size = 10 }
        })
        
        dialog:Add({
            type = "Label",
            text = "",
            height = 15
        })
        
        -- Buttons row
        local btnRow = dialog:Add({
            type = "HorizontalLayout",
            spacing = 20
        })
        
        -- Continue button
        local continueBtn = btnRow:Add({
            type = "Button",
            text = "Continue",
            width = 100,
            height = 35,
            style = {
                background = { r = 0.2, g = 0.6, b = 0.3 }
            }
        })
        
        continueBtn.Clicked = function()
            confirmed = true
            dialog:Hide()
        end
        
        -- Cancel button
        local cancelBtn = btnRow:Add({
            type = "Button",
            text = "Cancel",
            width = 100,
            height = 35,
            style = {
                background = { r = 0.6, g = 0.2, b = 0.2 }
            }
        })
        
        cancelBtn.Clicked = function()
            confirmed = false
            dialog:Hide()
        end
        
        dialog:Show()
    end)
    
    if not success then
        print("RoughCut: Error showing re-index confirmation dialog")
        return false
    end
    
    return confirmed
end

-- Handle re-index button click
function mediaManagement.handleReindex()
    -- Show confirmation dialog
    if not mediaManagement.showReindexConfirmation() then
        return
    end
    
    mediaManagement.showError("Re-indexing started...", true)
    
    local requestId = generateRequestId()
    _G._pending_requests[requestId] = {timestamp = os.time()}
    
    -- Call Python backend to trigger re-indexing
    local success, result = pcall(function()
        local request = {
            method = "trigger_reindex",
            params = {},
            id = requestId
        }
        
        local requestJson = json.encode(request)
        print("RC_JSONRPC:" .. requestJson)
        
        -- Wait for response with longer timeout (re-indexing can take time)
        -- 5 minutes allows for scanning large libraries (20,000+ files)
        -- while still detecting hung operations. Adjust based on library size.
        local response = waitForResponse(requestId, 300)  -- 5 minute timeout
        
        if not response then
            return {
                success = false,
                message = "Re-indexing timeout - operation may still be in progress"
            }
        end
        
        if response.error then
            return {
                success = false,
                message = response.error.message or "Re-indexing failed"
            }
        end
        
        return response.result
    end)
    
    if success and result then
        if result.success then
            local stats = result.result
            local message = string.format(
                "Re-indexing complete!\nNew: %d | Modified: %d | Moved: %d | Deleted: %d",
                stats.new_count or 0,
                stats.modified_count or 0,
                stats.moved_count or 0,
                stats.deleted_count or 0
            )
            
            mediaManagement.showError(message, true)
            
            -- Show success dialog
            if uiManagerRef then
                pcall(function()
                    uiManagerRef:ShowMessageDialog(
                        "Re-indexing Complete",
                        message,
                        "OK"
                    )
                end)
            end
        else
            mediaManagement.showError("Re-indexing failed: " .. (result.message or "Unknown error"))
        end
    else
        mediaManagement.showError("Failed to communicate with backend: " .. tostring(result))
    end
end

-- Get current window reference
function mediaManagement.getWindow()
    return currentWindowRef
end

-- Check if media folders are configured (for external use)
function mediaManagement.isConfigured()
    return currentConfig.configured
end

-- Get current configuration (for external use)
function mediaManagement.getConfig()
    return currentConfig
end

return mediaManagement
